"""Unit tests for authentication: token issuing and route protection."""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.application.auth.service import hash_password
from src.infrastructure.database.engine import get_db
from src.infrastructure.database.models import User


def _user(username="alice", password="s3cret", is_active=True):
    return User(
        id="u1",
        username=username,
        hashed_password=hash_password(password),
        is_active=is_active,
    )


@pytest.fixture
def db():
    return MagicMock()


@pytest.fixture
def client(db):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


def test_login_returns_access_token_for_valid_credentials(client, db, mocker):
    mocker.patch(
        "src.api.routers.auth.repositories.get_user_by_username",
        return_value=_user(),
    )

    resp = client.post(
        "/api/v1/auth/token", data={"username": "alice", "password": "s3cret"}
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_rejects_wrong_password(client, mocker):
    mocker.patch(
        "src.api.routers.auth.repositories.get_user_by_username",
        return_value=_user(),
    )

    resp = client.post(
        "/api/v1/auth/token", data={"username": "alice", "password": "wrong"}
    )

    assert resp.status_code == 401


def test_login_rejects_unknown_user(client, mocker):
    mocker.patch(
        "src.api.routers.auth.repositories.get_user_by_username", return_value=None
    )

    resp = client.post(
        "/api/v1/auth/token", data={"username": "ghost", "password": "s3cret"}
    )

    assert resp.status_code == 401


def test_login_rejects_inactive_user(client, mocker):
    mocker.patch(
        "src.api.routers.auth.repositories.get_user_by_username",
        return_value=_user(is_active=False),
    )

    resp = client.post(
        "/api/v1/auth/token", data={"username": "alice", "password": "s3cret"}
    )

    assert resp.status_code == 401


def test_protected_endpoint_requires_token(client):
    resp = client.get("/api/v1/quotes/BTCUSD/latest")
    assert resp.status_code == 401


def test_protected_endpoint_rejects_invalid_token(client):
    resp = client.get(
        "/api/v1/quotes/BTCUSD/latest",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert resp.status_code == 401


def test_protected_endpoint_accepts_valid_token(client, mocker):
    mocker.patch(
        "src.api.routers.auth.repositories.get_user_by_username",
        return_value=_user(),
    )
    mocker.patch(
        "src.api.routers.quotes.repositories.find_latest_quote", return_value=None
    )

    login_resp = client.post(
        "/api/v1/auth/token", data={"username": "alice", "password": "s3cret"}
    )
    token = login_resp.json()["access_token"]

    resp = client.get(
        "/api/v1/quotes/BTCUSD/latest",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 404


def test_health_does_not_require_token(client):
    resp = client.get("/health")
    assert resp.status_code == 200

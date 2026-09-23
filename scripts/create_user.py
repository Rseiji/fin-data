"""Create a user for API authentication.

Usage:
    PYTHONPATH=. python scripts/create_user.py <username> <password>

The database URL and schema are read from the environment or .env through
src.config.settings.Settings.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.application.auth.service import hash_password
from src.infrastructure.database import repositories
from src.infrastructure.database.engine import SessionLocal


def main(username: str, password: str) -> None:
    db = SessionLocal()
    try:
        if repositories.get_user_by_username(db, username) is not None:
            print(f"User '{username}' already exists")
            return
        repositories.create_user(db, username, hash_password(password))
        print(f"User '{username}' created successfully")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scripts/create_user.py <username> <password>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])

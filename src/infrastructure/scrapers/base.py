"""Base utilities shared by all scrapers."""
import logging
from typing import Any, Dict

import requests

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; fin-data-bot/1.0; "
        "+https://github.com/Rseiji/fin-data)"
    )
}

DEFAULT_TIMEOUT = 15


def fetch_json(url: str, params: Dict[str, Any] | None = None) -> Any:
    """Perform a GET request and return parsed JSON."""
    resp = requests.get(
        url, params=params, headers=DEFAULT_HEADERS, timeout=DEFAULT_TIMEOUT
    )
    resp.raise_for_status()
    return resp.json()


def fetch_html(url: str, params: Dict[str, Any] | None = None) -> str:
    """Perform a GET request and return the response text."""
    resp = requests.get(
        url, params=params, headers=DEFAULT_HEADERS, timeout=DEFAULT_TIMEOUT
    )
    resp.raise_for_status()
    return resp.text

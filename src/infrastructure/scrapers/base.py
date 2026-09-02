"""Base utilities shared by all scrapers."""
import logging
import time
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
    started_at = time.monotonic()
    resp = requests.get(
        url, params=params, headers=DEFAULT_HEADERS, timeout=DEFAULT_TIMEOUT
    )
    elapsed = time.monotonic() - started_at
    logger.debug("HTTP GET %s status=%s duration=%.2fs", resp.url, resp.status_code, elapsed)
    if resp.status_code == 429:
        logger.warning("HTTP rate limit reached for %s after %.2fs", resp.url, elapsed)
    resp.raise_for_status()
    return resp.json()


def fetch_html(url: str, params: Dict[str, Any] | None = None) -> str:
    """Perform a GET request and return the response text."""
    started_at = time.monotonic()
    resp = requests.get(
        url, params=params, headers=DEFAULT_HEADERS, timeout=DEFAULT_TIMEOUT
    )
    elapsed = time.monotonic() - started_at
    logger.debug("HTTP GET %s status=%s duration=%.2fs", resp.url, resp.status_code, elapsed)
    if resp.status_code == 429:
        logger.warning("HTTP rate limit reached for %s after %.2fs", resp.url, elapsed)
    resp.raise_for_status()
    return resp.text

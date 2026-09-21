"""Small client helpers for consuming paginated fin-data API responses."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

import requests


DEFAULT_TIMEOUT = 30
DEFAULT_PAGE_SIZE = 100


def _fetch_all_pages(
    request_page: Callable[[int, int], Dict[str, Any]],
    *,
    page_size: int,
) -> List[Dict[str, Any]]:
    if page_size < 1:
        raise ValueError("page_size must be greater than zero")

    items: List[Dict[str, Any]] = []
    offset = 0
    while True:
        page = request_page(page_size, offset)
        page_items = page.get("items")
        if not isinstance(page_items, list):
            raise ValueError("API response does not contain a valid items list")

        items.extend(page_items)
        if not page.get("has_next", False):
            return items

        next_offset = page.get("next_offset")
        if not isinstance(next_offset, int) or next_offset <= offset:
            raise ValueError("API response contains an invalid next_offset")
        offset = next_offset


def _build_page_request(
    api_url: str,
    path: str,
    *,
    params: Dict[str, Any],
    timeout: float,
) -> Callable[[int, int], Dict[str, Any]]:
    url = f"{api_url.rstrip('/')}/{path.lstrip('/')}"

    def request_page(page_size: int, offset: int) -> Dict[str, Any]:
        response = requests.get(
            url,
            params={**params, "limit": page_size, "offset": offset},
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()

    return request_page


def fetch_all_quote_history(
    symbol: str,
    api_url: str = "http://localhost:8000/api/v1",
    *,
    start: Optional[str] = None,
    end: Optional[str] = None,
    page_size: int = DEFAULT_PAGE_SIZE,
    timeout: float = DEFAULT_TIMEOUT,
) -> List[Dict[str, Any]]:
    """Fetch every historical quote for a symbol across all API pages."""
    params = {"start": start, "end": end}
    params = {key: value for key, value in params.items() if value is not None}
    request_page = _build_page_request(
        api_url,
        f"/quotes/{symbol.strip().upper()}/history",
        params=params,
        timeout=timeout,
    )
    return _fetch_all_pages(request_page, page_size=page_size)


def fetch_all_daily_summaries(
    symbol: str,
    api_url: str = "http://localhost:8000/api/v1",
    *,
    start: Optional[str] = None,
    end: Optional[str] = None,
    page_size: int = DEFAULT_PAGE_SIZE,
    timeout: float = DEFAULT_TIMEOUT,
) -> List[Dict[str, Any]]:
    """Fetch every daily summary for a symbol across all API pages."""
    params = {"start": start, "end": end}
    params = {key: value for key, value in params.items() if value is not None}
    request_page = _build_page_request(
        api_url,
        f"/quotes/{symbol.strip().upper()}/summary",
        params=params,
        timeout=timeout,
    )
    return _fetch_all_pages(request_page, page_size=page_size)
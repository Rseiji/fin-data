from unittest.mock import Mock

import pytest

from src.api.client import fetch_all_daily_summaries, fetch_all_quote_history


def _response(items, *, has_next, next_offset=None):
    response = Mock()
    response.json.return_value = {
        "items": items,
        "has_next": has_next,
        "next_offset": next_offset,
    }
    return response


def test_fetch_all_quote_history_iterates_until_last_page(mocker):
    get = mocker.patch(
        "src.api.client.requests.get",
        side_effect=[
            _response([{"id": "q1"}], has_next=True, next_offset=2),
            _response([{"id": "q2"}], has_next=False),
        ],
    )

    result = fetch_all_quote_history(" btcusd ", page_size=2)

    assert result == [{"id": "q1"}, {"id": "q2"}]
    assert get.call_args_list[0].kwargs["params"] == {
        "limit": 2,
        "offset": 0,
    }
    assert get.call_args_list[1].kwargs["params"] == {
        "limit": 2,
        "offset": 2,
    }


def test_fetch_all_daily_summaries_forwards_date_filters(mocker):
    get = mocker.patch(
        "src.api.client.requests.get",
        return_value=_response([], has_next=False),
    )

    result = fetch_all_daily_summaries(
        "PETR4",
        api_url="http://api.example/api/v1",
        start="2024-01-01T00:00:00Z",
        end="2024-01-31T23:59:59Z",
    )

    assert result == []
    assert get.call_args.args[0] == "http://api.example/api/v1/quotes/PETR4/summary"
    assert get.call_args.kwargs["params"] == {
        "start": "2024-01-01T00:00:00Z",
        "end": "2024-01-31T23:59:59Z",
        "limit": 100,
        "offset": 0,
    }


def test_fetch_all_pages_rejects_invalid_next_offset(mocker):
    mocker.patch(
        "src.api.client.requests.get",
        return_value=_response([{"id": "q1"}], has_next=True, next_offset=0),
    )

    with pytest.raises(ValueError, match="next_offset"):
        fetch_all_quote_history("BTCUSD")
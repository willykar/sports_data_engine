import pytest
import requests

from src.extract import fetch_matches, URL
from unittest.mock import Mock, patch


PAYLOAD = {
    "matches": [
        {"id": 1001, "utcDate": "2026-10-10T14:00:00Z", "status": "FINISHED"},
        {"id": 1002, "utcDate": "2026-10-10T16:30:00Z", "status": "TIMED"},
    ]
}


def _response(payload=None, raises=None):
    response = Mock()
    response.json.return_value = payload if payload is not None else PAYLOAD
    response.raise_for_status = Mock(side_effect=raises)
    return response


def test_fetch_matches_returns_the_parsed_payload():
    with patch("src.extract.load_dotenv"), \
         patch("src.extract.getenv", return_value="token"), \
         patch("src.extract.requests.get", return_value=_response()):

        result = fetch_matches()

    assert result == PAYLOAD
    assert len(result["matches"]) == 2


def test_fetch_matches_sends_the_api_token_as_a_header():
    with patch("src.extract.load_dotenv"), \
         patch("src.extract.getenv", return_value="secret-token"), \
         patch("src.extract.requests.get", return_value=_response()) as get:

        fetch_matches()

    assert get.call_args.args[0] == URL
    assert get.call_args.kwargs["headers"] == {"X-Auth-Token": "secret-token"}


def test_fetch_matches_sends_no_date_params_when_unwindowed():
    with patch("src.extract.load_dotenv"), \
         patch("src.extract.getenv", return_value="token"), \
         patch("src.extract.requests.get", return_value=_response()) as get:

        fetch_matches()

    # The whole competition, not a window: the API must not receive a range.
    assert get.call_args.kwargs["params"] is None


def test_fetch_matches_sends_both_dates_when_windowed():
    with patch("src.extract.load_dotenv"), \
         patch("src.extract.getenv", return_value="token"), \
         patch("src.extract.requests.get", return_value=_response()) as get:

        fetch_matches(date_from="2026-10-09", date_to="2026-10-11")

    assert get.call_args.kwargs["params"] == {
        "dateFrom": "2026-10-09",
        "dateTo": "2026-10-11",
    }


@pytest.mark.parametrize(
    "date_from, date_to",
    [
        ("2026-10-09", None),
        (None, "2026-10-11"),
    ],
)
def test_fetch_matches_rejects_one_date_without_the_other(date_from, date_to):
    # football-data.org rejects a half-open range, so fail here with a clear
    # message rather than on a 400 from the API.
    with pytest.raises(ValueError, match="together"):
        fetch_matches(date_from=date_from, date_to=date_to)


def test_fetch_matches_requires_the_api_key():
    with patch("src.extract.load_dotenv"), \
         patch("src.extract.getenv", return_value=None), \
         patch("src.extract.requests.get") as get:

        with pytest.raises(ValueError, match="football_data_api_key"):
            fetch_matches()

    # No request should be attempted without a token.
    get.assert_not_called()


def test_fetch_matches_raises_on_an_http_error():
    error = requests.HTTPError("429 Too Many Requests")

    with patch("src.extract.load_dotenv"), \
         patch("src.extract.getenv", return_value="token"), \
         patch("src.extract.requests.get", return_value=_response(raises=error)):

        with pytest.raises(requests.HTTPError):
            fetch_matches()


def test_fetch_matches_writes_nothing():
    # The DAG's branch calls this on every run just to count fixtures. It must
    # never touch data/raw/, or a no-games run would still rewrite the season.
    with patch("src.extract.load_dotenv"), \
         patch("src.extract.getenv", return_value="token"), \
         patch("src.extract.requests.get", return_value=_response()), \
         patch("src.extract.dump") as dump:

        fetch_matches(date_from="2026-10-09", date_to="2026-10-11")

    dump.assert_not_called()

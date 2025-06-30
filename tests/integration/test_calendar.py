from __future__ import annotations

import json
import re
from unittest.mock import MagicMock

import httpretty
from urllib import parse
import pytest

from schedule_app.services.google_client import GoogleClient


@pytest.fixture()
def client():
    return GoogleClient(credentials=MagicMock())


def test_fetch_calendar_events_request_url(client):
    start = "2025-01-01T00:00:00Z"
    end = "2025-01-02T00:00:00Z"

    url_re = re.compile(
        r"https://www.googleapis.com/calendar/v3/calendars/primary/events.*"
    )
    query = parse.urlencode(
        {
            "timeMin": start,
            "timeMax": end,
            "singleEvents": "true",
        }
    )
    expected_url = (
        "https://www.googleapis.com/calendar/v3/calendars/primary/events?" + query
    )

    httpretty.enable()
    httpretty.register_uri(
        httpretty.GET,
        uri=url_re,
        body=json.dumps({"items": []}),
        status=200,
    )
    try:
        client.fetch_calendar_events(time_min=start, time_max=end)
        assert httpretty.last_request().url == expected_url
    finally:
        httpretty.disable()
        httpretty.reset()

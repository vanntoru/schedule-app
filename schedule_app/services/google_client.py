"""Google API client stub for future implementation.

This module defines a minimal :class:`GoogleClient` with placeholders for
accessing Google Calendar and Google Sheets. Actual API integration will be
added later.
"""

from __future__ import annotations

from typing import Any
from urllib import parse, request
import json


# OAuth scopes required for accessing Google APIs

SCOPES = [
    "openid",
    "profile",
    "email",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]


class GoogleClient:
    """Lightweight wrapper around Google service clients."""

    def __init__(self, credentials: Any) -> None:
        """Initialize the client with OAuth2 *credentials*."""
        self.credentials = credentials

    def calendar_service(self) -> Any:
        """Return a Google Calendar service client (stub)."""
        raise NotImplementedError

    def sheets_service(self) -> Any:
        """Return a Google Sheets service client (stub)."""
        raise NotImplementedError

    def fetch_calendar_events(self, *, time_min: str, time_max: str) -> list[dict]:
        """Fetch calendar events within the given time range.

        Parameters
        ----------
        time_min: str
            ISO 8601 start datetime in UTC.
        time_max: str
            ISO 8601 end datetime in UTC.
        """

        query = parse.urlencode(
            {
                "timeMin": time_min,
                "timeMax": time_max,
                "singleEvents": "true",
            }
        )
        url = (
            "https://www.googleapis.com/calendar/v3/calendars/primary/events?" + query
        )
        req = request.Request(url)
        with request.urlopen(req) as resp:  # pragma: no cover - network stubbed
            data = json.loads(resp.read().decode())
        return data.get("items", [])

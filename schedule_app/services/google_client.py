"""Google API client stub for future implementation.

This module defines a minimal :class:`GoogleClient` with placeholders for
accessing Google Calendar and Google Sheets. Actual API integration will be
added later.
"""

from __future__ import annotations

from typing import Any
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen
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

    def __init__(self, credentials: Any | None = None) -> None:
        """Initialize the client with optional OAuth2 *credentials*."""
        self.credentials = credentials

    def calendar_service(self) -> Any:
        """Return a Google Calendar service client (stub)."""
        raise NotImplementedError

    def sheets_service(self) -> Any:
        """Return a Google Sheets service client (stub)."""
        raise NotImplementedError

    def fetch_calendar_events(
        self, *, start_utc: datetime, end_utc: datetime, calendar_id: str = "primary"
    ) -> list[dict]:
        """Fetch calendar events between *start_utc* and *end_utc*.

        This lightweight helper performs a direct HTTP request to the Google
        Calendar REST API. It is intentionally simple so that integration tests
        can mock the outgoing request without requiring the full Google client
        library.
        """

        params = {
            "timeMin": start_utc.astimezone(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "timeMax": end_utc.astimezone(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "singleEvents": "true",
            "orderBy": "startTime",
        }

        url = (
            f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events?"
            + urlencode(params)
        )

        req = Request(url)
        if self.credentials is not None:
            req.add_header("Authorization", f"Bearer {self.credentials}")

        with urlopen(req) as resp:
            payload = json.load(resp)

        return list(payload.get("items", []))

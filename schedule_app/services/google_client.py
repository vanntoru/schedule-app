"""Google API client stub for future implementation.

This module defines a minimal :class:`GoogleClient` with placeholders for
accessing Google Calendar and Google Sheets. Actual API integration will be
added later.  A convenience :meth:`GoogleClient.list_events` computes the
UTC range for a given day before calling :meth:`fetch_calendar_events`.
"""

from __future__ import annotations

from typing import Any
from urllib import parse, request
from urllib.error import HTTPError
import json
from datetime import datetime, timedelta, timezone

from schedule_app.models import Event
from schedule_app.exceptions import APIError


class GoogleAPIUnauthorized(APIError):
    """Raised when Google API request is unauthorized."""


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

    def __init__(self, credentials: Any | None) -> None:
        """Initialize the client with OAuth2 *credentials*."""
        self.credentials = credentials

    def calendar_service(self) -> Any:
        """Return a Google Calendar service client (stub)."""
        raise NotImplementedError

    def sheets_service(self) -> Any:
        """Return a Google Sheets service client (stub)."""
        raise NotImplementedError

    def _get_token(self) -> str:
        """Return OAuth access token from stored credentials."""

        creds = self.credentials
        if hasattr(creds, "token") and getattr(creds, "token"):
            return getattr(creds, "token")
        if isinstance(creds, dict) and creds.get("access_token"):
            return creds["access_token"]
        raise APIError("missing_token")

    def fetch_calendar_events(self, *, time_min: str, time_max: str) -> list[dict]:
        """Fetch calendar events within the given time range.

        Parameters
        ----------
        time_min: str
            ISO 8601 start datetime in UTC.
        time_max: str
            ISO 8601 end datetime in UTC.
        """

        token = self._get_token()

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
        req = request.Request(url, headers={"Authorization": f"Bearer {token}"})
        try:
            with request.urlopen(req) as resp:  # pragma: no cover - network stubbed
                data = json.loads(resp.read().decode())
        except HTTPError as e:  # pragma: no cover - network stubbed
            if e.code in (401, 403):
                raise GoogleAPIUnauthorized("unauthorized") from e
            raise
        return data.get("items", [])

    def _parse_dt(self, value: str) -> datetime:
        """Return a timezone-aware UTC datetime from ISO string."""

        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt

    def _to_event(self, data: dict) -> Event:
        """Convert a Google Calendar event dictionary to an :class:`Event`."""

        start_info = data.get("start", {})
        end_info = data.get("end", {})
        start_raw = start_info.get("dateTime") or start_info.get("date")
        end_raw = end_info.get("dateTime") or end_info.get("date")
        start_dt = self._parse_dt(start_raw) if start_raw else datetime.min.replace(tzinfo=timezone.utc)
        end_dt = self._parse_dt(end_raw) if end_raw else start_dt
        all_day = "date" in start_info or "date" in end_info
        return Event(
            id=data.get("id", ""),
            start_utc=start_dt,
            end_utc=end_dt,
            title=data.get("summary", ""),
            all_day=all_day,
        )

    def list_events(self, *, date: datetime) -> list[Event]:
        """Return events for the 24-hour period starting at UTC midnight.

        Parameters
        ----------
        date : datetime
            Target day. Naive values are treated as UTC.
        """

        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        else:
            date = date.astimezone(timezone.utc)

        start = datetime.combine(date.date(), datetime.min.time(), tzinfo=timezone.utc)
        end = start + timedelta(days=1)

        items = self.fetch_calendar_events(
            time_min=start.isoformat().replace("+00:00", "Z"),
            time_max=end.isoformat().replace("+00:00", "Z"),
        )

        return [self._to_event(item) for item in items]


__all__ = [
    "GoogleClient",
    "APIError",
    "GoogleAPIUnauthorized",
    "SCOPES",
]

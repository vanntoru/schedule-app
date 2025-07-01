"""Google API client stub for future implementation.

This module defines a minimal :class:`GoogleClient` with placeholders for
accessing Google Calendar and Google Sheets. Actual API integration will be
added later.  A convenience :meth:`GoogleClient.list_events` computes the
UTC range for a given day before calling :meth:`fetch_calendar_events`.
"""

from __future__ import annotations

from typing import Any
from urllib import parse, request
import json
from datetime import datetime, timedelta, timezone

from schedule_app.models import Event


# OAuth scopes required for accessing Google APIs

SCOPES = [
    "openid",
    "profile",
    "email",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]


class GoogleClient:
    """Lightweight wrapper around Google service clients.

    When *credentials* is falsy the instance operates in stub mode and
    :meth:`list_events` returns two predefined :class:`~schedule_app.models.Event`
    objects.
    """

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

        # Stub mode: return dummy events when credentials are absent
        if not self.credentials:
            return [
                Event(
                    id="dummy-1",
                    start_utc=start + timedelta(hours=9),
                    end_utc=start + timedelta(hours=10),
                    title="Dummy Event 1",
                ),
                Event(
                    id="dummy-2",
                    start_utc=start + timedelta(hours=13),
                    end_utc=start + timedelta(hours=14),
                    title="Dummy Event 2",
                ),
            ]

        raw = self.fetch_calendar_events(
            time_min=start.isoformat().replace("+00:00", "Z"),
            time_max=end.isoformat().replace("+00:00", "Z"),
        )

        events: list[Event] = []
        for item in raw:
            start_str = item.get("start", {}).get("dateTime")
            end_str = item.get("end", {}).get("dateTime")
            if not start_str or not end_str:
                continue
            start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00")).astimezone(
                timezone.utc
            )
            end_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00")).astimezone(
                timezone.utc
            )
            events.append(
                Event(
                    id=item.get("id", ""),
                    start_utc=start_dt,
                    end_utc=end_dt,
                    title=item.get("summary", ""),
                )
            )
        return events

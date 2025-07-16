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
import os

try:
    import schedule_app.config as config_module
except Exception:  # pragma: no cover - missing env vars in some test runs
    config_module = None
import json
from datetime import datetime, time, timedelta, timezone
import pytz

from schedule_app.models import Event, Block
from schedule_app.exceptions import APIError
from schedule_app.utils.validation import _parse_dt
from schedule_app.errors import InvalidBlockRow
from schedule_app.services.rounding import quantize
import uuid
import time


class GoogleAPIUnauthorized(APIError):
    """Raised when Google API calls are unauthorized."""

    def __init__(self, description: str = "unauthorized") -> None:
        super().__init__(description)


# OAuth scopes required for accessing Google APIs

# Scope for read-only access to Google Sheets
SPREADSHEETS_READONLY_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/calendar.readonly",
    SPREADSHEETS_READONLY_SCOPE,
]

# ---------------------------------------------------------------------------
# Sheet helpers
# ---------------------------------------------------------------------------


def _to_block(data: dict[str, str]) -> Block:
    """Convert a sheet row ``data`` to a :class:`Block`."""

    start_raw = (data.get("start_utc") or "").strip()
    end_raw = (data.get("end_utc") or "").strip()
    if not start_raw or not end_raw:
        raise InvalidBlockRow()

    try:
        start_dt = _parse_dt(start_raw)
        end_dt = _parse_dt(end_raw)
    except ValueError as exc:  # pragma: no cover - invalid data
        raise InvalidBlockRow() from exc

    if start_dt is None or end_dt is None or start_dt >= end_dt:
        raise InvalidBlockRow()

    start_dt = quantize(start_dt, up=False)
    end_dt = quantize(end_dt, up=True)

    title = (data.get("title") or "").strip() or None

    return Block(id=uuid.uuid4().hex, start_utc=start_dt, end_utc=end_dt, title=title)


def fetch_blocks_from_sheet(spreadsheet_id: str, cell_range: str) -> list[Block]:
    """Return blocks fetched from Google Sheets."""

    global _BLOCK_CACHE

    now = time.time()
    if _BLOCK_CACHE is not None:
        blocks, expiry = _BLOCK_CACHE
        if now < expiry:
            return blocks

    encoded_range = parse.quote(cell_range, safe="")
    url = (
        "https://sheets.googleapis.com/v4/spreadsheets/"
        f"{spreadsheet_id}/values/{encoded_range}"
    )

    req = request.Request(url)
    try:
        with request.urlopen(req) as resp:  # pragma: no cover - network stubbed
            data = json.loads(resp.read().decode())
    except HTTPError as e:  # pragma: no cover - network stubbed
        if e.code in (401, 403):
            raise GoogleAPIUnauthorized() from e
        raise

    rows = data.get("values", [])
    blocks: list[Block] = []
    if rows:
        headers = [str(h).strip().lower() for h in rows[0]]
        for row in rows[1:]:
            item = {headers[i]: row[i] for i in range(min(len(headers), len(row)))}
            blocks.append(_to_block(item))

    cache_sec = 300
    if config_module is not None:
        cache_sec = config_module.cfg.SHEETS_CACHE_SEC
    _BLOCK_CACHE = (blocks, now + cache_sec)
    return blocks


# blocks sheet cache: list of Block objects and expiry timestamp
_BLOCK_CACHE: tuple[list[Block], float] | None = None


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
        url = "https://www.googleapis.com/calendar/v3/calendars/primary/events?" + query
        req = request.Request(url, headers={"Authorization": f"Bearer {token}"})
        try:
            with request.urlopen(req) as resp:  # pragma: no cover - network stubbed
                data = json.loads(resp.read().decode())
        except HTTPError as e:  # pragma: no cover - network stubbed
            if e.code in (401, 403):
                raise GoogleAPIUnauthorized() from e
            raise
        return data.get("items", [])

    def _to_event(self, data: dict) -> Event:
        """Convert a Google Calendar event dictionary to an :class:`Event`."""

        start_info = data.get("start", {})
        end_info = data.get("end", {})
        start_raw = start_info.get("dateTime") or start_info.get("date")
        end_raw = end_info.get("dateTime") or end_info.get("date")
        start_dt = _parse_dt(start_raw) or datetime.min.replace(tzinfo=timezone.utc)
        end_dt = _parse_dt(end_raw) or start_dt
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
            Target day in JST. Naive values are treated as JST.
        """

        # -------------------------------
        # UI は JST 日付を渡してくる前提。
        # JST 00:00 を UTC に変換して 24 h 範囲を取得する。
        # -------------------------------
        if config_module is not None:
            tz_name = config_module.cfg.TIMEZONE
        else:
            tz_name = os.getenv("TIMEZONE", "Asia/Tokyo")

        tz = pytz.timezone(tz_name)

        if date.tzinfo is None:
            # naïve → JST
            local_start = tz.localize(datetime.combine(date.date(), time.min))
        else:
            # すでに aware なら JST に合わせる
            local_start = date.astimezone(tz).replace(
                hour=0, minute=0, second=0, microsecond=0
            )

        start = local_start.astimezone(timezone.utc)
        end = start + timedelta(days=1)

        items = self.fetch_calendar_events(
            time_min=start.isoformat().replace("+00:00", "Z"),
            time_max=end.isoformat().replace("+00:00", "Z"),
        )

        target_day = local_start.date()
        events: list[Event] = []
        for item in items:
            ev = self._to_event(item)

            if ev.all_day:
                start_info = item.get("start", {})
                end_info = item.get("end", {})
                start_date_raw = start_info.get("date")
                end_date_raw = end_info.get("date")
                start_date = (
                    datetime.fromisoformat(start_date_raw).date()
                    if start_date_raw
                    else target_day
                )
                end_date = (
                    datetime.fromisoformat(end_date_raw).date()
                    if end_date_raw
                    else None
                )
                include = False
                if end_date is not None:
                    if start_date <= target_day < end_date:
                        include = True
                else:
                    if start_date == target_day:
                        include = True
                if include:
                    events.append(ev)
            else:
                events.append(ev)

        return events


__all__ = [
    "GoogleClient",
    "GoogleAPIUnauthorized",
    "APIError",
    "SCOPES",
    "fetch_blocks_from_sheet",
]

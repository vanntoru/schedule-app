from __future__ import annotations

from datetime import datetime, timezone
import pytz
from http import HTTPStatus
from dataclasses import asdict
from zoneinfo import ZoneInfo

from schedule_app.models import Event
from schedule_app.config import cfg

from flask import Blueprint, request, session, jsonify

from schedule_app.services.google_client import (
    GoogleClient,
    APIError,
    GoogleAPIUnauthorized,
)


bp = Blueprint("calendar_bp", __name__)
calendar_bp = bp

# Global in-memory cache for Google Calendar events
EVENTS: dict[str, Event] = {}


def to_utc(info: dict) -> datetime:
    """Return a UTC datetime from a Google Calendar event time dict."""
    raw = info.get("dateTime") or info.get("date")
    if not raw:
        return datetime.min.replace(tzinfo=timezone.utc)
    dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    tzid = info.get("timeZone")
    if tzid:
        tz = ZoneInfo(tzid)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz)
        else:
            dt = dt.astimezone(tz)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _problem(status: int, code: str, detail: str):
    """Return a JSON Problem response."""
    try:
        title = HTTPStatus(status).phrase
    except Exception:
        title = "Error"
    response = jsonify(
        {
            "type": f"https://schedule.app/errors/{code}",
            "title": title,
            "status": status,
            "detail": detail,
            "instance": request.path,
        }
    )
    response.status_code = status
    response.mimetype = "application/problem+json"
    return response


def _event_to_dict(ev: Event) -> dict:
    d = asdict(ev)
    d["start_utc"] = ev.start_utc.isoformat().replace("+00:00", "Z")
    d["end_utc"] = ev.end_utc.isoformat().replace("+00:00", "Z")
    return d


@bp.get("/api/calendar")
def get_calendar():
    """Return events for the given day.

    The required ``date`` query parameter accepts an ISO 8601 datetime or
    ``YYYY-MM-DD``. Naive values are interpreted using ``cfg.TIMEZONE`` before
    being normalized to UTC.
    """
    date_str = request.args.get("date")
    if not date_str:
        return _problem(400, "bad-request", "missing date")

    try:
        date_obj = datetime.fromisoformat(date_str)
    except ValueError:
        return _problem(400, "bad-request", "invalid date")

    if date_obj.tzinfo is None:
        date_obj = pytz.timezone(cfg.TIMEZONE).localize(date_obj)

    creds = session.get("credentials")
    if not creds:
        return _problem(401, "unauthorized", "missing credentials")

    client = GoogleClient(creds)
    try:
        google_events = client.list_events(date=date_obj)
    except GoogleAPIUnauthorized as e:
        return _problem(401, "unauthorized", str(e))
    except APIError as e:
        return _problem(502, "bad-gateway", f"google_api: {e}")

    day_events: list[Event] = []
    for ev in google_events:
        EVENTS[ev.id] = ev
        day_events.append(ev)

    return jsonify([_event_to_dict(e) for e in day_events]), 200


__all__ = ["calendar_bp"]

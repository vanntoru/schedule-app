"""Calendar API blueprint."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Any

from flask import Blueprint, jsonify, request

from schedule_app.models import Event
from schedule_app.services.google_client import GoogleClient

bp = Blueprint("calendar_api", __name__, url_prefix="/api")

# Singleton stub client. In real deployments this would hold credentials.
gc = GoogleClient()


def _fetch_events(date: datetime) -> list[Event]:
    start = date.replace(tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    items = gc.fetch_calendar_events(start_utc=start, end_utc=end)
    events: list[Event] = []
    for it in items:
        start_raw = it.get("start", {}).get("dateTime") or it.get("start", {}).get("date")
        end_raw = it.get("end", {}).get("dateTime") or it.get("end", {}).get("date")
        if not start_raw or not end_raw:
            continue
        all_day = "date" in it.get("start", {})
        start_dt = datetime.fromisoformat(start_raw.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end_raw.replace("Z", "+00:00"))
        events.append(
            Event(
                id=it["id"],
                start_utc=start_dt,
                end_utc=end_dt,
                title=it.get("summary", ""),
                all_day=all_day,
            )
        )
    return events


@bp.get("/calendar")
def get_calendar() -> Any:
    """Return events for the given ISO date."""
    date_str = request.args.get("date")
    if not date_str:
        return jsonify([]), 400

    try:
        date = datetime.fromisoformat(date_str)
    except ValueError:
        return jsonify([]), 400

    events = _fetch_events(date)
    payload = []
    for evt in events:
        data = asdict(evt)
        data["start_utc"] = evt.start_utc.isoformat().replace("+00:00", "Z")
        data["end_utc"] = evt.end_utc.isoformat().replace("+00:00", "Z")
        payload.append(data)
    return jsonify(payload)

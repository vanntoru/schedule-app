from __future__ import annotations

from datetime import datetime
from http import HTTPStatus
from dataclasses import asdict

from schedule_app.models import Event

from flask import Blueprint, request, session, jsonify

from schedule_app.services.google_client import GoogleClient, APIError


bp = Blueprint("calendar_bp", __name__)
calendar_bp = bp


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
    date_str = request.args.get("date")
    if not date_str:
        return _problem(400, "bad-request", "missing date")

    try:
        date_obj = datetime.fromisoformat(date_str)
    except ValueError:
        return _problem(400, "bad-request", "invalid date")

    creds = session.get("credentials")
    if not creds:
        return _problem(401, "unauthorized", "missing credentials")

    client = GoogleClient(creds)
    try:
        events = client.list_events(date=date_obj)
    except APIError as e:
        return _problem(502, "bad-gateway", f"google_api: {e}")

    return jsonify([_event_to_dict(e) for e in events]), 200


__all__ = ["calendar_bp"]

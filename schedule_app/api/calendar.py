from __future__ import annotations

from datetime import datetime

from flask import Blueprint, request, session, abort, jsonify

from schedule_app.services.google_client import GoogleClient, APIError


bp = Blueprint("calendar_bp", __name__)
calendar_bp = bp


@bp.get("/api/calendar")
def get_calendar():
    date_str = request.args.get("date")
    if not date_str:
        abort(400, "missing date")

    try:
        date_obj = datetime.fromisoformat(date_str)
    except ValueError:
        abort(400, "invalid date")

    creds = session.get("credentials")
    if not creds:
        abort(401)

    client = GoogleClient(creds)
    try:
        events = client.list_events(date=date_obj)
    except APIError as e:
        abort(502, f"google_api: {e}")

    return jsonify([e.__dict__ for e in events]), 200


__all__ = ["calendar_bp"]

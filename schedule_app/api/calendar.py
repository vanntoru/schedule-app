from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta

from flask import Blueprint, abort, current_app, jsonify, request
from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError

from schedule_app.services.google_client import GoogleClient


bp_calendar = Blueprint("bp_calendar", __name__)


@bp_calendar.get("/api/calendar")
def get_calendar() -> tuple[list[dict], int] | tuple[dict, int]:
    date_str = request.args.get("date")
    if not date_str:
        abort(400, description="date parameter required")

    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        abort(400, description="invalid date format")

    start_utc = datetime.combine(date_obj, datetime.min.time())
    end_utc = start_utc + timedelta(days=1)

    client: GoogleClient = current_app.extensions["gclient"]

    try:
        events = client.list_events(start_utc=start_utc, end_utc=end_utc)
    except RefreshError:
        abort(401)
    except HttpError as exc:
        status = getattr(exc, "status_code", None)
        if status is None:
            status = getattr(getattr(exc, "resp", None), "status", None)
        if status == 403:
            abort(403)
        if status == 401:
            abort(401)
        raise

    return jsonify([asdict(ev) for ev in events]), 200


__all__ = ["bp_calendar"]

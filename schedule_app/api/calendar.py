from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request

bp = Blueprint("calendar", __name__)


@bp.get("/api/calendar")
def get_calendar():  # pragma: no cover - simple logic
    date_str = request.args.get("date")
    if not date_str:
        return "", 400
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return "", 400

    gclient = current_app.extensions.get("gclient")
    if gclient is None:  # pragma: no cover - not set in tests
        return "", 500

    try:
        events = gclient.list_events(date=date)
    except Exception:  # pragma: no cover - unauthorized
        return "", 401

    return jsonify([asdict(e) for e in events])

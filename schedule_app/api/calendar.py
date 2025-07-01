from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone

from flask import Blueprint, abort, current_app, jsonify, request
from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError

from schedule_app.services.google_client import GoogleClient, APIError


bp = Blueprint("calendar_bp", __name__)
calendar_bp = bp


@bp.get("/api/calendar")
def get_calendar() -> tuple[list[dict], int] | tuple[dict, int]:
    date_str = request.args.get("date")
    if not date_str:
        abort(400, description="date parameter required")

    # If '+' was decoded to ' ', restore it
    if " " in date_str and "+" not in date_str:
        date_str = date_str.replace(" ", "+")

    if date_str.endswith("Z"):
        date_str = date_str[:-1] + "+00:00"

    try:
        date_obj = datetime.fromisoformat(date_str)
    except ValueError:
        abort(400, description="invalid date format")

    if date_obj.tzinfo is None:
        date_obj = date_obj.replace(tzinfo=timezone.utc)
    else:
        date_obj = date_obj.astimezone(timezone.utc)

    client: GoogleClient = current_app.extensions["gclient"]

    try:
        events = client.list_events(date=date_obj)
    except APIError as exc:
        abort(502, description=str(exc))
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

    def _serialize(ev):
        data = asdict(ev)
        data["start_utc"] = ev.start_utc.astimezone(timezone.utc).isoformat()
        data["end_utc"] = ev.end_utc.astimezone(timezone.utc).isoformat()
        return data

    return jsonify([_serialize(ev) for ev in events]), 200


__all__ = ["calendar_bp"]

from __future__ import annotations

from datetime import datetime
from dataclasses import asdict

from schedule_app.models import Event

from flask import Blueprint, request, session, abort, jsonify, Response

from http import HTTPStatus

from schedule_app.services.google_client import (
    GoogleAPITransient,
    GoogleAPIUnauthorized,
    GoogleClient,
)


bp = Blueprint("calendar_bp", __name__)
calendar_bp = bp


def _event_to_dict(ev: Event) -> dict:
    d = asdict(ev)
    d["start_utc"] = ev.start_utc.isoformat().replace("+00:00", "Z")
    d["end_utc"] = ev.end_utc.isoformat().replace("+00:00", "Z")
    return d


def _problem(
    *,
    status: int,
    detail: str,
    instance: str,
    title: str | None = None,
    type: str | None = None,
) -> Response:
    payload = {
        "type": type or f"https://schedule.app/errors/{HTTPStatus(status).phrase.lower().replace(' ', '-')}",
        "title": title or HTTPStatus(status).phrase,
        "status": status,
        "detail": detail,
        "instance": instance,
    }
    resp = jsonify(payload)
    resp.status_code = status
    resp.mimetype = "application/problem+json"
    return resp


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
    except GoogleAPIUnauthorized:
        return _problem(
            status=HTTPStatus.UNAUTHORIZED,
            detail="Google OAuth token expired or access revoked. Re-authenticate.",
            instance=request.path,
        )
    except GoogleAPITransient:
        return _problem(
            status=HTTPStatus.BAD_GATEWAY,
            title="Bad Gateway",
            type="https://schedule.app/errors/bad-gateway",
            detail="Temporary error while contacting Google API.",
            instance=request.path,
        )

    return jsonify([_event_to_dict(e) for e in events]), 200


__all__ = ["calendar_bp"]

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from flask import Blueprint, abort, jsonify, request
from werkzeug.exceptions import BadRequest

from schedule_app.models import Block, Event
from schedule_app.services import schedule
from schedule_app.api.tasks import _task_from_json
from schedule_app.api.blocks import _parse_iso8601

bp = Blueprint("schedule", __name__, url_prefix="/api/schedule")
schedule_bp = bp


def _event_from_json(data: dict[str, Any]) -> Event:
    try:
        start = _parse_iso8601(data.get("start_utc"), "start_utc")
        end = _parse_iso8601(data.get("end_utc"), "end_utc")
    except BadRequest as exc:  # reuse validation from blocks API
        resp = jsonify(exc.description)
        resp.status_code = 422
        resp.mimetype = "application/problem+json"
        abort(resp)
    return Event(
        id=data.get("id", ""),
        start_utc=start,
        end_utc=end,
        title=data.get("title", ""),
        all_day=bool(data.get("all_day", False)),
    )


def _block_from_json(data: dict[str, Any]) -> Block:
    try:
        start = _parse_iso8601(data.get("start_utc"), "start_utc")
        end = _parse_iso8601(data.get("end_utc"), "end_utc")
    except BadRequest as exc:
        resp = jsonify(exc.description)
        resp.status_code = 422
        resp.mimetype = "application/problem+json"
        abort(resp)
    return Block(id=data.get("id", ""), start_utc=start, end_utc=end)


@bp.post("/generate")
def generate_schedule():  # noqa: D401 - simple endpoint
    """Generate a schedule grid for the specified date."""
    date_str = request.args.get("date")
    if not date_str:
        abort(400, description="date parameter required")
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        abort(400, description="invalid date format")

    algo = request.args.get("algo", "greedy")
    if algo not in {"greedy", "compact"}:
        abort(400, description="invalid algo")

    payload = request.get_json(silent=True) or {}
    tasks = [_task_from_json(t) for t in payload.get("tasks", [])]
    events = [_event_from_json(e) for e in payload.get("events", [])]
    blocks = [_block_from_json(b) for b in payload.get("blocks", [])]

    grid = schedule.generate(
        date_utc=date_obj,
        tasks=tasks,
        events=events,
        blocks=blocks,
        algorithm=algo,  # type: ignore[arg-type]
    )
    return jsonify({"slots": grid}), 200


__all__ = ["bp", "schedule_bp"]

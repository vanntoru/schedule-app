from __future__ import annotations

from datetime import datetime
from typing import Literal

from flask import Blueprint, abort, current_app, jsonify, request

from schedule_app.services.schedule import generate as generate_schedule
from schedule_app.api.tasks import TASKS
from schedule_app.api.blocks import BLOCKS

bp = Blueprint("schedule", __name__, url_prefix="/api/schedule")


@bp.post("/generate")
def generate():
    date_str = request.args.get("date")
    if not date_str:
        abort(400, description="date parameter required")
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        abort(400, description="invalid date format")

    algo = request.args.get("algo", "greedy")
    if algo not in {"greedy", "compact"}:
        abort(400, description="invalid algo")

    client = current_app.extensions.get("gclient")
    events = []
    if client is not None:
        events = client.list_events(date=date_obj)

    tasks = list(TASKS.values())
    blocks = list(BLOCKS.values())

    grid = generate_schedule(
        date_utc=date_obj,
        tasks=tasks,
        events=events,
        blocks=blocks,
        algorithm=algo,  # type: ignore[arg-type]
    )
    return jsonify(grid), 200


schedule_bp = bp
__all__ = ["schedule_bp"]

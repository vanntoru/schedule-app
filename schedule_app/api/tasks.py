from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone

from flask import Blueprint, abort, jsonify, request
from werkzeug.exceptions import HTTPException

from schedule_app.models import Task


bp = Blueprint("tasks", __name__, url_prefix="/api/tasks")

# in-memory task storage
TASKS: dict[str, Task] = {}


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        abort(422, description="invalid datetime")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt


def _task_to_dict(task: Task) -> dict:
    data = asdict(task)
    if task.earliest_start_utc is not None:
        data["earliest_start_utc"] = task.earliest_start_utc.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    else:
        data["earliest_start_utc"] = None
    return data


@bp.errorhandler(HTTPException)
def handle_http_error(exc: HTTPException):
    payload = {"type": "about:blank", "title": exc.name, "status": exc.code}
    if exc.code == 422:
        payload["type"] = "https://schedule.app/errors/invalid-field"
    if exc.description:
        payload["detail"] = exc.description
    return jsonify(payload), exc.code


@bp.get("")
def list_tasks():
    return jsonify([_task_to_dict(t) for t in TASKS.values()])


@bp.post("")
def create_task():
    data = request.get_json() or {}
    try:
        duration_raw = int(data.get("duration_raw_min"))
        duration = int(data.get("duration_min"))
    except (TypeError, ValueError):
        abort(422, description="invalid duration")

    if duration_raw <= 0 or duration_raw % 5 != 0:
        abort(422, description="duration_raw_min must be positive multiple of 5")
    if duration % 10 != 0:
        abort(422, description="duration_min must be multiple of 10")

    task_id = data.get("id")
    if not task_id:
        abort(422, description="id required")

    task = Task(
        id=task_id,
        title=data.get("title", ""),
        category=data.get("category", ""),
        duration_min=duration,
        duration_raw_min=duration_raw,
        priority=data.get("priority", "A"),
        earliest_start_utc=_parse_dt(data.get("earliest_start_utc")),
    )
    TASKS[task_id] = task
    return jsonify(_task_to_dict(task)), 201


@bp.put("/<id>")
def update_task(id: str):
    if id not in TASKS:
        abort(404)

    data = request.get_json() or {}
    try:
        duration_raw = int(data.get("duration_raw_min"))
        duration = int(data.get("duration_min"))
    except (TypeError, ValueError):
        abort(422, description="invalid duration")

    if duration_raw <= 0 or duration_raw % 5 != 0:
        abort(422, description="duration_raw_min must be positive multiple of 5")
    if duration % 10 != 0:
        abort(422, description="duration_min must be multiple of 10")

    task = Task(
        id=id,
        title=data.get("title", ""),
        category=data.get("category", ""),
        duration_min=duration,
        duration_raw_min=duration_raw,
        priority=data.get("priority", "A"),
        earliest_start_utc=_parse_dt(data.get("earliest_start_utc")),
    )
    TASKS[id] = task
    return jsonify(_task_to_dict(task)), 200


@bp.delete("/<id>")
def delete_task(id: str):
    if id not in TASKS:
        abort(404)
    TASKS.pop(id)
    return "", 204


__all__ = ["bp"]

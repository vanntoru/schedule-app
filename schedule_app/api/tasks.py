from __future__ import annotations

from dataclasses import asdict
from datetime import timezone
from typing import Any
import uuid

from flask import Blueprint, abort, jsonify, request, url_for, session
from http import HTTPStatus

from schedule_app.models import Task
from schedule_app.exceptions import APIError
from schedule_app.services.sheets_tasks import (
    fetch_tasks_from_sheet,
    InvalidSheetRowError,
    invalidate_cache,
)
from schedule_app.utils.validation import _parse_dt, _validate_durations

bp = Blueprint("tasks", __name__, url_prefix="/api/tasks")

# プロセス内メモリに保持（サーバ再起動で消える）
TASKS: dict[str, Task] = {}

__all__ = ["bp", "TASKS"]

# ---------------------------------------------------------------------------
# 内部ユーティリティ
# ---------------------------------------------------------------------------


def _problem(status: int, code: str, detail: str) -> None:
    """Problem Details 仕様フォーマットで abort する。"""
    title = "Validation failed" if status == 422 else HTTPStatus(status).phrase
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
    abort(response)




def _task_from_json(data: dict[str, Any]) -> Task:
    required = {"title", "category", "duration_min", "duration_raw_min", "priority"}
    missing = required - data.keys()
    if missing:
        _problem(422, "invalid-field", f"Missing field(s): {', '.join(sorted(missing))}")

    try:
        _validate_durations(data["duration_min"], data["duration_raw_min"])
    except ValueError:
        _problem(
            422,
            "invalid-field",
            "Duration must be a positive multiple of 5 minutes.",
        )

    if data["priority"] not in {"A", "B"}:
        _problem(422, "invalid-field", "Priority must be 'A' or 'B'.")

    try:
        es_utc = _parse_dt(data.get("earliest_start_utc"))
    except ValueError:
        _problem(422, "invalid-field", "Invalid datetime format.")

    return Task(
        id=data["id"],
        title=data["title"],
        category=data["category"],
        duration_min=data["duration_min"],
        duration_raw_min=data["duration_raw_min"],
        priority=data["priority"],
        earliest_start_utc=es_utc,
    )


def _serialize(task: Task) -> dict[str, Any]:
    d = asdict(task)
    if d["earliest_start_utc"] is not None:
        d["earliest_start_utc"] = (
            d["earliest_start_utc"].astimezone(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z")
        )
    return d


def _load_sheet_tasks(*, force: bool = False) -> list[Task]:
    try:
        return fetch_tasks_from_sheet(session, force=force)
    except InvalidSheetRowError as exc:
        _problem(422, "invalid-field", str(exc))
    except RuntimeError as exc:
        if str(exc) == "missing credentials":
            _problem(401, "unauthorized", "missing credentials")
        _problem(422, "invalid-field", str(exc))
    except Exception as exc:  # pragma: no cover - network errors
        raise APIError(str(exc))


# ---------------------------------------------------------------------------
# ルーティング
# ---------------------------------------------------------------------------


@bp.get("")
def list_tasks():
    """すべての Task を返す."""
    return jsonify([_serialize(t) for t in TASKS.values()])


@bp.post("")
def create_task():
    data = request.get_json(force=True, silent=False)
    data["id"] = str(uuid.uuid4())
    task = _task_from_json(data)
    TASKS[task.id] = task

    resp = jsonify(_serialize(task))
    resp.status_code = 201
    resp.headers["Location"] = url_for(".get_task", id=task.id)
    return resp


@bp.get("/<id>")
def get_task(id: str):
    task = TASKS.get(id)
    if task is None:
        _problem(404, "not-found", "Task not found.")
    return jsonify(_serialize(task))


@bp.put("/<id>")
def update_task(id: str):
    if id not in TASKS:
        _problem(404, "not-found", "Task not found.")

    data = request.get_json(force=True, silent=False) or {}
    data["id"] = id  # ID の整合性を保証
    task = _task_from_json(data)
    TASKS[id] = task
    return jsonify(_serialize(task))


@bp.delete("/<id>")
def delete_task(id: str):
    if id not in TASKS:
        _problem(404, "not-found", "Task not found.")
    del TASKS[id]
    return ("", 204)


@bp.get("/import")
def import_tasks():
    """Fetch tasks from Google Sheets and return them."""
    tasks = _load_sheet_tasks()

    return jsonify([_serialize(t) for t in tasks])


@bp.post("/import")
def import_tasks_post():
    """Fetch tasks from Google Sheets and replace existing tasks."""
    tasks = _load_sheet_tasks(force=True)

    TASKS.clear()
    for t in tasks:
        TASKS[t.id] = t

    return ("", 204)


@bp.delete("/cache")
def clear_cache() -> tuple[str, int]:
    """Invalidate the Google Sheets tasks cache."""

    invalidate_cache()
    return ("", 204)

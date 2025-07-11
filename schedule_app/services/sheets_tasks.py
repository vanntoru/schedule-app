from __future__ import annotations

from typing import Any
import math
import time
import uuid

from google.oauth2.credentials import Credentials  # type: ignore
from googleapiclient.discovery import build  # type: ignore

from schedule_app.config import cfg
from schedule_app.models import Task
from schedule_app.utils.validation import _parse_dt, _validate_durations


class InvalidSheetRowError(Exception):
    """Raised when a sheet row contains invalid data."""




# Simple in-memory cache (tasks, expiry timestamp)
_CACHE: tuple[list[Task], float] | None = None




def _to_task(data: dict[str, str]) -> Task:
    """Return a :class:`Task` converted from a sheet row dictionary."""

    try:
        raw_min = int(data.get("duration_min", "0"))
    except ValueError as e:  # pragma: no cover - invalid sheet data
        raise InvalidSheetRowError("invalid duration") from e

    try:
        raw_raw_min = int(data.get("duration_raw_min", str(raw_min)))
    except ValueError as e:  # pragma: no cover - invalid sheet data
        raise InvalidSheetRowError("invalid duration") from e

    try:
        _validate_durations(raw_min, raw_raw_min)
    except ValueError as e:
        raise InvalidSheetRowError("invalid duration") from e

    duration_min = math.ceil(raw_min / 10) * 10 if raw_min > 0 else 0

    priority = data.get("priority", "B").strip().upper() or "B"
    if priority not in {"A", "B"}:
        raise InvalidSheetRowError("invalid priority")

    earliest = (data.get("earliest_start_utc", "") or "").strip()
    try:
        es_dt = _parse_dt(earliest)
    except ValueError as e:
        raise InvalidSheetRowError("invalid datetime") from e

    task_id = data.get("id") or str(uuid.uuid4())

    return Task(
        id=task_id,
        title=data.get("title", ""),
        category=data.get("category", ""),
        duration_min=duration_min,
        duration_raw_min=raw_raw_min,
        priority=priority,
        earliest_start_utc=es_dt,
    )


def fetch_tasks_from_sheet(session: dict[str, Any], *, force: bool = False) -> list[Task]:
    """Return tasks fetched from Google Sheets."""

    global _CACHE

    now = time.time()
    if _CACHE is not None and not force:
        tasks, expiry = _CACHE
        if now < expiry:
            return tasks

    ssid = cfg.SHEETS_TASKS_SSID
    if not ssid:
        return []

    creds_info = session.get("credentials")
    if not creds_info:
        raise RuntimeError("missing credentials")

    creds = Credentials(token=creds_info.get("access_token"))
    service = build("sheets", "v4", credentials=creds, cache_discovery=False)
    resp = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=ssid, range=cfg.SHEETS_TASKS_RANGE)
        .execute()
    )

    rows = resp.get("values", [])
    tasks: list[Task] = []
    if rows:
        headers = [str(h).strip().lower() for h in rows[0]]
        for row in rows[1:]:
            data = {headers[i]: row[i] for i in range(min(len(headers), len(row)))}
            tasks.append(_to_task(data))

    _CACHE = (tasks, now + cfg.SHEETS_CACHE_SEC)
    return tasks


__all__ = ["fetch_tasks_from_sheet", "InvalidSheetRowError"]

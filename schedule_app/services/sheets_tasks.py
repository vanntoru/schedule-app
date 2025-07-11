from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import time

from google.oauth2.credentials import Credentials  # type: ignore
from googleapiclient.discovery import build  # type: ignore

from schedule_app.config import cfg
from schedule_app.models import Task


# Simple in-memory cache (tasks, expiry timestamp)
_CACHE: tuple[list[Task], float] | None = None


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _to_task(data: dict[str, str]) -> Task:
    duration_min = int(data.get("duration_min", "0"))
    duration_raw_min = int(data.get("duration_raw_min", str(duration_min)))
    return Task(
        id=data.get("id", ""),
        title=data.get("title", ""),
        category=data.get("category", ""),
        duration_min=duration_min,
        duration_raw_min=duration_raw_min,
        priority=data.get("priority", "B"),
        earliest_start_utc=_parse_dt(data.get("earliest_start_utc")),
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


__all__ = ["fetch_tasks_from_sheet"]

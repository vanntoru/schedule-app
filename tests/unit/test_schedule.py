from __future__ import annotations

from datetime import datetime, timezone, date, time
from zoneinfo import ZoneInfo
from schedule_app.config import cfg

from freezegun import freeze_time

from schedule_app.models import Task, Block
from schedule_app.services import schedule
from schedule_app.api.tasks import TASKS
from schedule_app.api.blocks import BLOCKS


def _dt(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(timezone.utc)


@freeze_time("2025-01-01T00:00:00Z")
def test_priority_order() -> None:
    TASKS.clear()
    BLOCKS.clear()
    TASKS["A1"] = Task(
        id="A1",
        title="",
        category="",
        duration_min=30,
        duration_raw_min=30,
        priority="A",
    )
    TASKS["B1"] = Task(
        id="B1",
        title="",
        category="",
        duration_min=30,
        duration_raw_min=30,
        priority="B",
    )

    result = schedule.generate_schedule(target_day=date(2025, 1, 1))
    slots = result["slots"]
    assert len(slots) == 144
    assert slots[:6] == [2] * 6


@freeze_time("2025-01-01T00:00:00Z")
def test_busy_slot() -> None:
    TASKS.clear()
    BLOCKS.clear()
    BLOCKS["b1"] = Block(
        id="b1",
        start_utc=_dt("2025-01-01T00:00:00Z"),
        end_utc=_dt("2025-01-01T01:00:00Z"),
    )
    TASKS["A1"] = Task(
        id="A1",
        title="",
        category="",
        duration_min=30,
        duration_raw_min=30,
        priority="A",
    )
    result = schedule.generate_schedule(target_day=date(2025, 1, 1))
    slots = result["slots"]
    assert len(slots) == 144
    jst = ZoneInfo(cfg.TIMEZONE)
    start_utc = (
        datetime.combine(date(2025, 1, 1), time.min, tzinfo=jst).astimezone(timezone.utc)
    )
    idx = int((_dt("2025-01-01T00:00:00Z") - start_utc).total_seconds() // 600)
    assert slots[0:3] == [2] * 3
    assert slots[idx:idx + 6] == [1] * 6


@freeze_time("2025-01-01T00:00:00Z")
def test_earliest_start() -> None:
    TASKS.clear()
    BLOCKS.clear()
    TASKS["A1"] = Task(
        id="A1",
        title="",
        category="",
        duration_min=30,
        duration_raw_min=30,
        priority="A",
        earliest_start_utc=_dt("2025-01-01T12:00:00Z"),
    )
    result = schedule.generate_schedule(target_day=date(2025, 1, 1))
    slots = result["slots"]
    assert len(slots) == 144
    jst = ZoneInfo(cfg.TIMEZONE)
    start_utc = (
        datetime.combine(date(2025, 1, 1), time.min, tzinfo=jst).astimezone(timezone.utc)
    )
    idx = int((_dt("2025-01-01T12:00:00Z") - start_utc).total_seconds() // 600)
    assert all(s == 0 for s in slots[:idx])
    assert slots[idx:idx + 3] == [2] * 3


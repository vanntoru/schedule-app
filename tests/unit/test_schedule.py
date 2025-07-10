from __future__ import annotations

from datetime import datetime, timezone, date

from freezegun import freeze_time

from schedule_app.models import Task, Block, Event
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
    assert slots[:6] == [1] * 6
    assert slots[6:9] == [2] * 3


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
    assert all(s == 0 for s in slots[:72])
    assert slots[72:75] == [2] * 3


@freeze_time("2025-01-01T00:00:00Z")
def test_event_spans_midnight() -> None:
    TASKS.clear()
    BLOCKS.clear()
    from schedule_app.api.calendar import EVENTS

    EVENTS.clear()
    EVENTS["e1"] = Event(
        id="e1",
        title="",
        start_utc=_dt("2024-12-31T23:30:00Z"),
        end_utc=_dt("2025-01-01T00:30:00Z"),
    )

    result = schedule.generate_schedule(target_day=date(2025, 1, 1))
    slots = result["slots"]
    assert len(slots) == 144
    assert slots[:3] == [1] * 3
    assert slots[3] == 0


@freeze_time("2025-01-01T00:00:00Z")
def test_all_day_event_ignored() -> None:
    TASKS.clear()
    BLOCKS.clear()
    from schedule_app.api.calendar import EVENTS

    EVENTS.clear()
    EVENTS["ad"] = Event(
        id="ad",
        title="",
        start_utc=_dt("2025-01-01T00:00:00Z"),
        end_utc=_dt("2025-01-02T00:00:00Z"),
        all_day=True,
    )

    result = schedule.generate_schedule(target_day=date(2025, 1, 1))
    slots = result["slots"]
    assert len(slots) == 144
    assert all(s == 0 for s in slots)


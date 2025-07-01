from __future__ import annotations

from datetime import datetime, timezone

from freezegun import freeze_time

from schedule_app.models import Event, Task
from schedule_app.services import schedule


def _dt(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(timezone.utc)


@freeze_time("2025-01-01T00:00:00Z")
def test_priority_order() -> None:
    tasks = [
        Task(
            id="A1",
            title="",
            category="",
            duration_min=30,
            duration_raw_min=30,
            priority="A",
        ),
        Task(
            id="B1",
            title="",
            category="",
            duration_min=30,
            duration_raw_min=30,
            priority="B",
        ),
    ]
    grid = schedule.generate(date_utc=_dt("2025-01-01T00:00:00Z"), tasks=tasks, events=[], blocks=[])
    assert len(grid) == 144
    assert grid[:3] == ["A1"] * 3
    assert grid[3:6] == ["B1"] * 3


@freeze_time("2025-01-01T00:00:00Z")
def test_busy_slot() -> None:
    event = Event(
        id="e1",
        start_utc=_dt("2025-01-01T00:00:00Z"),
        end_utc=_dt("2025-01-01T01:00:00Z"),
        title="busy",
    )
    task = Task(
        id="A1",
        title="",
        category="",
        duration_min=30,
        duration_raw_min=30,
        priority="A",
    )
    grid = schedule.generate(date_utc=_dt("2025-01-01T00:00:00Z"), tasks=[task], events=[event], blocks=[])
    assert len(grid) == 144
    assert all(slot is None for slot in grid[:6])
    assert grid[6:9] == ["A1"] * 3


@freeze_time("2025-01-01T00:00:00Z")
def test_earliest_start() -> None:
    task = Task(
        id="A1",
        title="",
        category="",
        duration_min=30,
        duration_raw_min=30,
        priority="A",
        earliest_start_utc=_dt("2025-01-01T12:00:00Z"),
    )
    grid = schedule.generate(date_utc=_dt("2025-01-01T00:00:00Z"), tasks=[task], events=[], blocks=[])
    assert len(grid) == 144
    assert all(slot is None for slot in grid[:72])
    assert grid[72:75] == ["A1"] * 3


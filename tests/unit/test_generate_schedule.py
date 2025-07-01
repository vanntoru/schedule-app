from __future__ import annotations

from datetime import datetime, date, timezone

from freezegun import freeze_time

from schedule_app.services.schedule import generate_schedule
from schedule_app.api.tasks import TASKS
from schedule_app.api.blocks import BLOCKS
from schedule_app.models import Task, Block


def _dt(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(timezone.utc)


@freeze_time("2025-01-01T00:00:00Z")
def test_generate_schedule_basic() -> None:
    TASKS.clear()
    BLOCKS.clear()
    TASKS["t1"] = Task(
        id="t1",
        title="task",
        category="gen",
        duration_min=30,
        duration_raw_min=30,
        priority="A",
    )
    result = generate_schedule(date(2025, 1, 1))
    assert result["date"] == "2025-01-01"
    assert result["unplaced"] == []
    assert result["slots"][:3] == [2, 2, 2]


@freeze_time("2025-01-01T00:00:00Z")
def test_generate_schedule_busy() -> None:
    TASKS.clear()
    BLOCKS.clear()
    BLOCKS["b1"] = Block(
        id="b1",
        start_utc=_dt("2025-01-01T00:00:00Z"),
        end_utc=_dt("2025-01-01T01:00:00Z"),
    )
    TASKS["t1"] = Task(
        id="t1",
        title="task",
        category="gen",
        duration_min=30,
        duration_raw_min=30,
        priority="A",
    )
    result = generate_schedule(date(2025, 1, 1))
    assert result["slots"][:6] == [1] * 6
    assert result["slots"][6:9] == [2, 2, 2]


@freeze_time("2025-01-01T00:00:00Z")
def test_generate_schedule_unplaced() -> None:
    TASKS.clear()
    BLOCKS.clear()
    BLOCKS["b1"] = Block(
        id="b1",
        start_utc=_dt("2025-01-01T00:00:00Z"),
        end_utc=_dt("2025-01-01T23:00:00Z"),
    )
    TASKS["t1"] = Task(
        id="t1",
        title="big",
        category="gen",
        duration_min=80,
        duration_raw_min=80,
        priority="A",
    )
    result = generate_schedule(date(2025, 1, 1))
    assert "t1" in result["unplaced"]
    assert all(slot != 2 for slot in result["slots"])  # no task placed

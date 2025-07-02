from __future__ import annotations

from datetime import date

from freezegun import freeze_time

from schedule_app.services.schedule import generate_schedule
from schedule_app.api.tasks import TASKS
from schedule_app.api.blocks import BLOCKS


@freeze_time("2025-01-01T00:00:00Z")
def test_access_grid_via_slots() -> None:
    TASKS.clear()
    BLOCKS.clear()
    result = generate_schedule(date(2025, 1, 1))
    grid = result["slots"]
    assert isinstance(grid, list)
    assert len(grid) == 144
    assert grid == [0] * 144

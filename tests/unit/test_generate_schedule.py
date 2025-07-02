from datetime import date
from freezegun import freeze_time
from schedule_app.services.schedule import generate_schedule
from schedule_app.api.tasks import TASKS
from schedule_app.api.blocks import BLOCKS

@freeze_time("2025-01-01T00:00:00Z")
def test_generate_schedule_empty() -> None:
    TASKS.clear()
    BLOCKS.clear()
    result = generate_schedule(target_day=date(2025, 1, 1), algo="greedy")
    assert result["date"] == "2025-01-01"
    assert len(result["slots"]) == 144
    assert result["slots"] == [0] * 144
    assert result["unplaced"] == []

from datetime import datetime, timezone, timedelta

from schedule_app.models import Event
from schedule_app.services.schedule import generate_schedule


def test_event_jst_mapped_to_correct_utc_slot():
    # 14:30 JST -> 05:30 UTC
    start = datetime(2025, 7, 2, 14, 30, tzinfo=timezone(timedelta(hours=9)))
    end = datetime(2025, 7, 2, 15, 30, tzinfo=timezone(timedelta(hours=9)))

    grid = generate_schedule(
        target_day=datetime(2025, 7, 2, tzinfo=timezone.utc).date(),
        algo="greedy",
        events=[
            Event(
                id="x",
                title="\u30c6\u30b9\u30c8",
                start_utc=start.astimezone(timezone.utc),
                end_utc=end.astimezone(timezone.utc),
            )
        ],
    )

    busy_idx = [i for i, s in enumerate(grid) if s == 1]
    assert busy_idx == list(range(33, 39))

from __future__ import annotations

from datetime import datetime, timezone
import pytest
from freezegun import freeze_time

from schedule_app.errors import InvalidBlockRow
from schedule_app.services.google_client import _to_block
from schedule_app.services.rounding import quantize


@freeze_time("2025-01-01T00:00:00Z")
def test_block_row_rounding() -> None:
    data = {
        "start_utc": "2025-01-01T01:03:00Z",
        "end_utc": "2025-01-01T01:27:00Z",
        "title": "B1",
    }
    block = _to_block(data)
    assert block.start_utc == datetime(2025, 1, 1, 1, 0, tzinfo=timezone.utc)
    assert block.end_utc == datetime(2025, 1, 1, 1, 30, tzinfo=timezone.utc)
    assert block.title == "B1"


@freeze_time("2025-01-01T00:00:00Z")
@pytest.mark.parametrize(
    "data",
    [
        {"start_utc": "", "end_utc": "2025-01-01T01:10:00Z"},
        {"start_utc": "2025-01-01T01:00:00Z", "end_utc": ""},
        {"start_utc": "bad", "end_utc": "2025-01-01T01:10:00Z"},
        {"start_utc": "2025-01-01T02:00:00Z", "end_utc": "2025-01-01T01:50:00Z"},
    ],
)
def test_block_row_validation_error(data: dict[str, str]) -> None:
    with pytest.raises(InvalidBlockRow):
        _to_block(data)


@freeze_time("2025-01-01T00:00:00Z")
def test_quantize_function() -> None:
    dt = datetime(2025, 1, 1, 0, 5, tzinfo=timezone.utc)
    assert quantize(dt, up=False) == datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    assert quantize(dt, up=True) == datetime(2025, 1, 1, 0, 10, tzinfo=timezone.utc)

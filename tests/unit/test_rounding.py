from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from schedule_app.services.rounding import quantize

@pytest.mark.parametrize(
    "iso,up,expected",
    [
        ("2025-01-01T00:05:00Z", False, "2025-01-01T00:00:00Z"),
        ("2025-01-01T00:05:00Z", True, "2025-01-01T00:10:00Z"),
        ("2025-01-01T00:00:00Z", True, "2025-01-01T00:00:00Z"),
    ],
)
def test_quantize(iso: str, up: bool, expected: str) -> None:
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00")).replace(tzinfo=None)
    want = datetime.fromisoformat(expected.replace("Z", "+00:00"))
    assert quantize(dt, up=up) == want


def test_quantize_with_timezone() -> None:
    jst = timezone(timedelta(hours=9))
    dt = datetime(2025, 1, 1, 9, 5, tzinfo=jst)
    want = datetime(2025, 1, 1, 9, 0, tzinfo=jst)
    assert quantize(dt, up=False, tz=jst) == want

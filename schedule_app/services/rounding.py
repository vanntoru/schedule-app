"""Time-rounding helpers (10-minute quantum)."""

from __future__ import annotations

import math
from datetime import datetime, timezone

SLOT_SEC = 600  # 10 minutes


def _to_utc(dt: datetime) -> datetime:
    """Return *dt* as a timezone-aware UTC datetime.

    *   naive ⇒ UTC と見なす（仕様書 §9「内部: UTC 固定」）
    *   TZ 付き ⇒ UTC に変換
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def quantize(dt: datetime, *, up: bool) -> datetime:
    """Round *dt* to the nearest 10-minute boundary.

    Parameters
    ----------
    dt : datetime
        UTC or naive (treated as UTC).
    up : bool
        False ⇒ floor, True ⇒ ceil.

    Returns
    -------
    datetime
        UTC, **timezone-aware**.
    """
    dt_utc = _to_utc(dt)
    ts = dt_utc.timestamp()
    rounded = (math.ceil(ts / SLOT_SEC) if up else math.floor(ts / SLOT_SEC)) * SLOT_SEC
    return datetime.fromtimestamp(rounded, timezone.utc)

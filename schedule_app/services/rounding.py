"""Time-rounding helpers (10-minute quantum)"""
from __future__ import annotations

import math
from datetime import datetime

SLOT_SEC = 600  # 10 minutes


def quantize(dt: datetime, *, up: bool) -> datetime:  # pragma: no cover
    """Round *dt* to the nearest 10-minute boundary.

    *up* == False → floor / *up* == True → ceil
    All calculations are done in UTC seconds since epoch."""
    ts = dt.timestamp()
    rounded = (math.ceil(ts / SLOT_SEC) if up else math.floor(ts / SLOT_SEC)) * SLOT_SEC
    return datetime.utcfromtimestamp(rounded)

"""Time-rounding helpers (10-minute quantum)."""

from __future__ import annotations

import math
from datetime import datetime, timezone, tzinfo

SLOT_SEC = 600  # 10 minutes


def _to_tz(dt: datetime, tz: tzinfo) -> datetime:
    """Return *dt* converted to the given timezone ``tz``.

    *   naive ⇒ assume ``tz``
    *   aware ⇒ convert to ``tz``
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tz)
    return dt.astimezone(tz)


def quantize(dt: datetime, *, up: bool, tz: tzinfo = timezone.utc) -> datetime:
    """Round *dt* to the nearest 10-minute boundary.

    Parameters
    ----------
    dt : datetime
        The datetime to round. Naive values are interpreted in ``tz``.
    tz : tzinfo, optional
        Target timezone for rounding and return value (default: UTC).
    up : bool
        False ⇒ floor, True ⇒ ceil.

    Returns
    -------
    datetime
        A timezone-aware datetime in ``tz``.
    """
    dt_local = _to_tz(dt, tz)
    ts = dt_local.timestamp()
    rounded = (math.ceil(ts / SLOT_SEC) if up else math.floor(ts / SLOT_SEC)) * SLOT_SEC
    return datetime.fromtimestamp(rounded, tz)

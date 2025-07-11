from __future__ import annotations

from datetime import datetime, timezone


def _parse_dt(value: str | None) -> datetime | None:
    """Return a timezone-aware UTC datetime or ``None``.

    Accepts ISO 8601 strings with an optional trailing ``"Z"``. Naive
    datetimes are interpreted as UTC. Invalid formats raise ``ValueError``.
    """
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _validate_durations(duration_min: int, duration_raw_min: int) -> None:
    """Validate duration values.

    Both values must be positive integers and multiples of five minutes.
    ``ValueError`` is raised on failure.
    """
    ok = (
        isinstance(duration_min, int)
        and isinstance(duration_raw_min, int)
        and duration_min > 0
        and duration_raw_min > 0
        and duration_min % 5 == 0
        and duration_raw_min % 5 == 0
    )
    if not ok:
        raise ValueError("invalid duration")

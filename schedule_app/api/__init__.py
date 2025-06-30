"""Flask blueprints for the REST API."""

from __future__ import annotations

# Explicitly export optional blueprints
__all__ = ["bp_calendar"]

try:
    from .calendar import bp_calendar  # type: ignore
except Exception:  # pragma: no cover - optional blueprint
    bp_calendar = None  # type: ignore

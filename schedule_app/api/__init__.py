"""Flask blueprints for the REST API."""

from __future__ import annotations

# Explicitly export optional blueprints
__all__ = ["calendar_bp", "tasks_bp", "schedule_bp"]

try:
    from .calendar import calendar_bp  # type: ignore
except Exception:  # pragma: no cover - optional blueprint
    calendar_bp = None  # type: ignore

try:
    from .tasks import bp as tasks_bp  # type: ignore
except Exception:  # pragma: no cover - optional blueprint
    tasks_bp = None  # type: ignore

try:
    from .schedule import schedule_bp  # type: ignore
except Exception:  # pragma: no cover - optional blueprint
    schedule_bp = None  # type: ignore

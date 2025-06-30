"""Flask blueprints for the REST API."""

from __future__ import annotations

# Explicitly export optional blueprints
__all__ = ["calendar_bp"]

try:
    from .calendar import bp as calendar_bp  # type: ignore
except Exception:  # pragma: no cover - optional blueprint
    calendar_bp = None  # type: ignore

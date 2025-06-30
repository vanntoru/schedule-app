"""Flask blueprints for the REST API."""

from __future__ import annotations

# Re-export commonly used blueprints
try:
    from .calendar import bp as calendar_bp  # type: ignore
except Exception:  # pragma: no cover - optional blueprint
    pass

__all__ = [name for name in globals() if name.endswith('_bp')]

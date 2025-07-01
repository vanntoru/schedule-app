from __future__ import annotations


def log_metric(name: str, data: dict | None = None) -> None:
    """Record a usage metric (no-op placeholder)."""
    return None

__all__ = ["log_metric"]

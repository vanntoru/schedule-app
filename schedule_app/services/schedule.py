"""Simplified scheduling service."""

from __future__ import annotations

from datetime import date
from typing import Literal, TypedDict

NUM_SLOTS = 24 * 6


class ScheduleGrid(TypedDict):
    """Schedule grid representation."""

    date: str
    algo: Literal["greedy", "compact"]
    slots: list[int]
    unplaced: list[str]


__all__ = ["NUM_SLOTS", "ScheduleGrid", "generate_schedule"]


def generate_schedule(
    target_date: date,
    *,
    algo: Literal["greedy", "compact"] = "greedy",
) -> ScheduleGrid:
    """Return a blank schedule grid for ``target_date``."""

    return {
        "date": target_date.isoformat(),
        "algo": algo,
        "slots": [0] * NUM_SLOTS,
        "unplaced": [],
    }


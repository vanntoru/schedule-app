"""Simple task scheduler service for the 1-Day Schedule Generator."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from schedule_app.models import Block, Event, Task
from schedule_app.services.rounding import quantize

__all__ = ["generate"]

SLOT_MIN = 10
DAY_SLOTS = 144


def _day_start(date_utc: datetime) -> datetime:
    if date_utc.tzinfo is None:
        date_utc = date_utc.replace(tzinfo=timezone.utc)
    else:
        date_utc = date_utc.astimezone(timezone.utc)
    return datetime.combine(date_utc.date(), datetime.min.time(), tzinfo=timezone.utc)


def _to_index(dt: datetime, *, base: datetime) -> int:
    delta = dt - base
    return int(delta.total_seconds() // (SLOT_MIN * 60))


def _mark_busy(slot_map: list[bool], start: datetime, end: datetime, *, base: datetime) -> None:
    s = _to_index(quantize(start, up=False), base=base)
    e = _to_index(quantize(end, up=True), base=base)
    s = max(s, 0)
    e = min(e, DAY_SLOTS)
    for i in range(s, e):
        if 0 <= i < DAY_SLOTS:
            slot_map[i] = True


def _init_slot_map(date_utc: datetime, events: list[Event], blocks: list[Block]) -> list[bool]:
    start = _day_start(date_utc)
    slot_map = [False] * DAY_SLOTS
    for ev in events:
        _mark_busy(slot_map, ev.start_utc, ev.end_utc, base=start)
    for blk in blocks:
        _mark_busy(slot_map, blk.start_utc, blk.end_utc, base=start)
    return slot_map


def _sort_tasks(tasks: list[Task], *, day_start: datetime) -> list[Task]:
    """Return *tasks* sorted by priority, start time and duration."""

    def key(t: Task) -> tuple[int, datetime, int]:
        prio = 0 if t.priority == "A" else 1
        es = t.earliest_start_utc or day_start
        if es < day_start:
            es = day_start
        es = quantize(es, up=True)
        return (prio, es, -t.duration_min)

    return sorted(tasks, key=key)


def _find_slot(slot_map: list[bool], start_idx: int, slots_needed: int) -> int | None:
    for idx in range(start_idx, DAY_SLOTS - slots_needed + 1):
        if all(not slot_map[i] for i in range(idx, idx + slots_needed)):
            return idx
    return None


def _place_tasks(slot_map: list[bool], tasks: list[Task], *, base: datetime) -> tuple[list[str | None], list[str]]:
    grid: list[str | None] = [None] * DAY_SLOTS
    unplaced: list[str] = []

    for task in tasks:
        es = task.earliest_start_utc or base
        es = quantize(es, up=True)
        start_idx = max(_to_index(es, base=base), 0)
        need = task.duration_min // SLOT_MIN
        idx = _find_slot(slot_map, start_idx, need)
        if idx is None:
            unplaced.append(task.id)
            continue
        for i in range(idx, idx + need):
            slot_map[i] = True
            grid[i] = task.id
    return grid, unplaced


def _compact_grid(grid: list[str | None]) -> list[str | None]:
    # simple placeholder: no-op compaction
    return grid


def generate(
    *,
    date_utc: datetime,
    tasks: list[Task],
    events: list[Event],
    blocks: list[Block],
    algorithm: Literal["greedy", "compact"] = "greedy",
) -> list[str | None]:
    """Generate a 10 minute schedule for the given day."""
    base = _day_start(date_utc)
    slot_map = _init_slot_map(base, events, blocks)
    sorted_tasks = _sort_tasks(tasks, day_start=date_utc)
    grid, _unplaced = _place_tasks(slot_map, sorted_tasks, base=base)
    if algorithm == "compact":
        grid = _compact_grid(grid)
    return grid

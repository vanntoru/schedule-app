"""Simple task scheduler service for the 1-Day Schedule Generator."""

from __future__ import annotations

from datetime import date, datetime, timezone, timedelta
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import pytz

from schedule_app.config import cfg

from schedule_app.models import Block, Event, Task
from schedule_app.services.rounding import quantize

__all__ = ["generate", "generate_schedule"]

SLOT_MIN = 10
DAY_SLOTS = 144


def _jst():
    """Return the configured timezone.

    Tries :class:`ZoneInfo` first and falls back to :mod:`pytz` if the zone
    is not available.
    """
    try:
        return ZoneInfo(cfg.TIMEZONE)
    except ZoneInfoNotFoundError:
        return pytz.timezone(cfg.TIMEZONE)



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


def _init_slot_map(start_utc: datetime, events: list[Event], blocks: list[Block]) -> list[bool]:
    """Return a slot map initialised with busy periods for ``start_utc``."""
    slot_map = [False] * DAY_SLOTS
    for ev in events:
        _mark_busy(slot_map, ev.start_utc, ev.end_utc, base=start_utc)
    for blk in blocks:
        _mark_busy(slot_map, blk.start_utc, blk.end_utc, base=start_utc)
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


def _place_tasks(slot_map: list[bool], tasks: list[Task], *, start_utc: datetime) -> tuple[list[str | None], list[str]]:
    grid: list[str | None] = [None] * DAY_SLOTS
    unplaced: list[str] = []

    for task in tasks:
        es = task.earliest_start_utc or start_utc
        es = quantize(es, up=True)
        start_idx = max(_to_index(es, base=start_utc), 0)
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
    start_utc = date_utc
    slot_map = _init_slot_map(start_utc, events, blocks)
    sorted_tasks = _sort_tasks(tasks, day_start=start_utc)
    grid, _unplaced = _place_tasks(slot_map, sorted_tasks, start_utc=start_utc)
    if algorithm == "compact":
        grid = _compact_grid(grid)
    return grid


def generate_schedule(target_day: date, *, algo: str = "greedy") -> dict:
    """Return a simple JSON friendly schedule for ``target_day``.

    Parameters
    ----------
    target_day:
        Date in the configured timezone (JST by default). It will be
        converted to UTC internally.
    algo:
        Scheduling algorithm to use. Only ``"greedy"`` or ``"compact"`` are
        currently supported.
    """

    from schedule_app.api.tasks import TASKS
    from schedule_app.api.blocks import BLOCKS
    try:
        from schedule_app.api.calendar import EVENTS  # calendar.py が EVENTS を保持
    except ImportError:
        EVENTS = {}

    start_utc = datetime.combine(target_day, datetime.min.time(), tzinfo=timezone.utc)
    end_utc = start_utc + timedelta(days=1)

    events = [
        ev
        for ev in EVENTS.values()
        if ev.end_utc > start_utc and ev.start_utc < end_utc
    ]

    tasks = list(TASKS.values())
    blocks = list(BLOCKS.values())

    grid = generate(
        date_utc=start_utc,
        tasks=tasks,
        events=events,
        blocks=blocks,
        algorithm=algo,
    )

    busy_map = _init_slot_map(start_utc, events, blocks)

    slots: list[int] = []
    for idx, cell in enumerate(grid):
        if cell is None:
            slots.append(1 if busy_map[idx] else 0)
        else:
            slots.append(2)

    placed_ids = {t_id for t_id in grid if t_id is not None}
    unplaced = [t.id for t in tasks if t.id not in placed_ids]

    return {
        "date": target_day.isoformat(),
        "algo": algo,
        "slots": slots,
        "unplaced": unplaced,
    }

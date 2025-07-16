"""Domain dataclasses for the 1-Day Schedule Generator."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass(slots=True, frozen=True)
class Event:
    id: str
    start_utc: datetime
    end_utc: datetime
    title: str
    all_day: bool = False


@dataclass(slots=True, frozen=True)
class Task:
    id: str
    title: str
    category: str
    duration_min: int          # 10分粒め
    duration_raw_min: int      # 入力そのまま (5分刻み可)
    priority: Literal["A", "B"]
    earliest_start_utc: datetime | None = None


@dataclass(slots=True, frozen=True)
class Block:
    """User-defined busy period with an optional label."""

    id: str
    start_utc: datetime
    end_utc: datetime
    title: str | None = None

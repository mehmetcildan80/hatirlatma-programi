from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time


@dataclass(slots=True)
class Task:
    title: str
    due_date: date
    description: str = ""
    due_time: time | None = None
    completed: bool = False
    id: int | None = None


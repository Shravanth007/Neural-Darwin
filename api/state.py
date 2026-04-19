from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.scheduler import SimulationScheduler

_scheduler: "SimulationScheduler | None" = None

def set_scheduler(scheduler: "SimulationScheduler") -> None:
    global _scheduler
    _scheduler = scheduler

def get_scheduler() -> "SimulationScheduler":
    if _scheduler is None:
        raise RuntimeError("Scheduler not initialized — call set_scheduler() first")
    return _scheduler

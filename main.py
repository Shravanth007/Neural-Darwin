from __future__ import annotations

import sys
import threading
import time

from config import BASE_DIR, TICK_INTERVAL_SECONDS
from core.scheduler import SimulationScheduler

def build_scheduler() -> SimulationScheduler:
    return SimulationScheduler.bootstrap()

def run_simulation_loop(scheduler: SimulationScheduler, stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        scheduler.tick_once()
        stop_event.wait(TICK_INTERVAL_SECONDS)

def launch_api_server(scheduler: SimulationScheduler) -> threading.Thread:

    from api.state import set_scheduler

    set_scheduler(scheduler)

    def _run() -> None:
        try:
            import uvicorn
        except ImportError:
            print("uvicorn not installed — run: pip install uvicorn[standard] fastapi")
            return
        uvicorn.run(
            "api.app:app",
            host="0.0.0.0",
            port=8000,
            log_level="warning",
        )

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return t

def main() -> None:
    scheduler = build_scheduler()
    stop_event = threading.Event()

    sim_thread = threading.Thread(
        target=run_simulation_loop,
        args=(scheduler, stop_event),
        daemon=True,
    )
    sim_thread.start()

    api_thread = launch_api_server(scheduler)

    print(f"Neural Darwin booted with {len(scheduler.state.agents)} agents (day/night cycle active).")
    print("  API server:  http://localhost:8000/api/health")
    print("  Frontend:    cd frontend && npm run dev  ->  http://localhost:5173")
    print("  (Press Ctrl+C to stop)")

    try:
        while sim_thread.is_alive():
            time.sleep(0.2)
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        sim_thread.join(timeout=1)

if __name__ == "__main__":
    main()

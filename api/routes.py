from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from api.state import get_scheduler
from config import CYCLE_TICKS, DAY_TICKS, GRID_SIZE

router = APIRouter(prefix="/api")

def _phase_label(tick: int) -> str:
    phase_tick = tick % CYCLE_TICKS
    if phase_tick < DAY_TICKS:
        remaining = DAY_TICKS - phase_tick
        return f"DAY — tax in {remaining} ticks"
    remaining = CYCLE_TICKS - phase_tick
    return f"NIGHT — reset in {remaining} ticks"

def _serialize_agent(agent) -> dict[str, Any]:
    return {
        "agent_id": agent.agent_id,
        "x": agent.position.x,
        "y": agent.position.y,
        "tokens": agent.tokens,
        "alive": agent.alive,
        "kills": agent.kills,
        "inventory": list(agent.inventory),
    }

def _serialize_event(row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "tick": row["tick"],
        "event_type": row["event_type"],
        "actor": row["actor"],
        "target": row["target"],
        "details": json.loads(row["details"]) if row["details"] else {},
        "created_at": row["created_at"],
    }

def _serialize_graveyard_entry(row) -> dict[str, Any]:
    return {
        "agent_id": row["agent_id"],
        "death_tick": row["death_tick"],
        "cause": row["cause"],
        "killer": row["killer"],
        "final_tokens": row["final_tokens"],
        "final_kills": row["final_kills"],
        "final_x": row["final_x"],
        "final_y": row["final_y"],
        "inventory": json.loads(row["inventory"]) if row["inventory"] else [],
    }

@router.get("/health")
def health():
    return {"status": "ok"}

@router.get("/state/summary")
def state_summary():
    s = get_scheduler().state
    with s.lock:
        phase_tick = s.tick % CYCLE_TICKS
        living = s.living_agents()
        dead = s.dead_agents()
        return {
            "tick": s.tick,
            "day": s.day,
            "phase": "DAY" if s.is_day else "NIGHT",
            "phase_tick": phase_tick,
            "phase_label": _phase_label(s.tick),
            "living_count": len(living),
            "dead_count": len(dead),
            "total_tokens": sum(a.tokens for a in living),
            "arena_busy": s.arena_manager.is_busy,
            "bounties_open": len(s.bounty_board.open_jobs()),
            "grid_size": GRID_SIZE,
            "cycle_ticks": CYCLE_TICKS,
            "day_ticks": DAY_TICKS,
        }

@router.get("/state/map")
def state_map():
    s = get_scheduler().state
    with s.lock:
        world = s.world

        zones: dict[str, str] = {}
        with world._lock:
            for (x, y), zone in world._zones.items():
                zones[f"{x},{y}"] = zone.value

        agents = [
            {"agent_id": a.agent_id, "x": a.position.x, "y": a.position.y}
            for a in s.living_agents()
        ]

        return {"size": world.size, "zones": zones, "agents": agents}

@router.get("/agents")
def list_agents():
    s = get_scheduler().state
    with s.lock:
        return [_serialize_agent(a) for a in s.agents.values()]

@router.get("/agents/{agent_id}")
def get_agent(agent_id: str):
    s = get_scheduler().state
    with s.lock:
        agent = s.agents.get(agent_id)
        if agent is None:
            raise HTTPException(status_code=404, detail=f"agent {agent_id!r} not found")
        return _serialize_agent(agent)

@router.get("/events")
def list_events(limit: int = Query(default=50, ge=1, le=500)):

    ledger = get_scheduler().state.ledger
    rows = ledger.recent_events(limit)
    return [_serialize_event(r) for r in rows]

@router.get("/graveyard")
def get_graveyard():

    ledger = get_scheduler().state.ledger
    rows = ledger.get_graveyard()
    return [_serialize_graveyard_entry(r) for r in rows]

@router.get("/bounties")
def get_bounties():
    s = get_scheduler().state
    with s.lock:
        return s.bounty_board.to_dict()

from __future__ import annotations

def wealth_points(agents) -> list[tuple[str, int]]:
    return [(agent["agent_id"], agent["tokens"]) for agent in agents]

from __future__ import annotations

def agent_summary(agent) -> dict[str, object]:
    return {
        "agent_id": agent["agent_id"],
        "tokens":   agent["tokens"],
        "position": (agent["x"], agent["y"]),
        "alive":    bool(agent["alive"]),
        "kills":    agent["kills"],
    }

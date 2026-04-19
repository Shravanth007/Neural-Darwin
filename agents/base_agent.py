from __future__ import annotations

from core.agent import AgentState

class BaseAgent:

    def __init__(self, state: AgentState):
        self.state = state

    def build_prompt(self) -> str:
        return (
            f"You are {self.state.agent_id}, an agent in the Neural Darwin world. "
            f"Tokens: {self.state.tokens}. "
            f"Position: {self.state.position.as_tuple()}. "
            f"Kills: {self.state.kills}. "
            "Survive, grow your token balance, and avoid or pursue bounties."
        )

    def decide(self) -> dict[str, str]:
        return {"action": "idle", "reason": "decision loop not implemented yet"}

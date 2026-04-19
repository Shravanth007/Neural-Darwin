from __future__ import annotations

import random
import threading
from dataclasses import dataclass, field
from typing import Any

from config import KNIFE_COST, STARTING_TOKENS
from core.world import Position, World

@dataclass
class AgentState:

    agent_id: str
    position: Position
    tokens: int = STARTING_TOKENS

    alive: bool = True
    kills: int = 0
    last_pulse_tick: int = 0

    inventory: list[str] = field(default_factory=list)

    message_log: list[dict[str, Any]] = field(default_factory=list)

    memory: list[str] = field(default_factory=list)

    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    @property
    def name(self) -> str:
        return self.agent_id

    def zone_name(self, world: World) -> str:
        return world.get_zone(self.position).value

    def can_afford(self, amount: int | float) -> bool:
        return self.tokens >= amount

    def debit(self, amount: int | float) -> None:
        with self._lock:
            self.tokens -= int(amount)

    def credit(self, amount: int | float) -> None:
        with self._lock:
            self.tokens += int(amount)

    def mark_dead(self) -> None:
        with self._lock:
            self.alive = False

    def has_knife(self) -> bool:
        return "Knife" in self.inventory

    def buy_knife(self, world: World) -> bool:

        if not world.is_market(self.position):
            return False
        if self.has_knife():
            return False
        if not self.can_afford(KNIFE_COST):
            return False
        with self._lock:
            self.tokens -= KNIFE_COST
            self.inventory.append("Knife")
        return True

    def receive_message(self, tick: int, sender: str, msg_type: str, text: str) -> None:
        with self._lock:
            self.message_log.append({
                "tick": tick,
                "from": sender,
                "type": msg_type,
                "text": text,
            })

def build_agent(agent_id: str, world: World, rng: random.Random | None = None) -> AgentState:

    roller = rng or random.Random()
    x = roller.randint(0, world.size - 1)
    y = roller.randint(0, world.size - 1)
    world.register_agent(agent_id, x, y)
    return AgentState(
        agent_id=agent_id,
        position=Position(x, y),
        tokens=STARTING_TOKENS,
    )

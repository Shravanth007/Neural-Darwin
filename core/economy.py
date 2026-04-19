from __future__ import annotations

from config import SANCTUARY_RENT_PER_TICK, TRADE_COST
from core.world import World

def trade_cost(world: World, position) -> int:

    modifier = world.get_zone_cost_modifier(position.x, position.y)
    return max(1, int(TRADE_COST * modifier))

def transfer_tokens(source, target, amount: int) -> None:

    if amount < 0:
        raise ValueError("amount must be positive")
    if not source.can_afford(amount):
        raise ValueError("insufficient funds")
    source.debit(amount)
    target.credit(amount)

def charge_rent(agent, world: World) -> float:

    if not agent.alive:
        return 0.0
    if not world.is_sanctuary(agent.position):
        return 0.0

    cost = SANCTUARY_RENT_PER_TICK
    if agent.tokens >= 1:

        actual = max(1, int(cost)) if cost < 1 else int(cost)
        agent.debit(actual)
        return float(actual)
    return 0.0

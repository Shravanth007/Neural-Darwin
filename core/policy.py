from __future__ import annotations

import random

from config import ARENA_MIN_BET, KNIFE_COST, MOVE_COST, TRADE_COST
from core.combat import resolve_bounty_kill, resolve_murder
from core.economy import trade_cost
from core.world import Position, ZoneType, chebyshev_distance_xy

# ponytail: rule-based heuristic policy; swap individual branches for LLM
# decisions (llm/pool.py) once that integration lands.

MURDER_CHANCE = 0.30
DUEL_CHANCE = 0.10
TRADE_CHANCE = 0.25
WANDER_CHANCE = 0.50
KNIFE_BUY_BUFFER = 3_000
KNIFE_SEEK_BUFFER = 5_000
MURDER_MIN_TARGET_TOKENS = 5_000


def run_agent_actions(scheduler, rng: random.Random | None = None) -> None:
    """One action per living agent per tick. Called from tick_once under the state lock."""
    roller = rng or random.Random()
    state = scheduler.state

    for agent in list(state.living_agents()):
        # re-check duel membership every iteration: an agent earlier in this
        # loop may have just started a duel with one iterated later
        duel = state.arena_manager.active_duel
        if duel and not duel.finished and agent.agent_id in duel.combatants:
            continue
        if not agent.alive:
            continue
        _act(scheduler, agent, roller)


def _act(scheduler, agent, rng: random.Random) -> None:
    state = scheduler.state
    world = state.world

    # 1. armed and next to someone: hunt bounties, sometimes murder
    if agent.has_knife():
        target = _adjacent_target(state, agent)
        if target is not None and _try_attack(scheduler, agent, target, rng):
            return

    # 2. both parties in the arena: occasionally throw down a duel
    if world.is_arena(agent.position) and rng.random() < DUEL_CHANCE:
        opponent = _arena_opponent(state, agent)
        if opponent is not None:
            ok, _ = scheduler.start_arena_duel(
                agent.agent_id, opponent.agent_id, ARENA_MIN_BET,
            )
            if ok:
                return

    # 3. at the market with cash to spare: arm up
    if (
        world.is_market(agent.position)
        and not agent.has_knife()
        and agent.tokens > KNIFE_COST + KNIFE_BUY_BUFFER
    ):
        ok, _ = scheduler.buy_weapon(agent.agent_id)
        if ok:
            return

    # 4. rich but unarmed: head to the market
    if not agent.has_knife() and agent.tokens > KNIFE_COST + KNIFE_SEEK_BUFFER:
        cells = world.get_zone_cells(ZoneType.MARKET)
        if cells and _step_towards(scheduler, agent, cells):
            return

    # 5. armed hunter: chase visible bountied agents (stop next to them —
    # kills require distance exactly 1, never 0)
    if agent.has_knife():
        marks = _visible_wanted(state, agent)
        if marks and _step_towards(scheduler, agent, marks, stop_adjacent=True):
            return

    # 6. speculative trade (discounted in the market zone)
    cost = trade_cost(world, agent.position)
    if rng.random() < TRADE_CHANCE and agent.tokens > cost + 1_000:
        agent.debit(cost)
        gain = rng.randint(0, TRADE_COST * 2)
        agent.credit(gain)
        state.ledger.append_event(
            state.tick, "trade", agent.agent_id, None,
            {"cost": cost, "gain": gain, "delta": gain - cost},
        )
        scheduler._check_death(agent, cause="trade_cost")
        return

    # 7. wander
    if rng.random() < WANDER_CHANCE:
        dx, dy = rng.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
        _move(scheduler, agent, agent.position.x + dx, agent.position.y + dy)


def _try_attack(scheduler, attacker, target, rng: random.Random) -> bool:
    state = scheduler.state

    if state.bounty_board.is_wanted(target.agent_id):
        result = resolve_bounty_kill(
            state.world, attacker, target, state.bounty_board, state.tick, rng=rng,
        )
        if result.get("success"):
            scheduler.on_bounty_kill(
                attacker.agent_id, target.agent_id,
                result["loot"], result["bounty_reward"],
            )
            return True
        if "attack_roll" in result:
            state.ledger.append_event(
                state.tick, "murder_attempt", attacker.agent_id, target.agent_id,
                {"reason": result.get("reason"), "kind": "bounty"},
            )
            scheduler._check_death(attacker, cause="murder_cost")
            return True
        return False

    if rng.random() < MURDER_CHANCE and target.tokens > MURDER_MIN_TARGET_TOKENS:
        result = resolve_murder(
            state.world, attacker, target, state.bounty_board, state.tick, rng=rng,
        )
        if result.get("success"):
            scheduler.on_murder(
                attacker.agent_id, target.agent_id,
                result["loot"], result["bounty_reward"],
            )
            return True
        if "attack_roll" in result:
            state.ledger.append_event(
                state.tick, "murder_attempt", attacker.agent_id, target.agent_id,
                {"reason": result.get("reason"), "kind": "murder"},
            )
            scheduler._check_death(attacker, cause="murder_cost")
            return True

    return False


def _adjacent_target(state, agent):
    world = state.world
    candidates = [
        other
        for other in state.living_agents()
        if other.agent_id != agent.agent_id
        and chebyshev_distance_xy(
            agent.position.x, agent.position.y,
            other.position.x, other.position.y,
        ) == 1
        and world.is_combat_allowed(other.position.x, other.position.y)
        and world.is_combat_allowed(agent.position.x, agent.position.y)
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda a: a.tokens)


def _arena_opponent(state, agent):
    if not agent.can_afford(ARENA_MIN_BET):
        return None
    for other in state.living_agents():
        if (
            other.agent_id != agent.agent_id
            and state.world.is_arena(other.position)
            and other.can_afford(ARENA_MIN_BET)
        ):
            return other
    return None


def _visible_wanted(state, agent) -> list[tuple[int, int]]:
    seen = state.world.get_visible_entities(agent.agent_id)
    return [
        (e["x"], e["y"])
        for e in seen
        if state.bounty_board.is_wanted(e["agent_id"])
    ]


def _step_towards(
    scheduler, agent, targets: list[tuple[int, int]], stop_adjacent: bool = False,
) -> bool:
    if not targets:
        return False
    ax, ay = agent.position.x, agent.position.y
    tx, ty = min(targets, key=lambda c: chebyshev_distance_xy(ax, ay, c[0], c[1]))
    dx, dy = tx - ax, ty - ay
    if dx == 0 and dy == 0:
        return False
    if stop_adjacent and chebyshev_distance_xy(ax, ay, tx, ty) <= 1:
        return False

    steps: list[tuple[int, int]] = []
    x_step = (ax + (1 if dx > 0 else -1), ay)
    y_step = (ax, ay + (1 if dy > 0 else -1))
    if abs(dx) >= abs(dy):
        if dx != 0:
            steps.append(x_step)
        if dy != 0:
            steps.append(y_step)
    else:
        steps.append(y_step)
        if dx != 0:
            steps.append(x_step)

    for nx, ny in steps:
        if stop_adjacent and (nx, ny) == (tx, ty):
            continue
        if _move(scheduler, agent, nx, ny):
            return True
    return False


def _move(scheduler, agent, nx: int, ny: int) -> bool:
    state = scheduler.state
    if not agent.can_afford(MOVE_COST):
        return False
    if not state.world.move_agent(agent.agent_id, nx, ny):
        return False
    # keep both position stores in sync (world grid + agent state)
    agent.position = Position(nx, ny)
    agent.debit(MOVE_COST)
    scheduler._check_death(agent, cause="move_cost")
    return True

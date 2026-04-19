from __future__ import annotations

import random
import threading
from dataclasses import dataclass, field
from typing import Any

from config import (
    ARENA_BULLET_COUNT,
    ARENA_DUEL_TICKS,
    ARENA_MIN_BET,
    ARENA_OBSTACLE_COUNT,
    ARENA_SHRINK_INTERVAL,
    ARENA_SUBGRID_SIZE,
    ARENA_TAX_RATIO,
    ARENA_WINNER_RATIO,
    BOUNTY_REWARD_RATIO,
    LOOT_RATIO,
    MURDER_COST,
)
from core.bounty import BountyBoard, BountyJob
from core.world import Position, World, chebyshev_distance

@dataclass
class ArenaCombatant:

    agent_id: str
    x: int = 0
    y: int = 0
    hp: int = 3
    bullets: int = ARENA_BULLET_COUNT
    alive: bool = True

@dataclass
class ArenaDuel:

    challenger_id: str
    defender_id: str
    bet_amount: int
    total_pool: int

    combatants: dict[str, ArenaCombatant] = field(default_factory=dict)
    obstacles: list[tuple[int, int]] = field(default_factory=list)
    grid_size: int = ARENA_SUBGRID_SIZE
    zone_min: int = 0
    zone_max: int = ARENA_SUBGRID_SIZE - 1

    start_tick: int = 0
    elapsed_ticks: int = 0
    finished: bool = False
    winner_id: str | None = None

    def is_in_zone(self, x: int, y: int) -> bool:

        return self.zone_min <= x <= self.zone_max and self.zone_min <= y <= self.zone_max

class ArenaDuelManager:

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.active_duel: ArenaDuel | None = None

    @property
    def is_busy(self) -> bool:
        with self._lock:
            return self.active_duel is not None and not self.active_duel.finished

    def start_duel(
        self,
        world: World,
        challenger,
        defender,
        bet_amount: int,
        tick: int,
        rng: random.Random | None = None,
    ) -> tuple[bool, str, ArenaDuel | None]:

        roller = rng or random.Random()

        with self._lock:
            if self.active_duel is not None and not self.active_duel.finished:
                return False, "arena is occupied — another duel is in progress", None

        ok, reason = can_place_arena_bet(world, challenger, defender, bet_amount)
        if not ok:
            return False, reason, None

        challenger.debit(bet_amount)
        defender.debit(bet_amount)
        total_pool = bet_amount * 2

        grid = ARENA_SUBGRID_SIZE
        obstacles: list[tuple[int, int]] = []
        while len(obstacles) < ARENA_OBSTACLE_COUNT:
            ox, oy = roller.randint(0, grid - 1), roller.randint(0, grid - 1)

            if (ox, oy) in ((0, 0), (grid - 1, grid - 1)):
                continue
            if (ox, oy) not in obstacles:
                obstacles.append((ox, oy))

        c1 = ArenaCombatant(agent_id=challenger.agent_id, x=0, y=0)
        c2 = ArenaCombatant(agent_id=defender.agent_id, x=grid - 1, y=grid - 1)

        duel = ArenaDuel(
            challenger_id=challenger.agent_id,
            defender_id=defender.agent_id,
            bet_amount=bet_amount,
            total_pool=total_pool,
            combatants={challenger.agent_id: c1, defender.agent_id: c2},
            obstacles=obstacles,
            grid_size=grid,
            zone_min=0,
            zone_max=grid - 1,
            start_tick=tick,
        )

        with self._lock:
            self.active_duel = duel

        return True, "duel started", duel

    def tick_duel(
        self,
        agents: dict[str, Any],
        ledger: Any,
        tick: int,
        rng: random.Random | None = None,
    ) -> dict[str, Any] | None:

        with self._lock:
            duel = self.active_duel
            if duel is None or duel.finished:
                return None

        roller = rng or random.Random()
        duel.elapsed_ticks += 1

        if duel.elapsed_ticks % ARENA_SHRINK_INTERVAL == 0:
            if duel.zone_max - duel.zone_min > 2:
                duel.zone_min += 1
                duel.zone_max -= 1

                for c in duel.combatants.values():
                    if c.alive and not duel.is_in_zone(c.x, c.y):
                        c.hp -= 1
                        if c.hp <= 0:
                            c.alive = False

        alive_combatants = [c for c in duel.combatants.values() if c.alive]
        for combatant in alive_combatants:
            opponent = self._get_opponent(duel, combatant.agent_id)
            if opponent is None or not opponent.alive:
                continue

            action = roller.choice(["move", "shoot"]) if combatant.bullets > 0 else "move"

            if action == "move":
                self._move_combatant(duel, combatant, opponent, roller)
            else:
                self._shoot(duel, combatant, opponent, roller)

        alive_after = [c for c in duel.combatants.values() if c.alive]

        result = None
        if len(alive_after) <= 1 or duel.elapsed_ticks >= ARENA_DUEL_TICKS:
            result = self._resolve_duel(duel, agents, ledger, tick, roller)

        return result

    def _get_opponent(self, duel: ArenaDuel, agent_id: str) -> ArenaCombatant | None:
        for c in duel.combatants.values():
            if c.agent_id != agent_id:
                return c
        return None

    def _move_combatant(
        self,
        duel: ArenaDuel,
        combatant: ArenaCombatant,
        opponent: ArenaCombatant,
        rng: random.Random,
    ) -> None:

        best_dx, best_dy = 0, 0
        best_dist = abs(combatant.x - opponent.x) + abs(combatant.y - opponent.y)

        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            nx, ny = combatant.x + dx, combatant.y + dy
            if not duel.is_in_zone(nx, ny):
                continue
            if (nx, ny) in duel.obstacles:
                continue
            dist = abs(nx - opponent.x) + abs(ny - opponent.y)
            if dist < best_dist:
                best_dist = dist
                best_dx, best_dy = dx, dy

        combatant.x += best_dx
        combatant.y += best_dy

    def _shoot(
        self,
        duel: ArenaDuel,
        shooter: ArenaCombatant,
        target: ArenaCombatant,
        rng: random.Random,
    ) -> None:

        if shooter.bullets <= 0:
            return

        shooter.bullets -= 1

        dist = abs(shooter.x - target.x) + abs(shooter.y - target.y)

        hit_chance = max(10, 80 - (dist - 1) * 10)

        if self._obstacle_blocks(duel, shooter, target):
            hit_chance = max(5, hit_chance // 2)

        roll = rng.randint(1, 100)
        if roll <= hit_chance:
            target.hp -= 1
            if target.hp <= 0:
                target.alive = False

    def _obstacle_blocks(
        self,
        duel: ArenaDuel,
        shooter: ArenaCombatant,
        target: ArenaCombatant,
    ) -> bool:

        dx = target.x - shooter.x
        dy = target.y - shooter.y
        steps = max(abs(dx), abs(dy))
        if steps == 0:
            return False
        for i in range(1, steps):
            ix = shooter.x + round(dx * i / steps)
            iy = shooter.y + round(dy * i / steps)
            if (ix, iy) in duel.obstacles:
                return True
        return False

    def _resolve_duel(
        self,
        duel: ArenaDuel,
        agents: dict[str, Any],
        ledger: Any,
        tick: int,
        rng: random.Random,
    ) -> dict[str, Any]:

        duel.finished = True

        alive = [c for c in duel.combatants.values() if c.alive]

        if len(alive) == 1:
            winner = alive[0]
        elif len(alive) == 2:

            a, b = alive
            if a.hp > b.hp:
                winner = a
            elif b.hp > a.hp:
                winner = b
            else:
                winner = rng.choice([a, b])
        else:

            duel.winner_id = None
            ledger.append_event(tick, "arena_duel_end", None, None, {
                "challenger": duel.challenger_id,
                "defender": duel.defender_id,
                "result": "double_elimination",
                "pool_burned": duel.total_pool,
            })
            return {
                "finished": True,
                "winner": None,
                "reason": "double_elimination",
                "pool": duel.total_pool,
            }

        duel.winner_id = winner.agent_id
        loser_id = (
            duel.defender_id if winner.agent_id == duel.challenger_id
            else duel.challenger_id
        )

        payout = int(duel.total_pool * ARENA_WINNER_RATIO)
        tax = duel.total_pool - payout

        winner_agent = agents.get(winner.agent_id)
        loser_agent = agents.get(loser_id)

        if winner_agent:
            winner_agent.credit(payout)
        if loser_agent:
            loser_agent.mark_dead()

        ledger.append_event(tick, "arena_duel_end", winner.agent_id, loser_id, {
            "bet": duel.bet_amount,
            "pool": duel.total_pool,
            "payout": payout,
            "tax_burned": tax,
            "elapsed_ticks": duel.elapsed_ticks,
        })

        return {
            "finished": True,
            "winner": winner.agent_id,
            "loser": loser_id,
            "payout": payout,
            "tax_burned": tax,
            "pool": duel.total_pool,
        }

def can_attempt_murder(
    world: World,
    attacker,
    target,
) -> tuple[bool, str]:

    if not attacker.alive or not target.alive:
        return False, "dead agents cannot fight"

    if not attacker.has_knife():
        return False, "attacker does not have a Knife — buy one at the MARKET (6000 tokens)"

    dist = chebyshev_distance(attacker.position, target.position)
    if dist != 1:
        return False, f"must be adjacent (distance 1) to kill, current distance: {dist}"

    if world.is_sanctuary(attacker.position) or world.is_sanctuary(target.position):
        return False, "killing is forbidden in sanctuary"
    if not world.is_combat_allowed(attacker.position.x, attacker.position.y):
        return False, "combat not allowed in this zone"
    if not attacker.can_afford(MURDER_COST):
        return False, "attacker cannot afford murder cost"
    return True, "ok"

def resolve_murder(
    world: World,
    attacker,
    target,
    bounty_board: BountyBoard,
    tick: int,
    rng: random.Random | None = None,
) -> dict:

    allowed, reason = can_attempt_murder(world, attacker, target)
    if not allowed:
        return {"success": False, "reason": reason}

    roller = rng or random.Random()

    attacker.debit(MURDER_COST)

    attack_roll = roller.randint(1, 100)
    defend_roll = roller.randint(1, 100)

    if attack_roll > defend_roll:
        loot = int(target.tokens * LOOT_RATIO)
        bounty_reward = int(target.tokens * BOUNTY_REWARD_RATIO)

        target.debit(loot)
        attacker.credit(loot)
        target.mark_dead()
        attacker.kills += 1

        job: BountyJob = bounty_board.post(
            victim_id=target.agent_id,
            killer_id=attacker.agent_id,
            reward=bounty_reward,
            tick=tick,
        )

        return {
            "success": True,
            "loot": loot,
            "bounty_posted": True,
            "bounty_reward": job.reward,
            "attack_roll": attack_roll,
            "defend_roll": defend_roll,
        }

    return {
        "success": False,
        "reason": "target survived",
        "attack_roll": attack_roll,
        "defend_roll": defend_roll,
    }

def resolve_bounty_kill(
    world: World,
    hunter,
    target,
    bounty_board: BountyBoard,
    tick: int,
    rng: random.Random | None = None,
) -> dict:

    job = bounty_board.open_bounty_for(target.agent_id)
    if job is None:
        return {"success": False, "reason": "target has no open bounty"}

    allowed, reason = can_attempt_murder(world, hunter, target)
    if not allowed:
        return {"success": False, "reason": reason}

    roller = rng or random.Random()
    hunter.debit(MURDER_COST)

    attack_roll = roller.randint(1, 100)
    defend_roll = roller.randint(1, 100)

    if attack_roll > defend_roll:
        loot = int(target.tokens * LOOT_RATIO)
        target.debit(loot)
        hunter.credit(loot)
        target.mark_dead()
        hunter.kills += 1

        bounty_board.fulfill(target.agent_id, hunter.agent_id, tick)
        hunter.credit(job.reward)

        return {
            "success": True,
            "loot": loot,
            "bounty_collected": True,
            "bounty_reward": job.reward,
            "attack_roll": attack_roll,
            "defend_roll": defend_roll,
        }

    return {
        "success": False,
        "reason": "target survived bounty hunt",
        "attack_roll": attack_roll,
        "defend_roll": defend_roll,
    }

def can_place_arena_bet(
    world: World,
    challenger,
    defender,
    amount: int,
) -> tuple[bool, str]:

    if amount < ARENA_MIN_BET:
        return False, f"bet below arena minimum ({ARENA_MIN_BET})"
    if not world.is_arena(challenger.position):
        return False, "challenger must be in the arena zone"
    if not world.is_arena(defender.position):
        return False, "defender must be in the arena zone"
    if not challenger.can_afford(amount):
        return False, "challenger cannot afford the bet"
    if not defender.can_afford(amount):
        return False, "defender cannot afford the bet"
    if not challenger.alive or not defender.alive:
        return False, "both agents must be alive"
    return True, "ok"

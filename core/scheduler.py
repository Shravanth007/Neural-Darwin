from __future__ import annotations

import threading
from dataclasses import dataclass, field

from config import (
    AGENT_COUNT,
    CYCLE_TICKS,
    DAILY_RESET_POOL,
    DAILY_TAX,
    DAY_TICKS,
    KNIFE_COST,
    MIN_POPULATION,
    STARTING_TOKENS,
    TOKEN_DEATH_THRESHOLD,
)
from core.agent import AgentState, build_agent
from core.bounty import BountyBoard
from core.combat import ArenaDuelManager
from core.economy import charge_rent
from core.ledger import Ledger
from core.policy import run_agent_actions
from core.world import World

@dataclass
class SimulationState:
    world: World
    ledger: Ledger
    bounty_board: BountyBoard
    arena_manager: ArenaDuelManager
    agents: dict[str, AgentState] = field(default_factory=dict)
    tick: int = 0
    day: int = 0
    _lock: threading.RLock = field(default_factory=threading.RLock, repr=False, compare=False)

    @property
    def lock(self) -> threading.RLock:
        return self._lock

    def living_agents(self) -> list[AgentState]:
        return [a for a in self.agents.values() if a.alive]

    def dead_agents(self) -> list[AgentState]:
        return [a for a in self.agents.values() if not a.alive]

    @property
    def phase_tick(self) -> int:

        return self.tick % CYCLE_TICKS

    @property
    def is_day(self) -> bool:
        return self.phase_tick < DAY_TICKS

    @property
    def is_night(self) -> bool:
        return not self.is_day

    @property
    def is_day_end(self) -> bool:

        return self.phase_tick == DAY_TICKS - 1

    @property
    def is_night_end(self) -> bool:

        return self.phase_tick == CYCLE_TICKS - 1

class SimulationScheduler:
    def __init__(self, state: SimulationState, autopilot: bool = True):
        self.state = state
        # autopilot drives built-in agent behavior; tests disable it to
        # exercise economy mechanics in isolation
        self.autopilot = autopilot
        # agents whose death has been fully processed; guards against a
        # second _handle_death (e.g. arena resolution after a mid-duel death)
        # duplicating events and clobbering the graveyard row
        self._buried: set[str] = set()

    @classmethod
    def bootstrap(cls) -> "SimulationScheduler":
        world = World()
        ledger = Ledger()
        bounty_board = BountyBoard()
        arena_manager = ArenaDuelManager()

        ledger.reset()

        world.randomize_zones()

        agents: dict[str, AgentState] = {}
        for i in range(1, AGENT_COUNT + 1):
            agent_id = f"Agent_{i}"
            agent = build_agent(agent_id, world)
            agents[agent_id] = agent

        state = SimulationState(
            world=world,
            ledger=ledger,
            bounty_board=bounty_board,
            arena_manager=arena_manager,
            agents=agents,
        )
        scheduler = cls(state)
        scheduler._record_bootstrap()
        return scheduler

    def _record_bootstrap(self) -> None:
        for agent in self.state.agents.values():
            self.state.ledger.append_event(
                tick=self.state.tick,
                event_type="spawn",
                actor=agent.agent_id,
                target=None,
                details={
                    "position": agent.position.as_tuple(),
                    "tokens": agent.tokens,
                },
            )
            self.state.ledger.snapshot_agent(self.state.tick, agent)

    def tick_once(self) -> None:
        with self.state.lock:
            self.state.tick += 1

            self._charge_sanctuary_rent()

            self._tick_arena_duel()

            if self.autopilot:
                run_agent_actions(self)

            if self.state.is_day_end:
                self._run_daily_tax()

            if self.state.is_night_end:
                self._run_night_reset()
                self.state.day += 1
                self.state.ledger.append_event(
                    self.state.tick, "day_cycle", None, None,
                    {"new_day": self.state.day, "phase": "dawn"},
                )

                self.state.world.randomize_zones()
                self.state.ledger.append_event(
                    self.state.tick, "zones_randomized", None, None,
                    {"day": self.state.day},
                )

            if self.state.phase_tick == DAY_TICKS:
                self.state.ledger.append_event(
                    self.state.tick, "phase_change", None, None, {"phase": "night"},
                )
            elif self.state.phase_tick == 0 and self.state.tick > 0:
                self.state.ledger.append_event(
                    self.state.tick, "phase_change", None, None, {"phase": "day"},
                )

            self._spawn_heir_if_needed()
            self._strip_dead_agents()
            self._snapshot_agents()

    def _charge_sanctuary_rent(self) -> None:

        for agent in self.state.living_agents():
            cost = charge_rent(agent, self.state.world)
            if cost > 0:
                self._check_death(agent, cause="sanctuary_rent")

    def _tick_arena_duel(self) -> None:

        manager = self.state.arena_manager
        if not manager.is_busy:
            return

        result = manager.tick_duel(
            agents=self.state.agents,
            ledger=self.state.ledger,
            tick=self.state.tick,
        )

        if result and result.get("finished"):
            duel = manager.active_duel
            if duel:

                self.state.ledger.update_arena_bet(
                    challenger=duel.challenger_id,
                    defender=duel.defender_id,
                    winner=result.get("winner"),
                    payout=result.get("payout", 0),
                    tax_burned=result.get("tax_burned", 0),
                )

                loser_id = result.get("loser")
                if loser_id:
                    loser = self.state.agents.get(loser_id)
                    if loser and not loser.alive:
                        self._handle_death(
                            loser,
                            cause="arena_duel",
                            killer=result.get("winner"),
                        )

    def buy_weapon(self, agent_id: str) -> tuple[bool, str]:
        with self.state.lock:
            agent = self.state.agents.get(agent_id)
            if agent is None or not agent.alive:
                return False, "agent not found or dead"

            if agent.buy_knife(self.state.world):
                self.state.ledger.log_weapon_purchase(
                    self.state.tick, agent_id, "Knife", KNIFE_COST,
                )
                self.state.ledger.append_event(
                    self.state.tick, "weapon_purchase", agent_id, None,
                    {"weapon": "Knife", "cost": KNIFE_COST},
                )
                return True, "Knife purchased"
            return False, "cannot buy knife (not at market, already owns one, or cannot afford)"

    def start_arena_duel(
        self,
        challenger_id: str,
        defender_id: str,
        bet_amount: int,
    ) -> tuple[bool, str]:
        with self.state.lock:
            challenger = self.state.agents.get(challenger_id)
            defender = self.state.agents.get(defender_id)
            if not challenger or not defender:
                return False, "agent not found"

            ok, reason, duel = self.state.arena_manager.start_duel(
                world=self.state.world,
                challenger=challenger,
                defender=defender,
                bet_amount=bet_amount,
                tick=self.state.tick,
            )

            if ok and duel:
                self.state.ledger.log_arena_bet(
                    self.state.tick,
                    challenger_id,
                    defender_id,
                    bet_amount,
                    duel.total_pool,
                )
                self.state.ledger.append_event(
                    self.state.tick, "arena_duel_start", challenger_id, defender_id,
                    {"bet": bet_amount, "pool": duel.total_pool},
                )
            return ok, reason

    def _run_daily_tax(self) -> None:

        for agent in self.state.living_agents():
            agent.debit(DAILY_TAX)
            self.state.ledger.append_event(
                self.state.tick,
                "daily_tax",
                agent.agent_id,
                None,
                {"delta": -DAILY_TAX, "day": self.state.day},
            )
            self._check_death(agent, cause="daily_tax")

    def _run_night_reset(self) -> None:

        survivors = self.state.living_agents()
        if not survivors:
            return
        payout = DAILY_RESET_POOL // len(survivors)
        for agent in survivors:
            agent.credit(payout)
            self.state.ledger.append_event(
                self.state.tick,
                "daily_reset_pool",
                agent.agent_id,
                None,
                {"delta": payout, "day": self.state.day},
            )

    def on_murder(
        self,
        attacker_id: str,
        victim_id: str,
        loot: int,
        bounty_reward: int,
    ) -> None:
        with self.state.lock:
            self.state.ledger.append_event(
                self.state.tick, "murder", attacker_id, victim_id, {"loot": loot},
            )
            self.state.ledger.append_event(
                self.state.tick, "bounty_posted", None, attacker_id,
                {"reward": bounty_reward, "reason": f"{attacker_id} killed {victim_id}"},
            )

            victim = self.state.agents.get(victim_id)
            if victim:
                self._handle_death(
                    victim,
                    cause="murdered",
                    killer=attacker_id,
                    bounty_info=f"Bounty of {bounty_reward} tokens placed on {attacker_id}.",
                )

    def on_bounty_kill(
        self,
        hunter_id: str,
        target_id: str,
        loot: int,
        bounty_reward: int,
    ) -> None:
        with self.state.lock:
            self.state.ledger.append_event(
                self.state.tick, "bounty_kill", hunter_id, target_id,
                {"loot": loot, "bounty_reward": bounty_reward},
            )
            self.state.ledger.append_event(
                self.state.tick, "bounty_fulfilled", hunter_id, target_id,
                {"reward_paid": bounty_reward},
            )

            target = self.state.agents.get(target_id)
            if target:
                self._handle_death(
                    target,
                    cause="bounty_kill",
                    killer=hunter_id,
                    bounty_info=f"Bounty collected by {hunter_id} for {bounty_reward} tokens.",
                )

    def _handle_death(
        self,
        agent: AgentState,
        cause: str,
        killer: str | None = None,
        bounty_info: str = "",
    ) -> None:

        if agent.agent_id in self._buried:
            return
        self._buried.add(agent.agent_id)

        if agent.alive:
            agent.mark_dead()

        self.state.world.deregister_agent(agent.agent_id)

        self.state.ledger.move_to_graveyard(
            agent=agent,
            death_tick=self.state.tick,
            cause=cause,
            killer=killer,
        )

        self.state.ledger.broadcast_death(
            dead_agent_id=agent.agent_id,
            tick=self.state.tick,
            all_agents=self.state.agents,
            bounty_info=bounty_info,
        )

        self.state.ledger.append_event(
            self.state.tick, "death", agent.agent_id, None,
            {"reason": cause, "tokens": agent.tokens, "killer": killer},
        )

    def _check_death(self, agent: AgentState, cause: str = "token_threshold") -> None:

        if agent.alive and agent.tokens <= TOKEN_DEATH_THRESHOLD:
            self._handle_death(agent, cause=cause)

    def _strip_dead_agents(self) -> None:

        for agent in self.state.dead_agents():

            self.state.world.deregister_agent(agent.agent_id)

    def _spawn_heir_if_needed(self) -> None:

        if len(self.state.living_agents()) >= MIN_POPULATION:
            return

        existing_ids = set(self.state.agents)
        heir_index = 1
        while f"Heir_{heir_index}" in existing_ids:
            heir_index += 1

        heir_id = f"Heir_{heir_index}"
        heir = build_agent(heir_id, self.state.world)
        heir.tokens = max(5_000, STARTING_TOKENS // 2)
        self.state.agents[heir_id] = heir

        self.state.ledger.append_event(
            self.state.tick,
            "heir_spawn",
            heir_id,
            None,
            {
                "tokens": heir.tokens,
                "position": heir.position.as_tuple(),
                "population": len(self.state.living_agents()),
            },
        )

    def _snapshot_agents(self) -> None:
        for agent in self.state.agents.values():
            self.state.ledger.snapshot_agent(self.state.tick, agent)

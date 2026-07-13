from __future__ import annotations

import random
import tempfile
import unittest
from pathlib import Path

from config import KNIFE_COST, MOVE_COST
from core.agent import AgentState
from core.bounty import BountyBoard
from core.combat import ArenaDuelManager
from core.ledger import Ledger
from core.policy import _act, run_agent_actions
from core.scheduler import SimulationScheduler, SimulationState
from core.world import Position, World


class PolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.world = World()
        self.ledger = Ledger(Path(self._tmp.name) / "policy.db")
        self.state = SimulationState(
            world=self.world,
            ledger=self.ledger,
            bounty_board=BountyBoard(),
            arena_manager=ArenaDuelManager(),
            agents={},
        )
        self.scheduler = SimulationScheduler(self.state, autopilot=False)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _add(self, agent_id: str, x: int, y: int, **kwargs) -> AgentState:
        agent = AgentState(agent_id, Position(x, y), **kwargs)
        self.state.agents[agent_id] = agent
        self.world.register_agent(agent_id, x, y)
        return agent

    def test_unarmed_rich_agent_moves_toward_market(self) -> None:
        agent = self._add("Agent_1", 10, 10, tokens=KNIFE_COST + 10_000)
        start = agent.position

        _act(self.scheduler, agent, random.Random(0))

        self.assertNotEqual(agent.position, start)
        self.assertEqual(agent.tokens, KNIFE_COST + 10_000 - MOVE_COST)
        self.assertEqual(
            self.world.get_agent_position("Agent_1"),
            agent.position.as_tuple(),
        )

    def test_agent_at_market_buys_knife(self) -> None:
        agent = self._add("Agent_1", 3, 3, tokens=KNIFE_COST + 10_000)

        _act(self.scheduler, agent, random.Random(0))

        self.assertTrue(agent.has_knife())
        self.assertEqual(agent.tokens, 10_000)

    def test_armed_agent_collects_adjacent_bounty(self) -> None:
        hunter = self._add("Hunter", 5, 5, inventory=["Knife"])
        outlaw = self._add("Outlaw", 6, 5, tokens=8_000)
        self.state.bounty_board.post(
            victim_id="Victim", killer_id="Outlaw", reward=4_000, tick=1,
        )

        _act(self.scheduler, hunter, random.Random(5))

        self.assertFalse(outlaw.alive)
        self.assertEqual(hunter.kills, 1)
        self.assertGreater(hunter.tokens, 20_000)
        self.assertIsNone(self.state.bounty_board.open_bounty_for("Outlaw"))
        self.assertEqual(len(self.ledger.get_graveyard()), 1)

    def test_handle_death_is_idempotent(self) -> None:
        agent = self._add("Agent_1", 10, 10)

        self.scheduler._handle_death(agent, cause="murdered", killer="Agent_2")
        self.scheduler._handle_death(agent, cause="arena_duel", killer="Agent_3")

        graves = self.ledger.get_graveyard()
        self.assertEqual(len(graves), 1)
        self.assertEqual(graves[0]["cause"], "murdered")
        death_events = [
            r for r in self.ledger.recent_events(20) if r["event_type"] == "death"
        ]
        self.assertEqual(len(death_events), 1)

    def test_hunter_stops_adjacent_to_bounty_target(self) -> None:
        from core.policy import _step_towards

        hunter = self._add("Hunter", 5, 5, inventory=["Knife"])

        moved = _step_towards(self.scheduler, hunter, [(6, 5)], stop_adjacent=True)

        self.assertFalse(moved)
        self.assertEqual(hunter.position, Position(5, 5))

    def test_run_agent_actions_skips_dead_agents(self) -> None:
        agent = self._add("Agent_1", 10, 10)
        agent.mark_dead()
        start = agent.position

        run_agent_actions(self.scheduler, random.Random(0))

        self.assertEqual(agent.position, start)


if __name__ == "__main__":
    unittest.main()

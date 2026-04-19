from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from config import AGENT_COUNT, DAILY_RESET_POOL, DAILY_TAX, DAY_TICKS, MIN_POPULATION, NIGHT_TICKS
from core.agent import AgentState
from core.bounty import BountyBoard
from core.combat import ArenaDuelManager
from core.ledger import Ledger
from core.scheduler import SimulationScheduler, SimulationState
from core.world import Position, World

class SchedulerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmp.name) / "scheduler.db"
        self.world = World()
        self.ledger = Ledger(self.db_path)
        self.state = SimulationState(
            world=self.world,
            ledger=self.ledger,
            bounty_board=BountyBoard(),
            arena_manager=ArenaDuelManager(),
            agents={},
        )
        self.scheduler = SimulationScheduler(self.state)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_bootstrap_creates_default_population(self) -> None:
        with patch("core.scheduler.Ledger", return_value=self.ledger):
            scheduler = SimulationScheduler.bootstrap()
        self.assertEqual(len(scheduler.state.agents), AGENT_COUNT)
        self.assertEqual(len(scheduler.state.living_agents()), AGENT_COUNT)

    def test_day_end_collects_tax(self) -> None:
        agent = AgentState("Agent_1", Position(10, 10), tokens=10_000)
        self.state.agents[agent.agent_id] = agent
        self.state.tick = DAY_TICKS - 2

        self.scheduler.tick_once()

        self.assertEqual(agent.tokens, 10_000 - DAILY_TAX)
        events = [row["event_type"] for row in self.ledger.recent_events(10)]
        self.assertIn("daily_tax", events)

        tax_rows = [
            row for row in self.ledger.recent_events(20)
            if row["event_type"] == "daily_tax"
        ]
        self.assertTrue(tax_rows)
        details = json.loads(tax_rows[0]["details"])
        self.assertEqual(details["day"], 0)

    def test_night_end_distributes_reset_pool_and_advances_day(self) -> None:
        a1 = AgentState("Agent_1", Position(10, 10), tokens=10_000)
        a2 = AgentState("Agent_2", Position(11, 10), tokens=10_000)
        self.state.agents = {a1.agent_id: a1, a2.agent_id: a2}
        self.state.tick = DAY_TICKS + NIGHT_TICKS - 2

        self.scheduler.tick_once()

        payout = DAILY_RESET_POOL // 2
        self.assertEqual(a1.tokens, 10_000 + payout)
        self.assertEqual(a2.tokens, 10_000 + payout)
        self.assertEqual(self.state.day, 1)

        reset_rows = [
            row for row in self.ledger.recent_events(20)
            if row["event_type"] == "daily_reset_pool"
        ]
        self.assertEqual(len(reset_rows), 2)
        for row in reset_rows:
            details = json.loads(row["details"])
            self.assertEqual(details["day"], 0)

    def test_sanctuary_rent_is_charged_per_tick(self) -> None:
        sanctuary_cell = next(iter(self.world.get_zone_cells(self.world.get_zone(Position(1, 48)))))
        agent = AgentState("Agent_1", Position(*sanctuary_cell), tokens=10)
        self.state.agents[agent.agent_id] = agent

        self.scheduler.tick_once()

        self.assertLess(agent.tokens, 10)

    def test_heir_spawns_below_min_population(self) -> None:
        for idx in range(MIN_POPULATION - 1):
            self.state.agents[f"Agent_{idx}"] = AgentState(f"Agent_{idx}", Position(idx, idx))

        self.scheduler.tick_once()

        living = self.state.living_agents()
        self.assertGreaterEqual(len(living), MIN_POPULATION)
        heir_ids = [agent.agent_id for agent in living if agent.agent_id.startswith("Heir_")]
        self.assertEqual(len(heir_ids), 1)

if __name__ == "__main__":
    unittest.main()

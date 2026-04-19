from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core.agent import AgentState
from core.ledger import Ledger
from core.world import Position

class LedgerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmp.name) / "test_simulation.db"
        self.ledger = Ledger(self.db_path)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_event_and_snapshot_queries(self) -> None:
        agent = AgentState("Agent_1", Position(2, 3), tokens=1234)
        self.ledger.append_event(0, "spawn", agent.agent_id, None, {"tokens": agent.tokens})
        self.ledger.snapshot_agent(0, agent)
        agent.position = Position(4, 5)
        agent.tokens = 1500
        self.ledger.snapshot_agent(2, agent)

        recent = self.ledger.recent_events()
        self.assertEqual(len(recent), 1)
        latest = self.ledger.latest_agent_snapshots()
        self.assertEqual(len(latest), 1)
        self.assertEqual(latest[0]["x"], 4)
        self.assertEqual(latest[0]["y"], 5)
        self.assertEqual(self.ledger.current_tick(), 2)

    def test_graveyard_weapon_and_arena_logging(self) -> None:
        agent = AgentState("Agent_2", Position(7, 9), tokens=500, inventory=["Knife"])
        self.ledger.move_to_graveyard(agent, death_tick=5, cause="murder", killer="Agent_3")
        self.ledger.log_weapon_purchase(1, "Agent_2", "Knife", 6000)
        self.ledger.log_arena_bet(2, "Agent_2", "Agent_3", 1000, 2000)
        self.ledger.update_arena_bet("Agent_2", "Agent_3", "Agent_2", 1700, 300)

        graveyard = self.ledger.get_graveyard()
        self.assertEqual(len(graveyard), 1)
        self.assertEqual(graveyard[0]["killer"], "Agent_3")

        with self.ledger.connect() as conn:
            weapon_rows = conn.execute("SELECT weapon, cost FROM weapon_purchases").fetchall()
            arena_rows = conn.execute(
                "SELECT winner, payout, tax_burned, status FROM arena_bets"
            ).fetchall()

        self.assertEqual(weapon_rows[0], ("Knife", 6000))
        self.assertEqual(arena_rows[0], ("Agent_2", 1700, 300, "finished"))

    def test_current_day_uses_full_cycle_ticks(self) -> None:
        agent = AgentState("Agent_9", Position(1, 1), tokens=100)
        self.ledger.snapshot_agent(239, agent)
        self.assertEqual(self.ledger.current_day(), 0)
        self.ledger.snapshot_agent(240, agent)
        self.assertEqual(self.ledger.current_day(), 1)

if __name__ == "__main__":
    unittest.main()

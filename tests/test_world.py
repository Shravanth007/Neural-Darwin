from __future__ import annotations

import random
import unittest

from config import GRID_SIZE, ZONE_CELL_COUNTS, ZONE_LAYOUT
from core.agent import AgentState
from core.world import Position, World, ZoneType, chebyshev_distance

class WorldTests(unittest.TestCase):
    def test_default_zone_layout_matches_config(self) -> None:
        world = World()

        for zone_name, cells in ZONE_LAYOUT.items():
            for x, y in cells:
                self.assertEqual(world.get_zone(x, y), ZoneType[zone_name])

        counts = world.zone_counts()
        self.assertEqual(counts[ZoneType.MARKET], ZONE_CELL_COUNTS["MARKET"])
        self.assertEqual(counts[ZoneType.ARENA], ZONE_CELL_COUNTS["ARENA"])
        self.assertEqual(counts[ZoneType.SANCTUARY], ZONE_CELL_COUNTS["SANCTUARY"])
        self.assertEqual(counts[ZoneType.VAULT], ZONE_CELL_COUNTS["VAULT"])
        total_special = sum(ZONE_CELL_COUNTS.values())
        self.assertEqual(counts[ZoneType.WASTELAND], GRID_SIZE * GRID_SIZE - total_special)

    def test_randomize_zones_preserves_zone_counts_and_no_overlap(self) -> None:
        world = World()
        world.randomize_zones(random.Random(7))

        counts = world.zone_counts()
        self.assertEqual(counts[ZoneType.MARKET], ZONE_CELL_COUNTS["MARKET"])
        self.assertEqual(counts[ZoneType.ARENA], ZONE_CELL_COUNTS["ARENA"])
        self.assertEqual(counts[ZoneType.SANCTUARY], ZONE_CELL_COUNTS["SANCTUARY"])
        self.assertEqual(counts[ZoneType.VAULT], ZONE_CELL_COUNTS["VAULT"])

        occupied = set()
        for zone_type in (ZoneType.MARKET, ZoneType.ARENA, ZoneType.SANCTUARY, ZoneType.VAULT):
            for cell in world.get_zone_cells(zone_type):
                self.assertNotIn(cell, occupied)
                occupied.add(cell)

    def test_visibility_and_messaging_rules(self) -> None:
        world = World()
        sender = AgentState("A", Position(10, 10))
        nearby = AgentState("B", Position(12, 12))
        far = AgentState("C", Position(20, 20))
        world.register_agent(sender.agent_id, 10, 10)
        world.register_agent(nearby.agent_id, 12, 12)
        world.register_agent(far.agent_id, 20, 20)

        visible = world.get_visible_entities(sender.agent_id)
        visible_ids = {entry["agent_id"] for entry in visible}
        self.assertIn("B", visible_ids)
        self.assertNotIn("C", visible_ids)

        ok, _ = world.send_personal_message(sender, nearby, "hello", tick=1)
        self.assertTrue(ok)
        self.assertEqual(len(nearby.message_log), 1)

        too_far, _ = world.send_personal_message(sender, far, "hello", tick=1)
        self.assertFalse(too_far)
        self.assertEqual(len(far.message_log), 0)

    def test_chebyshev_distance(self) -> None:
        self.assertEqual(chebyshev_distance(Position(0, 0), Position(0, 0)), 0)
        self.assertEqual(chebyshev_distance(Position(0, 0), Position(2, 3)), 3)

if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import random
import unittest

from config import BOUNTY_REWARD_RATIO, LOOT_RATIO, MURDER_COST
from core.agent import AgentState
from core.bounty import BountyBoard
from core.combat import can_attempt_murder, can_place_arena_bet, resolve_bounty_kill, resolve_murder
from core.world import Position, World

class CombatTests(unittest.TestCase):
    def setUp(self) -> None:
        self.world = World()
        self.bounty_board = BountyBoard()

    def test_murder_requires_knife_and_adjacency(self) -> None:
        attacker = AgentState("Hunter", Position(5, 5))
        target = AgentState("Target", Position(6, 6))

        allowed, reason = can_attempt_murder(self.world, attacker, target)
        self.assertFalse(allowed)
        self.assertIn("Knife", reason)

        attacker.inventory.append("Knife")
        allowed, reason = can_attempt_murder(self.world, attacker, target)
        self.assertTrue(allowed)
        self.assertEqual(reason, "ok")

        target.position = Position(8, 8)
        allowed, reason = can_attempt_murder(self.world, attacker, target)
        self.assertFalse(allowed)
        self.assertIn("distance", reason)

    def test_murder_is_forbidden_in_sanctuary(self) -> None:
        attacker = AgentState("Hunter", Position(1, 48), inventory=["Knife"])
        target = AgentState("Target", Position(2, 48))

        allowed, reason = can_attempt_murder(self.world, attacker, target)
        self.assertFalse(allowed)
        self.assertIn("sanctuary", reason.lower())

    def test_successful_murder_loots_and_posts_bounty(self) -> None:
        attacker = AgentState("Hunter", Position(5, 5), inventory=["Knife"])
        target = AgentState("Victim", Position(6, 5), tokens=10_000)

        result = resolve_murder(
            self.world,
            attacker,
            target,
            self.bounty_board,
            tick=3,
            rng=random.Random(5),
        )

        self.assertTrue(result["success"])
        expected_loot = int(10_000 * LOOT_RATIO)
        expected_bounty = int(10_000 * BOUNTY_REWARD_RATIO)
        self.assertEqual(result["loot"], expected_loot)
        self.assertEqual(attacker.tokens, 20_000 - MURDER_COST + expected_loot)
        self.assertEqual(target.tokens, 10_000 - expected_loot)
        self.assertFalse(target.alive)
        self.assertEqual(attacker.kills, 1)
        open_job = self.bounty_board.open_bounty_for(attacker.agent_id)
        self.assertIsNotNone(open_job)
        self.assertEqual(open_job.reward, expected_bounty)

    def test_bounty_kill_requires_open_bounty_and_pays_reward(self) -> None:
        killer = AgentState("Killer", Position(5, 5), inventory=["Knife"])
        victim = AgentState("Victim", Position(6, 5), tokens=8_000)
        hunter = AgentState("BountyHunter", Position(8, 8), inventory=["Knife"])

        murder = resolve_murder(
            self.world,
            killer,
            victim,
            self.bounty_board,
            tick=2,
            rng=random.Random(5),
        )
        self.assertTrue(murder["success"])

        hunter.position = Position(5, 6)
        result = resolve_bounty_kill(
            self.world,
            hunter,
            killer,
            self.bounty_board,
            tick=4,
            rng=random.Random(5),
        )

        self.assertTrue(result["success"])
        self.assertTrue(result["bounty_collected"])
        self.assertFalse(killer.alive)
        self.assertIsNone(self.bounty_board.open_bounty_for(killer.agent_id))

    def test_arena_bet_requires_arena_presence(self) -> None:
        challenger = AgentState("A", Position(25, 25))
        defender = AgentState("B", Position(25, 25))
        ok, reason = can_place_arena_bet(self.world, challenger, defender, 1_000)
        self.assertTrue(ok)
        self.assertEqual(reason, "ok")

        defender.position = Position(24, 25)
        ok, reason = can_place_arena_bet(self.world, challenger, defender, 1_000)
        self.assertFalse(ok)
        self.assertIn("arena", reason.lower())

if __name__ == "__main__":
    unittest.main()

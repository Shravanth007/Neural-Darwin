from __future__ import annotations

import unittest

from config import TRADE_COST
from core.agent import AgentState
from core.economy import charge_rent, trade_cost, transfer_tokens
from core.world import Position, World

class EconomyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.world = World()

    def test_market_trade_cost_is_discounted(self) -> None:
        market_cost = trade_cost(self.world, Position(3, 3))
        wasteland_cost = trade_cost(self.world, Position(0, 0))

        self.assertLess(market_cost, wasteland_cost)
        self.assertEqual(wasteland_cost, TRADE_COST)

    def test_transfer_tokens_moves_balance(self) -> None:
        source = AgentState("A", Position(0, 0), tokens=100)
        target = AgentState("B", Position(0, 1), tokens=50)

        transfer_tokens(source, target, 25)

        self.assertEqual(source.tokens, 75)
        self.assertEqual(target.tokens, 75)

    def test_charge_rent_only_applies_in_sanctuary(self) -> None:
        sanctuary_agent = AgentState("S", Position(1, 48), tokens=10)
        wasteland_agent = AgentState("W", Position(0, 0), tokens=10)

        sanctuary_cost = charge_rent(sanctuary_agent, self.world)
        wasteland_cost = charge_rent(wasteland_agent, self.world)

        self.assertGreater(sanctuary_cost, 0)
        self.assertEqual(wasteland_cost, 0)

if __name__ == "__main__":
    unittest.main()

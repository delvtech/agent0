"""
Unit tests for the core Agent API.
"""

# pylint: disable=abstract-method

import unittest
from dataclasses import dataclass

from elfpy.agent import Agent
from elfpy.types import MarketState, Quantity, StretchedTime, TokenType
from elfpy.markets import Market
from elfpy.pricing_models.base import PricingModel
from elfpy.pricing_models.hyperdrive import HyperdrivePricingModel
from elfpy.pricing_models.yieldspace import YieldSpacePricingModel


class ErrorPolicy(Agent):
    """
    This class was made for testing purposes. It does not implement the required self.action() method
    """

    def __init__(self, wallet_address, budget=1000):
        """call basic policy init then add custom stuff"""
        super().__init__(wallet_address, budget)
        self.amount_to_spend = 500

    # self.action() method is intentionally not implemented, so we can test error behavior

    __test__ = False  # pytest: don't test this class

@dataclass
class TestCaseGetMax:
    """Test case for get_max_long and get_max_short tests"""

    market_state: MarketState
    fee_percent: float
    time_remaining: StretchedTime

    __test__ = False  # pytest: don't test this class


class TestAgent(unittest.TestCase):
    """Unit tests for the core Agent API"""

    @staticmethod
    def setup_market() -> Market:
        """Instantiate a market object for testing purposes"""

        # Give an initial market state
        pricing_model = HyperdrivePricingModel()
        market_state = MarketState(
            share_reserves=1_000_000,
            bond_reserves=1_000_000,
            base_buffer=0,
            bond_buffer=0,
            init_share_price=1,
            share_price=1,
        )
        fee_percent=0.1,
        time_remaining=StretchedTime(days=365, time_stretch=pricing_model.calc_time_stretch(0.05)),

        market = Market(
            pricing_model=pricing_model,
            market_state=market_state,
            fee_percent=fee_percent,
            position_duration=time_remaining,
        )

        return market

    def test_get_max_safety(self):
        """
        Ensures that get_max_long and get_max_short will not exceed the balance
        of an agent in a variety of market conditions.
        """
        pricing_models: list[PricingModel] = [HyperdrivePricingModel(), YieldSpacePricingModel()]

        test_cases: list[TestCaseGetMax] = [
            TestCaseGetMax(
                market_state=MarketState(
                    share_reserves=1_000_000,
                    bond_reserves=1_000_000,
                    base_buffer=0,
                    bond_buffer=0,
                    init_share_price=1,
                    share_price=1,
                ),
                fee_percent=0.1,
                time_remaining=StretchedTime(days=365, time_stretch=pricing_models[0].calc_time_stretch(0.05)),
            ),
            TestCaseGetMax(
                market_state=MarketState(
                    share_reserves=1_000_000,
                    bond_reserves=1_000_000,
                    base_buffer=100_000,
                    bond_buffer=100_000,
                    init_share_price=1,
                    share_price=1,
                ),
                fee_percent=0.1,
                time_remaining=StretchedTime(days=365, time_stretch=pricing_models[0].calc_time_stretch(0.05)),
            ),
            TestCaseGetMax(
                market_state=MarketState(
                    share_reserves=100_000_000,
                    bond_reserves=1_000_000,
                    base_buffer=0,
                    bond_buffer=0,
                    init_share_price=1,
                    share_price=1,
                ),
                fee_percent=0.1,
                time_remaining=StretchedTime(days=365, time_stretch=pricing_models[0].calc_time_stretch(0.05)),
            ),
            TestCaseGetMax(
                market_state=MarketState(
                    share_reserves=1_000_000,
                    bond_reserves=100_000_000,
                    base_buffer=0,
                    bond_buffer=0,
                    init_share_price=1,
                    share_price=1,
                ),
                fee_percent=0.1,
                time_remaining=StretchedTime(days=365, time_stretch=pricing_models[0].calc_time_stretch(0.05)),
            ),
            TestCaseGetMax(
                market_state=MarketState(
                    share_reserves=500_000,
                    bond_reserves=1_000_000,
                    base_buffer=0,
                    bond_buffer=0,
                    init_share_price=1.5,
                    share_price=2,
                ),
                fee_percent=0.1,
                time_remaining=StretchedTime(days=365, time_stretch=pricing_models[0].calc_time_stretch(0.05)),
            ),
            TestCaseGetMax(
                market_state=MarketState(
                    share_reserves=1_000_000,
                    bond_reserves=1_000_000,
                    base_buffer=0,
                    bond_buffer=0,
                    init_share_price=1.5,
                    share_price=2,
                ),
                fee_percent=0.1,
                time_remaining=StretchedTime(days=365, time_stretch=pricing_models[0].calc_time_stretch(0.05)),
            ),
            TestCaseGetMax(
                market_state=MarketState(
                    share_reserves=1_000_000,
                    bond_reserves=1_000_000,
                    base_buffer=0,
                    bond_buffer=0,
                    init_share_price=1.5,
                    share_price=2,
                ),
                fee_percent=0.5,
                time_remaining=StretchedTime(days=365, time_stretch=pricing_models[0].calc_time_stretch(0.05)),
            ),
            TestCaseGetMax(
                market_state=MarketState(
                    share_reserves=1_000_000,
                    bond_reserves=1_000_000,
                    base_buffer=0,
                    bond_buffer=0,
                    init_share_price=1.5,
                    share_price=2,
                ),
                fee_percent=0.1,
                time_remaining=StretchedTime(days=91, time_stretch=pricing_models[0].calc_time_stretch(0.05)),
            ),
            TestCaseGetMax(
                market_state=MarketState(
                    share_reserves=1_000_000,
                    bond_reserves=1_000_000,
                    base_buffer=0,
                    bond_buffer=0,
                    init_share_price=1.5,
                    share_price=2,
                ),
                fee_percent=0.1,
                time_remaining=StretchedTime(days=91, time_stretch=pricing_models[0].calc_time_stretch(0.25)),
            ),
        ]

        for test_case in test_cases:
            for pricing_model in pricing_models:
                market = Market(
                    pricing_model=pricing_model,
                    market_state=test_case.market_state,
                    fee_percent=test_case.fee_percent,
                    position_duration=test_case.time_remaining,
                )

                # Ensure safety for Agents with different budgets.
                for budget in (1e-3 * 10 ** (3 * x) for x in range(0, 5)):
                    agent = Agent(wallet_address=0, budget=budget)

                    # Ensure that get_max_long is safe.
                    max_long = agent.get_max_long(market)
                    self.assertGreaterEqual(agent.wallet.base, max_long)
                    (market_max_long, _) = market.pricing_model.get_max_long(
                        market_state=market.market_state,
                        fee_percent=market.fee_percent,
                        time_remaining=market.position_duration,
                    )
                    self.assertLessEqual(
                        max_long,
                        market_max_long,
                    )

                    # Ensure that get_max_short is safe.
                    max_short = agent.get_max_short(market)
                    trade_result = market.pricing_model.calc_out_given_in(
                        in_=Quantity(amount=max_short, unit=TokenType.PT),
                        market_state=market.market_state,
                        fee_percent=market.fee_percent,
                        time_remaining=market.position_duration,
                    )
                    max_loss = max_short - trade_result.user_result.d_base
                    self.assertGreaterEqual(agent.wallet.base, max_loss)
                    (_, market_max_short) = market.pricing_model.get_max_short(
                        market_state=market.market_state,
                        fee_percent=market.fee_percent,
                        time_remaining=market.position_duration,
                    )
                    self.assertLessEqual(
                        max_short,
                        market_max_short,
                    )

    # Test agent instantiation
    def test_init(self):
        """Tests for Agent instantiation"""

        # instantiate the market

        market = self.setup_market()

        agent = ErrorPolicy(wallet_address=1)

        with self.assertRaises(NotImplementedError):
            agent.action(market)

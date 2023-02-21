"""Testing for the get_max_long function of the pricing models"""
from __future__ import annotations

import copy
from dataclasses import dataclass
import unittest
from elfpy.pricing_models.yieldspace import YieldSpacePricingModel

import elfpy.types as types
import elfpy.simulators.trades as trades
import elfpy.utils.time as time_utils
from elfpy.markets.hyperdrive import MarketDeltas, MarketState
from elfpy.pricing_models.base import PricingModel
from elfpy.pricing_models.hyperdrive import HyperdrivePricingModel

# pylint: disable=duplicate-code


@dataclass
class TestCaseGetMax:
    """Dataclass for get_max_long test cases"""

    market_state: MarketState
    time_remaining: time_utils.StretchedTime

    __test__ = False  # pytest: don't test this class


class TestGetMax(unittest.TestCase):
    """Tests get_max_short and get_max_long functions within the pricing model."""

    def test_get_max(self):
        """
        Tests that get_max_long and get_max_short are safe, by checking
            apr >= 0
            share_price * market_state.share_reserves >= base_buffer
            bond_reserves >= bond_buffer
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
                    trade_fee_percent=0.1,
                    redemption_fee_percent=0.1,
                ),
                time_remaining=time_utils.StretchedTime(
                    days=365, time_stretch=pricing_models[0].calc_time_stretch(0.05), normalizing_constant=365
                ),
            ),
            TestCaseGetMax(
                market_state=MarketState(
                    share_reserves=1_000_000,
                    bond_reserves=1_000_000,
                    base_buffer=100_000,
                    bond_buffer=100_000,
                    init_share_price=1,
                    share_price=1,
                    trade_fee_percent=0.1,
                    redemption_fee_percent=0.1,
                ),
                time_remaining=time_utils.StretchedTime(
                    days=365, time_stretch=pricing_models[0].calc_time_stretch(0.05), normalizing_constant=365
                ),
            ),
            TestCaseGetMax(
                market_state=MarketState(
                    share_reserves=100_000_000,
                    bond_reserves=1_000_000,
                    base_buffer=0,
                    bond_buffer=0,
                    init_share_price=1,
                    share_price=1,
                    trade_fee_percent=0.1,
                    redemption_fee_percent=0.1,
                ),
                time_remaining=time_utils.StretchedTime(
                    days=365, time_stretch=pricing_models[0].calc_time_stretch(0.05), normalizing_constant=365
                ),
            ),
            TestCaseGetMax(
                market_state=MarketState(
                    share_reserves=1_000_000,
                    bond_reserves=834_954,
                    base_buffer=0,
                    bond_buffer=0,
                    init_share_price=1,
                    share_price=1,
                    trade_fee_percent=0.1,
                    redemption_fee_percent=0.1,
                ),
                time_remaining=time_utils.StretchedTime(
                    days=365, time_stretch=pricing_models[0].calc_time_stretch(0.27), normalizing_constant=365
                ),
            ),
            TestCaseGetMax(
                market_state=MarketState(
                    share_reserves=500_000,
                    bond_reserves=1_000_000,
                    base_buffer=0,
                    bond_buffer=0,
                    init_share_price=1.5,
                    share_price=2,
                    trade_fee_percent=0.1,
                    redemption_fee_percent=0.1,
                ),
                time_remaining=time_utils.StretchedTime(
                    days=365, time_stretch=pricing_models[0].calc_time_stretch(0.05), normalizing_constant=365
                ),
            ),
            TestCaseGetMax(
                market_state=MarketState(
                    share_reserves=1_000_000,
                    bond_reserves=1_000_000,
                    base_buffer=0,
                    bond_buffer=0,
                    init_share_price=1.5,
                    share_price=2,
                    trade_fee_percent=0.1,
                    redemption_fee_percent=0.1,
                ),
                time_remaining=time_utils.StretchedTime(
                    days=365, time_stretch=pricing_models[0].calc_time_stretch(0.05), normalizing_constant=365
                ),
            ),
            TestCaseGetMax(
                market_state=MarketState(
                    share_reserves=1_000_000,
                    bond_reserves=1_000_000,
                    base_buffer=0,
                    bond_buffer=0,
                    init_share_price=1.5,
                    share_price=2,
                    trade_fee_percent=0.5,
                    redemption_fee_percent=0.1,
                ),
                time_remaining=time_utils.StretchedTime(
                    days=365, time_stretch=pricing_models[0].calc_time_stretch(0.05), normalizing_constant=365
                ),
            ),
            TestCaseGetMax(
                market_state=MarketState(
                    share_reserves=1_000_000,
                    bond_reserves=1_000_000,
                    base_buffer=0,
                    bond_buffer=0,
                    init_share_price=1.5,
                    share_price=2,
                    trade_fee_percent=0.1,
                    redemption_fee_percent=0.1,
                ),
                time_remaining=time_utils.StretchedTime(
                    days=91, time_stretch=pricing_models[0].calc_time_stretch(0.05), normalizing_constant=365
                ),
            ),
            TestCaseGetMax(
                market_state=MarketState(
                    share_reserves=1_000_000,
                    bond_reserves=1_000_000,
                    base_buffer=0,
                    bond_buffer=0,
                    init_share_price=1.5,
                    share_price=2,
                    trade_fee_percent=0.1,
                    redemption_fee_percent=0.1,
                ),
                time_remaining=time_utils.StretchedTime(
                    days=91, time_stretch=pricing_models[0].calc_time_stretch(0.25), normalizing_constant=365
                ),
            ),
        ]

        for test_case in test_cases:
            for pricing_model in pricing_models:
                # Get the max long.
                (max_long, _) = pricing_model.get_max_long(
                    market_state=test_case.market_state,
                    time_remaining=test_case.time_remaining,
                )

                # Ensure that the max long is valid.
                self.assertGreaterEqual(max_long, 0.0)

                # Simulate the trade and ensure the trade was safe.
                trade_result = pricing_model.calc_out_given_in(
                    in_=types.Quantity(amount=max_long, unit=types.TokenType.BASE),
                    market_state=test_case.market_state,
                    time_remaining=test_case.time_remaining,
                )
                self._ensure_market_safety(
                    pricing_model=pricing_model, trade_result=trade_result, test_case=test_case, is_long=True
                )

                # Get the max short.
                (_, max_short) = pricing_model.get_max_short(
                    market_state=test_case.market_state,
                    time_remaining=test_case.time_remaining,
                )

                # Ensure that the max short is valid.
                self.assertGreaterEqual(max_short, 0.0)

                # Simulate the trade.
                trade_result = pricing_model.calc_out_given_in(
                    in_=types.Quantity(amount=max_short, unit=types.TokenType.PT),
                    market_state=test_case.market_state,
                    time_remaining=test_case.time_remaining,
                )
                self._ensure_market_safety(
                    pricing_model=pricing_model,
                    trade_result=trade_result,
                    test_case=test_case,
                    is_long=False,
                )

    def _ensure_market_safety(
        self,
        pricing_model: PricingModel,
        trade_result: trades.TradeResult,
        test_case: TestCaseGetMax,
        is_long: bool,
    ) -> None:
        market_state = copy.copy(test_case.market_state)

        # Simulate the trade.
        if is_long:
            delta = MarketDeltas(
                d_base_asset=trade_result.market_result.d_base,
                d_bond_asset=trade_result.market_result.d_bonds,
                d_base_buffer=trade_result.breakdown.with_fee,
            )
        else:
            delta = MarketDeltas(
                d_base_asset=trade_result.market_result.d_base,
                d_bond_asset=trade_result.market_result.d_bonds,
                d_bond_buffer=-trade_result.user_result.d_bonds,
            )
        market_state.apply_delta(delta=delta)

        # Ensure that the pool is in a valid state after the trade.
        apr = pricing_model.calc_apr_from_reserves(market_state=market_state, time_remaining=test_case.time_remaining)
        self.assertGreaterEqual(apr, 0.0)

        self.assertGreaterEqual(
            market_state.share_price * market_state.share_reserves,
            market_state.base_buffer,
        )

        self.assertGreaterEqual(
            market_state.bond_reserves,
            market_state.bond_buffer,
        )

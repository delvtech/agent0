"""Testing for the get_max_long function of the pricing models"""
from __future__ import annotations
import copy
import logging
from dataclasses import dataclass
import unittest

import elfpy.markets.trades as trades
import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market
import elfpy.types as types
import elfpy.time as time
import elfpy.utils.outputs as output_utils

from elfpy.markets.hyperdrive.hyperdrive_pricing_model import HyperdrivePricingModel
from elfpy.markets.hyperdrive.hyperdrive_market_deltas import HyperdriveMarketDeltas
from elfpy.math import FixedPoint


@dataclass
class TestCaseGetMax:
    """Dataclass for get_max_long test cases"""

    market_state: hyperdrive_market.HyperdriveMarketState
    time_remaining: time.StretchedTime

    __test__ = False  # pytest: don't test this class


class TestGetMax(unittest.TestCase):
    """Tests get_max_short and get_max_long functions within the pricing model"""

    def test_get_max(self):
        """
        Tests that get_max_long and get_max_short are safe, by checking
            apr >= 0
            share_price * market_state.share_reserves >= base_buffer
            bond_reserves >= bond_buffer
        """
        output_utils.setup_logging(log_filename="test_get_max")
        pricing_model: HyperdrivePricingModel = HyperdrivePricingModel()
        test_cases: list[TestCaseGetMax] = [
            TestCaseGetMax(  # Test 0
                market_state=hyperdrive_market.HyperdriveMarketState(
                    share_reserves=FixedPoint("1_000_000.0"),
                    bond_reserves=FixedPoint("1_000_000.0"),
                    base_buffer=FixedPoint("0.0"),
                    bond_buffer=FixedPoint("0.0"),
                    init_share_price=FixedPoint("1.0"),
                    share_price=FixedPoint("1.0"),
                    curve_fee_multiple=FixedPoint("0.1"),
                    flat_fee_multiple=FixedPoint("0.1"),
                ),
                time_remaining=time.StretchedTime(
                    days=FixedPoint("365.0"),
                    time_stretch=pricing_model.calc_time_stretch(FixedPoint("0.05")),
                    normalizing_constant=FixedPoint("365.0"),
                ),
            ),
            TestCaseGetMax(  # Test 1
                market_state=hyperdrive_market.HyperdriveMarketState(
                    share_reserves=FixedPoint("1_000_000.0"),
                    bond_reserves=FixedPoint("1_000_000.0"),
                    base_buffer=FixedPoint("100_000.0"),
                    bond_buffer=FixedPoint("100_000.0"),
                    init_share_price=FixedPoint("1.0"),
                    share_price=FixedPoint("1.0"),
                    curve_fee_multiple=FixedPoint("0.1"),
                    flat_fee_multiple=FixedPoint("0.1"),
                ),
                time_remaining=time.StretchedTime(
                    days=FixedPoint("365.0"),
                    time_stretch=pricing_model.calc_time_stretch(FixedPoint("0.05")),
                    normalizing_constant=FixedPoint("365.0"),
                ),
            ),
            TestCaseGetMax(  # Test 2
                market_state=hyperdrive_market.HyperdriveMarketState(
                    share_reserves=FixedPoint("100_000_000.0"),
                    bond_reserves=FixedPoint("1_000_000.0"),
                    base_buffer=FixedPoint("0.0"),
                    bond_buffer=FixedPoint("0.0"),
                    init_share_price=FixedPoint("1.0"),
                    share_price=FixedPoint("1.0"),
                    curve_fee_multiple=FixedPoint("0.1"),
                    flat_fee_multiple=FixedPoint("0.1"),
                ),
                time_remaining=time.StretchedTime(
                    days=FixedPoint("365.0"),
                    time_stretch=pricing_model.calc_time_stretch(FixedPoint("0.05")),
                    normalizing_constant=FixedPoint("365.0"),
                ),
            ),
            TestCaseGetMax(  # Test 3
                market_state=hyperdrive_market.HyperdriveMarketState(
                    share_reserves=FixedPoint("1_000_000.0"),
                    bond_reserves=FixedPoint("834_954.0"),
                    base_buffer=FixedPoint("0.0"),
                    bond_buffer=FixedPoint("0.0"),
                    init_share_price=FixedPoint("1.0"),
                    share_price=FixedPoint("1.0"),
                    curve_fee_multiple=FixedPoint("0.1"),
                    flat_fee_multiple=FixedPoint("0.1"),
                ),
                time_remaining=time.StretchedTime(
                    days=FixedPoint("365.0"),
                    time_stretch=pricing_model.calc_time_stretch(FixedPoint("0.27")),
                    normalizing_constant=FixedPoint("365.0"),
                ),
            ),
            TestCaseGetMax(  # Test 4
                market_state=hyperdrive_market.HyperdriveMarketState(
                    share_reserves=FixedPoint("500_000.0"),
                    bond_reserves=FixedPoint("1_000_000.0"),
                    base_buffer=FixedPoint("0.0"),
                    bond_buffer=FixedPoint("0.0"),
                    init_share_price=FixedPoint("1.5"),
                    share_price=FixedPoint("2.0"),
                    curve_fee_multiple=FixedPoint("0.1"),
                    flat_fee_multiple=FixedPoint("0.1"),
                ),
                time_remaining=time.StretchedTime(
                    days=FixedPoint("365.0"),
                    time_stretch=pricing_model.calc_time_stretch(FixedPoint("0.05")),
                    normalizing_constant=FixedPoint("365.0"),
                ),
            ),
            TestCaseGetMax(  # Test 5
                market_state=hyperdrive_market.HyperdriveMarketState(
                    share_reserves=FixedPoint("1_000_000.0"),
                    bond_reserves=FixedPoint("1_000_000.0"),
                    base_buffer=FixedPoint("0.0"),
                    bond_buffer=FixedPoint("0.0"),
                    init_share_price=FixedPoint("1.5"),
                    share_price=FixedPoint("2.0"),
                    curve_fee_multiple=FixedPoint("0.1"),
                    flat_fee_multiple=FixedPoint("0.1"),
                ),
                time_remaining=time.StretchedTime(
                    days=FixedPoint("365.0"),
                    time_stretch=pricing_model.calc_time_stretch(FixedPoint("0.05")),
                    normalizing_constant=FixedPoint("365.0"),
                ),
            ),
            TestCaseGetMax(  # Test 6
                market_state=hyperdrive_market.HyperdriveMarketState(
                    share_reserves=FixedPoint("1_000_000.0"),
                    bond_reserves=FixedPoint("1_000_000.0"),
                    base_buffer=FixedPoint("0.0"),
                    bond_buffer=FixedPoint("0.0"),
                    init_share_price=FixedPoint("1.5"),
                    share_price=FixedPoint("2.0"),
                    curve_fee_multiple=FixedPoint("0.5"),
                    flat_fee_multiple=FixedPoint("0.1"),
                ),
                time_remaining=time.StretchedTime(
                    days=FixedPoint("365.0"),
                    time_stretch=pricing_model.calc_time_stretch(FixedPoint("0.05")),
                    normalizing_constant=FixedPoint("365.0"),
                ),
            ),
            TestCaseGetMax(  # Test 7
                market_state=hyperdrive_market.HyperdriveMarketState(
                    share_reserves=FixedPoint("1_000_000.0"),
                    bond_reserves=FixedPoint("1_000_000.0"),
                    base_buffer=FixedPoint("0.0"),
                    bond_buffer=FixedPoint("0.0"),
                    init_share_price=FixedPoint("1.5"),
                    share_price=FixedPoint("2.0"),
                    curve_fee_multiple=FixedPoint("0.1"),
                    flat_fee_multiple=FixedPoint("0.1"),
                ),
                time_remaining=time.StretchedTime(
                    days=FixedPoint("91.0"),
                    time_stretch=pricing_model.calc_time_stretch(FixedPoint("0.05")),
                    normalizing_constant=FixedPoint("365.0"),
                ),
            ),
            TestCaseGetMax(  # Test 8
                market_state=hyperdrive_market.HyperdriveMarketState(
                    share_reserves=FixedPoint("1_000_000.0"),
                    bond_reserves=FixedPoint("1_000_000.0"),
                    base_buffer=FixedPoint("0.0"),
                    bond_buffer=FixedPoint("0.0"),
                    init_share_price=FixedPoint("1.5"),
                    share_price=FixedPoint("2.0"),
                    curve_fee_multiple=FixedPoint("0.1"),
                    flat_fee_multiple=FixedPoint("0.1"),
                ),
                time_remaining=time.StretchedTime(
                    days=FixedPoint("91.0"),
                    time_stretch=pricing_model.calc_time_stretch(FixedPoint("0.25")),
                    normalizing_constant=FixedPoint("365.0"),
                ),
            ),
        ]
        for test_number, test_case in enumerate(test_cases):
            logging.info("\ntest=%s with \n %s \n and %s", test_number, test_case, pricing_model)
            # Initialize lp_total_supply to y + x
            test_case.market_state.lp_total_supply = (
                test_case.market_state.share_reserves * test_case.market_state.share_price
                + test_case.market_state.bond_reserves
            )
            # Get the max long.
            (max_long, _) = pricing_model.get_max_long(
                market_state=test_case.market_state,
                time_remaining=test_case.time_remaining,
            )

            # Ensure that the max long is valid.
            self.assertGreaterEqual(max_long, FixedPoint("0.0"))

            # Simulate the trade and ensure the trade was safe.
            trade_result = pricing_model.calc_out_given_in(
                in_=types.Quantity(amount=max_long, unit=types.TokenType.BASE),
                market_state=test_case.market_state,
                time_remaining=test_case.time_remaining,
            )
            logging.info("long test")
            self._ensure_market_safety(
                pricing_model=pricing_model, trade_result=trade_result, test_case=test_case, is_long=True
            )

            # Get the max short.
            (_, max_short) = pricing_model.get_max_short(
                market_state=test_case.market_state,
                time_remaining=test_case.time_remaining,
            )

            # Ensure that the max short is valid.
            self.assertGreaterEqual(max_short, FixedPoint("0.0"))

            # Simulate the trade.
            trade_result = pricing_model.calc_out_given_in(
                in_=types.Quantity(amount=max_short, unit=types.TokenType.PT),
                market_state=test_case.market_state,
                time_remaining=test_case.time_remaining,
            )
            logging.info("short test")
            self._ensure_market_safety(
                pricing_model=pricing_model,
                trade_result=trade_result,
                test_case=test_case,
                is_long=False,
            )
        output_utils.close_logging()

    def _ensure_market_safety(
        self,
        pricing_model: HyperdrivePricingModel,
        trade_result: trades.TradeResult,
        test_case: TestCaseGetMax,
        is_long: bool,
    ) -> None:
        market_state = copy.copy(test_case.market_state)

        # Simulate the trade.
        if is_long:
            delta = HyperdriveMarketDeltas(
                d_base_asset=trade_result.market_result.d_base,
                d_bond_asset=trade_result.market_result.d_bonds,
                d_base_buffer=trade_result.breakdown.with_fee,
            )
        else:  # is a short
            delta = HyperdriveMarketDeltas(
                d_base_asset=trade_result.market_result.d_base,
                d_bond_asset=trade_result.market_result.d_bonds,
                d_bond_buffer=-trade_result.user_result.d_bonds,
            )
        market_state.apply_delta(delta=delta)

        # Ensure that the pool is in a valid state after the trade.
        apr = pricing_model.calc_apr_from_reserves(market_state=market_state, time_remaining=test_case.time_remaining)
        self.assertGreaterEqual(apr, FixedPoint("0.0"))

        self.assertGreaterEqual(
            market_state.share_price * market_state.share_reserves,
            market_state.base_buffer,
        )

        self.assertGreaterEqual(
            market_state.bond_reserves,
            market_state.bond_buffer,
        )

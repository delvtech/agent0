"""Testing for the get_max_long function of the pricing models"""
from __future__ import annotations

import logging
from dataclasses import dataclass
import unittest

import pytest

from elfpy.pricing_models.yieldspace import YieldspacePricingModel
import elfpy
import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market
import elfpy.markets.hyperdrive.hyperdrive_actions as hyperdrive_actions
import elfpy.time as time
import elfpy.utils.outputs as output_utils
from elfpy.pricing_models.base import PricingModel
from elfpy.pricing_models.hyperdrive import HyperdrivePricingModel


@dataclass
class TestCaseGetMax:
    """Dataclass for get_max_long test cases"""

    case_number: int
    market_state: hyperdrive_market.MarketState
    time_remaining: time.StretchedTime

    __test__ = False  # pytest: don't test this class


PRICING_MODELS: list[PricingModel] = [HyperdrivePricingModel(), YieldspacePricingModel()]
TEST_CASES: list[TestCaseGetMax] = [
    TestCaseGetMax(
        case_number=0,
        market_state=hyperdrive_market.MarketState(
            share_reserves=1_000_000,
            bond_reserves=1_000_000,
            base_buffer=0,
            bond_buffer=0,
            init_share_price=1,
            share_price=1,
            curve_fee_multiple=0.1,
            flat_fee_multiple=0.1,
        ),
        time_remaining=time.StretchedTime(
            days=365, time_stretch=PRICING_MODELS[0].calc_time_stretch(0.05), normalizing_constant=365
        ),
    ),
    TestCaseGetMax(
        case_number=1,
        market_state=hyperdrive_market.MarketState(
            share_reserves=1_000_000,
            bond_reserves=1_000_000,
            base_buffer=100_000,
            bond_buffer=100_000,
            init_share_price=1,
            share_price=1,
            curve_fee_multiple=0.1,
            flat_fee_multiple=0.1,
        ),
        time_remaining=time.StretchedTime(
            days=365, time_stretch=PRICING_MODELS[0].calc_time_stretch(0.05), normalizing_constant=365
        ),
    ),
    TestCaseGetMax(
        case_number=2,
        market_state=hyperdrive_market.MarketState(
            share_reserves=100_000_000,
            bond_reserves=1_000_000,
            base_buffer=0,
            bond_buffer=0,
            init_share_price=1,
            share_price=1,
            curve_fee_multiple=0.1,
            flat_fee_multiple=0.1,
        ),
        time_remaining=time.StretchedTime(
            days=365, time_stretch=PRICING_MODELS[0].calc_time_stretch(0.05), normalizing_constant=365
        ),
    ),
    TestCaseGetMax(
        case_number=3,
        market_state=hyperdrive_market.MarketState(
            share_reserves=1_000_000,
            bond_reserves=834_954,
            base_buffer=0,
            bond_buffer=0,
            init_share_price=1,
            share_price=1,
            curve_fee_multiple=0.1,
            flat_fee_multiple=0.1,
        ),
        time_remaining=time.StretchedTime(
            days=365, time_stretch=PRICING_MODELS[0].calc_time_stretch(0.27), normalizing_constant=365
        ),
    ),
    TestCaseGetMax(
        case_number=4,
        market_state=hyperdrive_market.MarketState(
            share_reserves=500_000,
            bond_reserves=1_000_000,
            base_buffer=0,
            bond_buffer=0,
            init_share_price=1.5,
            share_price=2,
            curve_fee_multiple=0.1,
            flat_fee_multiple=0.1,
        ),
        time_remaining=time.StretchedTime(
            days=365, time_stretch=PRICING_MODELS[0].calc_time_stretch(0.05), normalizing_constant=365
        ),
    ),
    TestCaseGetMax(
        case_number=5,
        market_state=hyperdrive_market.MarketState(
            share_reserves=1_000_000,
            bond_reserves=1_000_000,
            base_buffer=0,
            bond_buffer=0,
            init_share_price=1.5,
            share_price=2,
            curve_fee_multiple=0.1,
            flat_fee_multiple=0.1,
        ),
        time_remaining=time.StretchedTime(
            days=365, time_stretch=PRICING_MODELS[0].calc_time_stretch(0.05), normalizing_constant=365
        ),
    ),
    TestCaseGetMax(
        case_number=6,
        market_state=hyperdrive_market.MarketState(
            share_reserves=1_000_000,
            bond_reserves=1_000_000,
            base_buffer=0,
            bond_buffer=0,
            init_share_price=1.5,
            share_price=2,
            curve_fee_multiple=0.5,
            flat_fee_multiple=0.1,
        ),
        time_remaining=time.StretchedTime(
            days=365, time_stretch=PRICING_MODELS[0].calc_time_stretch(0.05), normalizing_constant=365
        ),
    ),
    TestCaseGetMax(
        case_number=7,
        market_state=hyperdrive_market.MarketState(
            share_reserves=1_000_000,
            bond_reserves=1_000_000,
            base_buffer=0,
            bond_buffer=0,
            init_share_price=1.5,
            share_price=2,
            curve_fee_multiple=0.1,
            flat_fee_multiple=0.1,
        ),
        time_remaining=time.StretchedTime(
            days=91, time_stretch=PRICING_MODELS[0].calc_time_stretch(0.05), normalizing_constant=365
        ),
    ),
    TestCaseGetMax(
        case_number=8,
        market_state=hyperdrive_market.MarketState(
            share_reserves=1_000_000,
            bond_reserves=1_000_000,
            base_buffer=0,
            bond_buffer=0,
            init_share_price=1.5,
            share_price=2,
            curve_fee_multiple=0.1,
            flat_fee_multiple=0.1,
        ),
        time_remaining=time.StretchedTime(
            days=91, time_stretch=PRICING_MODELS[0].calc_time_stretch(0.25), normalizing_constant=365
        ),
    ),
]


class Test(unittest.TestCase):
    """Test class holds all the objects needed for testing get_max_long and get_max_short.

    It is instantiated once per test case, and the test case is defined by the TestCaseGetMax object."""

    case_number: int
    market_state: hyperdrive_market.MarketState
    market: hyperdrive_market.Market

    def __init__(self, test_case: TestCaseGetMax, pricing_model, *args, **kwargs):
        output_utils.setup_logging(log_filename="test_get_max")

        # Initialize lp_total_supply to y + x
        test_case.market_state.lp_total_supply = (
            test_case.market_state.share_reserves * test_case.market_state.share_price
            + test_case.market_state.bond_reserves
        )

        self.case_number = test_case.case_number
        self.market_state = test_case.market_state
        self.market = hyperdrive_market.Market(
            market_state=test_case.market_state,
            position_duration=test_case.time_remaining,
            pricing_model=pricing_model,
            block_time=time.BlockTime(0),
        )
        super().__init__(*args, **kwargs)


@pytest.mark.parametrize("pricing_model", PRICING_MODELS, ids=lambda model: f"model={model.model_name()}")
@pytest.mark.parametrize("test_case", TEST_CASES, ids=lambda case: f"case={case.case_number}")
def test_max_long_trade(test_case, pricing_model):
    """Successfully execute a max long trade."""
    test = Test(test_case, pricing_model)
    logging.info("\nlong test, case=%s with \n %s \n and %s", test.case_number, test_case, pricing_model)

    # Get the max long.
    max_long, _ = pricing_model.get_max_long(market_state=test.market_state, time_remaining=test_case.time_remaining)

    # Ensure that the max long is valid.
    test.assertGreaterEqual(max_long, 0.0)

    # Simulate the trade and ensure the trade was safe.
    market_deltas, _ = hyperdrive_actions.calc_open_long(wallet_address=0, base_amount=max_long, market=test.market)
    test.market_state.apply_delta(market_deltas)
    elfpy.check_non_zero(test.market_state)

    # Ensure that the pool is in a valid state after the trade.
    apr = pricing_model.calc_apr_from_reserves(market_state=test.market_state, time_remaining=test_case.time_remaining)
    test.assertGreaterEqual(apr, 0.0)

    # Show you can't trade a single unit more.
    with test.assertRaises(AssertionError):
        market_deltas, _ = hyperdrive_actions.calc_open_long(wallet_address=0, base_amount=1, market=test.market)
        test.market_state.apply_delta(market_deltas)
        elfpy.check_non_zero(test.market_state)


@pytest.mark.parametrize("pricing_model", PRICING_MODELS, ids=lambda model: f"model={model.model_name()}")
@pytest.mark.parametrize("test_case", TEST_CASES, ids=lambda case: f"case={case.case_number}")
def test_max_short_trade(test_case, pricing_model):
    """Successfully execute a max short trade."""
    test = Test(test_case, pricing_model)
    logging.info("\nshort test, case=%s with \n %s \n and %s", test.case_number, test_case, pricing_model)

    # Get the max short.
    max_short_base, max_short_bonds = pricing_model.get_max_short(
        market_state=test.market_state, time_remaining=test_case.time_remaining
    )

    # Ensure that the max short is valid.
    test.assertGreaterEqual(max_short_base, 0.0)
    test.assertGreaterEqual(max_short_bonds, 0.0)

    # Simulate the trade.
    market_deltas, _ = hyperdrive_actions.calc_open_short(
        wallet_address=0, bond_amount=max_short_bonds, market=test.market
    )
    test.market_state.apply_delta(market_deltas)
    elfpy.check_non_zero(test.market_state)

    # Ensure that the pool is in a valid state after the trade.
    apr = pricing_model.calc_apr_from_reserves(market_state=test.market_state, time_remaining=test_case.time_remaining)
    test.assertGreaterEqual(apr, 0.0)

    # Show you can't trade a single unit more.
    with test.assertRaises(AssertionError):
        market_deltas, _ = hyperdrive_actions.calc_open_short(wallet_address=0, bond_amount=1, market=test.market)
        test.market_state.apply_delta(market_deltas)
        elfpy.check_non_zero(test.market_state)


if __name__ == "__main__":
    unittest.main()

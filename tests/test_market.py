"""Testing for the ElfPy package market module methods"""
from __future__ import annotations  # types are strings by default in 3.11

import unittest

import numpy as np

import elfpy.pricing_models.base as base_pm
import elfpy.pricing_models.hyperdrive as hyperdrive_pm
import elfpy.pricing_models.yieldspace as yieldspace_pm
import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market
import elfpy.markets.borrow as borrow
import elfpy.time as time
from elfpy.time.time import BlockTime


class BaseMarketTest(unittest.TestCase):
    """Generic Parameter Test class"""

    # TODO: Switching to fixed point or 64 bit float should allow us to increase this to WEI
    # issue #112
    APPROX_EQ: float = 1e-15

    def test_position_duration(self):
        """Test to make sure market init fails when normalizing_constant != days"""
        pd_good = time.StretchedTime(
            days=365,
            time_stretch=1,
            normalizing_constant=365,
        )
        pd_nonorm = time.StretchedTime(
            days=365,
            time_stretch=1,
            normalizing_constant=36,
        )
        _ = hyperdrive_market.Market(
            pricing_model=base_pm.PricingModel(),
            market_state=hyperdrive_market.MarketState(),
            block_time=BlockTime(),
            position_duration=pd_good,
        )
        with self.assertRaises(AssertionError):
            _ = hyperdrive_market.Market(
                pricing_model=base_pm.PricingModel(),
                market_state=hyperdrive_market.MarketState(),
                block_time=BlockTime(),
                position_duration=pd_nonorm,
            )

    def test_market_state_copy(self):
        """Test the market state ability to deep copy itself"""
        market_state = hyperdrive_market.MarketState()
        market_state_copy = market_state.copy()
        assert market_state is not market_state_copy  # not the same object
        assert market_state == market_state_copy  # they have the same attribute values
        market_state_copy.share_reserves += 10
        assert market_state != market_state_copy  # now they should have different attribute values

    def test_initialize(self):
        """Unit tests for the pricing model calc_liquidity function

        Example check for the test:
            test 1: 5M target_liquidity; 5% APR;
            6mo remaining; 22.186877016851916 time_stretch (targets 5% APR);
            1 init share price; 1 share price
            l = target_liquidity = 5_000_000
            r = target_apr = 0.05
            days = 182.5
            normalizing_constant = 182.5  # normalizing_constant = days on market init
            init_share_price = 1
            share_price = 1

            time_stretch = 3.09396 / (0.02789 * r * 100)
            t = days / 365
            T = days / normalizing_constant / time_stretch
            u = init_share_price
            c = share_price  # share price of the LP in the yield source
            z = share_reserves = l / c
            y = bond_reserves = (z / 2) * (u * (1 + r * t) ** (1 / T) - c)
            total_liquidity = c * z

            p = ((2 * y + c * z) / (u * z)) ** (-T)  # spot price from reserves
            final_apr = (1 - p) / (p * t)
        """

        test_cases = [
            # test 1: 5M target_liquidity; 5% APR;
            #   6mo duration; 22.186877016851916 time_stretch (targets 5% APR);
            #   1 init share price; 1 share price; Hyperdrive
            {
                "target_liquidity": 5_000_000,  # Targeting 5M liquidity
                "target_apr": 0.05,  # fixed rate APR you'd get from purchasing bonds; r = 0.05
                "position_duration": time.StretchedTime(
                    days=182.5,
                    time_stretch=22.186877016851916,
                    normalizing_constant=182.5,
                ),
                "init_share_price": 1,  # original share price pool started; u = 1
                "share_price": 1,  # share price of the LP in the yield source; c = 1
                "pricing_model": hyperdrive_pm.HyperdrivePricingModel(),
                "expected_share_reserves": 5_000_000,  # target_liquidity / share_price
                "expected_bond_reserves": 1_823_834.7868545868,
            },
            # test 2: 5M target_liquidity; 2% APR;
            #   6mo duration; 22.186877016851916 time_stretch (targets 5% APR);
            #   1 init share price; 1 share price; Yieldspace
            {
                "target_liquidity": 5_000_000,  # Targeting 5M liquidity
                "target_apr": 0.02,  # fixed rate APR you'd get from purchasing bonds; r = 0.02
                "position_duration": time.StretchedTime(
                    days=182.5,
                    time_stretch=55.467192542129794,
                    normalizing_constant=182.5,
                ),
                "init_share_price": 1,  # original share price pool started; u = 1
                "share_price": 1,  # share price of the LP in the yield source; c = 1
                "pricing_model": yieldspace_pm.YieldspacePricingModel(),
                "expected_share_reserves": 5_000_000.0,  # target_liquidity / share_price
                "expected_bond_reserves": 1_841_446.767658661,
            },
            # test 3: 5M target_liquidity; 8% APR;
            #   6mo duration; 22.186877016851916 time_stretch (targets 5% APR);
            #   1 init share price; 1 share price; Hyperdrive
            {
                "target_liquidity": 5_000_000,  # Targeting 5M liquidity
                "target_apr": 0.08,  # fixed rate APR you'd get from purchasing bonds; r = 0.08
                "position_duration": time.StretchedTime(
                    days=182.5,
                    time_stretch=13.866798135532449,
                    normalizing_constant=182.5,
                ),
                "init_share_price": 1,  # original share price pool started; u = 1
                "share_price": 1,  # share price of the LP in the yield source; c = 1
                "pricing_model": hyperdrive_pm.HyperdrivePricingModel(),
                "expected_share_reserves": 5_000_000.0,
                "expected_bond_reserves": 1_806_633.2221533637,
            },
            # test 4:  10M target_liquidity; 3% APR
            #   3mo duration; 36.97812836141986 time_stretch (targets 3% APR);
            #   2 init share price; 2 share price; Hyperdrive
            {
                "target_liquidity": 10_000_000,  # targeting 10M liquidity
                "target_apr": 0.03,  # fixed rate APR you'd get from purchasing bonds; r = 0.03
                "position_duration": time.StretchedTime(
                    days=91.25,
                    time_stretch=36.97812836141987,
                    normalizing_constant=91.25,
                ),
                "init_share_price": 2,  # original share price when pool started
                "share_price": 2,  # share price of the LP in the yield source
                "pricing_model": hyperdrive_pm.HyperdrivePricingModel(),
                "expected_share_reserves": 5_000_000.0,
                "expected_bond_reserves": 1_591_223.795848793,
            },
            # test 5:  10M target_liquidity; 5% APR
            #   9mo duration; 36.97812836141986 time_stretch (targets 3% APR);
            #   1.3 init share price; 1.3 share price; Hyperdrive
            {
                "target_liquidity": 10_000_000,  # Targeting 10M liquidity
                "target_apr": 0.001,  # fixed rate APR you'd get from purchasing bonds; r = 0.03
                "position_duration": time.StretchedTime(
                    days=273.75,
                    time_stretch=1109.3438508425959,
                    normalizing_constant=273.75,
                ),
                "init_share_price": 1.3,  # original share price when pool started
                "share_price": 1.3,  # share price of the LP in the yield source
                "pricing_model": hyperdrive_pm.HyperdrivePricingModel(),
                "expected_share_reserves": 7_692_307.692307692,
                "expected_bond_reserves": 6_486_058.016848019,
            },
            # test 6:  10M target_liquidity; 3% APR
            #   3mo duration; 36.97812836141986 time_stretch (targets 3% APR);
            #   2 init share price; 2 share price; Yieldspace
            {
                "target_liquidity": 10_000_000,  # Targeting 10M liquidity
                "target_apr": 0.03,  # fixed rate APR you'd get from purchasing bonds; r = 0.03
                "position_duration": time.StretchedTime(
                    days=91.25,
                    time_stretch=36.97812836141987,
                    normalizing_constant=91.25,
                ),
                "init_share_price": 2,  # original share price when pool started
                "share_price": 2,  # share price of the LP in the yield source
                "pricing_model": yieldspace_pm.YieldspacePricingModel(),
                "expected_share_reserves": 5_000_000.0,
                "expected_bond_reserves": 1_591_223.795848793,
            },
            # test 7:  Borrow market is initialized empty
            {
                "pricing_model": borrow.BorrowPricingModel(),
                "borrow_amount": 0.0,
                "borrow_shares": 0.0,
                "borrow_outstanding": 0.0,
            },
        ]
        # Loop through the test cases & pricing model
        for test_index, test_case in enumerate(test_cases):
            test_number = test_index + 1
            if isinstance(test_case["pricing_model"], borrow.BorrowPricingModel):
                market = borrow.Market(block_time=BlockTime(), market_state=borrow.MarketState())
                market_deltas, _ = market.initialize(wallet_address=0)
                market.market_state.apply_delta(market_deltas)
                np.testing.assert_equal(
                    actual=market.market_state.borrow_amount,
                    desired=test_case["borrow_amount"],
                    err_msg=f"{test_number=}\nunexpected borrow_amount",
                )
                np.testing.assert_almost_equal(
                    actual=market.market_state.borrow_shares,
                    desired=test_case["borrow_shares"],
                    err_msg=f"{test_number=}\nunexpected borrow_shares",
                )
                np.testing.assert_almost_equal(
                    actual=market.market_state.borrow_outstanding,
                    desired=test_case["borrow_outstanding"],
                    err_msg=f"{test_number=}\nunexpected collateral_amount",
                )
            else:
                market = hyperdrive_market.Market(
                    position_duration=test_case["position_duration"],
                    market_state=hyperdrive_market.MarketState(
                        init_share_price=test_case["init_share_price"],
                        share_price=test_case["share_price"],
                    ),
                    block_time=BlockTime(),
                    pricing_model=test_case["pricing_model"],
                )
                _ = market.initialize(
                    wallet_address=0,
                    contribution=test_case["target_liquidity"],
                    target_apr=test_case["target_apr"],
                )
                self.assertAlmostEqual(
                    market.fixed_apr,
                    test_case["target_apr"],
                    delta=self.APPROX_EQ,
                    msg=f"{test_number=}\nunexpected market fixed_apr",
                )
                np.testing.assert_almost_equal(
                    actual=market.market_state.share_reserves,
                    desired=test_case["expected_share_reserves"],
                    err_msg=f"{test_number=}\nunexpected share_reserves",
                )
                np.testing.assert_almost_equal(
                    actual=market.market_state.bond_reserves,
                    desired=test_case["expected_bond_reserves"],
                    err_msg=f"{test_number=}\nunexpected bond_reserves",
                )

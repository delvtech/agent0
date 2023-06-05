"""Testing for the ElfPy package market module methods"""
from __future__ import annotations

import unittest
from elfpy.markets.borrow import BorrowMarket, BorrowMarketState, BorrowPricingModel

import elfpy.time as time

from elfpy.markets.hyperdrive import (
    Checkpoint,
    HyperdriveMarket,
    HyperdriveMarketState,
    HyperdrivePricingModel,
    YieldspacePricingModel,
)
from elfpy.math import FixedPoint

# TODO: remove this after FixedPoint PRs are finished


class MarketTest(unittest.TestCase):
    """Generic Parameter Test class"""

    # TODO: This approx should be much lower
    # issue #112
    APPROX_EQ: FixedPoint = FixedPoint(1e-6)

    def test_position_duration(self):
        """Test to make sure market init fails when normalizing_constant != days"""
        pd_good = time.StretchedTime(
            days=FixedPoint("365.0"),
            time_stretch=FixedPoint("1.0"),
            normalizing_constant=FixedPoint("365.0"),
        )
        pd_nonorm = time.StretchedTime(
            days=FixedPoint("365.0"),
            time_stretch=FixedPoint("1.0"),
            normalizing_constant=FixedPoint("36.0"),
        )
        for pricing_model in [YieldspacePricingModel(), HyperdrivePricingModel()]:
            _ = HyperdriveMarket(
                pricing_model=pricing_model,
                market_state=HyperdriveMarketState(),
                block_time=time.BlockTime(),
                position_duration=pd_good,
            )
            with self.assertRaises(AssertionError):
                _ = HyperdriveMarket(
                    pricing_model=pricing_model,
                    market_state=HyperdriveMarketState(),
                    block_time=time.BlockTime(),
                    position_duration=pd_nonorm,
                )

    def test_market_state_copy(self):
        """Test the market state ability to deep copy itself"""
        market_state = HyperdriveMarketState()
        market_state_copy = market_state.copy()
        assert market_state is not market_state_copy  # not the same object
        assert market_state == market_state_copy  # they have the same attribute values
        market_state_copy.share_reserves += FixedPoint("10.0")
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
            # test 0: 5M target_liquidity; 5% APR;
            #   6mo duration; 22.186877016851916 time_stretch (targets 5% APR);
            #   1 init share price; 1 share price; Hyperdrive
            {
                "target_liquidity": FixedPoint("5_000_000.0"),  # Targeting 5M liquidity
                "target_apr": FixedPoint("0.05"),  # fixed rate APR you'd get from purchasing bonds; r = 0.05
                "position_duration": time.StretchedTime(
                    days=FixedPoint("182.5"),
                    time_stretch=FixedPoint("22.186877016851916"),
                    normalizing_constant=FixedPoint("182.5"),
                ),
                "init_share_price": FixedPoint("1.0"),  # original share price pool started; u = 1
                "share_price": FixedPoint("1.0"),  # share price of the LP in the yield source; c = 1
                "pricing_model": HyperdrivePricingModel(),
                "expected_share_reserves": FixedPoint("5_000_000.0"),  # target_liquidity / share_price
                "expected_bond_reserves": FixedPoint("1_823_834.7868545868"),
            },
            # test 1: 5M target_liquidity; 2% APR;
            #   6mo duration; 22.186877016851916 time_stretch (targets 5% APR);
            #   1 init share price; 1 share price; Yieldspace
            {
                "target_liquidity": FixedPoint("5_000_000.0"),  # Targeting 5M liquidity
                "target_apr": FixedPoint("0.02"),  # fixed rate APR you'd get from purchasing bonds; r = 0.02
                "position_duration": time.StretchedTime(
                    days=FixedPoint("182.5"),
                    time_stretch=FixedPoint("55.467192542129794"),
                    normalizing_constant=FixedPoint("182.5"),
                ),
                "init_share_price": FixedPoint("1.0"),  # original share price pool started; u = 1
                "share_price": FixedPoint("1.0"),  # share price of the LP in the yield source; c = 1
                "pricing_model": YieldspacePricingModel(),
                "expected_share_reserves": FixedPoint("5_000_000.0"),  # target_liquidity / share_price
                "expected_bond_reserves": FixedPoint("1_841_446.767658661"),
            },
            # test 2: 5M target_liquidity; 8% APR;
            #   6mo duration; 22.186877016851916 time_stretch (targets 5% APR);
            #   1 init share price; 1 share price; Hyperdrive
            {
                "target_liquidity": FixedPoint("5_000_000.0"),  # Targeting 5M liquidity
                "target_apr": FixedPoint("0.08"),  # fixed rate APR you'd get from purchasing bonds; r = 0.08
                "position_duration": time.StretchedTime(
                    days=FixedPoint("182.5"),
                    time_stretch=FixedPoint("13.866798135532449"),
                    normalizing_constant=FixedPoint("182.5"),
                ),
                "init_share_price": FixedPoint("1.0"),  # original share price pool started; u = 1
                "share_price": FixedPoint("1.0"),  # share price of the LP in the yield source; c = 1
                "pricing_model": HyperdrivePricingModel(),
                "expected_share_reserves": FixedPoint("5_000_000.0"),
                "expected_bond_reserves": FixedPoint("1_806_633.2221533637"),
            },
            # test 3:  10M target_liquidity; 3% APR
            #   3mo duration; 36.97812836141986 time_stretch (targets 3% APR);
            #   2 init share price; 2 share price; Hyperdrive
            {
                "target_liquidity": FixedPoint("10_000_000.0"),  # targeting 10M liquidity
                "target_apr": FixedPoint("0.03"),  # fixed rate APR you'd get from purchasing bonds; r = 0.03
                "position_duration": time.StretchedTime(
                    days=FixedPoint("91.25"),
                    time_stretch=FixedPoint("36.97812836141987"),
                    normalizing_constant=FixedPoint("91.25"),
                ),
                "init_share_price": FixedPoint("2.0"),  # original share price when pool started
                "share_price": FixedPoint("2.0"),  # share price of the LP in the yield source
                "pricing_model": HyperdrivePricingModel(),
                "expected_share_reserves": FixedPoint("5_000_000.0"),
                "expected_bond_reserves": FixedPoint("1_591_223.795848793"),
            },
            # test 4:  10M target_liquidity; 5% APR
            #   9mo duration; 36.97812836141986 time_stretch (targets 3% APR);
            #   1.3 init share price; 1.3 share price; Hyperdrive
            {
                "target_liquidity": FixedPoint("10_000_000.0"),  # Targeting 10M liquidity
                "target_apr": FixedPoint("0.001"),  # fixed rate APR you'd get from purchasing bonds; r = 0.03
                "position_duration": time.StretchedTime(
                    days=FixedPoint("273.75"),
                    time_stretch=FixedPoint("1109.3438508425959"),
                    normalizing_constant=FixedPoint("273.75"),
                ),
                "init_share_price": FixedPoint("1.3"),  # original share price when pool started
                "share_price": FixedPoint("1.3"),  # share price of the LP in the yield source
                "pricing_model": HyperdrivePricingModel(),
                "expected_share_reserves": FixedPoint("7_692_307.692307692"),
                "expected_bond_reserves": FixedPoint("6_486_058.016848019"),
            },
            # test 5:  10M target_liquidity; 3% APR
            #   3mo duration; 36.97812836141986 time_stretch (targets 3% APR);
            #   2 init share price; 2 share price; Yieldspace
            {
                "target_liquidity": FixedPoint("10_000_000.0"),  # Targeting 10M liquidity
                "target_apr": FixedPoint("0.03"),  # fixed rate APR you'd get from purchasing bonds; r = 0.03
                "position_duration": time.StretchedTime(
                    days=FixedPoint("91.25"),
                    time_stretch=FixedPoint("36.97812836141987"),
                    normalizing_constant=FixedPoint("91.25"),
                ),
                "init_share_price": FixedPoint("2.0"),  # original share price when pool started
                "share_price": FixedPoint("2.0"),  # share price of the LP in the yield source
                "pricing_model": YieldspacePricingModel(),
                "expected_share_reserves": FixedPoint("5_000_000.0"),
                "expected_bond_reserves": FixedPoint("1_591_223.795848793"),
            },
            # test 6:  Borrow market is initialized empty
            {
                "pricing_model": BorrowPricingModel(),
                "borrow_amount": FixedPoint("0.0"),
                "borrow_shares": FixedPoint("0.0"),
                "borrow_outstanding": FixedPoint("0.0"),
            },
        ]
        # Loop through the test cases & pricing model
        for test_number, test_case in enumerate(test_cases):
            if isinstance(test_case["pricing_model"], BorrowPricingModel):
                market = BorrowMarket(
                    pricing_model=test_case["pricing_model"],
                    block_time=time.BlockTime(),
                    market_state=BorrowMarketState(),
                )
                market_deltas, _ = market.initialize()
                market.market_state.apply_delta(market_deltas)
                self.assertAlmostEqual(
                    market.market_state.borrow_amount,
                    test_case["borrow_amount"],
                    delta=self.APPROX_EQ,
                    msg=f"{test_number=}\nunexpected borrow_amount",
                )
                self.assertAlmostEqual(
                    market.market_state.borrow_shares,
                    test_case["borrow_shares"],
                    delta=self.APPROX_EQ,
                    msg=f"{test_number=}\nunexpected borrow_shares",
                )
                self.assertAlmostEqual(
                    market.market_state.borrow_outstanding,
                    test_case["borrow_outstanding"],
                    delta=self.APPROX_EQ,
                    msg=f"{test_number=}\nunexpected collateral_amount",
                )
            else:
                market = HyperdriveMarket(
                    position_duration=test_case["position_duration"],
                    market_state=HyperdriveMarketState(
                        init_share_price=test_case["init_share_price"],
                        share_price=test_case["share_price"],
                    ),
                    block_time=time.BlockTime(),
                    pricing_model=test_case["pricing_model"],
                )
                _ = market.initialize(test_case["target_liquidity"], test_case["target_apr"])
                self.assertAlmostEqual(
                    market.fixed_apr,
                    test_case["target_apr"],
                    delta=self.APPROX_EQ,
                    msg=f"{test_number=}\nunexpected market fixed_apr",
                )
                self.assertAlmostEqual(
                    market.market_state.share_reserves,
                    test_case["expected_share_reserves"],
                    delta=self.APPROX_EQ,
                    msg=f"{test_number=}\nunexpected share_reserves",
                )
                self.assertAlmostEqual(
                    market.market_state.bond_reserves,
                    test_case["expected_bond_reserves"],
                    delta=self.APPROX_EQ,
                    msg=f"{test_number=}\nunexpected bond_reserves",
                )

    def test_market_state_check_non_zero(self):
        """Test the MarkeState ability to verify none of the inputs are <=0"""
        # pylint: disable=too-many-statements
        with self.assertRaises(AssertionError):
            market_state = HyperdriveMarketState(lp_total_supply=FixedPoint(-1.0))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = HyperdriveMarketState(share_reserves=FixedPoint(-1.0))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = HyperdriveMarketState(bond_reserves=FixedPoint(-1.0))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = HyperdriveMarketState(base_buffer=FixedPoint(-1.0))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = HyperdriveMarketState(bond_buffer=FixedPoint(-1.0))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = HyperdriveMarketState(variable_apr=FixedPoint(-1.0))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = HyperdriveMarketState(share_price=FixedPoint(-1.0))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = HyperdriveMarketState(init_share_price=FixedPoint(-1.0))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = HyperdriveMarketState(curve_fee_multiple=FixedPoint(-1.0))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = HyperdriveMarketState(flat_fee_multiple=FixedPoint(-1.0))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = HyperdriveMarketState(governance_fee_multiple=FixedPoint(-1.0))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = HyperdriveMarketState(gov_fees_accrued=FixedPoint(-1.0))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = HyperdriveMarketState(longs_outstanding=FixedPoint(-1.0))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = HyperdriveMarketState(shorts_outstanding=FixedPoint(-1.0))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = HyperdriveMarketState(long_average_maturity_time=FixedPoint(-1.0))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = HyperdriveMarketState(short_average_maturity_time=FixedPoint(-1.0))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = HyperdriveMarketState(long_base_volume=FixedPoint(-1.0))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = HyperdriveMarketState(short_base_volume=FixedPoint(-1.0))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = HyperdriveMarketState(
                checkpoints={FixedPoint(0): Checkpoint(share_price=FixedPoint(-1.0))},
            )
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = HyperdriveMarketState(
                checkpoints={FixedPoint(0): Checkpoint(long_share_price=FixedPoint(-1.0))},
            )
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = HyperdriveMarketState(
                checkpoints={FixedPoint(0): Checkpoint(long_base_volume=FixedPoint(-1.0))},
            )
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = HyperdriveMarketState(
                checkpoints={FixedPoint(0): Checkpoint(short_base_volume=FixedPoint(-1.0))},
            )
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = HyperdriveMarketState(checkpoint_duration=FixedPoint(-1.0))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = HyperdriveMarketState(checkpoint_duration_days=FixedPoint(-1.0))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = HyperdriveMarketState(
                total_supply_longs={
                    FixedPoint(0): FixedPoint(0),
                    FixedPoint(1): FixedPoint(10.0),
                    FixedPoint(2): FixedPoint(-1.0),
                },
            )
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = HyperdriveMarketState(total_supply_shorts={FixedPoint(0): FixedPoint(-1.0)})
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = HyperdriveMarketState(total_supply_withdraw_shares=FixedPoint(-1.0))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = HyperdriveMarketState(withdraw_shares_ready_to_withdraw=FixedPoint(-1.0))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = HyperdriveMarketState(withdraw_capital=FixedPoint(-1))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = HyperdriveMarketState(withdraw_interest=FixedPoint(-1))
            market_state.check_valid_market_state()

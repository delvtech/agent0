"""Testing for the ElfPy package market module methods"""
from __future__ import annotations

import unittest
from collections import defaultdict

import elfpy.pricing_models.hyperdrive as hyperdrive_pm
import elfpy.pricing_models.yieldspace as yieldspace_pm
import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market
import elfpy.markets.borrow as borrow
import elfpy.time as time
from elfpy.math import FixedPoint

# TODO: remove this after FixedPoint PRs are finished


class MarketTest(unittest.TestCase):
    """Generic Parameter Test class"""

    # TODO: This approx should be much lower
    # issue #112
    APPROX_EQ: FixedPoint = FixedPoint(1e-6)

    def test_position_duration(self):
        """Test to make sure market init fails when normalizing_constant != days"""
        pd_good = time.StretchedTimeFP(
            days=FixedPoint("365.0"),
            time_stretch=FixedPoint("1.0"),
            normalizing_constant=FixedPoint("365.0"),
        )
        pd_nonorm = time.StretchedTimeFP(
            days=FixedPoint("365.0"),
            time_stretch=FixedPoint("1.0"),
            normalizing_constant=FixedPoint("36.0"),
        )
        for pricing_model in [yieldspace_pm.YieldspacePricingModelFP(), hyperdrive_pm.HyperdrivePricingModelFP()]:
            _ = hyperdrive_market.Market(
                pricing_model=pricing_model,
                market_state=hyperdrive_market.MarketState(),
                block_time=time.BlockTimeFP(),
                position_duration=pd_good,
            )
            with self.assertRaises(AssertionError):
                _ = hyperdrive_market.Market(
                    pricing_model=pricing_model,
                    market_state=hyperdrive_market.MarketState(),
                    block_time=time.BlockTimeFP(),
                    position_duration=pd_nonorm,
                )

    def test_market_state_copy(self):
        """Test the market state ability to deep copy itself"""
        market_state = hyperdrive_market.MarketState()
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
                "position_duration": time.StretchedTimeFP(
                    days=FixedPoint("182.5"),
                    time_stretch=FixedPoint("22.186877016851916"),
                    normalizing_constant=FixedPoint("182.5"),
                ),
                "init_share_price": FixedPoint("1.0"),  # original share price pool started; u = 1
                "share_price": FixedPoint("1.0"),  # share price of the LP in the yield source; c = 1
                "pricing_model": hyperdrive_pm.HyperdrivePricingModelFP(),
                "expected_share_reserves": FixedPoint("5_000_000.0"),  # target_liquidity / share_price
                "expected_bond_reserves": FixedPoint("1_823_834.7868545868"),
            },
            # test 1: 5M target_liquidity; 2% APR;
            #   6mo duration; 22.186877016851916 time_stretch (targets 5% APR);
            #   1 init share price; 1 share price; Yieldspace
            {
                "target_liquidity": FixedPoint("5_000_000.0"),  # Targeting 5M liquidity
                "target_apr": FixedPoint("0.02"),  # fixed rate APR you'd get from purchasing bonds; r = 0.02
                "position_duration": time.StretchedTimeFP(
                    days=FixedPoint("182.5"),
                    time_stretch=FixedPoint("55.467192542129794"),
                    normalizing_constant=FixedPoint("182.5"),
                ),
                "init_share_price": FixedPoint("1.0"),  # original share price pool started; u = 1
                "share_price": FixedPoint("1.0"),  # share price of the LP in the yield source; c = 1
                "pricing_model": yieldspace_pm.YieldspacePricingModelFP(),
                "expected_share_reserves": FixedPoint("5_000_000.0"),  # target_liquidity / share_price
                "expected_bond_reserves": FixedPoint("1_841_446.767658661"),
            },
            # test 2: 5M target_liquidity; 8% APR;
            #   6mo duration; 22.186877016851916 time_stretch (targets 5% APR);
            #   1 init share price; 1 share price; Hyperdrive
            {
                "target_liquidity": FixedPoint("5_000_000.0"),  # Targeting 5M liquidity
                "target_apr": FixedPoint("0.08"),  # fixed rate APR you'd get from purchasing bonds; r = 0.08
                "position_duration": time.StretchedTimeFP(
                    days=FixedPoint("182.5"),
                    time_stretch=FixedPoint("13.866798135532449"),
                    normalizing_constant=FixedPoint("182.5"),
                ),
                "init_share_price": FixedPoint("1.0"),  # original share price pool started; u = 1
                "share_price": FixedPoint("1.0"),  # share price of the LP in the yield source; c = 1
                "pricing_model": hyperdrive_pm.HyperdrivePricingModelFP(),
                "expected_share_reserves": FixedPoint("5_000_000.0"),
                "expected_bond_reserves": FixedPoint("1_806_633.2221533637"),
            },
            # test 3:  10M target_liquidity; 3% APR
            #   3mo duration; 36.97812836141986 time_stretch (targets 3% APR);
            #   2 init share price; 2 share price; Hyperdrive
            {
                "target_liquidity": FixedPoint("10_000_000.0"),  # targeting 10M liquidity
                "target_apr": FixedPoint("0.03"),  # fixed rate APR you'd get from purchasing bonds; r = 0.03
                "position_duration": time.StretchedTimeFP(
                    days=FixedPoint("91.25"),
                    time_stretch=FixedPoint("36.97812836141987"),
                    normalizing_constant=FixedPoint("91.25"),
                ),
                "init_share_price": FixedPoint("2.0"),  # original share price when pool started
                "share_price": FixedPoint("2.0"),  # share price of the LP in the yield source
                "pricing_model": hyperdrive_pm.HyperdrivePricingModelFP(),
                "expected_share_reserves": FixedPoint("5_000_000.0"),
                "expected_bond_reserves": FixedPoint("1_591_223.795848793"),
            },
            # test 4:  10M target_liquidity; 5% APR
            #   9mo duration; 36.97812836141986 time_stretch (targets 3% APR);
            #   1.3 init share price; 1.3 share price; Hyperdrive
            {
                "target_liquidity": FixedPoint("10_000_000.0"),  # Targeting 10M liquidity
                "target_apr": FixedPoint("0.001"),  # fixed rate APR you'd get from purchasing bonds; r = 0.03
                "position_duration": time.StretchedTimeFP(
                    days=FixedPoint("273.75"),
                    time_stretch=FixedPoint("1109.3438508425959"),
                    normalizing_constant=FixedPoint("273.75"),
                ),
                "init_share_price": FixedPoint("1.3"),  # original share price when pool started
                "share_price": FixedPoint("1.3"),  # share price of the LP in the yield source
                "pricing_model": hyperdrive_pm.HyperdrivePricingModelFP(),
                "expected_share_reserves": FixedPoint("7_692_307.692307692"),
                "expected_bond_reserves": FixedPoint("6_486_058.016848019"),
            },
            # test 5:  10M target_liquidity; 3% APR
            #   3mo duration; 36.97812836141986 time_stretch (targets 3% APR);
            #   2 init share price; 2 share price; Yieldspace
            {
                "target_liquidity": FixedPoint("10_000_000.0"),  # Targeting 10M liquidity
                "target_apr": FixedPoint("0.03"),  # fixed rate APR you'd get from purchasing bonds; r = 0.03
                "position_duration": time.StretchedTimeFP(
                    days=FixedPoint("91.25"),
                    time_stretch=FixedPoint("36.97812836141987"),
                    normalizing_constant=FixedPoint("91.25"),
                ),
                "init_share_price": FixedPoint("2.0"),  # original share price when pool started
                "share_price": FixedPoint("2.0"),  # share price of the LP in the yield source
                "pricing_model": yieldspace_pm.YieldspacePricingModelFP(),
                "expected_share_reserves": FixedPoint("5_000_000.0"),
                "expected_bond_reserves": FixedPoint("1_591_223.795848793"),
            },
            # test 6:  Borrow market is initialized empty
            {
                "pricing_model": borrow.PricingModel(),
                "borrow_amount": FixedPoint("0.0"),
                "borrow_shares": FixedPoint("0.0"),
                "borrow_outstanding": FixedPoint("0.0"),
            },
        ]
        # Loop through the test cases & pricing model
        for test_number, test_case in enumerate(test_cases):
            if isinstance(test_case["pricing_model"], borrow.PricingModel):
                market = borrow.Market(
                    pricing_model=test_case["pricing_model"],
                    block_time=time.BlockTimeFP(),
                    market_state=borrow.MarketState(),
                )
                market_deltas, _ = market.initialize(wallet_address=0)
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
                market = hyperdrive_market.Market(
                    position_duration=test_case["position_duration"],
                    market_state=hyperdrive_market.MarketState(
                        init_share_price=test_case["init_share_price"],
                        share_price=test_case["share_price"],
                    ),
                    block_time=time.BlockTimeFP(),
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
            market_state = hyperdrive_market.MarketState(lp_total_supply=FixedPoint(-1.0))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = hyperdrive_market.MarketState(share_reserves=FixedPoint(-1.0))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = hyperdrive_market.MarketState(bond_reserves=FixedPoint(-1.0))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = hyperdrive_market.MarketState(base_buffer=FixedPoint(-1.0))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = hyperdrive_market.MarketState(bond_buffer=FixedPoint(-1.0))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = hyperdrive_market.MarketState(variable_apr=FixedPoint(-1.0))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = hyperdrive_market.MarketState(share_price=FixedPoint(-1.0))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = hyperdrive_market.MarketState(init_share_price=FixedPoint(-1.0))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = hyperdrive_market.MarketState(curve_fee_multiple=FixedPoint(-1.0))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = hyperdrive_market.MarketState(flat_fee_multiple=FixedPoint(-1.0))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = hyperdrive_market.MarketState(governance_fee_multiple=FixedPoint(-1.0))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = hyperdrive_market.MarketState(gov_fees_accrued=FixedPoint(-1.0))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = hyperdrive_market.MarketState(longs_outstanding=FixedPoint(-1.0))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = hyperdrive_market.MarketState(shorts_outstanding=FixedPoint(-1.0))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = hyperdrive_market.MarketState(long_average_maturity_time=FixedPoint(-1.0))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = hyperdrive_market.MarketState(short_average_maturity_time=FixedPoint(-1.0))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = hyperdrive_market.MarketState(long_base_volume=FixedPoint(-1.0))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = hyperdrive_market.MarketState(short_base_volume=FixedPoint(-1.0))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = hyperdrive_market.MarketState(
                checkpoints=defaultdict(
                    hyperdrive_market.Checkpoint,
                    {FixedPoint(0): hyperdrive_market.Checkpoint(share_price=FixedPoint(-1.0))},
                )
            )
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = hyperdrive_market.MarketState(
                checkpoints=defaultdict(
                    hyperdrive_market.Checkpoint,
                    {FixedPoint(0): hyperdrive_market.Checkpoint(long_share_price=FixedPoint(-1.0))},
                ),
            )
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = hyperdrive_market.MarketState(
                checkpoints=defaultdict(
                    hyperdrive_market.Checkpoint,
                    {FixedPoint(0): hyperdrive_market.Checkpoint(long_base_volume=FixedPoint(-1.0))},
                ),
            )
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = hyperdrive_market.MarketState(
                checkpoints=defaultdict(
                    hyperdrive_market.Checkpoint,
                    {FixedPoint(0): hyperdrive_market.Checkpoint(short_base_volume=FixedPoint(-1.0))},
                )
            )
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = hyperdrive_market.MarketState(checkpoint_duration=FixedPoint(-1.0))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = hyperdrive_market.MarketState(checkpoint_duration_days=FixedPoint(-1.0))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = hyperdrive_market.MarketState(
                total_supply_longs=defaultdict(
                    FixedPoint,
                    {FixedPoint(0): FixedPoint(0), FixedPoint(1): FixedPoint(10.0), FixedPoint(2): FixedPoint(-1.0)},
                )
            )
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = hyperdrive_market.MarketState(
                total_supply_shorts=defaultdict(FixedPoint, {FixedPoint(0): FixedPoint(-1.0)})
            )
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = hyperdrive_market.MarketState(total_supply_withdraw_shares=FixedPoint(-1.0))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = hyperdrive_market.MarketState(withdraw_shares_ready_to_withdraw=FixedPoint(-1.0))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = hyperdrive_market.MarketState(withdraw_capital=FixedPoint(-1))
            market_state.check_valid_market_state()
        with self.assertRaises(AssertionError):
            market_state = hyperdrive_market.MarketState(withdraw_interest=FixedPoint(-1))
            market_state.check_valid_market_state()

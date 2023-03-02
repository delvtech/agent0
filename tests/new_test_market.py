"""Testing for the ElfPy package modules"""
from __future__ import annotations  # types are strings by default in 3.11

import unittest
import logging

import numpy as np

import elfpy.pricing_models.base as base_pm
import elfpy.pricing_models.hyperdrive as hyperdrive_pm
import elfpy.pricing_models.yieldspace as yieldspace_pm
import elfpy.markets.hyperdrive as hyperdrive_market
import elfpy.markets.borrow as borrow
import elfpy.utils.outputs as output_utils
import elfpy.utils.sim_utils as sim_utils
import elfpy.simulators.simulators as simulators
import elfpy.time as time


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
            position_duration=pd_good,
        )
        with self.assertRaises(AssertionError):
            _ = hyperdrive_market.Market(
                pricing_model=base_pm.PricingModel(),
                market_state=hyperdrive_market.MarketState(),
                position_duration=pd_nonorm,
            )

    def test_market_state_copy(self):
        market_state = hyperdrive_market.MarketState()
        market_state_copy = market_state.copy()
        assert market_state is not market_state_copy  # not the same object
        assert market_state == market_state_copy  # they have the same attribute values
        market_state_copy.share_reserves += 10
        assert market_state != market_state_copy  # now they should have different attribute values

    def test_market_init(self):
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
                "target_liquidity": 10_000_000,  # Targeting 10M liquidity
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
                market = borrow.Market(market_state=borrow.MarketState())
                market_deltas, _ = market.initialize_market(wallet_address=0)
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

    def test_market_init_apr_and_liquidity(self):
        """Compare two methods of initializing liquidity: agent-based as above, and the direct calc_liquidity method"""
        output_utils.setup_logging(log_filename=".logging/test_trades.log", log_level=logging.DEBUG)
        for target_liquidity in (1e2, 1e3, 1e4, 1e5, 1e6, 1e7, 1e8, 1e9):
            for target_fixed_apr in (0.01, 0.03, 0.05, 0.10, 0.25, 0.5, 1, 1.1):
                for num_position_days in [90, 365]:
                    for pricing_model_name in ["Yieldspace", "Hyperdrive"]:
                        config = simulators.Config()
                        config.pricing_model_name = pricing_model_name
                        config.target_liquidity = target_liquidity
                        config.trade_fee_percent = 0.1
                        config.redemption_fee_percent = 0.0
                        config.target_fixed_apr = target_fixed_apr
                        config.num_trading_days = 3
                        config.num_blocks_per_day = 3
                        config.variable_apr = [0.05] * config.num_trading_days
                        config.num_position_days = num_position_days
                        # construct the market via sim utils
                        simulator = sim_utils.get_simulator(config)
                        # then construct it by hand
                        market_direct = hyperdrive_market.Market(
                            pricing_model=simulator.market.pricing_model,
                            market_state=hyperdrive_market.MarketState(
                                base_buffer=simulator.market.market_state.base_buffer,
                                bond_buffer=simulator.market.market_state.bond_buffer,
                                variable_apr=simulator.market.market_state.variable_apr,
                                share_price=simulator.market.market_state.share_price,
                                init_share_price=simulator.market.market_state.init_share_price,
                                trade_fee_percent=simulator.market.market_state.trade_fee_percent,
                                redemption_fee_percent=simulator.market.market_state.redemption_fee_percent,
                            ),
                            position_duration=simulator.market.position_duration,
                        )
                        share_reserves = target_liquidity / market_direct.market_state.share_price
                        annualized_time = market_direct.position_duration.days / 365
                        bond_reserves = (share_reserves / 2) * (
                            market_direct.market_state.init_share_price
                            * (1 + target_fixed_apr * annualized_time)
                            ** (1 / market_direct.position_duration.stretched_time)
                            - market_direct.market_state.share_price
                        )
                        market_deltas = hyperdrive_market.MarketDeltas(
                            d_base_asset=target_liquidity,
                            d_bond_asset=bond_reserves,
                            d_lp_total_supply=market_direct.market_state.share_price * share_reserves + bond_reserves,
                        )
                        market_direct.update_market(market_deltas)
                        total_liquidity_direct = (
                            market_direct.pricing_model.calc_total_liquidity_from_reserves_and_price(
                                market_state=market_direct.market_state,
                                share_price=market_direct.market_state.share_price,
                            )
                        )
                        total_liquidity_agent = (
                            simulator.market.pricing_model.calc_total_liquidity_from_reserves_and_price(
                                market_state=simulator.market.market_state,
                                share_price=simulator.market.market_state.share_price,
                            )
                        )
                        # compare outputs
                        logging.debug(
                            (
                                "\n\n----\n"
                                "target_liquidity=%g\n"
                                "target_fixed_apr=%g\n"
                                "num_position_days=%g\n"
                                "pricing_model_name=%s\n"
                                "simulator.market.market_state=%s"
                            ),
                            target_liquidity,
                            target_fixed_apr,
                            num_position_days,
                            pricing_model_name,
                            simulator.market.market_state,
                        )
                        assert np.allclose(total_liquidity_direct, total_liquidity_agent, atol=0, rtol=1e-15), (
                            f"ERROR: {total_liquidity_direct=}"
                            f"does not equal {total_liquidity_agent=} "
                            f"off by {(np.abs(total_liquidity_direct - total_liquidity_agent))=}."
                        )
                        assert np.allclose(market_direct.fixed_apr, simulator.market.fixed_apr, atol=0, rtol=1e-12), (
                            f"ERROR: {market_direct.fixed_apr=}"
                            f" does not equal {simulator.market.fixed_apr=}"
                            f"off by {(np.abs(market_direct.fixed_apr - simulator.market.fixed_apr))=}."
                        )
                        assert np.allclose(target_liquidity, total_liquidity_agent, atol=0, rtol=1e-15), (
                            f"ERROR: {target_liquidity=}"
                            f"does not equal {total_liquidity_agent=} "
                            f"off by {(np.abs(target_liquidity - total_liquidity_agent))=}."
                        )
                        assert np.allclose(target_fixed_apr, simulator.market.fixed_apr, atol=0, rtol=1e-12), (
                            f"ERROR: {target_fixed_apr=}"
                            f" does not equal {simulator.market.fixed_apr=}"
                            f"off by {(np.abs(target_fixed_apr - simulator.market.fixed_apr))=}."
                        )
        output_utils.close_logging()

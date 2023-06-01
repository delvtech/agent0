"""Testing for the ElfPy package modules"""
from __future__ import annotations  # types are strings by default in 3.11

import logging
import unittest

import elfpy.markets.hyperdrive.hyperdrive_actions as hyperdrive_actions
import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market
import elfpy.pricing_models.hyperdrive as hyperdrive_pm
import elfpy.time as time
import elfpy.utils.outputs as output_utils
import elfpy.utils.sim_utils as sim_utils
from elfpy.math import FixedPoint
from elfpy.simulators.config import Config

# pylint: disable=too-many-locals


class SimUtilsTest(unittest.TestCase):
    """Tests for the sim utils"""

    APPROX_EQ: FixedPoint = FixedPoint(1e-17)

    def test_get_initialized_market(self):
        """Compare two methods of initializing liquidity: agent-based as above, and the direct calc_liquidity method"""
        output_utils.setup_logging(log_filename="test_sim_utils", log_level=logging.DEBUG)
        for target_liquidity in (1e2, 1e3, 1e4, 1e5, 1e6, 1e7, 1e8, 1e9):
            for target_fixed_apr in (0.01, 0.03, 0.05, 0.10, 0.25, 0.5, 1.0, 1.1):
                for num_position_days in [90, 365]:
                    for pricing_model_name in ["Hyperdrive"]:
                        config = Config()
                        config.pricing_model_name = pricing_model_name
                        config.target_liquidity = target_liquidity
                        config.curve_fee_multiple = 0.1
                        config.flat_fee_multiple = 0.0
                        config.num_trading_days = 3
                        config.num_blocks_per_day = 3
                        config.variable_apr = [0.05] * config.num_trading_days
                        config.num_position_days = num_position_days
                        config.target_fixed_apr = target_fixed_apr
                        # construct the market via sim utils
                        block_time = time.BlockTime()
                        pricing_model = hyperdrive_pm.HyperdrivePricingModel()
                        market, _, _ = sim_utils.get_initialized_hyperdrive_market(pricing_model, block_time, config)
                        # then construct it by hand
                        market_direct = hyperdrive_market.Market(
                            pricing_model=market.pricing_model,
                            market_state=hyperdrive_market.MarketState(
                                base_buffer=market.market_state.base_buffer,
                                bond_buffer=market.market_state.bond_buffer,
                                variable_apr=market.market_state.variable_apr,
                                share_price=market.market_state.share_price,
                                init_share_price=market.market_state.init_share_price,
                                curve_fee_multiple=market.market_state.curve_fee_multiple,
                                flat_fee_multiple=market.market_state.flat_fee_multiple,
                            ),
                            block_time=time.BlockTime(),
                            position_duration=market.position_duration,
                        )
                        share_reserves = FixedPoint(target_liquidity) / market_direct.market_state.share_price
                        annualized_time = market_direct.position_duration.days / FixedPoint("365.0")
                        bond_reserves = (share_reserves / FixedPoint("2.0")) * (
                            market_direct.market_state.init_share_price
                            * (FixedPoint("1.0") + FixedPoint(target_fixed_apr) * annualized_time)
                            ** (FixedPoint("1.0") / market_direct.position_duration.stretched_time)
                            - market_direct.market_state.share_price
                        )
                        market_deltas = hyperdrive_actions.MarketDeltas(
                            d_base_asset=FixedPoint(target_liquidity),
                            d_bond_asset=bond_reserves,
                            d_lp_total_supply=market_direct.market_state.share_price * share_reserves + bond_reserves,
                        )
                        market_direct.update_market(market_deltas)
                        total_liquidity_direct = (
                            market_direct.market_state.share_reserves * market_direct.market_state.share_price
                        )
                        total_liquidity_agent = market.market_state.share_reserves * market.market_state.share_price
                        # compare outputs
                        logging.debug(
                            (
                                "\n\n----\n"
                                "target_liquidity=%g\n"
                                "target_fixed_apr=%g\n"
                                "num_position_days=%g\n"
                                "pricing_model_name=%s\n"
                                "market.market_state=%s"
                            ),
                            target_liquidity,
                            target_fixed_apr,
                            num_position_days,
                            pricing_model_name,
                            market.market_state,
                        )
                        self.assertAlmostEqual(
                            total_liquidity_direct,
                            total_liquidity_agent,
                            delta=self.APPROX_EQ,
                            msg=(
                                f"ERROR: {total_liquidity_direct=}"
                                f"does not equal {total_liquidity_agent=} "
                                f"off by {(abs(total_liquidity_direct - total_liquidity_agent))=}."
                            ),
                        )
                        self.assertAlmostEqual(
                            market_direct.fixed_apr,
                            market.fixed_apr,
                            delta=self.APPROX_EQ,
                            msg=(
                                f"ERROR: {market_direct.fixed_apr=}"
                                f" does not equal {market.fixed_apr=}"
                                f"off by {(abs(market_direct.fixed_apr - market.fixed_apr))=}."
                            ),
                        )
                        self.assertAlmostEqual(
                            FixedPoint(target_liquidity),
                            total_liquidity_agent,
                            delta=self.APPROX_EQ,
                            msg=(
                                f"ERROR: {target_liquidity=}"
                                f"does not equal {total_liquidity_agent=} "
                                f"off by {(abs(FixedPoint(target_liquidity) - total_liquidity_agent))=}."
                            ),
                        )
                        self.assertAlmostEqual(
                            FixedPoint(target_fixed_apr),
                            market.fixed_apr,
                            delta=self.APPROX_EQ,
                            msg=(
                                f"ERROR: {target_fixed_apr=}"
                                f" does not equal {market.fixed_apr=}"
                                f"off by {(abs(FixedPoint(target_fixed_apr) - market.fixed_apr))=}."
                            ),
                        )
        output_utils.close_logging()

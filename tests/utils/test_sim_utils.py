"""Testing for the ElfPy package modules"""
from __future__ import annotations  # types are strings by default in 3.11

import logging
import unittest

import numpy as np

import elfpy.markets.hyperdrive as hyperdrive_market
import elfpy.pricing_models.hyperdrive as hyperdrive_pm
import elfpy.pricing_models.yieldspace as yieldspace_pm
import elfpy.simulators.simulators as simulators
import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market
import elfpy.markets.hyperdrive.hyperdrive_actions as hyperdrive_actions
import elfpy.utils.outputs as output_utils
import elfpy.utils.sim_utils as sim_utils
from elfpy.time.time import BlockTime

# pylint: disable=too-many-locals


class SimUtilsTest(unittest.TestCase):
    """Tests for the sim utils"""

    def test_get_initialized_market(self):
        """Compare two methods of initializing liquidity: agent-based as above, and the direct calc_liquidity method"""
        output_utils.setup_logging(log_filename="test_sim_utils", log_level=logging.DEBUG)
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
                        block_time = BlockTime()
                        if pricing_model_name.lower() == "hyperdrive":
                            pricing_model = hyperdrive_pm.HyperdrivePricingModel()
                        else:
                            pricing_model = yieldspace_pm.YieldspacePricingModel()
                        market, _, _ = sim_utils.get_initialized_market(pricing_model, block_time, config)
                        # then construct it by hand
                        market_direct = hyperdrive_market.Market(
                            pricing_model=market.pricing_model,
                            market_state=hyperdrive_market.MarketState(
                                base_buffer=market.market_state.base_buffer,
                                bond_buffer=market.market_state.bond_buffer,
                                variable_apr=market.market_state.variable_apr,
                                share_price=market.market_state.share_price,
                                init_share_price=market.market_state.init_share_price,
                                trade_fee_percent=market.market_state.trade_fee_percent,
                                redemption_fee_percent=market.market_state.redemption_fee_percent,
                            ),
                            block_time=BlockTime(),
                            position_duration=market.position_duration,
                        )
                        share_reserves = target_liquidity / market_direct.market_state.share_price
                        annualized_time = market_direct.position_duration.days / 365
                        bond_reserves = (share_reserves / 2) * (
                            market_direct.market_state.init_share_price
                            * (1 + target_fixed_apr * annualized_time)
                            ** (1 / market_direct.position_duration.stretched_time)
                            - market_direct.market_state.share_price
                        )
                        market_deltas = hyperdrive_actions.MarketDeltas(
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
                        total_liquidity_agent = market.pricing_model.calc_total_liquidity_from_reserves_and_price(
                            market_state=market.market_state,
                            share_price=market.market_state.share_price,
                        )
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
                        assert np.allclose(total_liquidity_direct, total_liquidity_agent, atol=0, rtol=1e-15), (
                            f"ERROR: {total_liquidity_direct=}"
                            f"does not equal {total_liquidity_agent=} "
                            f"off by {(np.abs(total_liquidity_direct - total_liquidity_agent))=}."
                        )
                        assert np.allclose(market_direct.fixed_apr, market.fixed_apr, atol=0, rtol=1e-12), (
                            f"ERROR: {market_direct.fixed_apr=}"
                            f" does not equal {market.fixed_apr=}"
                            f"off by {(np.abs(market_direct.fixed_apr - market.fixed_apr))=}."
                        )
                        assert np.allclose(target_liquidity, total_liquidity_agent, atol=0, rtol=1e-15), (
                            f"ERROR: {target_liquidity=}"
                            f"does not equal {total_liquidity_agent=} "
                            f"off by {(np.abs(target_liquidity - total_liquidity_agent))=}."
                        )
                        assert np.allclose(target_fixed_apr, market.fixed_apr, atol=0, rtol=1e-12), (
                            f"ERROR: {target_fixed_apr=}"
                            f" does not equal {market.fixed_apr=}"
                            f"off by {(np.abs(target_fixed_apr - market.fixed_apr))=}."
                        )
        output_utils.close_logging()

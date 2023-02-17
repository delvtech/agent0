"""Testing for the ElfPy package modules"""
from __future__ import annotations  # types are strings by default in 3.11

import unittest
import logging

import numpy as np
import utils_for_tests as test_utils  # utilities for testing

import elfpy.utils.outputs as output_utils  # utilities for file outputs
from elfpy.types import MarketState, Config
from elfpy.markets import Market

# because we're testing lots of stuff here!
# pylint: disable=too-many-arguments


class SingleTradeTests(unittest.TestCase):
    """
    Tests for the SingeLong policy

    .. todo:: In a followup PR, loop over pricing model types & rerun tests
    """

    def run_base_trade_test(
        self,
        agent_policies,
        delete_logs=True,
        target_liquidity=None,
        target_pool_apr=None,
        init_only=False,
    ):
        """Assigns member variables that are useful for many tests"""
        output_utils.setup_logging(log_filename=".logging/test_trades.log", log_level=logging.DEBUG)
        for num_position_days in [90, 365]:
            for pricing_model_name in ["Yieldspace", "Hyperdrive"]:
                config = Config()
                config.pricing_model_name = pricing_model_name
                config.target_liquidity = 10e6 if not target_liquidity else target_liquidity
                config.trade_fee_percent = 0.1
                config.redemption_fee_percent = 0.0
                config.target_pool_apr = 0.05 if not target_pool_apr else target_pool_apr
                config.num_trading_days = 3  # sim 3 days to keep it fast for testing
                config.num_blocks_per_day = 3  # 3 block a day, keep it fast for testing
                config.vault_apr = [0.05] * config.num_trading_days
                config.num_position_days = num_position_days  # how long until token maturity
                simulator = test_utils.setup_simulation_entities(config, agent_policies)
                if target_pool_apr:
                    market_apr = simulator.market.apr
                    # use rtol here because liquidity spans 2 orders of magnitude
                    assert np.allclose(market_apr, target_pool_apr, atol=0, rtol=1e-12), (
                        f"test_trade.run_base_lp_test: ERROR: {target_pool_apr=} does not equal {market_apr=} "
                        f"with error of {(np.abs(market_apr - target_pool_apr)/target_pool_apr)=:.2e}"
                    )
                    logging.debug(
                        (
                            "test_trade.run_base_lp_test: target_pool_apr=%g equals market_apr=%g"
                            " within (np.abs(market_apr - target_pool_apr)/target_pool_apr)=%.2e}"
                        ),
                        target_pool_apr,
                        market_apr,
                        (np.abs(market_apr - target_pool_apr) / target_pool_apr),
                    )
                if target_liquidity:
                    total_liquidity = (
                        simulator.market.market_state.share_reserves * simulator.market.market_state.share_price
                    )
                    # use rtol here because liquidity spans 7 orders of magnitude
                    assert np.allclose(total_liquidity, target_liquidity, atol=0, rtol=1e-15), (
                        f"test_trade.run_base_lp_test: ERROR: {target_liquidity=} does not equal {total_liquidity=} "
                        f"with error of {(np.abs(total_liquidity - target_liquidity)/target_liquidity)=:.2e}."
                    )
                    logging.debug(
                        (
                            "test_trade.run_base_lp_test: total_liquidity=%g equals target_liquidity=%g"
                            " within (np.abs(total_liquidity - target_liquidity)/target_liquidity)=%.2e}"
                        ),
                        total_liquidity,
                        target_liquidity,
                        (np.abs(total_liquidity - target_liquidity) / target_liquidity),
                    )
                if not init_only:
                    simulator.run_simulation()
        output_utils.close_logging(delete_logs=delete_logs)
        # TODO: This test and test_compare_agent_to_calc_liquidity need to be merged
        return simulator  # type: ignore

    def test_compare_agent_to_calc_liquidity(self):
        """Compare two methods of initializing liquidity: agent-based as above, and the direct calc_liquidity method"""
        for target_liquidity in (1e2, 1e3, 1e4, 1e5, 1e6, 1e7, 1e8, 1e9):
            for target_pool_apr in (0.01, 0.03, 0.05, 0.10, 0.25, 0.5, 1, 1.1):
                logging.debug(
                    (
                        "test_compare_agent_to_calc_liquidit:run_base_trade_test"
                        "with target_liquidity=%g, target_pool_apr=%g",
                    ),
                    target_liquidity,
                    target_pool_apr,
                )
                # run_base_trade_test initializes a market with an LP agent
                simulator = self.run_base_trade_test(
                    agent_policies=[],
                    target_liquidity=target_liquidity,
                    target_pool_apr=target_pool_apr,
                    init_only=True,
                )
                # assign the results of the init_lp agent to explicit variables
                share_reserves_direct, bond_reserves_direct = simulator.market.pricing_model.calc_liquidity(
                    market_state=simulator.market.market_state,  # used only for share_price and init_share_price
                    target_liquidity=target_liquidity,
                    target_apr=target_pool_apr,
                    position_duration=simulator.market.position_duration,
                )
                market_direct = Market(
                    pricing_model=simulator.market.pricing_model,
                    market_state=MarketState(
                        share_reserves=share_reserves_direct,
                        bond_reserves=bond_reserves_direct,
                        base_buffer=simulator.market.market_state.base_buffer,
                        bond_buffer=simulator.market.market_state.bond_buffer,
                        lp_reserves=simulator.market.market_state.lp_reserves,
                        vault_apr=simulator.market.market_state.vault_apr,
                        share_price=simulator.market.market_state.share_price,
                        init_share_price=simulator.market.market_state.init_share_price,
                        trade_fee_percent=simulator.market.market_state.trade_fee_percent,
                        redemption_fee_percent=simulator.market.market_state.redemption_fee_percent,
                    ),
                    position_duration=simulator.market.position_duration,
                )
                total_liquidity_direct = market_direct.pricing_model.calc_total_liquidity_from_reserves_and_price(
                    market_state=market_direct.market_state, share_price=market_direct.market_state.share_price
                )
                total_liquidity_agent = simulator.market.pricing_model.calc_total_liquidity_from_reserves_and_price(
                    market_state=simulator.market.market_state, share_price=simulator.market.market_state.share_price
                )
                assert np.allclose(total_liquidity_direct, total_liquidity_agent, atol=0, rtol=1e-15), (
                    f"test_trade.test_compare_agent_to_calc_liquidity: ERROR: {total_liquidity_direct=}"
                    f"does not equal {total_liquidity_agent=} "
                    f"off by {(np.abs(total_liquidity_direct - total_liquidity_agent))=}."
                )
                assert np.allclose(market_direct.apr, simulator.market.apr, atol=0, rtol=1e-12), (
                    f"test_trade.test_compare_agent_to_calc_liquidity: ERROR: {market_direct.apr=}"
                    f" does not equal {simulator.market.apr=}"
                    f"off by {(np.abs(market_direct.apr - simulator.market.apr))=}."
                )

    def test_single_long(self):
        """Tests the BaseUser class"""
        self.run_base_trade_test(agent_policies=["single_long"])

    def test_single_short(self):
        """Tests the BaseUser class"""
        self.run_base_trade_test(agent_policies=["single_short"])

    def test_base_lps(self):
        """Tests base LP setups"""
        self.run_base_trade_test(agent_policies=["single_lp"], target_liquidity=1e6, target_pool_apr=0.05)

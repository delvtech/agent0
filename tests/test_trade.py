"""Testing for the ElfPy package modules"""
# types are strings by default in 3.11
from __future__ import annotations

import unittest
import logging

import numpy as np

import elfpy.types as types
import elfpy.utils.outputs as output_utils  # utilities for file outputs
import elfpy.utils.sim_utils as sim_utils
import elfpy.simulators.simulators as simulators
import elfpy.markets.hyperdrive as hyperdrive

# because we're testing lots of stuff here!
# pylint: disable=too-many-arguments


class SingleTradeTests(unittest.TestCase):
    """
    Tests for the SingeLong policy

    .. todo:: In a followup PR, loop over pricing model types & rerun tests
    """

    def test_market_init_apr_and_liquidity(self):
        """Compare two methods of initializing liquidity: agent-based as above, and the direct calc_liquidity method"""
        output_utils.setup_logging(log_filename=".logging/test_trades.log", log_level=logging.DEBUG)
        for target_liquidity in (1e2, 1e3, 1e4, 1e5, 1e6, 1e7, 1e8, 1e9):
            for target_pool_apr in (0.01, 0.03, 0.05, 0.10, 0.25, 0.5, 1, 1.1):
                for num_position_days in [90, 365]:
                    for market_type in [types.MarketType.YIELDSPACE, types.MarketType.HYPERDRIVE]:
                        config = simulators.Config()
                        config.market_types = [market_type]
                        config.target_liquidity = target_liquidity
                        config.trade_fee_percent = 0.1
                        config.redemption_fee_percent = 0.0
                        config.target_fixed_apr = target_pool_apr
                        config.num_trading_days = 3  # sim 3 days to keep it fast for testing
                        config.num_blocks_per_day = 3  # 3 block a day, keep it fast for testing
                        config.variable_apr = [0.05] * config.num_trading_days
                        config.num_position_days = num_position_days  # how long until token maturity
                        simulator = sim_utils.get_simulator(config)
                        logging.debug(
                            (
                                "\n\n----\n"
                                "target_liquidity=%g\n"
                                "target_pool_apr=%g\n"
                                "num_position_days=%g\n"
                                "pricing_model_name=%s\n"
                                "simulator.markets[market_type].market_state=%s"
                            ),
                            target_liquidity,
                            target_pool_apr,
                            num_position_days,
                            market_type,
                            simulator.markets[market_type].market_state,
                        )
                        # assign the results of the init_lp agent to explicit variables
                        # market_state is used only for share_price and init_share_price
                        # TODO: Redo this to compute the direct reserves exactly instead of calling calc_liquidity
                        #       this ensures that the underlying function is changed and messed up at some point
                        share_reserves_direct, bond_reserves_direct = simulator.markets[
                            market_type
                        ].pricing_model.calc_liquidity(
                            market_state=simulator.markets[market_type].market_state,
                            target_liquidity=target_liquidity,
                            target_apr=target_pool_apr,
                            position_duration=simulator.markets[market_type].position_duration,
                        )
                        market_direct = hyperdrive.HyperdriveMarket(
                            pricing_model=simulator.markets[market_type].pricing_model,
                            market_state=hyperdrive.MarketState(
                                share_reserves=share_reserves_direct,
                                bond_reserves=bond_reserves_direct,
                                base_buffer=simulator.markets[market_type].market_state.base_buffer,
                                bond_buffer=simulator.markets[market_type].market_state.bond_buffer,
                                lp_total_supply=simulator.markets[market_type].market_state.lp_total_supply,
                                variable_apr=simulator.markets[market_type].market_state.variable_apr,
                                share_price=simulator.markets[market_type].market_state.share_price,
                                init_share_price=simulator.markets[market_type].market_state.init_share_price,
                                trade_fee_percent=simulator.markets[market_type].market_state.trade_fee_percent,
                                redemption_fee_percent=simulator.markets[
                                    market_type
                                ].market_state.redemption_fee_percent,
                            ),
                            position_duration=simulator.markets[market_type].position_duration,
                        )
                        total_liquidity_direct = (
                            market_direct.pricing_model.calc_total_liquidity_from_reserves_and_price(
                                market_state=market_direct.market_state,
                                share_price=market_direct.market_state.share_price,
                            )
                        )
                        total_liquidity_agent = simulator.markets[
                            market_type
                        ].pricing_model.calc_total_liquidity_from_reserves_and_price(
                            market_state=simulator.markets[market_type].market_state,
                            share_price=simulator.markets[market_type].market_state.share_price,
                        )
                        assert np.allclose(total_liquidity_direct, total_liquidity_agent, atol=0, rtol=1e-15), (
                            f"ERROR: {total_liquidity_direct=}"
                            f"does not equal {total_liquidity_agent=} "
                            f"off by {(np.abs(total_liquidity_direct - total_liquidity_agent))=}."
                        )
                        assert np.allclose(
                            market_direct.fixed_apr, simulator.markets[market_type].fixed_apr, atol=0, rtol=1e-12
                        ), (
                            f"ERROR: {market_direct.fixed_apr=}"
                            f" does not equal {simulator.markets[market_type].fixed_apr=}"
                            f"off by {(np.abs(market_direct.fixed_apr - simulator.markets[market_type].fixed_apr))=}."
                        )
                        assert np.allclose(target_liquidity, total_liquidity_agent, atol=0, rtol=1e-15), (
                            f"ERROR: {target_liquidity=}"
                            f"does not equal {total_liquidity_agent=} "
                            f"off by {(np.abs(target_liquidity - total_liquidity_agent))=}."
                        )
                        assert np.allclose(
                            target_pool_apr, simulator.markets[market_type].fixed_apr, atol=0, rtol=1e-12
                        ), (
                            f"ERROR: {target_pool_apr=}"
                            f" does not equal {simulator.markets[market_type].fixed_apr=}"
                            f"off by {(np.abs(target_pool_apr - simulator.markets[market_type].fixed_apr))=}."
                        )
        output_utils.close_logging()

    def test_single_trade(self):
        """Tests the BaseUser class"""
        test_cases = [
            {
                "agent_policy": "single_long",
                "num_position_days": 90,
                "market_type": types.MarketType.YIELDSPACE,
            },  # Test 1
            {
                "agent_policy": "single_long",
                "num_position_days": 365,
                "market_type": types.MarketType.YIELDSPACE,
            },  # Test 2
            {
                "agent_policy": "single_long",
                "num_position_days": 90,
                "market_type": types.MarketType.HYPERDRIVE,
            },  # Test 3
            {
                "agent_policy": "single_long",
                "num_position_days": 365,
                "market_type": types.MarketType.HYPERDRIVE,
            },  # Test 4
            {
                "agent_policy": "single_short",
                "num_position_days": 90,
                "market_type": types.MarketType.YIELDSPACE,
            },  # Test 5
            {
                "agent_policy": "single_short",
                "num_position_days": 365,
                "market_type": types.MarketType.YIELDSPACE,
            },  # Test 6
            {
                "agent_policy": "single_short",
                "num_position_days": 90,
                "market_type": types.MarketType.HYPERDRIVE,
            },  # Test 7
            {
                "agent_policy": "single_short",
                "num_position_days": 365,
                "market_type": types.MarketType.HYPERDRIVE,
            },  # Test 8
        ]

        output_utils.setup_logging(log_filename=".logging/test_trades.log", log_level=logging.DEBUG)
        for test_number, test_case in enumerate(test_cases):
            market_type = test_case["market_type"]
            config = simulators.Config()
            config.market_types = [market_type]
            config.target_liquidity = 10e6
            config.trade_fee_percent = 0.1
            config.redemption_fee_percent = 0.0
            config.target_fixed_apr = 0.05
            config.num_trading_days = 3
            config.num_blocks_per_day = 3
            config.variable_apr = [0.05] * config.num_trading_days
            config.num_position_days = test_case["num_position_days"]
            simulator = sim_utils.get_simulator(config)
            simulator.add_agents(
                [sim_utils.get_policy(test_case["agent_policy"])(wallet_address=1, budget=config.target_liquidity)]
            )
            simulator.run_simulation(liquidate_on_end=False)
            print(
                f"\n\n----\n{test_number=}\n{test_case=}\n"
                f"{simulator.markets[market_type].market_state=}\n{simulator.agents[1].wallet=}"
            )
            if test_case["agent_policy"] == "single_long":
                assert len(simulator.agents[1].wallet.longs) > 0
            elif test_case["agent_policy"] == "single_short":
                assert len(simulator.agents[1].wallet.shorts) > 0
            else:
                assert False, "Agent policy test only enabled for single_long and single_short"
        output_utils.close_logging()


if __name__ == "__main__":
    my_test = SingleTradeTests()
    my_test.test_market_init_apr_and_liquidity()

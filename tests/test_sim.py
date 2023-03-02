"""Testing for the ElfPy package modules"""
from __future__ import annotations
import builtins  # types are strings by default in 3.11

import logging
import unittest

import pandas as pd
import numpy as np
from numpy.random import RandomState

import elfpy.simulators.simulators as simulators
import elfpy.agents.wallet as wallet
import elfpy.markets.hyperdrive as hyperdrive
from elfpy.utils import sim_utils  # utilities for setting up a simulation
import elfpy.utils.outputs as output_utils


class TestSimulator(unittest.TestCase):
    """Test running a simulation using each pricing model type"""

    @staticmethod
    def setup_logging(log_level=logging.DEBUG):
        """Setup logging and handlers for the test"""
        log_filename = ".logging/test_sim.log"
        output_utils.setup_logging(log_filename, log_level=log_level)

    def test_hyperdrive_sim(self):
        """Tests hyperdrive simulation"""
        self.setup_logging()
        config = simulators.Config()
        config.pricing_model_name = "Hyperdrive"
        config.num_trading_days = 3
        config.num_blocks_per_day = 3
        config.variable_apr = [0.01] * config.num_trading_days
        simulator = sim_utils.get_simulator(config)
        simulator.run_simulation()
        output_utils.close_logging()

    def test_yieldspace_sim(self):
        """Tests yieldspace simulation"""
        self.setup_logging()
        config = simulators.Config()
        config.pricing_model_name = "Yieldspace"
        config.num_trading_days = 3
        config.num_blocks_per_day = 3
        config.variable_apr = [0.01] * config.num_trading_days
        simulator = sim_utils.get_simulator(config)
        simulator.run_simulation()
        output_utils.close_logging()

    def test_set_rng(self):
        """Test error handling & resetting simulator random number generator"""
        self.setup_logging()
        config = simulators.Config()
        config.num_trading_days = 3
        config.num_blocks_per_day = 3
        config.variable_apr = [0.01] * config.num_trading_days
        simulator = sim_utils.get_simulator(config)
        new_rng = np.random.default_rng(1234)
        simulator.set_rng(new_rng)
        assert simulator.rng == new_rng
        for bad_input in ([1234, "1234", RandomState(1234)],):
            with self.assertRaises(TypeError):
                simulator.set_rng(bad_input)  # type: ignore
        output_utils.close_logging()

    def test_simulation_state(self):
        """Test override & initalizaiton of random variables

        Runs a small number of trades, then checks that simulation_state
        has the correct number of logs per category.
        """
        self.setup_logging()
        config = simulators.Config()
        config.num_trading_days = 3
        config.num_blocks_per_day = 3
        config.variable_apr = [0.01] * config.num_trading_days
        simulator = sim_utils.get_simulator(config)
        simulator.run_simulation()
        simulation_state_num_writes = np.array([len(value) for value in simulator.simulation_state.__dict__.values()])
        goal_writes = simulation_state_num_writes[0]
        try:
            np.testing.assert_equal(simulation_state_num_writes, goal_writes)
        except builtins.BaseException as exc:
            bad_keys = [
                key
                for key in simulator.simulation_state.__dict__
                if len(simulator.simulation_state[key]) != goal_writes
            ]
            raise AssertionError(
                "ERROR: Analysis keys have an incorrect number of entries:"
                f"\n\t{bad_keys}"
                f"\n\tlengths={[len(simulator.simulation_state[key]) for key in bad_keys]}"
                f"\n\t{goal_writes=}"
            ) from exc
        output_utils.close_logging()

    def test_new_simulation_state(self):
        """Build a fake simulation state and then test it against the sim state aggregator"""
        # pylint: disable=too-many-locals
        num_runs = 1
        num_days_per_run = 3
        num_blocks_per_day = 2
        num_trades_per_block = 2
        total_num_days = num_runs * num_days_per_run
        total_num_blocks = total_num_days * num_blocks_per_day
        total_num_trades = total_num_blocks * num_trades_per_block
        # use totals to set "run_number" to cause failure if the other columns do not have enough rows
        runs = pd.DataFrame(
            {
                "run_number": [0] * num_runs,
                "config": [simulators.Config()],
                "agent_init": [[wallet.Wallet(address) for address in range(2)]],
                "market_init": [hyperdrive.MarketState()],
                "market_step_size": [0.001],
                "position_duration": [90],
            }
        )
        days = pd.DataFrame(
            {
                "run_number": [0] * total_num_days,
                "day": [0, 1, 2],
                "variable_apr": [0, 5, 9],
                "share_price": [1, 2, 3],
            }
        )
        blocks = pd.DataFrame(
            {
                "run_number": [0] * total_num_blocks,
                "day": [0, 0, 1, 1, 2, 2],
                "block_number": [0, 1, 2, 3, 4, 5],
                "market_time": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5],
            }
        )
        trades = pd.DataFrame(
            {
                "run_number": [0] * total_num_trades,
                "day": [0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2],
                "block_number": [0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5],
                "trade_number": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
                "fixed_apr": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1],
                "spot_price": [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0, 2.1],
                "market_deltas": [[idx, 8] for idx in range(total_num_trades)],
                "agent_address": [0] * total_num_trades,
                "agent_deltas": [[idx, 9] for idx in range(total_num_trades)],
            }
        )
        all_trades = trades.merge(blocks.merge(days.merge(runs)))
        sim_state = simulators.NewSimulationState()
        sim_state.update(run_vars=simulators.RunSimVariables(**runs.iloc[0].to_dict()))
        block_number = 0  # this is a cumulative tracker across days
        trade_number = 0  # this is a cumulative tracker across blocks and days
        for day in range(num_days_per_run):
            sim_state.update(day_vars=simulators.DaySimVariables(**days.iloc[day].to_dict()))
            for _ in range(num_blocks_per_day):
                sim_state.update(block_vars=simulators.BlockSimVariables(**blocks.iloc[block_number].to_dict()))
                for _ in range(num_trades_per_block):
                    sim_state.update(trade_vars=simulators.TradeSimVariables(**trades.iloc[trade_number].to_dict()))
                    trade_number += 1
                block_number += 1
        assert np.all(sim_state.run_updates == runs), f"{sim_state.run_updates=}\n{runs}"
        assert np.all(sim_state.day_updates == days), f"{sim_state.day_updates=}\n{days}"
        assert np.all(sim_state.block_updates == blocks), f"{sim_state.block_updates=}\n{blocks}"
        assert np.all(sim_state.trade_updates == trades), f"{sim_state.trade_updates=}\n{trades}"
        assert np.all(sim_state.combined_dataframe == all_trades), f"{sim_state.combined_dataframe}\n{all_trades}"

    def test_aggregate_agent_and_market_states(self):
        """Tests tweet aggregation with new dataframe in a simulation"""
        self.setup_logging()
        config = simulators.Config()
        config.num_trading_days = 4
        config.num_blocks_per_day = 4
        config.variable_apr = [0.01] * config.num_trading_days
        config.do_dataframe_states = True
        simulator = sim_utils.get_simulator(
            config=config,
            agents=[
                sim_utils.get_policy("single_long")(wallet_address=address, budget=1_000) for address in range(1, 3)
            ],
        )
        simulator.run_simulation()
        # TODO: Check aggregated_states against simulator.simulation_state to make
        #       sure agent & market states are equal after each block
        # aggregated_states = post_processing.aggregate_agent_and_market_states(
        #     simulator.new_simulation_state.combined_dataframe
        # )


if __name__ == "__main__":
    test = TestSimulator()
    test.test_new_simulation_state()
    test.test_aggregate_agent_and_market_states()

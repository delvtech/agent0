"""Testing for the ElfPy package modules"""
from __future__ import annotations  # types are strings by default in 3.11

import logging
import unittest

import numpy as np
from numpy.random import RandomState

from elfpy.types import Config
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
        config = Config()
        config.pricing_model_name = "Hyperdrive"
        config.num_trading_days = 3
        config.num_blocks_per_day = 3
        simulator = sim_utils.get_simulator(config)
        simulator.run_simulation()
        output_utils.close_logging()

    def test_yieldspace_sim(self):
        """Tests yieldspace simulation"""
        self.setup_logging()
        config = Config()
        config.pricing_model_name = "Yieldspace"
        config.num_trading_days = 3
        config.num_blocks_per_day = 3
        simulator = sim_utils.get_simulator(config)
        simulator.run_simulation()
        output_utils.close_logging()

    def test_set_rng(self):
        """Test error handling & resetting simulator random number generator"""
        self.setup_logging()
        config = Config()
        config.num_trading_days = 3
        config.num_blocks_per_day = 3
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
        config = Config()
        config.num_trading_days = 3
        config.num_blocks_per_day = 3
        simulator = sim_utils.get_simulator(config)
        simulator.run_simulation()
        simulation_state_num_writes = np.array([len(value) for value in simulator.simulation_state.__dict__.values()])
        goal_writes = simulation_state_num_writes[0]
        try:
            np.testing.assert_equal(simulation_state_num_writes, goal_writes)
        except Exception as exc:
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

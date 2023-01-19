"""
Testing for the ElfPy package modules
"""

# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-locals
# pylint: disable=attribute-defined-outside-init
# pylint: disable=duplicate-code

import logging
import unittest

import numpy as np
from numpy.random import RandomState

from elfpy.simulators import Simulator
from elfpy.utils.config import Config
from elfpy.utils.parse_config import load_and_parse_config_file
from elfpy.utils import sim_utils  # utilities for setting up a simulation
import elfpy.utils.outputs as output_utils
import elfpy.utils.parse_config as config_utils


class BaseSimTest(unittest.TestCase):
    """Simulator base test class"""

    # TODO: modernize this class, using helper functions, lower days to 3, etc.

    @staticmethod
    def setup_logging(log_level=logging.DEBUG):
        """Setup logging and handlers for the test"""
        log_filename = ".logging/test_sim.log"
        output_utils.setup_logging(log_filename, log_level=log_level)

    @staticmethod
    def close_logging(delete_logs=True):
        """Close logging and handlers for the test"""
        output_utils.close_logging(delete_logs=delete_logs)

    def setup_simulator_inputs(
        config_file, override_dict=None
    ) -> tuple[Config, Market, Dict[int, Agent], Generator, RandomSimulationVariables]:
        """Instantiate input objects to the simulator class"""
        if override_dict is None:
            override_dict = {}
        config = config_utils.override_config_variables(load_and_parse_config_file(config_file), override_dict)
        return config

    @staticmethod
    def setup_simulator(config_file, override_dict=None):
        """Instantiate the simulator object"""
        config = BaseSimTest.setup_config(config_file, override_dict)
        simulator = sim_utils.get_simulator(config)
        return simulator

    def setup_and_run_simulator(self, config_file, override_dict):
        """Construct and run the simulator"""
        simulator = self.setup_simulator(config_file, override_dict)
        # run the simulation
        simulator.run_simulation()
        return simulator

    def run_hyperdrive_test(self, delete_logs=True):
        """Tests the simulator output to verify that indices are correct"""
        self.setup_logging()
        config_file = "config/example_config.toml"
        for rng_seed in range(1, 10):
            try:
                override_dict = {"num_trading_days": 5, "num_blocks_per_day": 3}
                _ = self.setup_and_run_simulator(config_file, override_dict)
            # pylint: disable=broad-except
            except Exception as exc:
                raise AssertionError(f"ERROR: Test failed at seed {rng_seed}") from exc
        self.close_logging(delete_logs=delete_logs)

    def run_set_rng_test(self, delete_logs=True):
        """Verifies that the rng gets set properly & fails properly"""
        self.setup_logging()
        config_file = "config/example_config.toml"
        override_dict = {"num_trading_days": 5, "num_blocks_per_day": 3}
        simulator = self.setup_simulator(config_file, override_dict)
        new_rng = np.random.default_rng(1234)
        simulator.set_rng(new_rng)
        assert simulator.rng == new_rng
        for bad_input in ([1234, "1234", RandomState(1234)],):
            with self.assertRaises(TypeError):
                simulator.set_rng(bad_input)
        self.close_logging(delete_logs=delete_logs)

    def run_log_config_variables_test(self, delete_logs=True):
        """Verfies that the config variables are successfully logged"""
        self.setup_logging(log_level=logging.INFO)
        config_file = "config/example_config.toml"
        simulator = self.setup_simulator(config_file)
        simulator.log_config_variables()
        self.assertLogs(level=logging.INFO)
        self.close_logging(delete_logs=delete_logs)

    def run_random_variables_test(self, delete_logs=True):
        """Test random variable creation & overriding"""
        self.setup_logging()
        config_file = "config/example_config.toml"
        override_list = [
            {},
            {"fee_percent": 0.1},
            {
                "num_trading_days": 3,
                "vault_apr": {"type": "Constant", "value": 0.05},
            },  # this should get generated as a list
            {
                "num_trading_days": 3,
                "vault_apr": {"type": "GeometricBrownianMotion", "initial": 0.05},
            },  # this should get generated as a list
            {"num_trading_days": 3, "vault_apr": [0.05, 0.04, 0.03]},
        ]
        for override_dict in override_list:
            simulator = self.setup_simulator(config_file, override_dict)
            random_sim_vars = simulator.random_variables

            # Ensure that the random variable list is being assigned properly.
            if "vault_apr" in override_dict and isinstance(override_dict["vault_apr"], float):
                # check that broadcasting works
                assert len(simulator.random_variables.vault_apr) == override_dict["num_trading_days"]

            # Ensure that the random variable list is created if it is None.
            simulator = Simulator(
                config=simulator.config,
                market=simulator.market,
                random_simulation_variables=None,
            )
            assert simulator.random_variables is not None
            assert np.all(simulator.random_variables != random_sim_vars)

        # Ensure that initializing the simulator with an invalid override list
        # raises an error.
        incorrect_override_dict = {"num_trading_days": 5, "vault_apr": [0.05, 0.04, 0.03]}
        invalid_config = BaseSimTest.setup_config(config_file, incorrect_override_dict)
        simulator = BaseSimTest.setup_simulator(config_file)
        with self.assertRaises(ValueError):
            Simulator(
                config=invalid_config,
                market=simulator.market,
            )

        self.close_logging(delete_logs=delete_logs)

    def run_simulation_state_test(self, delete_logs=True):
        """Runs a small number of trades, then checks that simulation_state
        has the correct number of logs per category.
        """
        self.setup_logging()
        config_file = "config/example_config.toml"
        override_dict = {"num_trading_days": 3, "num_blocks_per_day": 3}
        simulator = self.setup_and_run_simulator(config_file, override_dict)
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
            raise AssertionError(f"ERROR: Analysis keys have too many entries: {bad_keys}") from exc
        self.close_logging(delete_logs=delete_logs)


class TestSimulator(BaseSimTest):
    """Test running a simulation using each pricing model type"""

    # TODO: add similar test for a sim using the other PMs
    def test_hyperdrive_sim(self):
        """Tests hyperdrive setup"""
        self.run_hyperdrive_test()

    def test_log_config_variables(self):
        """Tests the log_config_variables function"""
        self.run_log_config_variables_test(delete_logs=True)

    def test_set_rng(self):
        """Test error handling & resetting simulator random number generator"""
        self.run_set_rng_test(delete_logs=True)

    def test_random_variables(self):
        """Test override & initalizaiton of random variables"""
        self.run_random_variables_test(delete_logs=True)

    def test_simulation_state(self):
        """Test override & initalizaiton of random variables"""
        self.run_simulation_state_test(delete_logs=True)

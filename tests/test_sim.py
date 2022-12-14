"""
Testing for the ElfPy package modules
"""

# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-locals
# pylint: disable=attribute-defined-outside-init
# pylint: disable=duplicate-code

import logging
import unittest
import os
import numpy as np
from numpy.random import RandomState

from elfpy.simulators import Simulator
from elfpy.utils.parse_config import load_and_parse_config_file
from elfpy.utils import sim_utils  # utilities for setting up a simulation


class BaseSimTest(unittest.TestCase):
    """Simulator base test class"""

    def setup_simulator(self, config_file, override_dict=None):
        """Instantiate the simulator & other objects"""
        if override_dict is None:
            override_dict = {}  # empty dict means nothing is overridden
        # instantiate config object
        config = sim_utils.override_config_variables(load_and_parse_config_file(config_file), override_dict)
        # instantiate random number generator
        rng = np.random.default_rng(config.simulator.random_seed)
        # run random number generators to get random simulation arguments
        random_sim_vars = sim_utils.override_random_variables(
            sim_utils.get_random_variables(config, rng), override_dict
        )
        # instantiate the pricing model
        pricing_model = sim_utils.get_pricing_model(model_name=config.amm.pricing_model_name)
        # instantiate the market
        market = sim_utils.get_market(
            pricing_model,
            random_sim_vars.target_pool_apy,
            random_sim_vars.fee_percent,
            config.simulator.token_duration,
            random_sim_vars.init_share_price,
        )
        # instantiate the init_lp agent
        init_agents = {
            0: sim_utils.get_init_lp_agent(
                config,
                market,
                pricing_model,
                random_sim_vars.target_liquidity,
                random_sim_vars.target_pool_apy,
                random_sim_vars.fee_percent,
            )
        }
        # set up simulator with only the init_lp_agent
        simulator = Simulator(
            config=config,
            pricing_model=pricing_model,
            market=market,
            agents=init_agents,
            rng=rng,
            random_simulation_variables=random_sim_vars,
        )
        # initialize the market using the LP agent
        simulator.collect_and_execute_trades()
        return simulator

    def setup_and_run_simulator(self, config_file, override_dict):
        """Construct and run the simulator"""
        simulator = self.setup_simulator(config_file, override_dict)
        # run the simulation
        simulator.run_simulation()

    @staticmethod
    def setup_logging(logging_level=logging.DEBUG):
        """Setup logging and handlers for the test"""
        log_dir = ".logging"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        name = "test_sim.log"
        handler = logging.FileHandler(os.path.join(log_dir, name), "w")
        logging.getLogger().setLevel(logging_level)  # events of this level and above will be tracked
        handler.setFormatter(
            logging.Formatter(
                "\n%(asctime)s: %(levelname)s: %(module)s.%(funcName)s:\n%(message)s", "%y-%m-%d %H:%M:%S"
            )
        )
        logging.getLogger().handlers = [
            handler,
        ]

    def run_hyperdrive_test(self, delete_logs=True):
        """Tests the simulator output to verify that indices are correct"""
        self.setup_logging()
        config_file = "config/example_config.toml"
        for rng_seed in range(1, 10):
            try:
                # simulator.setup_simulated_entities()
                override_dict = {"num_trading_days": 5, "num_blocks_per_day": 3}
                self.setup_and_run_simulator(config_file, override_dict)
            # pylint: disable=broad-except
            except Exception as exc:
                assert False, f"ERROR: Test failed at seed {rng_seed} with exception\n{exc}"
        if delete_logs:
            file_loc = logging.getLogger().handlers[0].baseFilename
            os.remove(file_loc)

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
        if delete_logs:
            file_loc = logging.getLogger().handlers[0].baseFilename
            os.remove(file_loc)

    def run_log_config_variables_test(self, delete_logs=True):
        """Verfies that the config variables are successfully logged"""
        self.setup_logging(logging_level=logging.INFO)
        config_file = "config/example_config.toml"
        simulator = self.setup_simulator(config_file)
        simulator.log_config_variables()
        self.assertLogs(level=logging.INFO)
        if delete_logs:
            file_loc = logging.getLogger().handlers[0].baseFilename
            os.remove(file_loc)


class TestSimulator(BaseSimTest):
    """Test running a simulation using each pricing model type"""

    # TODO: add similar test for a sim using the element pricing model
    def test_hyperdrive_sim(self):
        """Tests hyperdrive setup"""
        self.run_hyperdrive_test()

    def test_log_config_variables(self):
        """Tests the log_config_variables function"""
        self.run_log_config_variables_test(delete_logs=True)

    def test_set_rng(self):
        """Test error handling & resetting simulator random number generator"""
        self.run_set_rng_test(delete_logs=True)

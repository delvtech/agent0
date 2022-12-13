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

from elfpy.simulators import Simulator
from elfpy.utils.parse_config import load_and_parse_config_file
from elfpy.utils import sim_utils  # utilities for setting up a simulation


class BaseTraderTest(unittest.TestCase):
    """Simulator base test class"""

    @staticmethod
    def setup_and_run_simulator(config_file, override_dict):
        """Construct and run the simulator"""
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
        # run the simulation
        simulator.run_simulation()
        return (market, pricing_model)

    @staticmethod
    def setup_logging():
        """Setup logging and handlers for the test"""
        logging_level = logging.DEBUG
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


class TestSimulator(BaseTraderTest):
    """Test running a simulation using each pricing model type"""

    def test_hyperdrive_sim(self):
        """Tests hyperdrive setup"""
        self.run_hyperdrive_test()

    # TODO: add similar test for a sim using the element pricing model

"""
Testing for logging in the ElfPy package modules
"""

# pylint: disable=duplicate-code

import unittest
import logging
import itertools
import os
import sys
from typing import Any

import numpy as np

from elfpy.utils.parse_config import load_and_parse_config_file
from elfpy.simulators import Simulator
from elfpy.utils import sim_utils  # utilities for setting up a simulation


class BaseLogTest(unittest.TestCase):
    """Generic test class"""

    @staticmethod
    def setup_and_run_simulator(config_file, override_dict: dict[str, Any]):
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
        # get trading agent list
        simulator.run_simulation()

    def run_logging_test(self, delete_logs=True):
        """
        For each logging level, run the simulator and check the logs
        """
        log_dir = ".logging"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        logging_levels = [
            logging.DEBUG,  # 10
            logging.INFO,  # 20
            logging.WARNING,  # 30
            logging.ERROR,  # 40
            logging.CRITICAL,  # 50
        ]
        handler_types = ["file", "stream"]
        for (level, handler_type) in itertools.product(logging_levels, handler_types):
            if handler_type == "file":
                name = f"test_logging_level-{level}.log"
                handler = logging.FileHandler(os.path.join(log_dir, name), "w")
            else:
                handler = logging.StreamHandler(sys.stdout)
            logging.getLogger().setLevel(level)  # events of this level and above will be tracked
            handler.setFormatter(
                logging.Formatter(
                    "\n%(asctime)s: %(levelname)s: %(module)s.%(funcName)s:\n%(message)s", "%y-%m-%d %H:%M:%S"
                )
            )
            logging.getLogger().handlers = [
                handler,
            ]

            config_file = "config/example_config.toml"
            override_dict = {
                "pricing_model_name": "Hyperdrive",
                "num_trading_days": 10,
                "num_blocks_per_day": 3,  # 1 block a day, keep it fast for testing
            }
            self.setup_and_run_simulator(config_file, override_dict)
            self.assertLogs(level=level)
            if delete_logs and handler_type == "file":
                file_loc = logging.getLogger().handlers[0].baseFilename
                os.remove(file_loc)


class TestLogging(BaseLogTest):
    """Run the logging tests"""

    def test_logging(self):
        """Tests logging"""
        self.run_logging_test(delete_logs=True)

"""
Testing for logging in the ElfPy package modules
"""

import unittest
import logging
import itertools
import os
import sys

import numpy as np

from elfpy.utils.parse_config import load_and_parse_config_file
from elfpy.simulators import Simulator


class LoggingTest(unittest.TestCase):
    """Generic test class"""

    def test_logging(self):
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
            config = load_and_parse_config_file(config_file)
            simulator = Simulator(config)
            simulator.set_rng(np.random.default_rng(simulator.config.simulator.random_seed))
            simulator.set_random_variables()
            override_dict = {
                "pricing_model_name": "Hyperdrive",
                "num_blocks_per_day": 1,  # 1 block a day, keep it fast for testing
            }
            simulator.setup_simulated_entities(override_dict)
            simulator.run_simulation()
            self.assertLogs(level=level)
            # comment this to view the generated log files
            if handler_type == "file":
                file_loc = logging.getLogger().handlers[0].baseFilename
                os.remove(file_loc)

"""Testing for logging in the ElfPy package modules"""
from __future__ import annotations

import unittest
import logging
import itertools
import os
import sys

import elfpy.utils.outputs as output_utils
from elfpy.simulators.config import Config
from elfpy.utils import sim_utils


class TestLogging(unittest.TestCase):
    """Run the logging tests"""

    def test_logging(self):
        """Tests logging"""
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
        for level, handler_type in itertools.product(logging_levels, handler_types):
            if handler_type == "file":
                log_name = f"test_logging_level-{level}.log"
                handler = logging.FileHandler(os.path.join(log_dir, log_name), "w")
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
            config = Config()
            config.pricing_model_name = "Yieldspace"
            config.num_trading_days = 3
            config.num_blocks_per_day = 3
            config.variable_apr = [0.05] * config.num_trading_days
            simulator = sim_utils.get_simulator(config)  # initialize
            simulator.run_simulation()  # run
            self.assertLogs(level=level)
            if handler_type == "file":
                output_utils.delete_log_file()

    def test_log_config_variables(self):
        """Verfies that the config variables are successfully logged"""
        log_filename = ".logging/test_sim.log"
        output_utils.setup_logging(log_filename, log_level=logging.INFO)
        config = Config()
        logging.info("%s", config)
        self.assertLogs(level=logging.INFO)
        output_utils.close_logging()

    def test_text_to_logging_level(self):
        """Test that logging level strings result in the correct integera amounts"""
        # change up case to test .lower()
        logging_levels = ["notset", "debug", "info", "Warning", "Error", "CRITICAL"]
        logging_constants = [0, 10, 20, 30, 40, 50]
        for level_str, level_int in zip(logging_levels, logging_constants):
            func_level = output_utils.text_to_log_level(level_str)
            assert level_int == func_level

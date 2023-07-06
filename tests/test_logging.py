"""Testing for logging in the ElfPy package modules"""
from __future__ import annotations

import itertools
import logging
import os
import sys
import unittest
from datetime import datetime

from ape.exceptions import TransactionError

import elfpy.utils.logs as log_utils
from elfpy.data.db_schema import PoolConfig, PoolInfo
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
                log_utils.close_logging()

    def test_log_config_variables(self):
        """Verfies that the config variables are successfully logged"""
        log_filename = ".logging/test_logging.log"
        log_utils.setup_logging(log_filename, log_level=logging.INFO)
        config = Config()
        logging.info("%s", config)
        self.assertLogs(level=logging.INFO)
        log_utils.close_logging()

    def test_multiple_handlers(self):
        """Verfies that two handlers are created if we log to file and stdout"""
        log_filename = ".logging/test_logging.log"
        # one handler because we're logging to file only
        log_utils.setup_logging(log_filename, log_stdout=False)
        self.assertEqual(len(logging.getLogger().handlers), 1)
        log_utils.close_logging()
        # one handler because we're logging to stdout only
        log_utils.setup_logging()
        self.assertEqual(len(logging.getLogger().handlers), 1)
        log_utils.close_logging()
        # two handlers because we're logging to file and stdout
        log_utils.setup_logging(log_filename, log_stdout=True)
        self.assertEqual(len(logging.getLogger().handlers), 2)
        log_utils.close_logging()

    def test_hyperdrive_crash_report_logging(self):
        """Tests logging"""
        log_utils.setup_hyperdrive_crash_report_logging()
        config = Config()
        config.pricing_model_name = "Yieldspace"
        config.num_trading_days = 3
        config.num_blocks_per_day = 3
        config.variable_apr = [0.05] * config.num_trading_days
        simulator = sim_utils.get_simulator(config)  # initialize
        simulator.run_simulation()  # run

        self.assertLogs(level=logging.CRITICAL)
        log_utils.log_hyperdrive_crash_report(
            "CLOSE_LONG",
            TransactionError("Message"),
            1.23,
            "0x0000000000000000000000000000000000000000",
            PoolInfo(blockNumber=1234, timestamp=datetime.fromtimestamp(12345678)),
            PoolConfig(contractAddress="0x0000000000000000000000000000000000000000"),
        )
        log_utils.close_logging()

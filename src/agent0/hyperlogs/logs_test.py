"""Tests for logging utils modules."""

from __future__ import annotations

import itertools
import logging
import os
import sys
import unittest

from . import add_file_handler, add_stdout_handler, close_logging, get_root_logger, setup_logging


class TestLogging(unittest.TestCase):
    """Run the logging tests."""

    def test_logging(self):
        """Tests logging."""
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
            get_root_logger().setLevel(level)  # events of this level and above will be tracked
            handler.setFormatter(
                logging.Formatter(
                    "\n%(asctime)s: %(levelname)s: %(module)s.%(funcName)s:\n%(message)s", "%y-%m-%d %H:%M:%S"
                )
            )
            get_root_logger().handlers = [
                handler,
            ]
            logging.debug("Debug test")
            logging.info("Info test")
            logging.warning("Warning test")
            logging.error("Error test")
            logging.critical("Critical test")
            self.assertLogs(level=level)
            if handler_type == "file":
                close_logging()

    def test_multiple_handlers_setup_logging(self):
        """Verfies that two handlers are created if we log to file and stdout."""
        log_filename = ".logging/test_logging.log"
        # one handler because we're logging to file only
        setup_logging(log_filename=log_filename, log_stdout=False, keep_previous_handlers=False)
        self.assertEqual(len(get_root_logger().handlers), 1)
        close_logging()
        # No handlers after closing
        self.assertEqual(len(get_root_logger().handlers), 0)
        # one handler because we're logging to stdout only
        setup_logging(log_stdout=True)
        self.assertEqual(len(get_root_logger().handlers), 1)
        close_logging()
        # No handlers after closing
        self.assertEqual(len(get_root_logger().handlers), 0)
        # two handlers because we're logging to file and stdout
        setup_logging(log_filename=log_filename, log_stdout=True)
        self.assertEqual(len(get_root_logger().handlers), 2)
        close_logging()
        # No handlers after closing
        self.assertEqual(len(get_root_logger().handlers), 0)

    def test_multiple_handlers_add_handlers(self):
        """Verfies that two handlers are created if we log to file and stdout."""
        log_filename = ".logging/test_logging.log"
        # one handler because we're logging to file only
        add_stdout_handler(keep_previous_handlers=False)
        self.assertEqual(len(get_root_logger().handlers), 1)
        close_logging()
        # one handler because we're logging to stdout only
        add_file_handler(log_filename=log_filename)
        self.assertEqual(len(get_root_logger().handlers), 1)
        close_logging()
        # two handlers because we're logging to file and stdout
        add_stdout_handler(keep_previous_handlers=False)
        add_file_handler(log_filename=log_filename)
        self.assertEqual(len(get_root_logger().handlers), 2)
        close_logging()

"""Helper functions for delivering simulation outputs"""
from __future__ import annotations

import json
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

import elfpy


## Logging
def setup_logging(
    log_filename: str | None = None,
    max_bytes: int = elfpy.DEFAULT_LOG_MAXBYTES,
    log_level: int = elfpy.DEFAULT_LOG_LEVEL,
    delete_previous_logs: bool = False,
    log_file_and_stdout: bool = False,
    log_formatter: str = elfpy.DEFAULT_LOG_FORMATTER,
) -> None:
    r"""Setup logging and handlers with default settings"""
    # pylint: disable=too-many-arguments
    if log_filename is None and log_file_and_stdout is True:
        raise ValueError(f"{log_filename=} cannot be None and {log_file_and_stdout=} be True")
    handlers = []
    log_formatter = logging.Formatter(log_formatter, elfpy.DEFAULT_LOG_DATETIME)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(log_formatter)
    if log_filename is not None:
        log_dir, log_name = os.path.split(log_filename)
        if not log_name.endswith(".log"):
            log_name += ".log"
        if log_dir == "":  # we have just a filename, log to default .logging directory
            base_folder = os.path.dirname(os.path.dirname(os.path.abspath(elfpy.__file__)))
            log_dir = os.path.join(base_folder, ".logging")
        if not os.path.exists(log_dir):  # create log_dir if necessary
            os.makedirs(log_dir)
        # delete the log file if it exists
        if delete_previous_logs and os.path.exists(os.path.join(log_dir, log_name)):
            os.remove(os.path.join(log_dir, log_name))
        file_handler = RotatingFileHandler(os.path.join(log_dir, log_name), mode="w", maxBytes=max_bytes)
        file_handler.setFormatter(log_formatter)
        handlers.append(file_handler)
    if log_file_and_stdout is True or log_filename is None:
        handlers.append(stream_handler)
    logging.getLogger().setLevel(log_level)  # events of this level and above will be tracked
    logging.getLogger().handlers = handlers  # overwrite handlers with the desired one


def close_logging(delete_logs=True):
    r"""Close logging and handlers for the test"""
    logging.shutdown()
    if delete_logs:
        for handler in logging.getLogger().handlers:
            if hasattr(handler, "baseFilename") and not isinstance(handler, logging.StreamHandler):
                # access baseFilename in a type safe way
                handler_file_name = getattr(handler, "baseFilename", None)
                if handler_file_name is not None and os.path.exists(handler_file_name):
                    os.remove(handler_file_name)
            handler.close()

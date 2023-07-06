"""Utility functions for logging."""
from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

import elfpy


def setup_logging(
    log_filename: str | None = None,
    max_bytes: int = elfpy.DEFAULT_LOG_MAXBYTES,
    log_level: int = elfpy.DEFAULT_LOG_LEVEL,
    delete_previous_logs: bool = False,
    log_stdout: bool = True,
    log_formatter: logging.Formatter | None = None,
) -> None:
    # pylint: disable=too-many-arguments
    """
    Setup logging and handlers with default settings.

    Note:
        The log_filename can be a path to the log file. If log_filename is not provided,
        log_file_and_stdout can be set to True to log to both file and standard output (console). If
        neither log_filename nor log_file_and_stdout is specified, the log messages will be sent to
        standard output only.

    Arguments
    ----------
        log_filename : (str, optional)
            Path and name of the log file.
        max_bytes : (int, optional)
            Maximum size of the log file in bytes. Defaults to elfpy.DEFAULT_LOG_MAXBYTES.
        log_level : (int, optional)
            Log level to track. Defaults to elfpy.DEFAULT_LOG_LEVEL.
        delete_previous_logs : (bool, optional)
            Whether to delete previous log file if it exists. Defaults to False.
        log_file_and_stdout : (bool, optional)
            Whether to log to both file and standard output. Defaults to False.
        log_formatter (logging.Formatter, optional):
            Log formatter object. Defaults to None.

    Raises
    ------
        ValueError: If log_filename is None and log_file_and_stdout is True.

    """

    # Create log handlers
    handlers = []
    if log_formatter is None:
        log_formatter = logging.Formatter(elfpy.DEFAULT_LOG_FORMATTER, elfpy.DEFAULT_LOG_DATETIME)

    if log_stdout:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(log_formatter)
        handlers.append(stream_handler)

    if log_filename is not None:
        log_dir, log_name = _prepare_log_path(log_filename)

        # Delete the log file if requested
        if delete_previous_logs and os.path.exists(os.path.join(log_dir, log_name)):
            os.remove(os.path.join(log_dir, log_name))

        file_handler = _create_file_handler(log_dir, log_name, log_formatter, max_bytes)
        handlers.append(file_handler)

    # Configure the root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    logger.handlers = handlers


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


def _prepare_log_path(log_filename: str):
    """Prepare log file path and name"""
    log_dir, log_name = os.path.split(log_filename)

    # Append ".log" extension if necessary
    if not log_name.endswith(".log"):
        log_name += ".log"

    # Use default log directory if log_dir is not provided
    if log_dir == "":
        base_folder = os.path.dirname(os.path.dirname(os.path.abspath(elfpy.__file__)))
        log_dir = os.path.join(base_folder, ".logging")

    # Create log directory if necessary
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    return log_dir, log_name


def _create_file_handler(log_dir: str, log_name: str, log_formatter: logging.Formatter, max_bytes: int):
    """Create a file handler for the given log file"""
    log_path = os.path.join(log_dir, log_name)
    handler = RotatingFileHandler(log_path, mode="w", maxBytes=max_bytes)
    handler.setFormatter(log_formatter)
    return handler

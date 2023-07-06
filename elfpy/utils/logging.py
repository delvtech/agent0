import logging
import os
import sys
from logging.handlers import RotatingFileHandler

import elfpy


def setup_logging(
    log_filename: str | None = None,
    max_bytes: int = elfpy.DEFAULT_LOG_MAXBYTES,
    log_level: str = elfpy.DEFAULT_LOG_LEVEL,
    delete_previous_logs: bool = False,
    log_file_and_stdout: bool = False,
    log_formatter: logging.Formatter | None = None,
) -> None:
    """
    Setup logging and handlers with default settings.

    Parameters:
        log_filename (str, optional): Path and name of the log file.
        max_bytes (int, optional): Maximum size of the log file in bytes. Defaults to elfpy.DEFAULT_LOG_MAXBYTES.
        log_level (str, optional): Log level to track. Defaults to elfpy.DEFAULT_LOG_LEVEL.
        delete_previous_logs (bool, optional): Whether to delete previous log file if it exists. Defaults to False.
        log_file_and_stdout (bool, optional): Whether to log to both file and standard output. Defaults to False.
        log_formatter (logging.Formatter, optional): Log formatter object. Defaults to None.

    Raises:
        ValueError: If log_filename is None and log_file_and_stdout is True.

    Note:
        The log_filename can be a path to the log file. If log_filename is not provided,
        log_file_and_stdout can be set to True to log to both file and standard output (console).
        If neither log_filename nor log_file_and_stdout is specified, the log messages will be sent to standard output only.
    """

    # Validate arguments
    if log_filename is None and log_file_and_stdout is True:
        raise ValueError(f"{log_filename=} cannot be None and {log_file_and_stdout=} be True")

    # Create log handlers
    handlers = []
    if log_formatter is None:
        log_formatter = logging.Formatter(elfpy.DEFAULT_LOG_FORMATTER, elfpy.DEFAULT_LOG_DATETIME)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(log_formatter)

    if log_filename is not None:
        log_dir, log_name = _prepare_log_path(log_filename)

        # Delete the log file if requested
        if delete_previous_logs and os.path.exists(os.path.join(log_dir, log_name)):
            os.remove(os.path.join(log_dir, log_name))

        file_handler = _create_file_handler(log_dir, log_name, log_formatter, max_bytes)
        handlers.append(file_handler)

    if log_file_and_stdout is True or log_filename is None:
        handlers.append(stream_handler)

    # Configure the root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    logger.handlers = handlers


def _prepare_log_path(log_filename):
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


def _create_file_handler(log_dir, log_name, log_formatter, max_bytes):
    """Create a file handler for the given log file"""
    log_path = os.path.join(log_dir, log_name)
    handler = RotatingFileHandler(log_path, mode="w", maxBytes=max_bytes)
    handler.setFormatter(log_formatter)
    return handler

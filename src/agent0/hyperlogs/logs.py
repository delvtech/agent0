"""Utility functions for logging."""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

# Logging defaults
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_LOG_FORMATTER = "\n%(asctime)s: %(levelname)s: %(filename)s:%(lineno)s::%(module)s::%(funcName)s:\n%(message)s"
DEFAULT_LOG_DATETIME = "%y-%m-%d %H:%M:%S"
DEFAULT_LOG_MAXBYTES = int(2e6)  # 2MB


def setup_logging(
    log_filename: str | None = None,
    max_bytes: int | None = None,
    log_level: int | None = None,
    delete_previous_logs: bool = False,
    log_stdout: bool = True,
    log_format_string: str | None = None,
    keep_previous_handlers: bool = False,
) -> None:
    r"""Set up basic logging with default settings, customized by inputs.

    This function should only be run once, as it implements the default settings.
    To customize logging behavior, only add_stdout_handler or add_file_handler should be run.

    The log_filename can be a path to the log file. If log_filename is not provided,
    log_file_and_stdout can be set to True to log to both file and standard output (console). If
    neither log_filename nor log_file_and_stdout is specified, the log messages will be sent to
    standard output only.

    Arguments
    ---------
    log_filename: str, optional
        Path and name of the log file.
    max_bytes: int, optional
        Maximum size of the log file in bytes. Defaults to hyperlogs.DEFAULT_LOG_MAXBYTES.
    log_level: int, optional
        Log level to track. Defaults to hyperlogs.DEFAULT_LOG_LEVEL.
    delete_previous_logs: bool, optional
        Whether to delete previous log file if it exists. Defaults to False.
    log_stdout: bool, optional
        Whether to log to standard output. Defaults to True.
    log_format_string: str, optional
        Log formatter object. Defaults to None.
    keep_previous_handlers: bool, optional
        Whether to keep previous handlers. Defaults to False.

    .. todo::
        - Test the various optional input combinations
    """
    # pylint: disable=too-many-arguments
    # remove all handlers if requested
    if not keep_previous_handlers:
        remove_handlers(get_root_logger())
    # add handler logging to stdout if requested
    if log_stdout is True:
        add_stdout_handler(log_format_string=log_format_string, log_level=log_level)
    # add handler logging to file if requested
    if log_filename is not None:
        add_file_handler(
            log_filename=log_filename,
            delete_previous_logs=delete_previous_logs,
            log_format_string=log_format_string,
            max_bytes=max_bytes,
            log_level=log_level,
        )
    # Set the root logger's level to the lowest level among all of its
    # While the root logger doesn't log anything, it captures logging statements to feed to the handlers
    # Therefore set the root logger's level to the lowest level among all of its handlers
    if get_root_logger().handlers:
        get_root_logger().setLevel(min(handler.level for handler in get_root_logger().handlers))
    else:
        get_root_logger().setLevel(create_log_level(log_level))


def close_logging(delete_logs=True) -> None:
    """Close logging and remove handlers for the test.

    Arguments
    ---------
    delete_logs: bool
        Whether to delete logs before closing logging.
    """
    logging.shutdown()
    root_logger = get_root_logger()
    if delete_logs:
        # Close all handlers
        for handler in root_logger.handlers:
            if hasattr(handler, "baseFilename") and not isinstance(handler, logging.StreamHandler):
                # access baseFilename in a type safe way
                handler_file_name = getattr(handler, "baseFilename", None)
                if handler_file_name is not None and os.path.exists(handler_file_name):
                    os.remove(handler_file_name)
            handler.close()
    # Remove all handlers
    remove_handlers(root_logger)


def prepare_log_path(log_filename: str) -> tuple[str, str]:
    """Split filename into path and name. Postpend ".log" extension if necessary. Make dir if necessary.

    Arguments
    ---------
    log_filename: str
        Path and name of the log file.

    Returns
    -------
    tuple[log_dir: str, log_name: str]
        log_dir: str
            Path of the log file.
        log_name: str
            Name of the log file.
    """
    log_dir, log_name = os.path.split(log_filename)
    # Append ".log" extension if necessary
    if not log_name.endswith(".log"):
        log_name += ".log"
    # Use default log directory if log_dir is not provided
    if log_dir == "":
        # Default directory is wherever the scripts get ran from.
        base_folder = os.getcwd()
        log_dir = os.path.join(base_folder, ".logging")
    # Create log directory if necessary
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    return log_dir, log_name


def create_formatter(log_format_string: str | None = None) -> logging.Formatter:
    """Create Formatter object from a log format string, applying default settings if log_format_string is None.

    Default settings are defined in hyperlogs.DEFAULT_LOG_FORMATTER and hyperlogs.DEFAULT_LOG_DATETIME.

    Arguments
    ---------
    log_format_string: str, optional
        Logging format described in string format.

    Returns
    -------
    logging.Formatter
        Logging format as a Formatter object, after defaults are applied.
    """
    if log_format_string is None:
        log_formatter = logging.Formatter(DEFAULT_LOG_FORMATTER, DEFAULT_LOG_DATETIME)
    else:
        log_formatter = logging.Formatter(log_format_string, DEFAULT_LOG_DATETIME)
    return log_formatter


def create_log_level(log_level: int | None = None) -> int:
    """Create log level, applying default hyperlogs.DEFAULT_LOG_LEVEL if log_level is None.

    Arguments
    ---------
    log_level: int, optional
        Logging level to be created. Defaults to hyperlogs.DEFAULT_LOG_LEVEL.

    Returns
    -------
    int
        Logging level that was created, after defaults are applied.
    """
    if log_level is None:
        log_level = DEFAULT_LOG_LEVEL
    return log_level


def create_max_bytes(max_bytes: int | None = None) -> int:
    """Create max bytes, applying default hyperlogs.DEFAULT_LOG_MAXBYTES if max_bytes is None.

    Arguments
    ---------
    max_bytes: int, optional
        Maximum size of the log file in bytes. Defaults to hyperlogs.DEFAULT_LOG_MAXBYTES.

    Returns
    -------
    int
        Maximum size of the log file in bytes, after defaults are applied.
    """
    if max_bytes is None:
        max_bytes = DEFAULT_LOG_MAXBYTES
    return max_bytes


def get_root_logger(root_logger: logging.Logger | None = None) -> logging.Logger:
    """Retrieve root logger, isolated from other loggers (like pytest).

    Arguments
    ---------
    root_logger: logging.Logger, optional
        Logger to which to add the handler. Defaults to  logging.getLogger().

    Returns
    -------
    logging.Logger
        Root logger.
    """
    if root_logger is None:
        root_logger = logging.getLogger()
    return root_logger


def add_stdout_handler(
    logger: logging.Logger | None = None,
    log_format_string: str | None = None,
    log_level: int | None = logging.INFO,
    keep_previous_handlers: bool = True,
) -> None:
    """Add a stdout handler to the root logger.

    Arguments
    ---------
    logger: logging.Logger, optional
        Logger to which to add the handler. Defaults to get_root_logger().
    log_format_string: str, optional
        Logging format described in string format. Defaults to
        hyperlogs.DEFAULT_LOG_FORMAT and hyperlogs.DEFAULT_LOG_DATETIME.
    log_level: int, optional
        Log level to track. Defaults to hyperlogs.DEFAULT_LOG_LEVEL.
    keep_previous_handlers: bool, optional
        Whether to keep previous handlers. Defaults to True.
    """
    logger = get_root_logger(logger)
    if not keep_previous_handlers:
        remove_handlers(logger)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(create_log_level(log_level))
    stream_handler.setFormatter(create_formatter(log_format_string))
    logger.addHandler(stream_handler)


def add_file_handler(
    log_filename: str,
    logger: logging.Logger | None = None,
    delete_previous_logs: bool = False,
    log_format_string: str | None = None,
    log_level: int | None = logging.INFO,
    max_bytes=None,
    keep_previous_handlers: bool = True,
):
    """Add a file handler to the root logger.

    Arguments
    ---------
    log_filename: str
        Path and name of the log file.
    logger: logging.Logger, optional
        Logger to which to add the handler. Defaults to get_root_logger().
    delete_previous_logs: bool, optional
        Whether to delete previous log file if it exists. Defaults to False.
    log_format_string: str, optional
        Logging format described in string format.
    log_level: int, optional
        Log level to track. Defaults to hyperlogs.DEFAULT_LOG_LEVEL.
    max_bytes: int, optional
        Maximum size of the log file in bytes. Defaults to hyperlogs.DEFAULT_LOG_MAXBYTES.
    keep_previous_handlers: bool, optional
        Whether to keep previous handlers. Defaults to True.
    """
    # pylint: disable=too-many-arguments
    logger = get_root_logger(logger)
    if not keep_previous_handlers:
        remove_handlers(logger)
    log_dir, log_name = prepare_log_path(log_filename)
    # Delete the log file if requested
    if delete_previous_logs and os.path.exists(os.path.join(log_dir, log_name)):
        os.remove(os.path.join(log_dir, log_name))
    file_handler = create_file_handler(
        log_dir, log_name, create_formatter(log_format_string), create_max_bytes(max_bytes), create_log_level(log_level)
    )
    logger.addHandler(file_handler)


def remove_handlers(logger: logging.Logger):
    """Remove all handlers from the logger.

    Arguments
    ---------
    logger: logging.Logger
        Logger from which to remove handlers.
    """
    while logger.hasHandlers():
        logger.removeHandler(logger.handlers[0])


def create_file_handler(
    log_dir: str, log_name: str, log_formatter: logging.Formatter, max_bytes: int, log_level: int
) -> logging.Handler:
    """Create a file handler for the given log file.

    Arguments
    ---------
    log_dir: str
        Directory in which to log the file.
    log_name: str
        File name in which to log.
    log_formatter: logging.Formatter
        Logging format as a Formatter object.
    max_bytes: int
        Maximum size of the log file in bytes. Defaults to hyperlogs.DEFAULT_LOG_MAXBYTES.
    log_level: int
        Log level.

    Returns
    -------
    logging.Handler
        The logging handler.
    """
    log_path = os.path.join(log_dir, log_name)
    handler = RotatingFileHandler(log_path, mode="w", maxBytes=create_max_bytes(max_bytes))
    handler.setFormatter(log_formatter)
    handler.setLevel(log_level)
    return handler

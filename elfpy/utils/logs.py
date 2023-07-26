"""Utility functions for logging."""
from __future__ import annotations

import json
import logging
import os
import sys
import warnings
from logging.handlers import RotatingFileHandler

from web3.exceptions import InvalidTransaction

import elfpy
import elfpy.utils.format as format_utils
from elfpy.data.db_schema import Base, PoolConfig, PoolInfo


def initialize_basic_logging(
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
    log_filename : str, optional
        Path and name of the log file.
    max_bytes : int, optional
        Maximum size of the log file in bytes. Defaults to elfpy.DEFAULT_LOG_MAXBYTES.
    log_level : int, optional
        Log level to track. Defaults to elfpy.DEFAULT_LOG_LEVEL.
    delete_previous_logs : bool, optional
        Whether to delete previous log file if it exists. Defaults to False.
    log_stdout : bool, optional
        Whether to log to standard output. Defaults to True.
    log_format_string : str, optional
        Log formatter object. Defaults to None.
    keep_previous_handlers : bool, optional
        Whether to keep previous handlers. Defaults to False.

    .. todo::
        - Fix the docstring
        - Test the various optional input combinations
    """
    # pylint: disable=too-many-arguments
    # sane defaults to avoid spam from libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("web3").setLevel(logging.WARNING)
    warnings.filterwarnings("ignore", category=UserWarning, module="web3.contract.base_contract")
    # remove all handlers if requested
    if not keep_previous_handlers:
        _remove_handlers(get_root_logger())
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
        get_root_logger().setLevel(_create_log_level(log_level))


def close_logging(delete_logs=True):
    r"""Close logging and remove handlers for the test."""
    logging.shutdown()
    root_logger = get_root_logger()
    if delete_logs:
        for handler in root_logger.handlers:
            if hasattr(handler, "baseFilename") and not isinstance(handler, logging.StreamHandler):
                # access baseFilename in a type safe way
                handler_file_name = getattr(handler, "baseFilename", None)
                if handler_file_name is not None and os.path.exists(handler_file_name):
                    os.remove(handler_file_name)
            handler.close()
            root_logger.removeHandler(handler)


def _prepare_log_path(log_filename: str):
    """Prepare log file path and name."""
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


def _create_formatter(log_format_string: str | None = None):
    """Create Formatter object from a log format string, applying default settings if log_format_string is None."""
    if log_format_string is None:
        log_formatter = logging.Formatter(elfpy.DEFAULT_LOG_FORMATTER, elfpy.DEFAULT_LOG_DATETIME)
    else:
        log_formatter = logging.Formatter(log_format_string, elfpy.DEFAULT_LOG_DATETIME)
    return log_formatter


def _create_log_level(log_level):
    """Create log level, applying default settings if log_level is None."""
    if log_level is None:
        log_level = elfpy.DEFAULT_LOG_LEVEL
    return log_level


def get_root_logger(root_logger: logging.Logger | None = None) -> logging.Logger:
    """Retrieve root logger used for elf-simulations, isolated from other loggers (like pytest)."""
    if root_logger is None:
        root_logger = logging.getLogger()
    return root_logger


def add_stdout_handler(
    logger: logging.Logger | None = None,
    log_format_string: str | None = None,
    log_level: int | None = logging.INFO,
    keep_previous_handlers: bool = True,
):
    """Add a stdout handler to the root logger."""
    logger = get_root_logger(logger)
    if not keep_previous_handlers:
        _remove_handlers(logger)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(_create_log_level(log_level))
    stream_handler.setFormatter(_create_formatter(log_format_string))
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
    """Add a file handler to the root logger."""
    # pylint: disable=too-many-arguments
    logger = get_root_logger(logger)
    if not keep_previous_handlers:
        _remove_handlers(logger)
    if max_bytes is None:
        max_bytes = elfpy.DEFAULT_LOG_MAXBYTES
    log_dir, log_name = _prepare_log_path(log_filename)
    # Delete the log file if requested
    if delete_previous_logs and os.path.exists(os.path.join(log_dir, log_name)):
        os.remove(os.path.join(log_dir, log_name))
    file_handler = _create_file_handler(
        log_dir, log_name, _create_formatter(log_format_string), max_bytes, _create_log_level(log_level)
    )
    logger.addHandler(file_handler)


def _remove_handlers(logger: logging.Logger):
    while logger.handlers:
        logger.removeHandler(logger.handlers[-1])


def _create_file_handler(log_dir: str, log_name: str, log_formatter: logging.Formatter, max_bytes: int, log_level: int):
    """Create a file handler for the given log file."""
    log_path = os.path.join(log_dir, log_name)
    handler = RotatingFileHandler(log_path, mode="w", maxBytes=max_bytes)
    handler.setFormatter(log_formatter)
    handler.setLevel(log_level)
    return handler


def setup_hyperdrive_crash_report_logging(log_format_string: str | None = None):
    """Create a new logging file handler with CRITICAL log level for hyperdrive crash reporting.

    In the future, a custom log level could be used specific to crash reporting.
    """
    add_file_handler(
        logger=None,  # use the default root logger
        log_filename="hyperdrive_crash_report.log",
        log_format_string=log_format_string,
        delete_previous_logs=False,
        log_level=logging.CRITICAL,
    )


# TODO: move this to somewhere like elfpy/contracts/hyperdrive/logging.py
def log_hyperdrive_crash_report(
    # TODO: better typing for this, an enum?
    trade_type: str,
    error: InvalidTransaction,
    amount: float,
    agent_address: str,
    pool_info: PoolInfo,
    pool_config: PoolConfig,
):
    # pylint: disable=too-many-arguments
    """Log a crash report for a hyperdrive transaction.

    Arguments
    ---------
    trade_type : str
        The type of trade being executed.

    error : TransactionError
        The transaction error that occurred.

    amount : float
        The amount of the transaction.

    agent_address : str
        The address of the agent executing the transaction.

    pool_info : PoolInfo
        Information about the pool involved in the transaction.

    pool_config : PoolConfig
        Configuration of the pool involved in the transaction.

    Returns
    -------
    None
        This function does not return any value.
    """
    pool_info_dict = _get_dict_from_schema(pool_info)
    pool_info_dict["timestamp"] = int(pool_info.timestamp.timestamp())
    formatted_pool_info = json.dumps(pool_info_dict, indent=4)

    pool_config_dict = _get_dict_from_schema(pool_config)
    formatted_pool_config = json.dumps(pool_config_dict, indent=4)
    logging.critical(
        """Failed to execute %s: %s\n Amount: %s\n Agent: %s\n PoolInfo: %s\n PoolConfig: %s\n""",
        trade_type,
        error,
        format_utils.format_numeric_string(amount),
        agent_address,
        formatted_pool_info,
        formatted_pool_config,
    )


def _get_dict_from_schema(db_schema: Base):
    """Quick helper to convert a SqlAlcemcy Row into a dict for printing.  There might be a better way to do this."""
    db_dict = db_schema.__dict__
    del db_dict["_sa_instance_state"]
    return db_dict

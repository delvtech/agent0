"""Utility functions for logging."""
from __future__ import annotations

import json
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

import elfpy
import elfpy.utils.format as format_utils
from elfpy.data.db_schema import Base, PoolConfig, PoolInfo


def setup_logging(
    log_filename: str | None = None,
    max_bytes: int | None = None,
    log_level: int | None = None,
    delete_previous_logs: bool = False,
    log_stdout: bool = True,
    log_format_string: str | None = None,
    keep_previous_handlers: bool = False,
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
        log_stdout : (bool, optional)
            Whether to log to standard output. Defaults to True.
        log_format_string : (str, optional)
            Log formatter object. Defaults to None.

    .. todo::
        - Fix the docstring
        - Test the various optional input combinations
    """
    # handle defaults
    if max_bytes is None:
        max_bytes = elfpy.DEFAULT_LOG_MAXBYTES
    if log_level is None:
        log_level = elfpy.DEFAULT_LOG_LEVEL
    if log_format_string is None:
        log_formatter = logging.Formatter(elfpy.DEFAULT_LOG_FORMATTER, elfpy.DEFAULT_LOG_DATETIME)
    else:
        log_formatter = logging.Formatter(log_format_string, elfpy.DEFAULT_LOG_DATETIME)
    # create log handlers
    handlers = logging.getLogger().handlers if keep_previous_handlers else []
    # pipe to stdout if requested
    if log_stdout:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(log_formatter)
        handlers.append(stream_handler)
    # log to file
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
    # logging.getLogger().handlers = []


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


def setup_hyperdrive_crash_report_logging():
    """Logging specifically for hyperdrive crash reporting.  Currently hijacking CRITICAL level
    until we need a custom level."""
    setup_logging(".logging/hyperdrive_test_crash_report.log", log_level=logging.CRITICAL, keep_previous_handlers=True)


# TODO: move this to somewhere like elfpy/contracts/hyperdrive/logging.py
# TODO: don't use ape's TransactionError, use web3's InvalidTransaction when we switch
def log_hyperdrive_crash_report(
    # TODO: better typing for this, an enum?
    trade_type: str,
    error: TransactionError,
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
    """Quick helper to convert a SqlAlcemcy Row into a dict for printing.  There might be a better way to do this?"""
    db_dict = db_schema.__dict__
    del db_dict["_sa_instance_state"]
    return db_dict

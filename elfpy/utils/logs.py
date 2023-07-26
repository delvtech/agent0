"""Utility functions for logging."""
from __future__ import annotations

import json
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from web3.exceptions import InvalidTransaction

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
    delete_logs : bool
        Whether to delete logs before closing logging.
    """
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


def prepare_log_path(log_filename: str) -> tuple[str, str]:
    """Split filename into path and name. Postpend ".log" extension if necessary. Make dir if necessary.

    Arguments
    ---------
    log_filename : str
        Path and name of the log file.

    Returns
    -------
    tuple[log_dir : str, log_name : str]
        log_dir : str
            Path of the log file.
        log_name : str
            Name of the log file.
    """
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


def create_formatter(log_format_string: str | None = None) -> logging.Formatter:
    """Create Formatter object from a log format string, applying default settings if log_format_string is None.

    Default settings are defined in elfpy.DEFAULT_LOG_FORMATTER and elfpy.DEFAULT_LOG_DATETIME.

    Arguments
    ---------
    log_format_string : str, optional
        Logging format described in string format.

    Returns
    -------
    log_formatter : logging.Formatter
        Logging format as a Formatter object, after defaults are applied.
    """
    if log_format_string is None:
        log_formatter = logging.Formatter(elfpy.DEFAULT_LOG_FORMATTER, elfpy.DEFAULT_LOG_DATETIME)
    else:
        log_formatter = logging.Formatter(log_format_string, elfpy.DEFAULT_LOG_DATETIME)
    return log_formatter


def create_log_level(log_level: int | None = None) -> int:
    """Create log level, applying default elfpy.DEFAULT_LOG_LEVEL if log_level is None.

    Arguments
    ---------
    log_level : int, optional
        Logging level to be created. Defaults to elfpy.DEFAULT_LOG_LEVEL.

    Returns
    -------
    log_level : int
        Logging level that was created, after defaults are applied.
    """
    if log_level is None:
        log_level = elfpy.DEFAULT_LOG_LEVEL
    return log_level


def create_max_bytes(max_bytes: int | None = None) -> int:
    """Create max bytes, applying default elfpy.DEFAULT_LOG_MAXBYTES if max_bytes is None.

    Arguments
    ---------
    max_bytes : int, optional
        Maximum size of the log file in bytes. Defaults to elfpy.DEFAULT_LOG_MAXBYTES.

    Returns
    -------
    max_bytes : int
        Maximum size of the log file in bytes, after defaults are applied.
    """
    if max_bytes is None:
        max_bytes = elfpy.DEFAULT_LOG_MAXBYTES
    return max_bytes


def get_root_logger(root_logger: logging.Logger | None = None) -> logging.Logger:
    """Retrieve root logger used for elf-simulations, isolated from other loggers (like pytest).

    Arguments
    ---------
    root_logger : logging.Logger, optional
        Logger to which to add the handler. Defaults to  logging.getLogger().

    Returns
    -------
    root_logger : logging.Logger
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
    logger : logging.Logger, optional
        Logger to which to add the handler. Defaults to get_root_logger().
    log_format_string : str, optional
        Logging format described in string format. Defaults to
        elfpy.DEFAULT_LOG_FORMAT and elfpy.DEFAULT_LOG_DATETIME.
    log_level : int, optional
        Log level to track. Defaults to elfpy.DEFAULT_LOG_LEVEL.
    keep_previous_handlers : bool, optional
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
    log_filename : str
        Path and name of the log file.
    logger : logging.Logger, optional
        Logger to which to add the handler. Defaults to get_root_logger().
    delete_previous_logs : bool, optional
        Whether to delete previous log file if it exists. Defaults to False.
    log_format_string : str, optional
        Logging format described in string format.
    log_level : int, optional
        Log level to track. Defaults to elfpy.DEFAULT_LOG_LEVEL.
    max_bytes : int, optional
        Maximum size of the log file in bytes. Defaults to elfpy.DEFAULT_LOG_MAXBYTES.
    keep_previous_handlers : bool, optional
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
    logger : logging.Logger
        Logger from which to remove handlers.
    """
    while logger.handlers:
        logger.removeHandler(logger.handlers[-1])


def create_file_handler(
    log_dir: str, log_name: str, log_formatter: logging.Formatter, max_bytes: int, log_level: int
) -> logging.Handler:
    """Create a file handler for the given log file.

    Arguments
    ---------
    log_dir : str
        Directory in which to log the file.
    log_name : str
        File name in which to log.
    log_formatter : logging.Formatter
        Logging format as a Formatter object.
    max_bytes : int
        Maximum size of the log file in bytes. Defaults to elfpy.DEFAULT_LOG_MAXBYTES.
    log_level : int
        Log level.
    """
    log_path = os.path.join(log_dir, log_name)
    handler = RotatingFileHandler(log_path, mode="w", maxBytes=create_max_bytes(max_bytes))
    handler.setFormatter(log_formatter)
    handler.setLevel(log_level)
    return handler


def setup_hyperdrive_crash_report_logging(log_format_string: str | None = None) -> None:
    """Create a new logging file handler with CRITICAL log level for hyperdrive crash reporting.

    In the future, a custom log level could be used specific to crash reporting.

    Arguments
    ---------
    log_format_string : str, optional
        Logging format described in string format.
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
) -> None:
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


def _get_dict_from_schema(db_schema: Base) -> dict:
    """Convert a SqlAlcemcy Row into a dict for printing. There might be a better way to do this.

    Arguments
    ---------
    db_schema : Base
        The database schema to convert to a dict.

    Returns
    -------
    db_dict : dict
        The database schema as a dict.
    """
    db_dict = db_schema.__dict__
    del db_dict["_sa_instance_state"]
    return db_dict

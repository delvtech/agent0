"""Utility function for logging bot crash reports."""
from __future__ import annotations

import json
import logging

from web3.exceptions import InvalidTransaction

import elfpy.utils.format as format_utils
from elfpy.utils import logs
from eth_bots.data.db_schema import Base, PoolConfig, PoolInfo


def setup_hyperdrive_crash_report_logging(log_format_string: str | None = None) -> None:
    """Create a new logging file handler with CRITICAL log level for hyperdrive crash reporting.

    In the future, a custom log level could be used specific to crash reporting.

    Arguments
    ---------
    log_format_string : str, optional
        Logging format described in string format.
    """
    logs.add_file_handler(
        logger=None,  # use the default root logger
        log_filename="hyperdrive_crash_report.log",
        log_format_string=log_format_string,
        delete_previous_logs=False,
        log_level=logging.CRITICAL,
    )


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

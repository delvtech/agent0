"""Utility function for logging agent crash reports."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

import numpy as np
from agent0.hyperdrive.state import HyperdriveWallet
from elfpy.utils import logs
from fixedpointmath import FixedPoint
from hexbytes import HexBytes
from numpy.random._generator import Generator as NumpyGenerator
from web3.datastructures import AttributeDict, MutableAttributeDict


class ExtendedJSONEncoder(json.JSONEncoder):
    r"""Custom encoder for JSON string dumps"""
    # pylint: disable=too-many-return-statements

    def default(self, o):
        r"""Override default behavior"""
        if isinstance(o, set):
            return list(o)
        if isinstance(o, HexBytes):
            return o.hex()
        if isinstance(o, (AttributeDict, MutableAttributeDict)):
            return dict(o)
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, FixedPoint):
            return str(o)
        if isinstance(o, NumpyGenerator):
            return "NumpyGenerator"
        if isinstance(o, datetime):
            return str(o)
        try:
            return o.__dict__
        except AttributeError:
            pass
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, o)


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
    trade_type: str,
    error: Exception,
    amount: FixedPoint,
    agent_address: str,
    agent_wallet: HyperdriveWallet,
    pool_info: dict[str, Any],
    pool_config: dict[str, Any],
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
    agent_wallet: HyperdriveWallet
        The agent's current open positions
    pool_info : dict[str, Any]
        Information about the pool involved in the transaction. Gathered from HyperdriveInterface.
    pool_config : dict[str, Any]
        Configuration of the pool involved in the transaction. Gathered from HyperdriveInterface.

    Returns
    -------
    None
        This function does not return any value.
    """

    # We remove the 'fees' object since the tuple is already expanded from the api
    # TODO these should be objects instead of dicts here, i.e., returned from HyperdriveInterface
    pool_config = pool_config.copy()
    pool_config.pop("fees")
    formatted_pool_info = json.dumps(pool_info, indent=4, cls=ExtendedJSONEncoder)
    formatted_pool_config = json.dumps(pool_config, indent=4, cls=ExtendedJSONEncoder)

    wallet_dict = _hyperdrive_wallet_to_dict(agent_wallet)
    formatted_agent_wallet = json.dumps(wallet_dict, indent=4, cls=ExtendedJSONEncoder)

    # TODO set up logging in file handler
    logging.critical(
        """Failed to execute %s: %s\n Amount: %s\n Agent: %s\n Agent Wallet: %s\n PoolInfo: %s\n PoolConfig: %s\n""",
        trade_type,
        error,
        amount,
        agent_address,
        formatted_agent_wallet,
        formatted_pool_info,
        formatted_pool_config,
    )


def _hyperdrive_wallet_to_dict(wallet: HyperdriveWallet) -> dict[str, Any]:
    """Helper function to convert hyperdrive wallet object to a dict keyed by token, valued by amount

    Arguments
    ---------
    wallet : HyperdriveWallet
        The HyperdriveWallet object to convert

    Returns
    -------
    dict[str, Any]
        A dict keyed by token, valued by amount
        In the case of longs and shorts, valued by a dictionary keyed by maturity_time and balance
    """

    # Keeping amounts here as FixedPoints for json to handle
    return {
        wallet.balance.unit.value: wallet.balance.amount,
        "longs": [
            {"maturity_time": maturity_time, "balance": amount.balance}
            for maturity_time, amount in wallet.longs.items()
        ],
        "shorts": [
            {"maturity_time": maturity_time, "balance": amount.balance}
            for maturity_time, amount in wallet.shorts.items()
        ],
        "lp_tokens": wallet.lp_tokens,
        "withdraw_shares": wallet.withdraw_shares,
    }

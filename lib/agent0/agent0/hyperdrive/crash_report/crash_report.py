"""Utility function for logging agent crash reports."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from traceback import format_tb
from typing import TYPE_CHECKING, Any

import numpy as np
from agent0.hyperdrive.state import HyperdriveWallet, TradeResult
from elfpy.utils import logs
from fixedpointmath import FixedPoint
from hexbytes import HexBytes
from numpy.random._generator import Generator as NumpyGenerator
from web3.datastructures import AttributeDict, MutableAttributeDict

if TYPE_CHECKING:
    from agent0.hyperdrive.agents import HyperdriveAgent
    from agent0.hyperdrive.state import HyperdriveMarketAction
    from elfpy import types


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


def log_hyperdrive_crash_report(trade_result: TradeResult) -> None:
    # pylint: disable=too-many-arguments
    """Log a crash report for a hyperdrive transaction.

    Arguments
    ---------
    trade_result: TradeResult
        The trade result object that stores all crash information

    Returns
    -------
    None
        This function does not return any value.
    """

    exception = trade_result.exception
    formatted_exception = repr(exception)

    formatted_trade_obj = _hyperdrive_trade_obj_to_dict(trade_result.trade_object)
    formatted_trade_obj = json.dumps(formatted_trade_obj, indent=4, cls=ExtendedJSONEncoder)

    # Handle wallet outside of agents
    wallet_dict = _hyperdrive_wallet_to_dict(trade_result.agent.wallet)
    formatted_agent_wallet = json.dumps(wallet_dict, indent=4, cls=ExtendedJSONEncoder)

    # TODO Once pool_info and pool_config are objects, we need to add a conversion function
    # to convert to dict
    formatted_pool_info = json.dumps(trade_result.pool_info, indent=4, cls=ExtendedJSONEncoder)
    formatted_pool_config = json.dumps(trade_result.pool_config, indent=4, cls=ExtendedJSONEncoder)

    formatted_agent_info = _hyperdrive_agent_to_dict(trade_result.agent)
    formatted_agent_info = json.dumps(formatted_agent_info, indent=4, cls=ExtendedJSONEncoder)

    assert exception is not None
    formatted_traceback = "".join(format_tb(exception.__traceback__))

    logging.critical(
        """Exception: %s\nTrade: %s\nWallet: %s\nPoolInfo: %s\nPoolConfig: %s\nTraceback: %s\n""",
        formatted_exception,
        formatted_trade_obj,
        formatted_agent_wallet,
        formatted_pool_info,
        formatted_pool_config,
        formatted_traceback,
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


def _hyperdrive_trade_obj_to_dict(trade_obj: types.Trade[HyperdriveMarketAction]) -> dict[str, Any]:
    """Helper function to convert hyperdrive trade object to a dict

    Arguments
    ---------
    trade_obj: types.Trade[HyperdriveMarketAction]
        The trade object to convert

    Returns
    -------
    dict[str, Any]
        A dict ready to be converted to json
    """
    return {
        "market_type": trade_obj.market_type.name,
        "action_type": trade_obj.market_action.action_type.name,
        "trade_amount": trade_obj.market_action.trade_amount,
        "slippage_tolerance": trade_obj.market_action.slippage_tolerance,
        "maturity_time": trade_obj.market_action.maturity_time,
    }


def _hyperdrive_agent_to_dict(agent: HyperdriveAgent):
    return {"address": agent.checksum_address, "policy": agent.policy.name}

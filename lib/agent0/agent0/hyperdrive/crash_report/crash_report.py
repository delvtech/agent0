"""Utility function for logging agent crash reports."""
from __future__ import annotations

import json
import logging
import subprocess
from collections import OrderedDict
from datetime import datetime
from traceback import format_tb
from types import TracebackType
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
        if isinstance(o, TracebackType):
            return format_tb(o)
        if isinstance(o, Exception):
            return repr(o)

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
    trade_result: TradeResult, log_level: int | None = None, crash_report_file_prefix: str | None = None
) -> None:
    # pylint: disable=too-many-arguments
    """Log a crash report for a hyperdrive transaction.

    Arguments
    ---------
    trade_result: TradeResult
        The trade result object that stores all crash information
    log_level: int | None
        The logging level for this crash report. Defaults to critical.

    Returns
    -------
    None
        This function does not return any value.
    """
    if log_level is None:
        log_level = logging.CRITICAL

    # If we're crash reporting, an exception is expected
    assert trade_result.exception is not None

    # We use ordered dict to ensure the outermost order is preserved
    crash_report_json = json.dumps(
        OrderedDict(
            [
                ("exception", trade_result.exception),
                ("trade", _hyperdrive_trade_obj_to_dict(trade_result.trade_object)),
                ("wallet", _hyperdrive_wallet_to_dict(trade_result.agent.wallet)),
                ("agent_info", _hyperdrive_agent_to_dict(trade_result.agent)),
                # TODO Once pool_info and pool_config are objects,
                # we need to add a conversion function to convert to dict
                ("pool_config", trade_result.pool_config),
                ("pool_info", trade_result.pool_info),
                ("checkpoint_info", trade_result.checkpoint_info),
                ("additional_info", trade_result.additional_info),
                ("traceback", trade_result.exception.__traceback__),
                # NOTE if this crash report happens in a PR that gets squashed,
                # we loose this hash.
                ("commit_hash", _get_git_revision_hash()),
                ("anvil_dump_state", trade_result.anvil_state),
            ]
        ),
        indent=4,
        cls=ExtendedJSONEncoder,
    )

    # TODO the anvil dump state blows up the output, should likely print to stdout
    # without the state, and log the full crash report to a file. This allows us
    # to default state dumps to true, while keeping the output sane.
    logging.log(log_level, crash_report_json)


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


def _get_git_revision_hash() -> str:
    """Helper function for getting commit hash from git."""
    return subprocess.check_output(["git", "rev-parse", "HEAD"]).decode("ascii").strip()

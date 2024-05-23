"""Utility function for logging agent crash reports."""

from __future__ import annotations

import getpass
import json
import logging
import os
import platform
import subprocess
from collections import OrderedDict
from dataclasses import asdict
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from eth_account.signers.local import LocalAccount
from fixedpointmath import FixedPoint
from web3 import Web3
from web3.types import RPCEndpoint

from agent0.core.hyperdrive.agent import TradeResult
from agent0.ethpy.base.errors import ContractCallException
from agent0.hyperlogs import ExtendedJSONEncoder, logs
from agent0.hyperlogs.rollbar_utilities import log_rollbar_exception

if TYPE_CHECKING:
    from agent0.core.base import Trade
    from agent0.core.hyperdrive import HyperdriveMarketAction, HyperdriveWallet
    from agent0.core.hyperdrive.policies import HyperdriveBasePolicy
    from agent0.ethpy.hyperdrive import HyperdriveReadInterface
    from agent0.ethpy.hyperdrive.state import PoolState


def setup_hyperdrive_crash_report_logging(log_format_string: str | None = None) -> None:
    """Create a new logging file handler with CRITICAL log level for hyperdrive crash reporting.

    In the future, a custom log level could be used specific to crash reporting.

    Arguments
    ---------
    log_format_string: str, optional
        Logging format described in string format.
    """
    logs.add_file_handler(
        logger=None,  # use the default root logger
        log_filename="hyperdrive_crash_report.log",
        log_format_string=log_format_string,
        delete_previous_logs=False,
        log_level=logging.CRITICAL,
    )


# pylint: disable=too-many-statements
# pylint: disable=too-many-branches
# pylint: disable=too-many-arguments
def build_crash_trade_result(
    exception: Exception,
    interface: HyperdriveReadInterface,
    account: LocalAccount | None = None,
    wallet: HyperdriveWallet | None = None,
    policy: HyperdriveBasePolicy | None = None,
    trade_object: Trade[HyperdriveMarketAction] | None = None,
    additional_info: dict[str, Any] | None = None,
    pool_state: PoolState | None = None,
) -> TradeResult:
    """Build the trade result object when a crash happens.

    Arguments
    ---------
    exception: Exception
        The exception that was thrown
    interface: HyperdriveReadInterface
        An interface for Hyperdrive with contracts deployed on any chain with an RPC url.
    account: LocalAccount | None, optional.
        The LocalAccount object that made the trade. If None, won't report the agent.
    wallet: HyperdriveWallet | None, optional
        The agent's wallet. If None, won't report the wallet.
    policy: HyperdriveBasePolicy | None, optional
        The agent's policy. If None, won't report the policy.
    trade_object: Trade[HyperdriveMarketAction] | None, optional
        A trade provided by the LocalAccount. If None, won't report the trade object.
    additional_info: dict[str, Any] | None, optional
        Additional information used for crash reporting, optional
    pool_state: PoolState | None, optional
        The pool state for crash reporting. If none, will get the current pool state from the interface.

    Returns
    -------
    TradeResult
        The trade result object.
    """
    trade_result = TradeResult(
        trade_successful=False,
        account=account,
        wallet=wallet,
        policy=policy,
        trade_object=trade_object,
    )
    current_block_number = interface.get_block_number(interface.get_current_block())

    ## Check if the exception came from a contract call & determine block number
    # If it did, we fill various trade result data with custom data from
    # the exception
    trade_result.exception = exception
    if isinstance(exception, ContractCallException):
        trade_result.orig_exception = exception.orig_exception
        if exception.block_number is not None:
            trade_result.block_number = exception.block_number
        else:
            # Best effort to get the block it crashed on
            # We assume the exception happened in the previous block
            trade_result.block_number = current_block_number - 1
        trade_result.contract_call = {
            "contract_call_type": exception.contract_call_type,
            "function_name_or_signature": exception.function_name_or_signature,
            "fn_args": exception.fn_args,
            "fn_kwargs": exception.fn_kwargs,
        }
        trade_result.raw_transaction = exception.raw_txn
    else:
        # Best effort to get the block it crashed on
        # We assume the exception happened in the previous block
        trade_result.block_number = current_block_number - 1
        # We still build this structure so the schema stays the same
        trade_result.contract_call = {
            "contract_call_type": None,
            "function_name_or_signature": None,
            "fn_args": None,
            "fn_kwargs": None,
        }

    # We trust the caller to provide the correct pool state if it's being passed in.
    if pool_state is None:
        # Get the pool state at the desired block number
        try:
            pool_state = interface.get_hyperdrive_state(interface.get_block(trade_result.block_number))
        except Exception:  # pylint: disable=broad-except
            pass

    ## Get pool config
    # Pool config is static, so we can get it from the interface here
    if pool_state is not None:
        trade_result.raw_pool_config = pool_state.pool_config_to_dict
        # We call the conversion functions to convert them to human readable versions as well
        trade_result.pool_config = asdict(pool_state.pool_config)
        trade_result.pool_config["contract_address"] = interface.hyperdrive_contract.address
        trade_result.pool_config["inv_time_stretch"] = FixedPoint(1) / trade_result.pool_config["time_stretch"]

        ## Get pool info
        # We wrap contract calls in a try catch to avoid crashing during crash report
        try:
            trade_result.raw_pool_info = pool_state.pool_info_to_dict
        except Exception as exc:  # pylint: disable=broad-except
            logging.warning("Failed to get hyperdrive pool info in crash reporting: %s", repr(exc))
            trade_result.raw_pool_info = None
        trade_result.block_timestamp = pool_state.block.get("timestamp", None)
        if trade_result.raw_pool_info is not None and trade_result.block_timestamp is not None:
            trade_result.pool_info = asdict(pool_state.pool_info)
            trade_result.pool_info["timestamp"] = datetime.utcfromtimestamp(trade_result.block_timestamp)
            trade_result.pool_info["block_number"] = trade_result.block_number
            trade_result.pool_info["total_supply_withdrawal_shares"] = pool_state.total_supply_withdrawal_shares
        else:
            trade_result.pool_info = None

        ## Get pool checkpoint
        try:
            if trade_result.block_timestamp is not None:
                trade_result.raw_checkpoint = pool_state.checkpoint_to_dict
            else:
                logging.warning("Failed to get block_timestamp in crash_reporting")
                trade_result.raw_checkpoint = None
        except Exception as exc:  # pylint: disable=broad-except
            logging.warning("Failed to get hyperdrive checkpoint in crash reporting: %s", repr(exc))
            trade_result.raw_checkpoint = None
        if trade_result.raw_checkpoint is not None and trade_result.block_timestamp is not None:
            trade_result.checkpoint_info = asdict(pool_state.checkpoint)
            trade_result.checkpoint_info["checkpoint_id"] = interface.calc_checkpoint_id(
                block_timestamp=pool_state.block.get("timestamp")
            )
        else:
            trade_result.checkpoint_info = None

        # add additional information to the exception
        trade_result.additional_info = {
            "spot_price": interface.calc_spot_price(pool_state),
            "fixed_rate": interface.calc_spot_rate(pool_state),
            "variable_rate": pool_state.variable_rate,
            "vault_shares": pool_state.vault_shares,
        }

    ## Add extra info
    trade_result.contract_addresses = {
        "hyperdrive_address": interface.hyperdrive_contract.address,
        "base_token_address": interface.base_token_contract.address,
    }

    if additional_info is not None:
        if trade_result.additional_info is None:
            trade_result.additional_info = additional_info
        else:
            trade_result.additional_info.update(additional_info)

    return trade_result


# pylint: disable=too-many-locals
def log_hyperdrive_crash_report(
    trade_result: TradeResult,
    log_level: int | None = None,
    crash_report_to_file: bool = True,
    crash_report_file_prefix: str | None = None,
    log_to_rollbar: bool = False,
    rollbar_log_prefix: str | None = None,
    rollbar_data: dict | None = None,
    additional_info: dict | None = None,
) -> None:
    # pylint: disable=too-many-arguments
    """Log a crash report for a hyperdrive transaction.

    Arguments
    ---------
    trade_result: TradeResult
        The trade result object that stores all crash information.
    log_level: int | None, optional
        The logging level for this crash report.
        Defaults to critical.
    crash_report_to_file: bool, optional
        Whether or not to save the crash report to a file.
        Defaults to True.
    crash_report_file_prefix: str | None, optional
        Optional prefix to append a string to the crash report filename.
        The filename defaults to the timestamp of the report.
    log_to_rollbar: bool, optional
        If enabled, logs errors to the rollbar service.
        Defaults to False.
    rollbar_log_prefix: str | None, optional
        The prefix to prepend to rollbar exception messages
    rollbar_data: dict | None, optional
        Optional dictionary of data to use for the the rollbar report.
        If not provided, will default to logging all of the crash report to rollbar.
    additional_info: dict | None, optional
        Optional dictionary of additional data to include in the crash report.
    """
    if log_level is None:
        log_level = logging.CRITICAL

    # If we're crash reporting, an exception is expected
    assert trade_result.exception is not None

    # Add custom additional info to trade_results
    if additional_info is None:
        additional_info = {}

    if trade_result.additional_info is None:
        trade_result.additional_info = additional_info
    else:
        trade_result.additional_info.update(additional_info)

    curr_time = datetime.utcnow().replace(tzinfo=timezone.utc)
    fn_time_str = curr_time.strftime("%Y_%m_%d_%H_%M_%S_%f_%Z")
    time_str = curr_time.isoformat()

    orig_traceback = None
    if trade_result.orig_exception is not None:
        if isinstance(trade_result.orig_exception, list):
            orig_traceback = [exception.__traceback__ for exception in trade_result.orig_exception]
        elif isinstance(trade_result.orig_exception, (Exception, BaseException)):
            orig_traceback = trade_result.orig_exception.__traceback__
        else:
            assert False

    if trade_result.wallet is not None:
        wallet = trade_result.wallet
    else:
        wallet = None

    if trade_result.policy is not None:
        policy_name = trade_result.policy.name
    else:
        policy_name = None

    # Best attempt at getting a git commit version
    try:
        commit_hash = _get_git_revision_hash()
    except Exception:  # pylint: disable=broad-except
        commit_hash = None

    dump_obj = OrderedDict(
        [
            ("log_time", time_str),
            ("block_number", trade_result.block_number),
            ("block_timestamp", trade_result.block_timestamp),
            ("exception", trade_result.exception),
            ("orig_exception", trade_result.orig_exception),
            ("trade", _hyperdrive_trade_obj_to_dict(trade_result.trade_object)),
            ("contract_call", trade_result.contract_call),
            ("wallet", _hyperdrive_wallet_to_dict(wallet)),
            ("policy", policy_name),
            ("account_info", _hyperdrive_agent_to_dict(trade_result.account)),
            # TODO Once pool_info and pool_config are objects,
            # we need to add a conversion function to convert to dict
            ("pool_config", trade_result.pool_config),
            ("pool_info", trade_result.pool_info),
            ("checkpoint_info", trade_result.checkpoint_info),
            ("contract_addresses", trade_result.contract_addresses),
            ("additional_info", trade_result.additional_info),
            ("traceback", trade_result.exception.__traceback__),
            ("orig_traceback", orig_traceback),
            # NOTE if this crash report happens in a PR that gets squashed,
            # we loose this hash.
            ("commit_hash", commit_hash),
            # Environment details
        ]
    )

    # We use ordered dict to ensure the outermost order is preserved
    logging_crash_report = json.dumps(dump_obj, indent=2, cls=ExtendedJSONEncoder)

    logging.log(log_level, logging_crash_report)

    dump_obj["raw_transaction"] = trade_result.raw_transaction  # type: ignore
    dump_obj["raw_pool_config"] = trade_result.raw_pool_config  # type: ignore
    dump_obj["raw_pool_info"] = trade_result.raw_pool_info  # type: ignore
    dump_obj["raw_checkpoint"] = trade_result.raw_checkpoint  # type: ignore
    dump_obj["anvil_dump_state"] = trade_result.anvil_state  # type: ignore

    env_details = {
        "environment": os.getenv("APP_ENV", "development"),  # e.g., 'production', 'development'
        "platform": platform.system(),  # e.g., 'Linux', 'Windows'
        "platform_version": platform.version(),
        "hostname": platform.node(),
        "python_version": platform.python_version(),
        "time": datetime.utcnow().isoformat(),
        "user": getpass.getuser(),
    }

    # We print out a machine readable crash report
    crash_report_file = None
    if crash_report_to_file:
        dump_obj["env"] = env_details  # type: ignore
        # We add the machine readable version of the crash to the file
        # OrderedDict doesn't play nice with types
        # Generate filename
        if crash_report_file_prefix is None:
            crash_report_file_prefix = ""
        crash_report_dir = ".crash_report/"
        crash_report_file = f"{crash_report_dir}/{crash_report_file_prefix}{fn_time_str}.json"
        if not os.path.exists(crash_report_dir):
            os.makedirs(crash_report_dir)
        with open(crash_report_file, "w", encoding="utf-8") as file:
            json.dump(dump_obj, file, indent=2, cls=ExtendedJSONEncoder)

    if log_to_rollbar:
        if rollbar_data is None:
            # Don't log anvil dump state to rollbar
            dump_obj["anvil_dump_state"] = None  # type: ignore
            rollbar_data = dump_obj

        # Link to original crash report file in rollbar
        if crash_report_file is not None:
            rollbar_data["crash_report_file"] = os.path.abspath(crash_report_file)

        # Format data
        rollbar_data = json.loads(json.dumps(rollbar_data, indent=2, cls=ExtendedJSONEncoder))
        log_rollbar_exception(trade_result.exception, log_level, rollbar_data, rollbar_log_prefix=rollbar_log_prefix)


def _hyperdrive_wallet_to_dict(wallet: HyperdriveWallet | None) -> dict[str, Any]:
    """Helper function to convert hyperdrive wallet object to a dict keyed by token, valued by amount

    Arguments
    ---------
    wallet: HyperdriveWallet
        The HyperdriveWallet object to convert

    Returns
    -------
    dict[str, Any]
        A dict keyed by token, valued by amount
        In the case of longs and shorts, valued by a dictionary keyed by maturity_time and balance
    """
    # Keeping amounts here as FixedPoints for json to handle
    if wallet is None:
        return {}
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


def _hyperdrive_trade_obj_to_dict(trade_obj: Trade[HyperdriveMarketAction] | None) -> dict[str, Any]:
    """Helper function to convert hyperdrive trade object to a dict

    Arguments
    ---------
    trade_obj: Trade[HyperdriveMarketAction]
        The trade object to convert

    Returns
    -------
    dict[str, Any]
        A dict ready to be converted to json
    """
    if trade_obj is None:
        return {}
    return {
        "market_type": trade_obj.market_type.name,
        "action_type": trade_obj.market_action.action_type.name,
        "trade_amount": trade_obj.market_action.trade_amount,
        "slippage_tolerance": trade_obj.market_action.slippage_tolerance,
        "maturity_time": trade_obj.market_action.maturity_time,
    }


def _hyperdrive_agent_to_dict(agent: LocalAccount | None):
    if agent is None:
        return {}
    return {"address": agent.address}


def _get_git_revision_hash() -> str:
    """Helper function for getting commit hash from git."""
    # Use the directory of this file
    dir_path = os.path.dirname(os.path.realpath(__file__))
    return subprocess.check_output(["git", "-C", dir_path, "rev-parse", "HEAD"]).decode("ascii").strip()


def get_anvil_state_dump(web3: Web3) -> str | None:
    """Helper function for getting anvil dump state.

    Arguments
    ---------
    web3: Web3
        Web3 provider object.

    Returns
    -------
    str | None
        Returns the anvil state as a string, or None if it failed.
    """
    result: str | None = None
    try:
        response = web3.provider.make_request(method=RPCEndpoint("anvil_dumpState"), params=[])
        result = response.get("result", False)
    except Exception:  # pylint: disable=broad-exception-caught
        # do nothing, this is best effort crash reporting
        pass
    return result

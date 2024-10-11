"""Web3 powered functions for interfacing with smart contracts."""

from __future__ import annotations

import logging
import random
from typing import Any, Callable, Sequence

from eth_account.signers.local import LocalAccount
from eth_typing import ABI, ABIComponent, BlockIdentifier, BlockNumber, ChecksumAddress
from hexbytes import HexBytes
from pypechain.core import PypechainCallException, PypechainContractFunction
from web3 import Web3
from web3._utils.threads import Timeout
from web3.contract.contract import Contract, ContractFunction
from web3.exceptions import ContractCustomError, TimeExhausted, TransactionNotFound
from web3.types import Nonce, TxParams, TxReceipt, Wei

from .errors.errors import ContractCallException, ContractCallType, decode_error_selector_for_contract
from .errors.types import UnknownBlockError

# This is the default to be the standard for setting
# max_fee = (2 * base_fee) + max_priority_fee
DEFAULT_BASE_FEE_MULTIPLE = 2
DEFAULT_PRIORITY_FEE_MULTIPLE = 1

# pylint: disable=too-many-lines
# we have lots of parameters in smart_contract_transact and async_smart_contract_transact
# too many branches in smart_contract_preview_transaction
# ruff: noqa: PLR0912
# too many arguments in function async_smart_contract_transact
# ruff: noqa: PLR0913

# pylint: disable=too-many-arguments
# pylint: disable=too-many-positional-arguments
# pylint: disable=too-many-locals


def _check_txn_receipt(
    contract_function: PypechainContractFunction,
    tx_hash: HexBytes,
    tx_receipt: TxReceipt,
) -> TxReceipt:
    # Error checking when transaction doesn't throw an error, but instead
    # has errors in the tx_receipt
    block_number = tx_receipt.get("blockNumber")
    # Check status here
    status = tx_receipt.get("status", None)
    # Set block number as the second argument
    if status is None:
        raise UnknownBlockError("Receipt did not return status", f"{block_number=}")
    if status == 0:
        # We use web3 tracing to attempt to get the error message
        error_message = None
        try:
            # Tracing doesn't exist in typing for some reason.
            # Doing this in error checking with try/catch.
            trace = contract_function.w3.tracing.trace_transaction(tx_hash)  # type: ignore
            if len(trace) == 0:
                error_message = "Receipt has status of 0."
            else:
                # Trace gives a list of values, the last one should contain the error
                error_message = trace[-1].get("error", None)
                # If no trace, add back in status == 0 error
                if error_message is None:
                    error_message = "Receipt has status of 0."
        # TODO does this need to be BaseException?
        except Exception as e:  # pylint: disable=broad-exception-caught
            # Don't crash in crash reporting
            logging.warning("Tracing failed for handling failed status: %s", repr(e))
            error_message = f"Receipt has status of 0. Error getting trace: {repr(e)}"

        raise UnknownBlockError(f"{error_message}", f"{block_number=}", f"{tx_hash=}")

    return tx_receipt


def wait_for_transaction_receipt(
    contract_function: PypechainContractFunction,
    transaction_hash: HexBytes,
    timeout: float | None = None,
    start_latency: float = 0.01,
    backoff_multiplier: float = 2,
) -> TxReceipt:
    """Retrieve the transaction receipt, retrying with exponential backoff.

    This function is copied from `web3.eth.wait_for_transaction_receipt`, but using exponential backoff.

    TODO potentially add this function to pypechain for error handling

    Arguments
    ---------
    contract_function: PypechainContractFunction
        The contract function that was called.
    transaction_hash: HexBytes
        The hash of the transaction.
    timeout: float | None, optional
        The amount of time in seconds to time out the connection. Default is 30.
    start_latency: float
        The starting amount of time in seconds to wait between polls.
    backoff_multiplier: float
        The backoff factor for the exponential backoff.

    Returns
    -------
    TxReceipt
        The transaction receipt
    """
    if timeout is None:
        timeout = 120.0
    try:
        with Timeout(timeout) as _timeout:
            poll_latency = start_latency
            while True:
                try:
                    tx_receipt = contract_function.w3.eth.get_transaction_receipt(transaction_hash)
                except TransactionNotFound:
                    tx_receipt = None
                if tx_receipt is not None:
                    break
                _timeout.sleep(poll_latency)
                # Exponential backoff
                poll_latency *= backoff_multiplier
                # Add random latency to avoid collisions
                poll_latency += random.uniform(0, 0.1)
    except Timeout as exc:
        raise TimeExhausted(
            f"Transaction {HexBytes(transaction_hash) !r} is not in the chain " f"after {timeout} seconds"
        ) from exc

    try:
        return _check_txn_receipt(contract_function, transaction_hash, tx_receipt)
    except UnknownBlockError as e:
        # Raise a pypechain error here
        raise PypechainCallException(
            orig_exception=e,
            contract_call_type="transact",
            function_name=contract_function._function_name,  # pylint: disable=protected-access
            fn_args=contract_function.args,
            fn_kwargs=contract_function.kwargs,
            raw_txn=None,
            block_number=tx_receipt["blockNumber"],
        ) from e


async def async_wait_for_transaction_receipt(
    contract_function: PypechainContractFunction,
    transaction_hash: HexBytes,
    timeout: float | None = None,
    start_latency: float = 0.01,
    backoff_multiplier: float = 2,
) -> TxReceipt:
    """Retrieve the transaction receipt asynchronously, retrying with exponential backoff.

    This function is copied from `web3.eth.wait_for_transaction_receipt`, but using exponential backoff and async await.

    Arguments
    ---------
    contract_function: PypechainContractFunction
        The contract function that was called.
    transaction_hash: HexBytes
        The hash of the transaction.
    timeout: float | None, optional
        The amount of time in seconds to time out the connection. Default is 30.
    start_latency: float
        The starting amount of time in seconds to wait between polls.
    backoff_multiplier: float
        The backoff factor for the exponential backoff.

    Returns
    -------
    TxReceipt
        The transaction receipt
    """
    if timeout is None:
        timeout = 120.0
    try:
        with Timeout(timeout) as _timeout:
            poll_latency = start_latency
            while True:
                try:
                    tx_receipt = contract_function.w3.eth.get_transaction_receipt(transaction_hash)
                except TransactionNotFound:
                    tx_receipt = None
                if tx_receipt is not None:
                    break
                await _timeout.async_sleep(poll_latency)
                # Exponential backoff
                poll_latency *= backoff_multiplier
                # Add random latency to avoid collisions
                poll_latency += random.uniform(0, 0.1)

    except Timeout as exc:
        raise TimeExhausted(
            f"Transaction {HexBytes(transaction_hash) !r} is not in the chain " f"after {timeout} seconds"
        ) from exc

    # We need to catch `status = 0` error in wait for txn receipt.
    # This exception needs to be the same as the pypechain error,
    # which means we need the function object to make the exception.
    # We can add the `wait_for_transaction_receipt` function to pypechain,
    # but the async version doesn't make sense, as we'd be attaching it to a sync function.

    try:
        return _check_txn_receipt(contract_function, transaction_hash, tx_receipt)
    except UnknownBlockError as e:
        # Raise a pypechain error here
        raise PypechainCallException(
            orig_exception=e,
            contract_call_type="transact",
            function_name=contract_function._function_name,  # pylint: disable=protected-access
            fn_args=contract_function.args,
            fn_kwargs=contract_function.kwargs,
            raw_txn=None,
            block_number=tx_receipt["blockNumber"],
        ) from e

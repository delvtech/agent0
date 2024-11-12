"""Web3 powered functions for interfacing with smart contracts."""

from __future__ import annotations

import random

from hexbytes import HexBytes
from pypechain.core import PypechainContractFunction
from pypechain.core.contract_call_exception import check_txn_receipt
from web3._utils.threads import Timeout
from web3.exceptions import TimeExhausted, TransactionNotFound
from web3.types import TxReceipt


async def async_wait_for_transaction_receipt(
    contract_function: PypechainContractFunction,
    transaction_hash: HexBytes,
    timeout: float | None = None,
    start_latency: float = 0.01,
    backoff_multiplier: float = 2,
    validate_transaction: bool = False,
) -> TxReceipt:
    """Retrieve the transaction receipt asynchronously, retrying with exponential backoff.

    This function is copied from `web3.eth.wait_for_transaction_receipt`,
    but using exponential backoff and async await.
    This function also takes the place of `sign_transact_and_wait`, except it uses
    async await. This is due to agent0 using the sync version of web3py, but we wrap
    things in async calls.

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
    validate_transaction: bool, optional
        Whether to validate the transaction. If True, will throw an exception if the resulting
        tx_receipt returned a failure status.

    Returns
    -------
    TxReceipt
        The transaction receipt
    """
    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-positional-arguments
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

    if validate_transaction:
        return check_txn_receipt(contract_function, transaction_hash, tx_receipt)
    return tx_receipt

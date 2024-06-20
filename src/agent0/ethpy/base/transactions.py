"""Web3 powered functions for interfacing with smart contracts."""

from __future__ import annotations

import logging
import random
from typing import Any, Sequence

from eth_account.signers.local import LocalAccount
from eth_typing import BlockNumber, ChecksumAddress
from hexbytes import HexBytes
from web3 import Web3
from web3._utils.threads import Timeout
from web3.contract.contract import Contract, ContractFunction
from web3.exceptions import ContractCustomError, ContractPanicError, TimeExhausted, TransactionNotFound
from web3.types import ABI, ABIFunctionComponents, ABIFunctionParams, BlockData, Nonce, TxData, TxParams, TxReceipt, Wei

from agent0.utils import retry_call

from .errors.errors import ContractCallException, ContractCallType, decode_error_selector_for_contract
from .errors.types import UnknownBlockError

DEFAULT_READ_RETRY_COUNT = 5
DEFAULT_WRITE_RETRY_COUNT = 1
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
# too many return statements in _contract_function_abi_outputs
# ruff: noqa: PLR0911


# We define the function to check the exception to retry on
# for preview calls.
# This is the error we get when preview fails due to anvil
def _retry_preview_check(exc: Exception) -> bool:
    """Check the exception to retry on for preview calls."""
    return (
        isinstance(exc, ContractPanicError)
        and exc.args[0] == "Panic error 0x11: Arithmetic operation results in underflow or overflow."
    )


def _retry_txn_check(exc: Exception) -> bool:
    """Check the exception to retry on for transaction calls."""
    return isinstance(exc, UnknownBlockError) and exc.args[0] == "Receipt has status of 0"


def smart_contract_read(
    contract: Contract,
    function_name_or_signature: str,
    *fn_args,
    block_number: BlockNumber | None = None,
    read_retry_count: int | None = None,
    **fn_kwargs,
) -> dict[str, Any]:
    """Return from a smart contract read call.

    Arguments
    ---------
    contract: web3.contract.contract.Contract
        The contract that we are reading from.
    function_name_or_signature: str
        The name of the function to query.
    *fn_args: Unknown
        The arguments passed to the contract method.
    block_number: BlockNumber | None
        If set, will query the chain on the specified block
    read_retry_count: BlockNumber | None
        The number of times to retry the read call if it fails. Defaults to 5.
    **fn_kwargs: Unknown
        The keyword arguments passed to the contract method.

    Returns
    -------
    dict[str, Any]
        A dictionary of value names

    .. todo::
        Add better typing to the return value
        function to recursively find component names & types
        function to dynamically assign types to output variables
            would be cool if this also put stuff into FixedPoint
    """
    if read_retry_count is None:
        read_retry_count = DEFAULT_READ_RETRY_COUNT

    # get the callable contract function from function_name & call it
    if "(" in function_name_or_signature:
        function = contract.get_function_by_signature(function_name_or_signature)(*fn_args, **fn_kwargs)
    else:
        function = contract.get_function_by_name(function_name_or_signature)(*fn_args, **fn_kwargs)
    try:
        # Call function with retries
        return_values = retry_call(read_retry_count, None, function.call, block_identifier=block_number)
    except Exception as err:
        # Add additional information to the exception
        # This field is passed in if smart_contract_read is called with an explicit block
        # Will default to None, in which case crash reporting will do best attempt at getting
        # the block number
        # TODO add in raw_txn to smart contract read functions
        raise ContractCallException(
            "Error in smart contract read",
            orig_exception=err,
            contract_call_type=ContractCallType.READ,
            function_name_or_signature=function_name_or_signature,
            fn_args=fn_args,
            fn_kwargs=fn_kwargs,
            block_number=block_number,
        ) from err

    # If there is a single value returned, we want to put it in a list of length 1
    if not isinstance(return_values, Sequence) or isinstance(return_values, str):
        return_values = [return_values]

    if contract.abi:  # not all contracts have an associated ABI
        # NOTE: this will break if a function signature is passed.  need to update this helper
        return_names_and_types = _contract_function_abi_outputs(contract.abi, function_name_or_signature)
        if return_names_and_types is not None:
            if len(return_names_and_types) != len(return_values):
                raise AssertionError(
                    f"{len(return_names_and_types)=} must equal {len(return_values)=}."
                    f"\n{return_names_and_types=}\n{return_values=}"
                )
            function_return_dict = {}
            for var_name_and_type, var_value in zip(return_names_and_types, return_values):
                var_name = var_name_and_type[0]
                if var_name:
                    function_return_dict[var_name] = var_value
                else:
                    function_return_dict["value"] = var_value
            return function_return_dict
    return {f"value{idx}": value for idx, value in enumerate(return_values)}


# TODO cleanup
# pylint: disable=too-many-locals
# pylint: disable=too-many-branches
# pylint: disable=too-many-arguments
def smart_contract_preview_transaction(
    contract: Contract,
    signer_address: ChecksumAddress,
    function_name_or_signature: str,
    *fn_args,
    block_number: BlockNumber | None = None,
    read_retry_count: int | None = None,
    txn_options_value: int | None = None,
    **fn_kwargs,
) -> dict[str, Any]:
    """Return the values from a transaction without actually submitting the transaction.

    Arguments
    ---------
    contract: web3.contract.contract.Contract
        The contract that we are reading from.
    signer_address: ChecksumAddress
        The address that would sign the transaction.
    function_name_or_signature: str
        The name of the function
    *fn_args: Unknown
        The arguments passed to the contract method.
    block_number: BlockNumber | None
        If set, will query the chain on the specified block
    read_retry_count: int | None
        The number of times to retry the read call if it fails. Defaults to 5.
    txn_options_value: int | None
        The value field for the transaction.
    **fn_kwargs: Unknown
        The keyword arguments passed to the contract method.

    Returns
    -------
    dict[str, Any]
        Return values of the previewed transaction.

    .. todo::
        Add better typing to the return value
        function to recursively find component names & types
        function to dynamically assign types to output variables
            would be cool if this also put stuff into FixedPoint
    """
    if read_retry_count is None:
        read_retry_count = DEFAULT_READ_RETRY_COUNT

    # get the callable contract function from function_name & call it
    if "(" in function_name_or_signature:
        function = contract.get_function_by_signature(function_name_or_signature)(*fn_args, **fn_kwargs)
    else:
        function = contract.get_function_by_name(function_name_or_signature)(*fn_args, **fn_kwargs)

    # This is the additional transaction argument passed into function.call
    # that may contain additional call arguments such as max_gas, nonce, etc.
    if txn_options_value is not None:
        transaction_kwargs = TxParams({"from": signer_address, "value": Wei(txn_options_value)})
    else:
        transaction_kwargs = TxParams({"from": signer_address})

    raw_txn = {}
    # We build the raw transaction here in case of error, where we want to attach the raw txn to the crash report.
    # Note that we don't call `build_transaction`
    # since it adds the nonce to the transaction, and we ignore nonce in preview
    # This is a best attempt at building a transaction for the preview call, because
    # this function doesn't accept a block_number as an argument,
    # so there's a race condition if a new trade comes in and this preview call is no longer valid
    # Hence, we wrap this in a try/catch, and ignore if it fails
    try:
        raw_txn = function.build_transaction(transaction_kwargs)
    except Exception:  # pylint: disable=broad-except
        pass

    try:
        return_values = retry_call(
            read_retry_count,
            _retry_preview_check,
            function.call,
            transaction_kwargs,
            block_identifier=block_number,
        )
    # Wraps the exception with a contract call exception, adding additional information
    # If block number is set in the preview call, will add to crash report,
    # otherwise will do best attempt at getting the block it crashed at.
    except ContractCustomError as err:
        err.args += (f"ContractCustomError {decode_error_selector_for_contract(err.args[0], contract)} raised.",)
        raise ContractCallException(
            "Error in preview transaction",
            orig_exception=err,
            contract_call_type=ContractCallType.PREVIEW,
            function_name_or_signature=function_name_or_signature,
            fn_args=fn_args,
            fn_kwargs=fn_kwargs,
            raw_txn=dict(raw_txn),
            block_number=block_number,
        ) from err
    except Exception as err:
        raise ContractCallException(
            "Error in preview transaction",
            orig_exception=err,
            contract_call_type=ContractCallType.PREVIEW,
            function_name_or_signature=function_name_or_signature,
            fn_args=fn_args,
            fn_kwargs=fn_kwargs,
            raw_txn=dict(raw_txn),
            block_number=block_number,
        ) from err

    if not isinstance(return_values, Sequence):  # could be list or tuple
        return_values = [return_values]
    if contract.abi:  # not all contracts have an associated ABI
        # NOTE: this will break if a function signature is passed.  need to update this helper
        return_names_and_types = _contract_function_abi_outputs(contract.abi, function_name_or_signature)
        if return_names_and_types is not None:
            if len(return_names_and_types) != len(return_values):
                raise AssertionError(
                    f"{len(return_names_and_types)=} must equal {len(return_values)=}."
                    f"\n{return_names_and_types=}\n{return_values=}"
                )
            function_return_dict = {}
            for i, (var_name_and_type, var_value) in enumerate(zip(return_names_and_types, return_values)):
                var_name = var_name_and_type[0]
                if var_name:
                    function_return_dict[var_name] = var_value
                else:
                    function_return_dict[f"value{i}"] = var_value
            return function_return_dict
    return {f"value{idx}": value for idx, value in enumerate(return_values)}


def wait_for_transaction_receipt(
    web3: Web3,
    transaction_hash: HexBytes,
    timeout: float | None = None,
    start_latency: float = 0.01,
    backoff_multiplier: float = 2,
) -> TxReceipt:
    """Retrieve the transaction receipt, retrying with exponential backoff.

    This function is copied from `web3.eth.wait_for_transaction_receipt`, but using exponential backoff.

    Arguments
    ---------
    web3: Web3
        web3 provider object.
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
                    tx_receipt = web3.eth.get_transaction_receipt(transaction_hash)
                except TransactionNotFound:
                    tx_receipt = None
                if tx_receipt is not None:
                    break
                _timeout.sleep(poll_latency)
                # Exponential backoff
                poll_latency *= backoff_multiplier
                # Add random latency to avoid collisions
                poll_latency += random.uniform(0, 0.1)
        return tx_receipt

    except Timeout as exc:
        raise TimeExhausted(
            f"Transaction {HexBytes(transaction_hash) !r} is not in the chain " f"after {timeout} seconds"
        ) from exc


async def async_wait_for_transaction_receipt(
    web3: Web3,
    transaction_hash: HexBytes,
    timeout: float | None = None,
    start_latency: float = 0.01,
    backoff_multiplier: float = 2,
) -> TxReceipt:
    """Retrieve the transaction receipt asynchronously, retrying with exponential backoff.

    This function is copied from `web3.eth.wait_for_transaction_receipt`, but using exponential backoff and async await.

    Arguments
    ---------
    web3: Web3
        web3 provider object.
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
                    tx_receipt = web3.eth.get_transaction_receipt(transaction_hash)
                except TransactionNotFound:
                    tx_receipt = None
                if tx_receipt is not None:
                    break
                await _timeout.async_sleep(poll_latency)
                # Exponential backoff
                poll_latency *= backoff_multiplier
                # Add random latency to avoid collisions
                poll_latency += random.uniform(0, 0.1)
        return tx_receipt

    except Timeout as exc:
        raise TimeExhausted(
            f"Transaction {HexBytes(transaction_hash) !r} is not in the chain " f"after {timeout} seconds"
        ) from exc


def build_transaction(
    func_handle: ContractFunction,
    signer: LocalAccount,
    web3: Web3,
    nonce: Nonce | None = None,
    read_retry_count: int | None = None,
    txn_options_value: int | None = None,
    txn_options_gas: int | None = None,
    txn_options_base_fee_multiple: float | None = None,
    txn_options_priority_fee_multiple: float | None = None,
) -> TxParams:
    """Build a transaction for the given function.

    Arguments
    ---------
    func_handle: ContractFunction
        The function to call
    signer: LocalAccount
        The LocalAccount that will be used to pay for the gas & sign the transaction
    web3: Web3
        web3 container object
    nonce: Nonce | None
        The nonce to use for this transaction. Defaults to setting it to the result of `get_transaction_count`.
    read_retry_count: BlockNumber | None
        The number of times to retry the read call if it fails. Defaults to 5.
    txn_options_value: int | None
        The value field for the transaction.
    txn_options_gas: int | None = None
        The amount of gas used by the transaction. Defaults to estimateGas output.
    txn_options_base_fee_multiple: float | None = None
        The multiple applied to the base fee for the transaction. Defaults to 1.
    txn_options_priority_fee_multiple: float | None = None
        The multiple applied to the priority fee for the transaction. Defaults to 1.

    Returns
    -------
    TxParams
        The unsent raw transaction.
    """
    if read_retry_count is None:
        read_retry_count = DEFAULT_READ_RETRY_COUNT
    if txn_options_base_fee_multiple is None:
        txn_options_base_fee_multiple = DEFAULT_BASE_FEE_MULTIPLE
    if txn_options_priority_fee_multiple is None:
        txn_options_priority_fee_multiple = DEFAULT_PRIORITY_FEE_MULTIPLE
    signer_checksum_address = Web3.to_checksum_address(signer.address)
    # TODO figure out which exception here to retry on
    base_nonce = retry_call(read_retry_count, None, web3.eth.get_transaction_count, signer_checksum_address, "pending")
    if nonce is None:
        nonce = base_nonce
    # We explicitly check to ensure explicit nonce is larger than what web3 is reporting
    if base_nonce > nonce:
        logging.warning("Specified nonce %s is larger than current trx count %s", nonce, base_nonce)
        nonce = base_nonce

    # This is the additional transaction argument passed into function.call
    # that may contain additional call arguments such as max_gas, nonce, etc.
    transaction_kwargs = TxParams(
        {
            "from": signer_checksum_address,
            "nonce": nonce,
        }
    )
    if txn_options_value is not None:
        transaction_kwargs["value"] = Wei(txn_options_value)

    # Assign gas parameters
    # other than the optional gas parameter, this is the default behavior of web3py, exposed here for clarity
    max_priority_fee = int(web3.eth.max_priority_fee * txn_options_priority_fee_multiple)
    pending_block = web3.eth.get_block("pending")
    base_fee = pending_block.get("baseFeePerGas", None)
    if base_fee is not None:
        base_fee *= txn_options_base_fee_multiple
    else:
        raise AssertionError("The latest block does not have a baseFeePerGas")
    max_fee_per_gas = int(max_priority_fee + base_fee)
    transaction_kwargs["maxFeePerGas"] = Wei(max_fee_per_gas)
    transaction_kwargs["maxPriorityFeePerGas"] = Wei(max_priority_fee)
    if txn_options_gas is not None:
        transaction_kwargs["gas"] = txn_options_gas

    return func_handle.build_transaction(TxParams(transaction_kwargs))


async def _async_send_transaction_and_wait_for_receipt(
    unsent_txn: TxParams, signer: LocalAccount, web3: Web3, timeout: float | None = None
) -> TxReceipt:
    """Send a transaction and waits for the receipt asynchronously.

    Arguments
    ---------
    unsent_txn: TxParams
        The built transaction ready to be sent.
    signer: LocalAccount
        The LocalAccount that will be used to pay for the gas & sign the transaction.
    timeout: float | None, optional
        The number of seconds to wait for the transaction to be mined.
        Default is defined in `async_wait_for_transaction_receipt`.
    web3: Web3
        web3 provider object.

    Returns
    -------
    TxReceipt
        a TypedDict; success can be checked via tx_receipt["status"]
    """
    signed_txn = signer.sign_transaction(unsent_txn)
    tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
    tx_receipt = await async_wait_for_transaction_receipt(web3, tx_hash, timeout=timeout)

    # Error checking when transaction doesn't throw an error, but instead
    # has errors in the tx_receipt
    # The block number of this call failing is the previous block
    block_number = tx_receipt.get("blockNumber") - 1
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
            trace = web3.tracing.trace_transaction(tx_receipt["transactionHash"])  # type: ignore
            # Trace gives a list of values, the last one should contain the error
            error_message = trace[-1].get("error", None)
            # If no trace, add back in status == 0 error
            if error_message is None:
                error_message = f"Receipt has status of 0. No trace found: {trace=}"
        # TODO does this need to be BaseException?
        except Exception as e:  # pylint: disable=broad-exception-caught
            # Don't crash in crash reporting
            logging.warning("Tracing failed for handling failed status: %s", repr(e))
            error_message = f"Receipt has status of 0. Error getting trace: {repr(e)}"
        raise UnknownBlockError(f"{error_message}", f"{block_number=}", f"{tx_receipt=}")
    return tx_receipt


# TODO cleanup args
# pylint: disable=too-many-arguments
async def async_smart_contract_transact(
    web3: Web3,
    contract: Contract,
    signer: LocalAccount,
    function_name_or_signature: str,
    *fn_args,
    nonce: Nonce | None = None,
    read_retry_count: int | None = None,
    write_retry_count: int | None = None,
    txn_options_value: int | None = None,
    txn_options_gas: int | None = None,
    txn_options_base_fee_multiple: float | None = None,
    txn_options_priority_fee_multiple: float | None = None,
    timeout: float | None = None,
    **fn_kwargs,
) -> TxReceipt:
    """Execute a named function on a contract that requires a signature & gas.

    Copy of `smart_contract_transact`, but using async wait for `wait_for_transaction_receipt`

    Arguments
    ---------
    web3: Web3
        web3 provider object
    contract: Contract
        Any deployed web3 contract
    signer: LocalAccount
        The LocalAccount that will be used to pay for the gas & sign the transaction
    function_name_or_signature: str
        This function must exist in the compiled contract's ABI
    *fn_args: Unknown
        The positional arguments passed to the contract method.
    nonce: Nonce | None
        If set, will explicitly set the nonce to this value, otherwise will use web3 to get transaction count
    read_retry_count: BlockNumber | None
        The number of times to retry the read call if it fails. Defaults to 5.
    write_retry_count: BlockNumber | None
        The number of times to retry the transact call if it fails. Defaults to no retries.
    txn_options_value: int | None
        The value field for the transaction.
    txn_options_gas : int | None
        The amount of gas used by the transaction.
    txn_options_base_fee_multiple: float | None = None
        The multiple applied to the base fee for the transaction. Defaults to 1.
    txn_options_priority_fee_multiple: float | None = None
        The multiple applied to the priority fee for the transaction. Defaults to 1.
    timeout: float | None, optional
        The number of seconds to wait for the transaction to be mined.
        Default is defined in `_async_send_transaction_and_wait_for_receipt`.
    **fn_kwargs: Unknown
        The keyword arguments passed to the contract method.

    Returns
    -------
    TxReceipt
        a TypedDict; success can be checked via tx_receipt["status"]
    """
    if read_retry_count is None:
        read_retry_count = DEFAULT_READ_RETRY_COUNT
    if write_retry_count is None:
        write_retry_count = DEFAULT_WRITE_RETRY_COUNT

    if "(" in function_name_or_signature:
        func_handle = contract.get_function_by_signature(function_name_or_signature)(*fn_args, **fn_kwargs)
    else:
        func_handle = contract.get_function_by_name(function_name_or_signature)(*fn_args, **fn_kwargs)

    unsent_txn: TxParams = {}

    # We need to retry both build transaction with send and wait
    # so we compose both of these functions here in a private subfunction
    async def _async_build_send_and_wait():
        # Build transaction
        # Building transaction can fail when transaction itself isn't correct

        # We need to update the mutable variable above to ensure this variable
        # gets set if build succeeds for crash reporting
        # Updating this named dict multiple times should be okay
        # as long as `build_transaction` always returns the same keys
        unsent_txn.update(
            build_transaction(
                func_handle,
                signer,
                web3,
                nonce=nonce,
                read_retry_count=read_retry_count,
                txn_options_value=txn_options_value,
                txn_options_gas=txn_options_gas,
                txn_options_base_fee_multiple=txn_options_base_fee_multiple,
                txn_options_priority_fee_multiple=txn_options_priority_fee_multiple,
            )
        )
        return await _async_send_transaction_and_wait_for_receipt(unsent_txn, signer, web3, timeout=timeout)

    try:
        return await retry_call(
            write_retry_count,
            _retry_txn_check,
            _async_build_send_and_wait,
        )

    # Wraps the exception with a contract call exception, adding additional information
    # Other than UnknownBlockError, which gets the block number from the transaction receipt,
    # the rest will default to setting the block number to None, which then crash reporting
    # will attempt a best effort guess as to the block the chain was on before it crashed.
    except ContractCustomError as err:
        err.args += (f"ContractCustomError {decode_error_selector_for_contract(err.args[0], contract)} raised.",)
        # Race condition here, other transactions may have happened when we get the block number here
        # Hence, this is a best effort guess as to which block the chain was on when this exception was thrown.
        block_number = int(web3.eth.block_number)
        raise ContractCallException(
            "Error in smart_contract_transact",
            orig_exception=err,
            contract_call_type=ContractCallType.TRANSACTION,
            function_name_or_signature=function_name_or_signature,
            fn_args=fn_args,
            fn_kwargs=fn_kwargs,
            raw_txn=dict(unsent_txn),
            block_number=block_number,
        ) from err
    except UnknownBlockError as err:
        # Unknown block error means the transaction went through, but was rejected
        # At this point, we try a preview transaction to see if we can get a better error message
        # from the preview
        block_number_arg = err.args[1]
        assert "block_number=" in block_number_arg
        block_number = int(block_number_arg.split("block_number=")[1])

        orig_exception: list[Exception] = [err]
        try:
            smart_contract_preview_transaction(
                contract,
                signer.address,
                function_name_or_signature,
                *fn_args,
                block_number=BlockNumber(block_number),
                read_retry_count=1,  # No retries for this preview
                **fn_kwargs,
            )
            # If the preview was successful, then we raise this message here
            raise AssertionError("Preview was successful.")  # pylint: disable=raise-missing-from

        except Exception as preview_err:  # pylint: disable=broad-except
            # We add a message to the preview error saying what this error is
            preview_err.args = ("Previewing transaction on transaction failure:",) + preview_err.args
            # We report both the exception from the transaction and the exception from the preview
            orig_exception.append(preview_err)

        raise ContractCallException(
            "Error in smart_contract_transact: " + err.args[0],
            orig_exception=orig_exception,
            contract_call_type=ContractCallType.TRANSACTION,
            function_name_or_signature=function_name_or_signature,
            fn_args=fn_args,
            fn_kwargs=fn_kwargs,
            raw_txn=dict(unsent_txn),
            block_number=block_number,
        ) from err
    except Exception as err:
        # Race condition here, other transactions may have happened when we get the block number here
        # Hence, this is a best effort guess as to which block the chain was on when this exception was thrown.
        block_number = int(web3.eth.block_number)
        raise ContractCallException(
            "Error in smart_contract_transact",
            orig_exception=err,
            contract_call_type=ContractCallType.TRANSACTION,
            function_name_or_signature=function_name_or_signature,
            fn_args=fn_args,
            fn_kwargs=fn_kwargs,
            raw_txn=dict(unsent_txn),
            block_number=block_number,
        ) from err


def _send_transaction_and_wait_for_receipt(
    unsent_txn: TxParams, signer: LocalAccount, web3: Web3, timeout: float | None = None
) -> TxReceipt:
    """Send a transaction and waits for the receipt.

    Arguments
    ---------
    unsent_txn: TxParams
        The built transaction ready to be sent.
    signer: LocalAccount
        The LocalAccount that will be used to pay for the gas & sign the transaction.
    timeout: float | None, optional
        The number of seconds to wait for the transaction to be mined.
        Default is defined in `wait_for_transaction_receipt`.
    web3: Web3
        web3 provider object.

    Returns
    -------
    TxReceipt
        a TypedDict; success can be checked via tx_receipt["status"]
    """
    signed_txn = signer.sign_transaction(unsent_txn)
    tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
    tx_receipt = wait_for_transaction_receipt(web3, tx_hash, timeout=timeout)

    # Error checking when transaction doesn't throw an error, but instead
    # has errors in the tx_receipt
    # The block number of this call failing is the previous block
    block_number = tx_receipt.get("blockNumber") - 1
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
            trace = web3.tracing.trace_transaction(tx_receipt["transactionHash"])  # type: ignore
            # Trace gives a list of values, the last one should contain the error
            error_message = trace[-1].get("error", None)
            # If no trace, add back in status == 0 error
            if error_message is None:
                error_message = f"Receipt has status of 0. No trace found: {trace=}"
        # TODO does this need to be BaseException?
        except Exception as e:  # pylint: disable=broad-exception-caught
            # Don't crash in crash reporting
            logging.warning("Tracing failed for handling failed status: %s", repr(e))
            error_message = f"Receipt has status of 0. Error getting trace: {repr(e)}"
        raise UnknownBlockError(f"{error_message}", f"{block_number=}", f"{tx_receipt=}")
    return tx_receipt


def smart_contract_transact(
    web3: Web3,
    contract: Contract,
    signer: LocalAccount,
    function_name_or_signature: str,
    *fn_args,
    nonce: Nonce | None = None,
    read_retry_count: int | None = None,
    write_retry_count: int | None = None,
    txn_options_value: int | None = None,
    txn_options_gas: int | None = None,
    txn_options_base_fee_multiple: float | None = None,
    txn_options_priority_fee_multiple: float | None = None,
    timeout: float | None = None,
    **fn_kwargs,
) -> TxReceipt:
    """Execute a named function on a contract that requires a signature & gas.

    Arguments
    ---------
    web3: Web3
        web3 container object
    contract: Contract
        Any deployed web3 contract
    signer: LocalAccount
        The LocalAccount that will be used to pay for the gas & sign the transaction
    function_name_or_signature: str
        This function must exist in the compiled contract's ABI
    *fn_args: Unknown
        The positional arguments passed to the contract method.
    nonce: Nonce | None
        If set, will explicitly set the nonce to this value, otherwise will use web3 to get transaction count
    read_retry_count: BlockNumber | None
        The number of times to retry the read call if it fails. Defaults to 5.
    write_retry_count: BlockNumber | None
        The number of times to retry the transact call if it fails. Defaults to no retries.
    txn_options_value: int | None
        The value field for the transaction.
    txn_options_gas : int | None
        The amount of gas used by the transaction.
    txn_options_base_fee_multiple: float | None = None
        The multiple applied to the base fee for the transaction. Defaults to 1.
    txn_options_priority_fee_multiple: float | None = None
        The multiple applied to the priority fee for the transaction. Defaults to 1.
    timeout: float | None, optional
        The number of seconds to wait for the transaction to be mined.
        Default is defined in `send_transaction_and_wait_for_receipt`.
    **fn_kwargs: Unknown
        The keyword arguments passed to the contract method.

    Returns
    -------
    TxReceipt
        a TypedDict; success can be checked via tx_receipt["status"]
    """
    if read_retry_count is None:
        read_retry_count = DEFAULT_READ_RETRY_COUNT
    if write_retry_count is None:
        write_retry_count = DEFAULT_WRITE_RETRY_COUNT

    if "(" in function_name_or_signature:
        func_handle = contract.get_function_by_signature(function_name_or_signature)(*fn_args, **fn_kwargs)
    else:
        func_handle = contract.get_function_by_name(function_name_or_signature)(*fn_args, **fn_kwargs)

    unsent_txn: TxParams = {}

    # We need to retry both build transaction with send and wait
    # so we compose both of these functions here in a private subfunction
    def _build_send_and_wait():
        # Build transaction
        # Building transaction can fail when transaction itself isn't correct

        # We need to update the mutable variable above to ensure this variable
        # gets set if build succeeds for crash reporting
        # Updating this named dict multiple times should be okay
        # as long as `build_transaction` always returns the same keys
        unsent_txn.update(
            build_transaction(
                func_handle,
                signer,
                web3,
                nonce=nonce,
                read_retry_count=read_retry_count,
                txn_options_value=txn_options_value,
                txn_options_gas=txn_options_gas,
                txn_options_base_fee_multiple=txn_options_base_fee_multiple,
                txn_options_priority_fee_multiple=txn_options_priority_fee_multiple,
            )
        )
        return _send_transaction_and_wait_for_receipt(unsent_txn, signer, web3, timeout=timeout)

    try:
        return retry_call(
            write_retry_count,
            _retry_txn_check,
            _build_send_and_wait,
        )

    # Wraps the exception with a contract call exception, adding additional information
    # Other than UnknownBlockError, which gets the block number from the transaction receipt,
    # the rest will default to setting the block number to None, which then crash reporting
    # will attempt a best effort guess as to the block the chain was on before it crashed.
    except ContractCustomError as err:
        err.args += (f"ContractCustomError {decode_error_selector_for_contract(err.args[0], contract)} raised.",)
        raise ContractCallException(
            "Error in smart_contract_transact",
            orig_exception=err,
            contract_call_type=ContractCallType.TRANSACTION,
            function_name_or_signature=function_name_or_signature,
            fn_args=fn_args,
            fn_kwargs=fn_kwargs,
            raw_txn=dict(unsent_txn),
        ) from err
    except UnknownBlockError as err:
        # Unknown block error means the transaction went through, but was rejected
        # At this point, we try a preview transaction to see if we can get a better error message
        # from the preview
        block_number_arg = err.args[1]
        assert "block_number=" in block_number_arg
        block_number = int(block_number_arg.split("block_number=")[1])

        orig_exception: list[Exception] = [err]
        try:
            smart_contract_preview_transaction(
                contract,
                signer.address,
                function_name_or_signature,
                *fn_args,
                block_number=BlockNumber(block_number),
                read_retry_count=1,  # No retries for this preview
                **fn_kwargs,
            )
            # If the preview was successful, then we raise this message here
            raise AssertionError("Preview was successful.")  # pylint: disable=raise-missing-from

        except Exception as preview_err:  # pylint: disable=broad-except
            # We add a message to the preview error saying what this error is
            preview_err.args = ("Previewing transaction on transaction failure:",) + preview_err.args
            # We report both the exception from the transaction and the exception from the preview
            orig_exception.append(preview_err)

        raise ContractCallException(
            "Error in smart_contract_transact",
            orig_exception=orig_exception,
            contract_call_type=ContractCallType.TRANSACTION,
            function_name_or_signature=function_name_or_signature,
            fn_args=fn_args,
            fn_kwargs=fn_kwargs,
            raw_txn=dict(unsent_txn),
            block_number=block_number,
        ) from err
    except Exception as err:
        raise ContractCallException(
            "Error in smart_contract_transact",
            orig_exception=err,
            contract_call_type=ContractCallType.TRANSACTION,
            function_name_or_signature=function_name_or_signature,
            fn_args=fn_args,
            raw_txn=dict(unsent_txn),
            fn_kwargs=fn_kwargs,
        ) from err


# TODO clean up args
# pylint: disable=too-many-arguments
async def async_eth_transfer(
    web3: Web3,
    signer: LocalAccount,
    to_address: ChecksumAddress,
    amount_wei: int,
    max_priority_fee: int | None = None,
    nonce: Nonce | None = None,
    read_retry_count: int | None = None,
) -> TxReceipt:
    """Execute a generic Ethereum transaction to move ETH from one account to another.

    Arguments
    ---------
    web3: Web3
        web3 container object
    signer: LocalAccount
        The LocalAccount that will be used to pay for the gas & sign the transaction
    to_address: ChecksumAddress
        Address for where the Ethereum is going to
    amount_wei: int
        Amount to transfer, in WEI
    max_priority_fee: int
        Amount of tip to provide to the miner when a block is mined
    nonce: Nonce | None
        If set, will explicitly set the nonce to this value, otherwise will use web3 to get transaction count
    read_retry_count: BlockNumber | None
        The number of times to retry the read call if it fails. Defaults to 5.

    Returns
    -------
    TxReceipt
        a TypedDict; success can be checked via tx_receipt["status"]
    """
    if read_retry_count is None:
        read_retry_count = DEFAULT_READ_RETRY_COUNT
    signer_checksum_address = Web3.to_checksum_address(signer.address)
    base_nonce = retry_call(read_retry_count, None, web3.eth.get_transaction_count, signer_checksum_address, "pending")
    if nonce is None:
        nonce = base_nonce
    # We explicitly check to ensure explicit nonce is larger than what web3 is reporting
    if base_nonce > nonce:
        logging.warning("Specified nonce %s is larger than current trx count %s", nonce, base_nonce)
        nonce = base_nonce

    unsent_txn: TxParams = {
        "from": signer_checksum_address,
        "to": to_address,
        "value": Wei(amount_wei),
        "nonce": nonce,
        "chainId": web3.eth.chain_id,
    }
    if max_priority_fee is None:
        max_priority_fee = web3.eth.max_priority_fee
    pending_block = web3.eth.get_block("pending")
    base_fee = pending_block.get("baseFeePerGas", None)
    if base_fee is None:
        raise AssertionError("The latest block does not have a baseFeePerGas")
    max_fee_per_gas = max_priority_fee + base_fee
    unsent_txn["gas"] = web3.eth.estimate_gas(unsent_txn)
    unsent_txn["maxFeePerGas"] = Wei(max_fee_per_gas)
    unsent_txn["maxPriorityFeePerGas"] = Wei(max_priority_fee)
    signed_txn = signer.sign_transaction(unsent_txn)
    tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
    return await async_wait_for_transaction_receipt(web3, tx_hash)


# TODO clean up args
# pylint: disable=too-many-arguments
def eth_transfer(
    web3: Web3,
    signer: LocalAccount,
    to_address: ChecksumAddress,
    amount_wei: int,
    max_priority_fee: int | None = None,
    nonce: Nonce | None = None,
    read_retry_count: int | None = None,
) -> TxReceipt:
    """Execute a generic Ethereum transaction to move ETH from one account to another.

    Arguments
    ---------
    web3: Web3
        web3 container object
    signer: LocalAccount
        The LocalAccount that will be used to pay for the gas & sign the transaction
    to_address: ChecksumAddress
        Address for where the Ethereum is going to
    amount_wei: int
        Amount to transfer, in WEI
    max_priority_fee: int
        Amount of tip to provide to the miner when a block is mined
    nonce: Nonce | None
        If set, will explicitly set the nonce to this value, otherwise will use web3 to get transaction count
    read_retry_count: BlockNumber | None
        The number of times to retry the read call if it fails. Defaults to 5.

    Returns
    -------
    TxReceipt
        a TypedDict; success can be checked via tx_receipt["status"]
    """
    if read_retry_count is None:
        read_retry_count = DEFAULT_READ_RETRY_COUNT
    signer_checksum_address = Web3.to_checksum_address(signer.address)
    if nonce is None:
        # TODO figure out which exception here to retry on
        nonce = retry_call(read_retry_count, None, web3.eth.get_transaction_count, signer_checksum_address, "pending")
    unsent_txn: TxParams = {
        "from": signer_checksum_address,
        "to": to_address,
        "value": Wei(amount_wei),
        "nonce": nonce,
        "chainId": web3.eth.chain_id,
    }
    if max_priority_fee is None:
        max_priority_fee = web3.eth.max_priority_fee
    pending_block = web3.eth.get_block("pending")
    base_fee = pending_block.get("baseFeePerGas", None)
    if base_fee is None:
        raise AssertionError("The latest block does not have a baseFeePerGas")
    max_fee_per_gas = max_priority_fee + base_fee
    unsent_txn["gas"] = web3.eth.estimate_gas(unsent_txn)
    unsent_txn["maxFeePerGas"] = Wei(max_fee_per_gas)
    unsent_txn["maxPriorityFeePerGas"] = Wei(max_priority_fee)
    signed_txn = signer.sign_transaction(unsent_txn)

    tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
    return web3.eth.wait_for_transaction_receipt(tx_hash)


def fetch_contract_transactions_for_block(
    web3: Web3, contract: Contract, block_number: BlockNumber, read_retry_count: int | None = None
) -> list[TxData]:
    """Fetch transactions related to a contract for a given block number.

    Arguments
    ---------
    web3: Web3
        web3 provider object
    contract: Contract
        The contract to query the pool info from
    block_number: BlockNumber
        The block number to query from the chain
    read_retry_count: BlockNumber | None
        The number of times to retry the read call if it fails. Defaults to 5.

    Returns
    -------
    tuple[list[Transaction], list[WalletDelta]]
        A list of Transaction objects ready to be inserted into Postgres, and
        a list of wallet delta objects ready to be inserted into Postgres
    """
    if read_retry_count is None:
        read_retry_count = DEFAULT_READ_RETRY_COUNT
    # TODO figure out which exception here to retry on
    block: BlockData = retry_call(read_retry_count, None, web3.eth.get_block, block_number, full_transactions=True)
    all_transactions = block.get("transactions")

    if not all_transactions:
        logging.debug("no transactions in block %s", block.get("number"))
        return []
    contract_transactions: list[TxData] = []
    for transaction in all_transactions:
        if isinstance(transaction, HexBytes):
            logging.warning("transaction HexBytes, can't decode")
            continue
        if transaction.get("to") != contract.address:
            continue
        contract_transactions.append(transaction)

    return contract_transactions


def _get_name_and_type_from_abi(abi_outputs: ABIFunctionComponents | ABIFunctionParams) -> tuple[str, str]:
    """Retrieve and narrow the types for abi outputs."""
    return_value_name: str | None = abi_outputs.get("name")
    if return_value_name is None:
        return_value_name = "none"
    return_value_type: str | None = abi_outputs.get("type")
    if return_value_type is None:
        return_value_type = "none"
    return (return_value_name, return_value_type)


# TODO: add ability to parse function_signature as well
def _contract_function_abi_outputs(contract_abi: ABI, function_name: str) -> list[tuple[str, str]] | None:
    # TODO clean this function up
    # pylint: disable=too-many-return-statements
    """Parse the function abi to get the name and type for each output."""
    function_abi = None
    # find the first function matching the function_name
    for abi in contract_abi:  # loop over each entry in the abi list
        if abi.get("name") == function_name:  # check the name
            function_abi = abi  # pull out the one with the desired name
            break
    if function_abi is None:
        logging.warning("could not find function_name=%s in contract abi", function_name)
        return None
    function_outputs = function_abi.get("outputs")
    if function_outputs is None:
        logging.warning("function abi does not specify outputs")
        return None
    if not isinstance(function_outputs, Sequence):  # could be list or tuple
        logging.warning("function abi outputs are not a sequence")
        return None
    if len(function_outputs) > 1:  # multiple unnamed vars were returned
        return_names_and_types = []
        for output in function_outputs:
            return_names_and_types.append(_get_name_and_type_from_abi(output))
        return return_names_and_types
    if len(function_outputs) == 0:  # No function arguments returned from preview
        return None
    if (
        function_outputs[0].get("type") == "tuple" and function_outputs[0].get("components") is not None
    ):  # multiple named outputs were returned in a struct
        abi_components = function_outputs[0].get("components")
        if abi_components is None:
            logging.warning("function abi output components are not a included")
            return None
        return_names_and_types = []
        for component in abi_components:
            return_names_and_types.append(_get_name_and_type_from_abi(component))
    else:  # final condition is a single output
        return_names_and_types = [_get_name_and_type_from_abi(function_outputs[0])]
    return return_names_and_types

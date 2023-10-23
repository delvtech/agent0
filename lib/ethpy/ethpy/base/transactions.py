"""Web3 powered functions for interfacing with smart contracts"""
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
from web3.exceptions import (
    ContractCustomError,
    ContractLogicError,
    ContractPanicError,
    TimeExhausted,
    TransactionNotFound,
)
from web3.types import ABI, ABIFunctionComponents, ABIFunctionParams, BlockData, Nonce, TxData, TxParams, TxReceipt, Wei

from .errors.errors import ContractCallException, ContractCallType, decode_error_selector_for_contract
from .errors.types import UnknownBlockError
from .retry_utils import retry_call

# TODO these should be parameterized so the caller controls how many times to retry
READ_RETRY_COUNT = 5
# Not retrying on write counts
# TODO need to figure out exactly which error is due to an anvil error
# Currently catching write when status=0, but ideally this would be a specific
# "anvil is breaking" error. We're currently disabling by setting WRITE_RETRY_COUNT to 1.
WRITE_RETRY_COUNT = 1


def smart_contract_read(contract: Contract, function_name_or_signature: str, *fn_args, **fn_kwargs) -> dict[str, Any]:
    """Return from a smart contract read call

    Arguments
    ---------
    contract : web3.contract.contract.Contract
        The contract that we are reading from.
    function_name_or_signature : str
        The name of the function to query.
    *fn_args : Unknown
        The arguments passed to the contract method.
    **fn_kwargs : Unknown
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
    # get the callable contract function from function_name & call it
    if "(" in function_name_or_signature:
        function = contract.get_function_by_signature(function_name_or_signature)(*fn_args)
    else:
        function = contract.get_function_by_name(function_name_or_signature)(*fn_args)
    try:
        # Call function with retries
        return_values = retry_call(READ_RETRY_COUNT, None, function.call, **fn_kwargs)
    except Exception as err:
        # Add additional information to the exception
        # This field is passed in if smart_contract_read is called with an explicit block
        # TODO get current block number if this field wasn't passed into this call
        block_number = fn_kwargs.get("block_identifier", None)
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


def smart_contract_preview_transaction(
    contract: Contract,
    signer_address: ChecksumAddress,
    function_name_or_signature: str,
    *fn_args,
    **fn_kwargs,
) -> dict[str, Any]:
    """Returns the values from a transaction without actually submitting the transaction.

    Arguments
    ---------
    contract : web3.contract.contract.Contract
        The contract that we are reading from.
    signer_address: ChecksumAddress
        The address that would sign the transaction.
    function_name_or_signature : str
        The name of the function
    *fn_args : Unknown
        The arguments passed to the contract method.
    **fn_kwargs : Unknown
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
    # get the callable contract function from function_name & call it
    if "(" in function_name_or_signature:
        function = contract.get_function_by_signature(function_name_or_signature)(*fn_args)
    else:
        function = contract.get_function_by_name(function_name_or_signature)(*fn_args)

    # We define the function to check the exception to retry on
    # This is the error we get when preview fails due to anvil
    def retry_preview_check(exc: Exception) -> bool:
        return (
            isinstance(exc, ContractPanicError)
            and exc.args[0] == "Panic error 0x11: Arithmetic operation results in underflow or overflow."
        )

    try:
        return_values = retry_call(
            READ_RETRY_COUNT,
            retry_preview_check,
            function.call,
            {"from": signer_address},
            **fn_kwargs,
        )
    except Exception as err:
        # Add additional information to the exception
        # This field is passed in if smart_contract_read is called with an explicit block
        # TODO get current block number if this field wasn't passed into this call
        block_number = fn_kwargs.get("block_identifier", None)
        raise ContractCallException(
            "Error in preview transaction",
            orig_exception=err,
            contract_call_type=ContractCallType.PREVIEW,
            function_name_or_signature=function_name_or_signature,
            fn_args=fn_args,
            fn_kwargs=fn_kwargs,
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
            for var_name_and_type, var_value in zip(return_names_and_types, return_values):
                var_name = var_name_and_type[0]
                if var_name:
                    function_return_dict[var_name] = var_value
                else:
                    function_return_dict["value"] = var_value
            return function_return_dict
    return {f"value{idx}": value for idx, value in enumerate(return_values)}


async def async_wait_for_transaction_receipt(
    web3: Web3, transaction_hash: HexBytes, timeout: float = 30, start_latency: float = 1, backoff: float = 2
) -> TxReceipt:
    """Async version of wait_for_transaction_receipt
    This function is copied from `web3.eth.wait_for_transaction_receipt`, but using a non-blocking wait
    instead of a blocking wait

    Arguments
    ---------
    web3: Web3
        web3 provider object
    transaction_hash: HexBytes
        The hash of the transaction
    timeout: float
        The amount of time in seconds to time out the connection
    poll_latency: float
        The amount of time in seconds to wait between polls

    Returns
    -------
    TxReceipt
        The transaction receipt
    """
    try:
        with Timeout(timeout) as _timeout:
            poll_latency = start_latency + random.uniform(0, 1)
            while True:
                try:
                    tx_receipt = web3.eth.get_transaction_receipt(transaction_hash)
                except TransactionNotFound:
                    tx_receipt = None
                if tx_receipt is not None:
                    break
                await _timeout.async_sleep(poll_latency)
                # Exp backoff
                poll_latency *= backoff
                # Add random latency to avoid collisions
                poll_latency += random.uniform(0, 1)
        return tx_receipt

    except Timeout as exc:
        raise TimeExhausted(
            f"Transaction {HexBytes(transaction_hash) !r} is not in the chain " f"after {timeout} seconds"
        ) from exc


async def _async_send_transaction_and_wait_for_receipt(
    func_handle: ContractFunction, signer: LocalAccount, web3: Web3, nonce: Nonce | None = None
) -> TxReceipt:
    """
    Sends a transaction and waits for the receipt asynchronously.

    Arguments
    ---------
    func_handle: ContractFunction
        The function to call
    signer: LocalAccount
        The LocalAccount that will be used to pay for the gas & sign the transaction
    web3 : Web3
        web3 provider object
    nonce: Nonce | None
        If set, will explicitly set the nonce to this value, otherwise will use web3 to get transaction count

    Returns
    -------
    TxReceipt
        a TypedDict; success can be checked via tx_receipt["status"]
    """
    signer_checksum_address = Web3.to_checksum_address(signer.address)
    # TODO figure out which exception here to retry on
    base_nonce = retry_call(READ_RETRY_COUNT, None, web3.eth.get_transaction_count, signer_checksum_address)
    if nonce is None:
        nonce = base_nonce
    # We explicitly check to ensure explicit nonce is larger than what web3 is reporting
    if base_nonce > nonce:
        logging.warning("Specified nonce %s is larger than current trx count %s", nonce, base_nonce)
        nonce = base_nonce

    # We need to update the nonce when retrying a transaction
    unsent_txn = func_handle.build_transaction(
        {
            "from": signer_checksum_address,
            "nonce": nonce,
        }
    )
    signed_txn = signer.sign_transaction(unsent_txn)
    tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
    # TODO set poll time as a parameter
    return await async_wait_for_transaction_receipt(web3, tx_hash)


async def async_smart_contract_transact(
    web3: Web3,
    contract: Contract,
    signer: LocalAccount,
    function_name_or_signature: str,
    *fn_args,
    nonce: Nonce | None = None,
) -> TxReceipt:
    """Execute a named function on a contract that requires a signature & gas
    Copy of `smart_contract_transact`, but using async wait for `wait_for_transaction_receipt`

    Arguments
    ---------
    web3 : Web3
        web3 provider object
    contract : Contract
        Any deployed web3 contract
    signer : LocalAccount
        The LocalAccount that will be used to pay for the gas & sign the transaction
    function_name_or_signature : str
        This function must exist in the compiled contract's ABI
    fn_args : ordered list
        All remaining arguments will be passed to the contract function in the order received
    nonce: Nonce | None
        If set, will explicitly set the nonce to this value, otherwise will use web3 to get transaction count

    Returns
    -------
    TxReceipt
        a TypedDict; success can be checked via tx_receipt["status"]
    """

    try:
        if "(" in function_name_or_signature:
            func_handle = contract.get_function_by_signature(function_name_or_signature)(*fn_args)
        else:
            func_handle = contract.get_function_by_name(function_name_or_signature)(*fn_args)

        tx_receipt = await _async_send_transaction_and_wait_for_receipt(
            func_handle,
            signer,
            web3,
            nonce=nonce,
        )

        # Error checking when transaction doesn't throw an error, but instead
        # has errors in the tx_receipt

        # The block number of this call failing is the previous block
        block_number = tx_receipt.get("blockNumber") - 1
        # Check status here
        status = tx_receipt.get("status", None)
        orig_exception = None
        if status is None:
            orig_exception = UnknownBlockError("Receipt did not return status")
        if status == 0:
            orig_exception = UnknownBlockError("Receipt has status of 0", f"{tx_receipt=}")
        logs = tx_receipt.get("logs", None)
        if logs is None:
            orig_exception = UnknownBlockError("Receipt did not return logs")
        if len(logs) == 0:
            orig_exception = UnknownBlockError("Logs have a length of 0", f"{tx_receipt=}")

        if orig_exception is not None:
            raise ContractCallException(
                "Error in smart_contract_transact",
                orig_exception=orig_exception,
                contract_call_type=ContractCallType.TRANSACTION,
                function_name_or_signature=function_name_or_signature,
                fn_args=fn_args,
                fn_kwargs={},
                block_number=block_number,
            )
        return tx_receipt

    except ContractCustomError as err:
        err.args += (f"ContractCustomError {decode_error_selector_for_contract(err.args[0], contract)} raised.",)
        # Add additional information to the exception
        # TODO get block number of the call here
        raise ContractCallException(
            "Error in smart_contract_transact",
            orig_exception=err,
            contract_call_type=ContractCallType.TRANSACTION,
            function_name_or_signature=function_name_or_signature,
            fn_args=fn_args,
            fn_kwargs={},
        ) from err
    except ContractLogicError as err:
        # Add additional information to the exception
        # TODO get block number of the call here
        raise ContractCallException(
            "Error in smart_contract_transact",
            orig_exception=err,
            contract_call_type=ContractCallType.TRANSACTION,
            function_name_or_signature=function_name_or_signature,
            fn_args=fn_args,
            fn_kwargs={},
        ) from err
    except ContractCallException as err:
        # Avoid double wrapping exception
        raise err
    except Exception as err:
        # Add additional information to the exception
        # TODO get block number of the call here
        raise ContractCallException(
            "Error in smart_contract_transact",
            orig_exception=err,
            contract_call_type=ContractCallType.TRANSACTION,
            function_name_or_signature=function_name_or_signature,
            fn_args=fn_args,
            fn_kwargs={},
        ) from err


def _send_transaction_and_wait_for_receipt(
    func_handle: ContractFunction,
    signer: LocalAccount,
    web3: Web3,
    nonce: Nonce | None = None,
) -> TxReceipt:
    """
    Sends a transaction and waits for the receipt.

    Arguments
    ---------
    func_handle: ContractFunction
        The function to call
    signer: LocalAccount
        The LocalAccount that will be used to pay for the gas & sign the transaction
    web3 : Web3
        web3 provider object
    nonce: Nonce | None
        If set, will explicitly set the nonce to this value, otherwise will use web3 to get transaction count

    Returns
    -------
    TxReceipt
        a TypedDict; success can be checked via tx_receipt["status"]
    """
    signer_checksum_address = Web3.to_checksum_address(signer.address)
    # TODO figure out which exception here to retry on
    base_nonce = retry_call(READ_RETRY_COUNT, None, web3.eth.get_transaction_count, signer_checksum_address)
    if nonce is None:
        nonce = base_nonce
    # We explicitly check to ensure explicit nonce is larger than what web3 is reporting
    if base_nonce > nonce:
        logging.warning("Specified nonce %s is larger than current trx count %s", nonce, base_nonce)
        nonce = base_nonce

    unsent_txn = func_handle.build_transaction(
        {
            "from": signer_checksum_address,
            "nonce": nonce,
        }
    )
    signed_txn = signer.sign_transaction(unsent_txn)
    tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
    # TODO set poll time as a parameter
    return web3.eth.wait_for_transaction_receipt(tx_hash)


def smart_contract_transact(
    web3: Web3,
    contract: Contract,
    signer: LocalAccount,
    function_name_or_signature: str,
    *fn_args,
    nonce: Nonce | None = None,
) -> TxReceipt:
    """Execute a named function on a contract that requires a signature & gas

    Arguments
    ---------
    web3 : Web3
        web3 container object
    contract : Contract
        Any deployed web3 contract
    signer : LocalAccount
        The LocalAccount that will be used to pay for the gas & sign the transaction
    function_name_or_signature : str
        This function must exist in the compiled contract's ABI
    fn_args : ordered list
        All remaining arguments will be passed to the contract function in the order received
    nonce: Nonce | None
        If set, will explicitly set the nonce to this value, otherwise will use web3 to get transaction count

    Returns
    -------
    TxReceipt
        a TypedDict; success can be checked via tx_receipt["status"]
    """

    try:
        if "(" in function_name_or_signature:
            func_handle = contract.get_function_by_signature(function_name_or_signature)(*fn_args)
        else:
            func_handle = contract.get_function_by_name(function_name_or_signature)(*fn_args)
        tx_receipt = _send_transaction_and_wait_for_receipt(func_handle, signer, web3, nonce)

        # Error checking when transaction doesn't throw an error, but instead
        # has errors in the tx_receipt

        # The block number of this call failing is the previous block
        block_number = tx_receipt.get("blockNumber") - 1
        # Check status here
        status = tx_receipt.get("status", None)
        orig_exception = None
        if status is None:
            orig_exception = UnknownBlockError("Receipt did not return status")
        if status == 0:
            orig_exception = UnknownBlockError("Receipt has status of 0", f"{tx_receipt=}")
        logs = tx_receipt.get("logs", None)
        if logs is None:
            orig_exception = UnknownBlockError("Receipt did not return logs")
        if len(logs) == 0:
            orig_exception = UnknownBlockError("Logs have a length of 0", f"{tx_receipt=}")

        if orig_exception is not None:
            raise ContractCallException(
                "Error in smart_contract_transact",
                orig_exception=orig_exception,
                contract_call_type=ContractCallType.TRANSACTION,
                function_name_or_signature=function_name_or_signature,
                fn_args=fn_args,
                fn_kwargs={},
                block_number=block_number,
            )
        return tx_receipt
    except ContractCustomError as err:
        err.args += (
            f"ContractCustomError {decode_error_selector_for_contract(err.args[0], contract)} raised.\n"
            + f"function name: {function_name_or_signature}"
            + f"\nfunction args: {fn_args}",
        )
        # Add additional information to the exception
        # TODO get block number of the call here
        raise ContractCallException(
            "Error in smart_contract_transact",
            orig_exception=err,
            contract_call_type=ContractCallType.TRANSACTION,
            function_name_or_signature=function_name_or_signature,
            fn_args=fn_args,
            fn_kwargs={},
        ) from err
    except ContractLogicError as err:
        # Add additional information to the exception
        # TODO get block number of the call here
        raise ContractCallException(
            "Error in smart_contract_transact",
            orig_exception=err,
            contract_call_type=ContractCallType.TRANSACTION,
            function_name_or_signature=function_name_or_signature,
            fn_args=fn_args,
            fn_kwargs={},
        ) from err
    except ContractCallException as err:
        # Avoid double wrapping exception
        raise err
    except Exception as err:
        # Add additional information to the exception
        # TODO get block number of the call here
        raise ContractCallException(
            "Error in smart_contract_transact",
            orig_exception=err,
            contract_call_type=ContractCallType.TRANSACTION,
            function_name_or_signature=function_name_or_signature,
            fn_args=fn_args,
            fn_kwargs={},
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
) -> TxReceipt:
    """Execute a generic Ethereum transaction to move ETH from one account to another.

    Arguments
    ---------
    web3 : Web3
        web3 container object
    signer : LocalAccount
        The LocalAccount that will be used to pay for the gas & sign the transaction
    to_address : ChecksumAddress
        Address for where the Ethereum is going to
    amount_wei : int
        Amount to transfer, in WEI
    max_priority_fee : int
        Amount of tip to provide to the miner when a block is mined
    nonce: Nonce | None
        If set, will explicitly set the nonce to this value, otherwise will use web3 to get transaction count

    Returns
    -------
    TxReceipt
        a TypedDict; success can be checked via tx_receipt["status"]
    """
    signer_checksum_address = Web3.to_checksum_address(signer.address)
    base_nonce = retry_call(READ_RETRY_COUNT, None, web3.eth.get_transaction_count, signer_checksum_address)
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
    tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
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
) -> TxReceipt:
    """Execute a generic Ethereum transaction to move ETH from one account to another.

    Arguments
    ---------
    web3 : Web3
        web3 container object
    signer : LocalAccount
        The LocalAccount that will be used to pay for the gas & sign the transaction
    to_address : ChecksumAddress
        Address for where the Ethereum is going to
    amount_wei : int
        Amount to transfer, in WEI
    max_priority_fee : int
        Amount of tip to provide to the miner when a block is mined
    nonce: Nonce | None
        If set, will explicitly set the nonce to this value, otherwise will use web3 to get transaction count

    Returns
    -------
    TxReceipt
        a TypedDict; success can be checked via tx_receipt["status"]
    """
    signer_checksum_address = Web3.to_checksum_address(signer.address)
    if nonce is None:
        # TODO figure out which exception here to retry on
        nonce = retry_call(READ_RETRY_COUNT, None, web3.eth.get_transaction_count, signer_checksum_address)
    unsent_txn: TxParams = {
        "from": signer_checksum_address,
        "to": to_address,
        "value": Wei(amount_wei),
        # TODO figure out which exception here to retry on
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

    # TODO how do we want to handle retries here?
    # While this is fine for exceptions thrown, we may need to handle the case where the log status
    # return fail
    tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
    return web3.eth.wait_for_transaction_receipt(tx_hash)


def fetch_contract_transactions_for_block(web3: Web3, contract: Contract, block_number: BlockNumber) -> list[TxData]:
    """Fetch transactions related to a contract for a given block number.

    Arguments
    ---------
    web3: Web3
        web3 provider object
    contract: Contract
        The contract to query the pool info from
    block_number: BlockNumber
        The block number to query from the chain

    Returns
    -------
    tuple[list[Transaction], list[WalletDelta]]
        A list of Transaction objects ready to be inserted into Postgres, and
        a list of wallet delta objects ready to be inserted into Postgres
    """
    # TODO figure out which exception here to retry on
    block: BlockData = retry_call(READ_RETRY_COUNT, None, web3.eth.get_block, block_number, full_transactions=True)
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
    """Retrieve and narrow the types for abi outputs"""
    return_value_name: str | None = abi_outputs.get("name")
    if return_value_name is None:
        return_value_name = "none"
    return_value_type: str | None = abi_outputs.get("type")
    if return_value_type is None:
        return_value_type = "none"
    return (return_value_name, return_value_type)


# TODO: add ability to parse function_signature as well
def _contract_function_abi_outputs(contract_abi: ABI, function_name: str) -> list[tuple[str, str]] | None:
    """Parse the function abi to get the name and type for each output"""
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
    if (
        function_outputs[0].get("type") == "tuple" and function_outputs[0].get("components") is not None
    ):  # multiple named outputs were returned in a struct
        abi_components = function_outputs[0].get("components")
        if abi_components is None:
            logging.warning("function abi output componenets are not a included")
            return None
        return_names_and_types = []
        for component in abi_components:
            return_names_and_types.append(_get_name_and_type_from_abi(component))
    else:  # final condition is a single output
        return_names_and_types = [_get_name_and_type_from_abi(function_outputs[0])]
    return return_names_and_types

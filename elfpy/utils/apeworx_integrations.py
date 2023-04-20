"""Helper functions for integrating the sim repo with solidity contracts via Apeworx"""

from __future__ import annotations
from typing import TYPE_CHECKING, Any, Callable, Optional, Tuple

import logging
from dataclasses import dataclass

from ape.exceptions import TransactionError
from ape.api import ReceiptAPI, TransactionAPI
from ape.contracts.base import ContractTransaction, ContractTransactionHandler
import numpy as np
from elfpy.types import freezable

from elfpy.utils.format_number import format_string as fmt
from elfpy.utils.log_and_print import log_and_print
import elfpy.markets.hyperdrive.hyperdrive_assets as hyperdrive_assets

if TYPE_CHECKING:
    from ape.api.accounts import AccountAPI
    from ape.contracts.base import ContractInstance
    from ape.types import ContractLog
    from ethpm_types.abi import MethodABI


def get_transfer_single_event(tx_receipt: ReceiptAPI) -> ContractLog:
    r"""Parse the transaction receipt to get the "transfer single" trade event

    Arguments
    ---------
    tx_receipt : `ape_ethereum.transactions.ReceiptAPI<https://docs.apeworx.io/ape/stable/methoddocs/api.html#ape.api.transactions.ReceiptAPI>`_
        Ape transaction abstract class to represent a transaction receipt.


    Returns
    -------
    single_event : `ape.types.ContractLog<https://docs.apeworx.io/ape/stable/methoddocs/types.html#ape.types.ContractLog>`_
        The primary emitted trade (a "TransferSingle") event, excluding peripheral events.
    """
    single_events = [tx_event for tx_event in tx_receipt.events if tx_event.event_name == "TransferSingle"]
    if len(single_events) > 1:
        single_events = [tx_event for tx_event in single_events if tx_event.id != 0]  # exclude token id 0
    if len(single_events) > 1:
        logging.debug("Multiple TransferSingle events even after excluding token id 0:")
        for tx_event in single_events:
            logging.debug(tx_event)
    try:
        return single_events[0]
    except Exception as exc:
        raise ValueError(
            f'The transaction receipt should have one "TransferSingle" event, not {len(single_events)}.'
        ) from exc


def get_pool_state(tx_receipt: ReceiptAPI, hyperdrive_contract: ContractInstance):
    """
    Return everything returned by `getPoolInfo()` in the smart contracts, along with:

    Additional information includes:
    token_id : the id of the TransferSingle event (that isn't mint or burn), returned by `get_transfer_single_event`
    block_number_ : the block number of the transaction
    prefix_ : the prefix of the trade (LP, long, or short)
    maturity_timestamp : the maturity time of the trade

    Arguments
    ---------
    tx_receipt : `ape_ethereum.transactions.ReceiptAPI<https://docs.apeworx.io/ape/stable/methoddocs/api.html#ape.api.transactions.ReceiptAPI>`_
        Ape transaction abstract class to represent a transaction receipt.
    hyperdrive_contract : `ape.contracts.base.ContractInstance<https://docs.apeworx.io/ape/stable/methoddocs/contracts.html#ape.contracts.base.ContractInstance>`_
        Ape interactive instance of the initialized MockHyperdriveTestnet smart contract.

    Returns
    -------
    pool_state : dict[str, Any]
        An update dictionary for the Hyperdrive pool state.
    """
    transfer_single_event = get_transfer_single_event(tx_receipt)
    # The ID is a concatenation of the current share price and the maturity time of the trade
    token_id = int(transfer_single_event["id"])
    prefix, maturity_timestamp = hyperdrive_assets.decode_asset_id(token_id)
    pool_state = hyperdrive_contract.getPoolInfo().__dict__
    pool_state["block_number_"] = tx_receipt.block_number
    pool_state["token_id_"] = token_id
    pool_state["prefix_"] = prefix
    pool_state["maturity_timestamp_"] = maturity_timestamp  # in seconds
    logging.debug("hyperdrive_pool_state=%s", pool_state)
    return pool_state


def select_abi(
    method: Callable, params: Optional[dict] = None, args: Optional[Tuple] = None
) -> tuple[MethodABI, Tuple]:
    """
    Select the correct ABI for a method based on the provided parameters:
    - If `params` is provided, the ABI will be matched by keyword arguments (how *pythonic*! 🐍)
    - If `args` is provided, the ABI will be matched by the number of arguments.

    Arguments
    ---------
    method : Callable
        The method to select the ABI for.
    params : dict, optional
        The keyword arguments to match the ABI to.
    args : list, optional
        The arguments to match the ABI to.

    Returns
    -------
    selected_abi : ethpm_types.MethodABI
        The ABI that matches the provided parameters.
    args : list
        The matching keyword arguments, or the original arguments if no keywords were provided.

    Raises
    ------
    ValueError
        If no matching ABI is found.
    """
    if args is None:
        args = ()
    selected_abi: Optional[MethodABI] = None
    method_abis: list[MethodABI] = method.abis
    for abi in method_abis:  # loop through all the ABIs
        if params is not None:  # we try to match on keywords!
            found_args = [inpt.name for inpt in abi.inputs if inpt.name in params]
            if len(found_args) == len(abi.inputs):  # check if the selected args match the number of inputs
                selected_abi = abi  # we found all the arguments by name!
                args = tuple(params[arg] for arg in found_args)  # get the values for the arguments
                break
        elif len(args) == len(abi.inputs):  # check if the number of arguments matches the number of inputs
            selected_abi = abi  # pick this ABI because it has the right number of arguments, hope for the best
            break
    if selected_abi is None:
        raise ValueError(f"Could not find matching ABI for {method}")
    lstr = f"{selected_abi.name}({', '.join(f'{inpt}={arg}' for arg, inpt in zip(args, selected_abi.inputs))})"
    log_and_print(lstr)
    return selected_abi, args


@freezable(frozen=True, no_new_attribs=True)
@dataclass
class Info:
    """Fancy tuple that lets us return item.method and item.prefix instead of item[0] and item[1]"""

    method: Callable
    prefix: hyperdrive_assets.AssetIdPrefix


def ape_trade(
    trade_type: str,
    hyperdrive: ContractInstance,
    agent: AccountAPI,
    amount: int,
    maturity_time: Optional[int] = None,
    **kwargs: Any,
) -> tuple[Optional[dict[str, Any]], Optional[ReceiptAPI]]:
    """
    Execute a trade on the Hyperdrive contract.

    Arguments
    ---------
    trade_type: str
        The type of trade to execute. One of `ADD_LIQUIDITY,
        REMOVE_LIQUIDITY, OPEN_LONG, CLOSE_LONG, OPEN_SHORT, CLOSE_SHORT`
    hyperdrive : `ape.contracts.base.ContractInstance<https://docs.apeworx.io/ape/stable/methoddocs/contracts.html#ape.contracts.base.ContractInstance>`_
        Ape interactive instance of the initialized MockHyperdriveTestnet smart contract.
    agent : `ape.api.accounts.AccountAPI<https://docs.apeworx.io/ape/stable/methoddocs/api.html#ape.api.accounts.AccountAPI>`_
        The account that will execute the trade.
    amount : int
        Unsigned int-256 representation of the trade amount (base if not LP, otherwise LP tokens)
    maturity_time : int, optional
        The maturity time of the trade. Only used for `CLOSE_LONG`, and `CLOSE_SHORT`.

    Returns
    -------
    pool_state : [dict[str, Any]
        The Hyperdrive pool state after the trade.
    tx_receipt : `ReceiptAPI<https://docs.apeworx.io/ape/stable/methoddocs/api.html#ape.api.transactions.ReceiptAPI>`_
        The Ape transaction receipt.
    """

    # predefine which methods to call based on the trade type, and the corresponding asset ID prefix
    info = {
        "OPEN_LONG": Info(method=hyperdrive.openLong, prefix=hyperdrive_assets.AssetIdPrefix.LONG),
        "CLOSE_LONG": Info(method=hyperdrive.closeLong, prefix=hyperdrive_assets.AssetIdPrefix.LONG),
        "OPEN_SHORT": Info(method=hyperdrive.openShort, prefix=hyperdrive_assets.AssetIdPrefix.SHORT),
        "CLOSE_SHORT": Info(method=hyperdrive.closeShort, prefix=hyperdrive_assets.AssetIdPrefix.SHORT),
        "ADD_LIQUIDITY": Info(method=hyperdrive.addLiquidity, prefix=hyperdrive_assets.AssetIdPrefix.LP),
        "REMOVE_LIQUIDITY": Info(method=hyperdrive.removeLiquidity, prefix=hyperdrive_assets.AssetIdPrefix.LP),
    }
    if trade_type in {"CLOSE_LONG", "CLOSE_SHORT"}:  # get the specific asset we're closing
        assert maturity_time, "Maturity time must be provided to close a long or short trade"
        trade_asset_id = hyperdrive_assets.encode_asset_id(info[trade_type].prefix, maturity_time)
        amount = np.clip(amount, 0, hyperdrive.balanceOf(trade_asset_id, agent))

    # specify one big dict that holds the parameters for all six methods
    params = {
        "_asUnderlying": True,  # mockHyperdriveTestNet does not support as_underlying=False
        "_destination": agent,
        "_contribution": amount,
        "_shares": amount,
        "_baseAmount": amount,
        "_bondAmount": amount,
        "_minOutput": 0,
        "_maxDeposit": amount,
        "_minApr": 0,
        "_maxApr": int(100 * 1e18),
        "agent_contract": agent,
        "trade_amount": amount,
        "maturation_time": maturity_time,
    }
    # check the specified method for an ABI that we have all the parameters for
    selected_abi, args = select_abi(params=params, method=info[trade_type].method)

    # create a transaction with the selected ABI
    contract_txn: ContractTransaction = ContractTransaction(abi=selected_abi, address=hyperdrive.address)

    try:  # attempt to execute the transaction, allowing for a specified number of retries (default is 1)
        tx_receipt = attempt_txn(agent, contract_txn, *args, **kwargs)
        if tx_receipt is None:
            return None, None
        return get_pool_state(tx_receipt=tx_receipt, hyperdrive_contract=hyperdrive), tx_receipt
    except TransactionError as exc:
        var = trade_type, exc, fmt(amount), agent, hyperdrive.getPoolInfo().__dict__
        logging.error("Failed to execute %s: %s\n =>  Agent: %s\n => Pool: %s\n", *var)
        return None, None


def attempt_txn(
    agent: AccountAPI, contract_txn: ContractTransaction | ContractTransactionHandler, *args, **kwargs
) -> Optional[ReceiptAPI]:
    """
    Execute a transaction using fallback logic for undiagnosed cases
    where a transaction fails due to gas price being too low.

    - The first attempt uses the recommended base fee, and a fixed multiple of the recommended priority fee
    - On subsequent attempts, the priority fee is increased by a multiple of the base fee

    Arguments
    ---------
    agent : `ape.api.accounts.AccountAPI<https://docs.apeworx.io/ape/stable/methoddocs/api.html#ape.api.accounts.AccountAPI>`_
        Account that will execute the trade.
    contract_txn : `ape.contracts.base.ContractTransaction<https://docs.apeworx.io/ape/stable/methoddocs/contracts.html#ape.contracts.base.ContractTransaction>`_
    | `ape.contracts.base.ContractTransactionHandler<https://docs.apeworx.io/ape/stable/methoddocs/contracts.html#ape.contracts.base.ContractTransactionHandler>`_
        Contract to execute.
    *args : Any
        Positional arguments to pass to the contract transaction.
    **kwargs : Any
        Keyword arguments to pass to the contract transaction.

    Returns
    -------
    tx_receipt : Optional[Ape project `ReceiptAPI<https://docs.apeworx.io/ape/stable/methoddocs/api.html#ape.api.transactions.ReceiptAPI>`_]
        The transaction receipt. Not returned if the transaction fails.

    Raises
    ------
    TransactionError
        If the transaction fails for any reason other than gas price being too low.

    Notes
    -----
    The variable "mult" defines the fallback behavior when the first attempt fails
    each subsequent attempt multiples the max_fee by "mult"
    that is, the second attempt will have a max_fee of 2 * max_fee, the third will have a max_fee of 3 * max_fee, etc.
    """
    mult = kwargs.pop("mult") if hasattr(kwargs, "mult") else 2
    priority_fee_multiple = kwargs.pop("priority_fee_multiple") if hasattr(kwargs, "priority_fee_multiple") else 5
    if isinstance(contract_txn, ContractTransactionHandler):
        abi, args = select_abi(method=contract_txn, args=args)
        contract_txn = ContractTransaction(abi=abi, address=contract_txn.contract.address)
    latest = agent.provider.get_block("latest")
    if latest is None:
        raise ValueError("latest block not found")
    if not hasattr(latest, "base_fee"):
        raise ValueError("latest block does not have base_fee")
    base_fee = getattr(latest, "base_fee")

    # begin attempts, indexing attempt from 1 to mult (for the sake of easy calculation)
    for attempt in range(1, mult + 1):
        kwargs["max_fee_per_gas"] = int(base_fee * attempt + agent.provider.priority_fee * priority_fee_multiple)
        kwargs["max_priority_fee_per_gas"] = int(
            agent.provider.priority_fee * priority_fee_multiple + base_fee * (attempt - 1)
        )
        kwargs["sender"] = agent.address
        kwargs["nonce"] = agent.provider.get_nonce(agent.address)
        kwargs["gas_limit"] = 1_000_000
        # if you want a "STATIC" transaction type, uncomment the following line
        # kwargs["gas_price"] = kwargs["max_fee_per_gas"]
        log_and_print(f"txn attempt {attempt} of {mult} with {kwargs=}")
        serial_txn: TransactionAPI = contract_txn.serialize_transaction(*args, **kwargs)
        prepped_txn: TransactionAPI = agent.prepare_transaction(serial_txn)
        signed_txn: Optional[TransactionAPI] = agent.sign_transaction(prepped_txn)
        log_and_print(f" => sending {signed_txn=}")
        if signed_txn is None:
            raise ValueError("Failed to sign transaction")
        try:
            tx_receipt: ReceiptAPI = agent.provider.send_transaction(signed_txn)
            tx_receipt.await_confirmations()
            return tx_receipt
        except TransactionError as exc:
            if "replacement transaction underpriced" not in str(exc):
                raise exc
            log_and_print(f"Failed to send transaction: {exc}")
            continue
    return None

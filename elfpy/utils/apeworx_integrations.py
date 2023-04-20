"""Helper functions for integrating the sim repo with solidity contracts via Apeworx"""

from __future__ import annotations
from typing import TYPE_CHECKING, Any, Callable, Optional

import logging
from dataclasses import dataclass

# TODO: apeworx is not worxing with github actions when it is listed in requirements
# and pyright doesn't like imports that aren't also in requirements.
# pylint: disable=import-error
from ape.api import ReceiptAPI, TransactionAPI
from ape.contracts.base import ContractTransaction, ContractTransactionHandler
import numpy as np

from elfpy.utils import fmt
import elfpy.markets.hyperdrive.hyperdrive_assets as hyperdrive_assets

if TYPE_CHECKING:
    from ape.api.accounts import AccountAPI  # type: ignore[reportMissingImports]
    from ape.contracts.base import ContractInstance  # type: ignore[reportMissingImports]
    from ape.types import ContractLog  # type: ignore[reportMissingImports]
    from ape_ethereum.transactions import Receipt  # type: ignore[reportMissingImports]


def get_transfer_single_event(tx_receipt: Receipt) -> ContractLog:
    r"""Parse the transaction receipt to get the "transfer single" trade event

    Arguments
    ---------
    tx_receipt: ape_ethereum.transactions.Receipt
        `Ape transaction receipt
        <https://docs.apeworx.io/ape/stable/methoddocs/api.html#ape.api.transactions.ReceiptAPI>`_

    Returns
    -------
    ape.types.ContractLog
        The primary emitted trade (a "TransferSingle" `ContractLog
        <https://docs.apeworx.io/ape/stable/methoddocs/types.html#ape.types.ContractLog>`_
        ) event, excluding peripheral events.
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
    Aftering opening or closing a position, we query the smart contract for its updated pool info.
    We return everything returned by getPoolInfo in the smart contracts, along with:
        token_id: the id of the TransferSingle event (that isn't mint or burn), returned by get_transfer_single_event
        block_number_: the block number of the transaction
        prefix_: the prefix of the trade (LP, long, or short)
        maturity_timestamp: the maturity time of the trade

    Arguments
    ---------
    tx_receipt: ape_ethereum.transactions.Receipt
        `Ape transaction receipt
        <https://docs.apeworx.io/ape/stable/methoddocs/api.html#ape.api.transactions.ReceiptAPI>`_
    hyperdrive_contract: ape.contracts.base.ContractInstance
        Ape project `ContractInstance
        <https://docs.apeworx.io/ape/stable/methoddocs/contracts.html#ape.contracts.base.ContractInstance>`_
        wrapped around the initialized MockHyperdriveTestnet smart contract.

    Returns
    -------
    dict[str, Any]
        An update dictionary for the Hyperdrive pool state
    """
    transfer_single_event = get_transfer_single_event(tx_receipt)  # type: ignore
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


def select_abi(params: dict, method: Callable):
    for abi in method.abis:
        args, names = [], {}
        for idx, inpt in enumerate(abi.inputs):
            if inpt.name not in params:
                raise ValueError(f"Missing required argument {inpt.name} for {method}")
            args.insert(idx, params[inpt.name])
            names[idx] = inpt.name
        if len(args) == len(abi.inputs):
            print(f"{method.abis[0].name}({', '.join(f'{v}={args[i]}' for i,v in enumerate(names.values()))})")
            return abi, args  # type: ignore
    raise ValueError(f"Could not find matching ABI for {method}")


@dataclass
class Info:
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
    Accept a trade type and parameters and execute the trade on the Hyperdrive contract.

    Arguments
    ---------
    trade_type: str
        The type of trade to execute. One of "ADD_LIQUIDITY", "REMOVE_LIQUIDITY", "OPEN_LONG", "CLOSE_LONG", "OPEN_SHORT", "CLOSE_SHORT"
    hyperdrive: ape.contracts.base.ContractInstance
        Ape project `ContractInstance
        <https://docs.apeworx.io/ape/stable/methoddocs/contracts.html#ape.contracts.base.ContractInstance>`_
        wrapped around the initialized MockHyperdriveTestnet smart contract.
    agent: ape.api.accounts.AccountAPI
        Ape project `AccountAPI
        <https://docs.apeworx.io/ape/stable/methoddocs/api.html#ape.api.accounts.AccountAPI>`_
        representing the account that will execute the trade.
    amount: int
        Unsigned int-256 representation of the trade amount (base if not LP, otherwise LP tokens)
    maturity_time: Optional[int]
        The maturity time of the trade. Only used for "CLOSE_LONG", and "CLOSE_SHORT".

    Returns
    -------
    Tuple[dict[str, Any], ape_ethereum.transactions.Receipt]
        A tuple containing an update dictionary for the Hyperdrive pool state
        as well as the Ape-ethereum transaction `receipt
        <https://docs.apeworx.io/ape/stable/methoddocs/api.html#ape.api.transactions.ReceiptAPI>`_.
    """

    info = {
        "OPEN_LONG": Info(method=hyperdrive.openLong, prefix=hyperdrive_assets.AssetIdPrefix.LONG),
        "CLOSE_LONG": Info(method=hyperdrive.closeLong, prefix=hyperdrive_assets.AssetIdPrefix.LONG),
        "OPEN_SHORT": Info(method=hyperdrive.openShort, prefix=hyperdrive_assets.AssetIdPrefix.SHORT),
        "CLOSE_SHORT": Info(method=hyperdrive.closeShort, prefix=hyperdrive_assets.AssetIdPrefix.SHORT),
        "ADD_LIQUIDITY": Info(method=hyperdrive.addLiquidity, prefix=hyperdrive_assets.AssetIdPrefix.LP),
        "REMOVE_LIQUIDITY": Info(method=hyperdrive.removeLiquidity, prefix=hyperdrive_assets.AssetIdPrefix.LP),
    }
    if trade_type in {"CLOSE_LONG", "CLOSE_SHORT"}:
        assert maturity_time, "Maturity time must be provided to close a long or short trade"
        trade_asset_id = hyperdrive_assets.encode_asset_id(info[trade_type].prefix, maturity_time)
        amount = np.clip(amount, 0, hyperdrive.balanceOf(trade_asset_id, agent))
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
    selected_abi, args = select_abi(params=params, method=info[trade_type].method)
    contract_txn: ContractTransaction = ContractTransaction(abi=selected_abi, address=hyperdrive.address)

    try:
        tx_receipt = attempt_txn(agent, contract_txn, *args, **kwargs)
        return get_pool_state(tx_receipt=tx_receipt, hyperdrive_contract=hyperdrive), tx_receipt  # type: ignore
    except Exception as exc:
        pool = hyperdrive.getPoolInfo().__dict__
        string = "Failed to execute trade: %s\n => %s of %s\n => Agent: %s\n => Pool: %s\n"
        var = trade_type, fmt(amount), exc, agent, pool
        logging.error(string, *var)
        return None, None


def attempt_txn(
    agent: AccountAPI, contract_txn: ContractTransaction | ContractTransactionHandler, *args, **kwargs
) -> Optional[ReceiptAPI]:
    mult = kwargs.pop("mult") if hasattr(kwargs, "mult") else 2
    if isinstance(contract_txn, ContractTransactionHandler):
        abi = contract_txn.abis[0]
        if len(args) != len(abi.inputs) and len(contract_txn.abis) > 1:
            for abi in contract_txn.abis:
                if len(args) == len(abi.inputs):
                    break
        contract_txn = ContractTransaction(abi=abi, address=contract_txn.contract.address)
    priority_fee_multiple = 5
    latest = agent.provider.get_block("latest")
    base_fee = latest.base_fee  # type: ignore
    for attempt in range(1, mult + 1):
        kwargs["max_fee"] = int(base_fee * 2 * attempt + agent.provider.priority_fee * priority_fee_multiple)
        kwargs["priority_fee"] = int(agent.provider.priority_fee * priority_fee_multiple + base_fee * (attempt - 1))
        kwargs["sender"] = agent.address
        kwargs["nonce"] = agent.provider.get_nonce(agent.address)
        # kwargs["gas_limit"] = agent.provider.estimate_gas_cost(serial_txn) * 2  # 1_000_000
        kwargs["gas_limit"] = 1_000_000
        kwargs["gas_price"] = kwargs["max_fee"]
        print(f"txn attempt {attempt} of {mult} with {kwargs=}")
        serial_txn: TransactionAPI = contract_txn.serialize_transaction(*args, **kwargs)
        prepped_txn: TransactionAPI = agent.prepare_transaction(serial_txn)
        signed_txn: TransactionAPI = agent.sign_transaction(prepped_txn)  # type: ignore
        try:
            tx_receipt: ReceiptAPI = agent.provider.send_transaction(signed_txn)
            tx_receipt.await_confirmations()
            return tx_receipt
        except Exception as exc:
            if "replacement transaction underpriced" not in str(exc):
                raise exc
            print(f"Failed to send transaction: {exc}")
            continue

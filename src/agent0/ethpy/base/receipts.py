"""Utilities for handling transaction receipts"""

from __future__ import annotations

import warnings
from typing import Any, Sequence, cast

from web3 import Web3
from web3.contract.contract import Contract
from web3.types import ABIEvent, EventData, LogReceipt, TxReceipt


def get_transaction_logs(
    contract: Contract, tx_receipt: TxReceipt, event_names: Sequence[str] | None = None
) -> list[dict[str, Any]]:
    """Decode a transaction receipt.

    Arguments
    ---------
    contract: Contract
        The contract that emitted the receipt
    tx_receipt: TxReceipt
        The emitted receipt after a transaction was completed
    event_names: Sequence[str] | None
        If not None, then only return logs with matching event names


    Returns
    -------
    dict[str, Any]
        A dictionary containing the decoded logs from the transaction.
        If event_names is not None, then the returned dict will only
        include logs that have a corresponding "event" entry.
    """
    logs: list[dict[str, Any]] = []
    if tx_receipt.get("logs"):
        for log in tx_receipt["logs"]:
            event_data, event = get_event_object(contract, log, tx_receipt)
            if event_data and event:
                formatted_log = dict(event_data)
                formatted_log["event"] = event.get("name")
                if (event_names is not None and formatted_log["event"] in event_names) or (event_names is None):
                    formatted_log["args"] = dict(event_data["args"])
                    logs.append(formatted_log)
    return logs


def get_event_object(
    contract: Contract, log: LogReceipt, tx_receipt: TxReceipt
) -> tuple[EventData, ABIEvent] | tuple[None, None]:
    """Retrieve the event object and anonymous types for a given contract and log.

    Arguments
    ---------
    contract: Contract
        The contract that emitted the receipt
    log: LogReceipt
        A TypedDict parsed out of the transaction receipt
    tx_receipt: TxReceipt
        The emitted receipt after a transaction was completed

    Returns
    -------
    tuple[EventData, ABIEvent] | tuple[None, None]
        If the event is not found, return (None, None).
        Otherwise, return the decoded event information as (data, abi).
    """
    abi_events: list[ABIEvent] = [cast(ABIEvent, abi) for abi in contract.abi if abi.get("type", "") == "event"]
    for event in abi_events:
        # Get event signature components
        name = event.get("name")
        inputs: str = ",".join([param.get("type", "") for param in event.get("inputs", [])])
        # Hash event signature
        event_signature_text = f"{name}({inputs})"
        event_signature_hex = Web3.keccak(text=event_signature_text).hex()
        # Find match between log's event signature and ABI's event signature
        receipt_event_signature_hex = log["topics"][0].hex()  # first index gives event signature
        if event_signature_hex == receipt_event_signature_hex and name is not None:
            # Decode matching log
            contract_event = contract.events[name]()
            # TODO web3 is throwing a warning on mismatched ABI for events here, fix
            # https://github.com/delvtech/agent0/issues/1130
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                event_data: EventData = contract_event.process_receipt(tx_receipt)[0]
            return event_data, event
    return (None, None)

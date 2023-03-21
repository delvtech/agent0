"""Helper functions for integrating the sim repo with solidity contracts via Apeworx"""

from __future__ import annotations
from typing import TYPE_CHECKING, Any
from enum import IntEnum

import logging

# TODO: apeworx is not worxing with github actions when it is listed in requirements
# and pyright doesn't like imports that aren't also in requirements.
# pylint: disable=import-error
import ape  # type: ignore[reportMissingImports]

if TYPE_CHECKING:
    from ape.types import ContractLog  # type: ignore[reportMissingImports]
    from ape.api.accounts import AccountAPI  # type: ignore[reportMissingImports]
    from ape_ethereum.transactions import Receipt  # type: ignore[reportMissingImports]
    from ape.contracts.base import ContractInstance  # type: ignore[reportMissingImports]


class AssetIdPrefix(IntEnum):
    r"""The asset ID is used to encode the trade type in a transaction receipt"""
    LONG = 0
    SHORT = 1
    WITHDRAWAL_SHARE = 2


def encode_asset_id(prefix: int, timestamp: int) -> int:
    r"""Encodes a prefix and a timestamp into an asset ID.

    Asset IDs are used so that LP, long, and short tokens can all be represented
    in a single MultiToken instance. The zero asset ID indicates the LP token.

    Encode the asset ID by left-shifting the prefix by 248 bits,
    then bitwise-or-ing the result with the timestamp.

    Argments
    --------
    prefix: int
        A one byte prefix that specifies the asset type.
    timestamp: int
        A timestamp associated with the asset.

    Returns
    -------
    int
        The asset ID.
    """
    timestamp_mask = (1 << 248) - 1
    if timestamp > timestamp_mask:
        raise ValueError("Invalid timestamp")
    return (prefix << 248) | timestamp


def decode_asset_id(asset_id: int) -> tuple[int, int]:
    r"""Decodes a transaction asset ID into its constituent parts of an identifier, data, and a timestamp.

    First calculate the prefix mask by left-shifting 1 by 248 bits and subtracting 1 from the result.
    This gives us a bit-mask with 248 bits set to 1 and the rest set to 0.
    Then apply this mask to the input ID using the bitwise-and operator `&` to extract
    the lower 248 bits as the timestamp.

    Arguments
    ---------
    asset_id: int
        Encoded ID from a transaction. It is a concatenation, [identifier: 8 bits][timestamp: 248 bits]

    Returns
    -------
    tuple[int, int]
        identifier, timestamp
    """
    prefix_mask = (1 << 248) - 1
    prefix = asset_id >> 248  # shr 248 bits
    timestamp = asset_id & prefix_mask  # apply the prefix mask
    return prefix, timestamp


def get_transaction_trade_event(tx_receipt: Receipt) -> ContractLog:
    r"""Parse the transaction receipt to get the trade event

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
        ) event, excluding periferal events.
    """
    single_events: list[ContractLog] = []
    for tx_event in tx_receipt.events:
        if tx_event.event_name == "TransferSingle":
            single_events.append(tx_event)
    if len(single_events) != 1:
        raise ValueError(f'The transaction receipt should have one "TransferSingle" event, not {len(single_events)}.')
    return single_events[0]


def ape_open_position(
    trade_prefix: AssetIdPrefix,
    hyperdrive_contract: ContractInstance,
    agent_address: AccountAPI,
    trade_amount: int,
) -> tuple[dict[str, Any], Receipt]:
    r"""Open a long trade on the Hyperdrive Solidity contract using apeworx.

    Arguments
    ---------
    trade_prefix: AssetIdPrefix
        IntEnum specifying whether the trade is a long (0) or a short (1).
    hyperdrive_contract: ape.contracts.base.ContractInstance
        Ape project `ContractInstance
        <https://docs.apeworx.io/ape/stable/methoddocs/contracts.html#ape.contracts.base.ContractInstance>`_
        wrapped around the initialized MockHyperdriveTestnet smart contract.
    agent_address: ape.api.accounts.AccountAPI
        Ape address container, or `AccountAPI
        <https://docs.apeworx.io/ape/stable/methoddocs/api.html#ape.api.accounts.AccountAPI>`_
        representing the agent which is executing the action.
    base_amount: int
        Unsigned int-256 representation of the base amount that the agent wishes to provide.

    Returns
    -------
    Tuple[dict[str, Any], ape_ethereum.transactions.Receipt]
        A tuple containing an update dictionary for the Hyperdrive pool state
        as well as the Ape-ethereum transaction `receipt
        <https://docs.apeworx.io/ape/stable/methoddocs/api.html#ape.api.transactions.ReceiptAPI>`_.
    """
    with ape.accounts.use_sender(agent_address):  # sender for contract calls
        if trade_prefix == AssetIdPrefix.LONG:  # open a long
            min_output = 0
            as_underlying = False  # mockHyperdriveTestNet does not support as_underlying=True
            tx_receipt = hyperdrive_contract.openLong(  # type: ignore
                trade_amount,  # base
                min_output,
                agent_address,
                as_underlying,
            )
        elif trade_prefix == AssetIdPrefix.SHORT:  # open a short
            max_deposit = trade_amount
            as_underlying = False  # mockHyperdriveTestNet does not support as_underlying=True
            tx_receipt = hyperdrive_contract.openShort(  # type: ignore
                trade_amount,  # bonds
                max_deposit,
                agent_address,
                as_underlying,
            )
        else:
            raise ValueError(f"{trade_prefix=} must be 0 (long) or 1 (short).")
        # Return the updated pool state & transaction result
        transfer_single_event = get_transaction_trade_event(tx_receipt)
        # The ID is a concatenation of the current share price and the maturity time of the trade
        token_id = int(transfer_single_event["id"])
        prefix, maturity_timestamp = decode_asset_id(token_id)
        pool_state = hyperdrive_contract.getPoolInfo().__dict__  # type: ignore
        pool_state["block_number_"] = tx_receipt.block_number
        pool_state["token_id_"] = token_id
        pool_state["prefix_"] = prefix
        pool_state["maturity_timestamp_"] = maturity_timestamp
        logging.debug("hyperdrive_pool_state=%s", pool_state)
    return pool_state, tx_receipt


def ape_close_position(
    trade_prefix: AssetIdPrefix,
    hyperdrive_contract: ContractInstance,
    agent_address: AccountAPI,
    bond_amount: int,
    maturity_time: int,
) -> tuple[dict[str, Any], Receipt]:
    r"""Close a long or short position on the Hyperdrive Solidity contract using apeworx.

    Arguments
    ---------
    trade_prefix: AssetIdPrefix
        IntEnum specifying whether the trade is a long (0) or a short (1).
    hyperdrive_contract: ape.contracts.base.ContractInstance
        Ape project `ContractInstance
        <https://docs.apeworx.io/ape/stable/methoddocs/contracts.html#ape.contracts.base.ContractInstance>`_
        wrapped around the initialized MockHyperdriveTestnet smart contract.
    agent_address: ape.api.accounts.AccountAPI
        Ape address container, or `AccountAPI
        <https://docs.apeworx.io/ape/stable/methoddocs/api.html#ape.api.accounts.AccountAPI>`_
        representing the agent which is executing the action.
    bond_amount: int
        Unsigned int-256 representation of the bond amount that the agent wishes to sell.
    maturity_time: int
        Unsigned int-256 representation of the maturity time of the short being sold.
        This is equal to the pool position duration plus the checkpoint time that is
        closest to (but before) the corresponding open trade.

    Returns
    -------
    Tuple[dict[str, Any], ape_ethereum.transactions.Receipt]
        A tuple containing an update dictionary for the Hyperdrive pool state
        as well as the Ape-ethereum transaction `receipt
        <https://docs.apeworx.io/ape/stable/methoddocs/api.html#ape.api.transactions.ReceiptAPI>`_.
    """
    # pylint: disable=too-many-locals
    with ape.accounts.use_sender(agent_address):  # sender for contract calls
        # Ensure requested close amount is not greater than what is available in the pool
        trade_asset_id = encode_asset_id(trade_prefix, maturity_time)
        agent_balance = hyperdrive_contract.balanceOf(trade_asset_id, agent_address)  # type: ignore
        if bond_amount < agent_balance:
            trade_bond_amount = bond_amount
        else:
            trade_bond_amount = agent_balance
            logging.warning(
                "bond_amount=%g is greater than or equal to the Hyperdrive pool balance=%g",
                bond_amount,
                trade_bond_amount,
            )
        # Close the position
        min_output = 0
        as_underlying = False  # mockHyperdriveTestNet does not support as_underlying=True
        if trade_prefix == AssetIdPrefix.LONG:
            tx_receipt = hyperdrive_contract.closeLong(  # type: ignore
                maturity_time,
                trade_bond_amount,
                min_output,
                agent_address,
                as_underlying,
            )
        elif trade_prefix == AssetIdPrefix.SHORT:
            tx_receipt = hyperdrive_contract.closeShort(  # type: ignore
                maturity_time,
                trade_bond_amount,
                min_output,
                agent_address,
                as_underlying,
            )
        else:
            raise ValueError(f"{trade_prefix=} must be 0 (long) or 1 (short).")
        # Return the updated pool state & transaction result
        transfer_single_event = get_transaction_trade_event(tx_receipt)
        # The ID is a concatenation of the current share price and the maturity time of the trade
        token_id = int(transfer_single_event["id"])
        prefix, maturity_timestamp = decode_asset_id(token_id)
        pool_state = hyperdrive_contract.getPoolInfo().__dict__  # type: ignore
        pool_state["block_number_"] = tx_receipt.block_number  # type: ignore
        pool_state["token_id_"] = token_id
        pool_state["prefix_"] = prefix
        pool_state["maturity_timestamp_"] = maturity_timestamp
        logging.debug("hyperdrive_pool_state=%s", pool_state)
    return pool_state, tx_receipt

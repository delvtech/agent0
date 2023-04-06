"""Helper functions for integrating the sim repo with solidity contracts via Apeworx"""

from __future__ import annotations
<<<<<<< HEAD
=======
from typing import TYPE_CHECKING, Any, Optional
>>>>>>> 2c64d99 (run successfully for 5 days straight)

import logging
from typing import TYPE_CHECKING, Any

# TODO: apeworx is not worxing with github actions when it is listed in requirements
# and pyright doesn't like imports that aren't also in requirements.
# pylint: disable=import-error
import ape  # type: ignore[reportMissingImports]

import elfpy.markets.hyperdrive.assets as hyperdrive_assets

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


def get_pool_state(tx_receipt: Receipt, hyperdrive_contract: ContractInstance):
    """
    Aftering opening or closing a position, we query the smart contract for its updated pool info.
    We return everything returned by getPoolInfo in the smart contracts, along with:
        token_id: the id of the TransferSingle event (that isn't mint or burn), returned by get_transfer_single_event
        block_number_: the block number of the transaction
        prefix_: the prefix of the trade (long, short, or LP)
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
    transfer_single_event = get_transfer_single_event(tx_receipt)
    # The ID is a concatenation of the current share price and the maturity time of the trade
    token_id = int(transfer_single_event["id"])
    prefix, maturity_timestamp = hyperdrive_market.decode_asset_id(token_id)
    pool_state = hyperdrive_contract.getPoolInfo().__dict__
    pool_state["block_number_"] = tx_receipt.block_number
    pool_state["token_id_"] = token_id
    pool_state["prefix_"] = prefix
    pool_state["maturity_timestamp_"] = maturity_timestamp  # in seconds
    logging.debug("hyperdrive_pool_state=%s", pool_state)
    return pool_state


def ape_open_position(
    trade_prefix: hyperdrive_assets.AssetIdPrefix,
    hyperdrive_contract: ContractInstance,
    agent_address: AccountAPI,
    trade_amount: int,
) -> tuple[dict[str, Any], Receipt]:
    r"""Open a long trade on the Hyperdrive Solidity contract using apeworx.

    Arguments
    ---------
<<<<<<< HEAD
    trade_prefix: hyperdrive_assets.AssetIdPrefix
        IntEnum specifying whether the trade is a long (0) or a short (1).
=======
    trade_prefix: hyperdrive_market.AssetIdPrefix
        IntEnum specifying whether the trade is a long (0), short (1), or LP (3).
>>>>>>> 2c64d99 (run successfully for 5 days straight)
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
    as_underlying = True  # mockHyperdriveTestNet does not support as_underlying=False
    with ape.accounts.use_sender(agent_address):  # sender for contract calls
        if trade_prefix == hyperdrive_assets.AssetIdPrefix.LONG:  # open a long
            min_output = 0  # python sims does not support alternative min_output
            tx_receipt: Receipt = hyperdrive_contract.openLong(
                trade_amount,  # base
                min_output,
                agent_address,
                as_underlying,
            )
        elif trade_prefix == hyperdrive_assets.AssetIdPrefix.SHORT:  # open a short
            max_deposit = trade_amount  # python sims does not support alternative max_deposit
            tx_receipt: Receipt = hyperdrive_contract.openShort(
                trade_amount,  # bonds
                max_deposit,
                agent_address,
                as_underlying,
            )
        elif trade_prefix == hyperdrive_market.AssetIdPrefix.LP:  # open a LP
            tx_receipt: Receipt = hyperdrive_contract.addLiquidity(
                trade_amount,  # bonds
                0,  # min apr
                int(100 * 1e18),  # max apr
                agent_address,
                as_underlying,
            )
        else:
            raise ValueError(f"{trade_prefix=} must be 0 (long), 1 (short), or 3 (LP)")
        # Return the updated pool state & transaction result
<<<<<<< HEAD
        transfer_single_event = get_transfer_single_event(tx_receipt)
        # The ID is a concatenation of the current share price and the maturity time of the trade
        token_id = int(transfer_single_event["id"])
        prefix, maturity_timestamp = hyperdrive_assets.decode_asset_id(token_id)
        pool_state = hyperdrive_contract.getPoolInfo().__dict__  # type: ignore
        pool_state["block_number_"] = tx_receipt.block_number  # type: ignore
        pool_state["token_id_"] = token_id
        pool_state["prefix_"] = prefix
        pool_state["maturity_timestamp_"] = maturity_timestamp  # in seconds
        logging.debug("hyperdrive_pool_state=%s", pool_state)
=======
        pool_state = get_pool_state(tx_receipt, hyperdrive_contract)
>>>>>>> 2c64d99 (run successfully for 5 days straight)
    return pool_state, tx_receipt


def ape_close_position(
    trade_prefix: hyperdrive_assets.AssetIdPrefix,
    hyperdrive_contract: ContractInstance,
    agent_address: AccountAPI,
    bond_amount: int,
    maturity_time: Optional[int] = None,
) -> tuple[dict[str, Any], Receipt]:
    r"""Close a long or short position on the Hyperdrive Solidity contract using apeworx.

    Arguments
    ---------
<<<<<<< HEAD
    trade_prefix: hyperdrive_assets.AssetIdPrefix
        IntEnum specifying whether the trade is a long (0) or a short (1).
=======
    trade_prefix: hyperdrive_market.AssetIdPrefix
        IntEnum specifying whether the trade is a long (0), short (1), or LP (3).
>>>>>>> 2c64d99 (run successfully for 5 days straight)
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
        Unsigned int-256 representation of the maturity time in seconds of the short being sold.
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
    as_underlying = True  # mockHyperdriveTestNet does not support as_underlying=False
    with ape.accounts.use_sender(agent_address):  # sender for contract calls
        # Ensure requested close amount is not greater than what is available in the pool
        if trade_prefix == 3:
            trade_asset_id = 0
        elif maturity_time is None:
            raise ValueError(f"{maturity_time=} must be provided for a long or short trade")
        else:
            trade_asset_id = hyperdrive_market.encode_asset_id(trade_prefix, maturity_time)
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
        as_underlying = True  # mockHyperdriveTestNet does not support as_underlying=False
        if trade_prefix == hyperdrive_assets.AssetIdPrefix.LONG:
            tx_receipt = hyperdrive_contract.closeLong(  # type: ignore
                maturity_time,
                trade_bond_amount,
                min_output,
                agent_address,
                as_underlying,
            )
        elif trade_prefix == hyperdrive_assets.AssetIdPrefix.SHORT:
            tx_receipt = hyperdrive_contract.closeShort(  # type: ignore
                maturity_time,
                trade_bond_amount,
                min_output,
                agent_address,
                as_underlying,
            )
        elif trade_prefix == hyperdrive_market.AssetIdPrefix.LP:
            tx_receipt = hyperdrive_contract.removeLiquidity(  # type: ignore
                trade_bond_amount,
                min_output,
                agent_address,
                as_underlying,
            )
        else:
            raise ValueError(f"{trade_prefix=} must be 0 (long), 1 (short), or 3 (LP)")
        # Return the updated pool state & transaction result
        pool_state = get_pool_state(tx_receipt, hyperdrive_contract)
    return pool_state, tx_receipt

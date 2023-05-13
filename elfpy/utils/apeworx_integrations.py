"""Helper functions for integrating the sim repo with solidity contracts via Apeworx"""

from __future__ import annotations
from typing import TYPE_CHECKING, Any, Callable, Optional, Tuple
from pathlib import Path

import logging
from dataclasses import dataclass
from collections import defaultdict, namedtuple

from ape.types import AddressType
from ape.exceptions import TransactionError
from ape.api import BlockAPI, ReceiptAPI, TransactionAPI
from ape.contracts import ContractContainer
from ape.managers.project import ProjectManager
from ape.contracts.base import ContractTransaction, ContractTransactionHandler
import numpy as np
import pandas as pd

import elfpy
from elfpy import types
from elfpy.types import freezable

import elfpy
from elfpy import types
from elfpy.markets.hyperdrive import hyperdrive_assets, hyperdrive_market
from elfpy.utils.outputs import number_to_string as fmt
from elfpy.utils.outputs import log_and_show
from elfpy.agents.wallet import Long, Short, Wallet
from elfpy.math import FixedPoint
from elfpy.agents.wallet import Long, Short, Wallet

if TYPE_CHECKING:
    from ape.api.accounts import AccountAPI
    from ape.contracts.base import ContractInstance
    from ape.types import ContractLog
    from ethpm_types.abi import MethodABI


class HyperdriveProject(ProjectManager):
    """Hyperdrive project class, to provide static typing for the Hyperdrive contract."""

    hyperdrive: ContractContainer
    address: str = "0xB311B825171AF5A60d69aAD590B857B1E5ed23a2"

    def __init__(self, path: Path) -> None:
        """Initialize the project, loading the Hyperdrive contract."""
        if path.name == "examples":  # if in examples folder, move up a level
            path = path.parent
        super().__init__(path)
        self.load_contracts()
        try:
            self.hyperdrive: ContractContainer = self.get_contract("Hyperdrive")
        except AttributeError as err:
            raise AttributeError("Hyperdrive contract not found") from err

    def get_hyperdrive_contract(self) -> ContractInstance:
        """Get the Hyperdrive contract instance."""
        return self.hyperdrive.at(self.conversion_manager.convert(self.address, AddressType))


def get_market_state_from_contract(contract: ContractInstance, **kwargs) -> hyperdrive_market.MarketState:
    """Return the current market state from the smart contract.

    Parameters
    ----------
    contract: `ape.contracts.base.ContractInstance <https://docs.apeworx.io/ape/stable/methoddocs/contracts.html#ape.contracts.base.ContractInstance>`_
        Contract pointing to the initialized MockHyperdriveTestnet smart contract.

    Returns
    -------
    hyperdrive_market.MarketState
    """
    pool_state = contract.getPoolInfo(**kwargs).__dict__
    hyper_config = contract.getPoolConfig(**kwargs).__dict__
    hyper_config["timeStretch"] = 1 / (hyper_config["timeStretch"] / 1e18)  # convert to elf-sims format
    hyper_config["term_length"] = hyper_config["positionDuration"] / (60 * 60 * 24)  # in days
    asset_id = hyperdrive_assets.encode_asset_id(
        hyperdrive_assets.AssetIdPrefix.WITHDRAWAL_SHARE, hyper_config["positionDuration"]
    )
    total_supply_withdraw_shares = contract.balanceOf(asset_id, contract.address)

    return hyperdrive_market.MarketState(
        lp_total_supply=int(FixedPoint(pool_state["lpTotalSupply"])),
        share_reserves=int(FixedPoint(pool_state["shareReserves"])),
        bond_reserves=int(FixedPoint(pool_state["bondReserves"])),
        base_buffer=int(FixedPoint(pool_state["longsOutstanding"])),  # so do we not need any buffers now?
        # TODO: bond_buffer=0,
        variable_apr=0.01,  # TODO: insert real value
        share_price=int(FixedPoint(pool_state["sharePrice"])),
        init_share_price=int(FixedPoint(hyper_config["initialSharePrice"])),
        curve_fee_multiple=int(FixedPoint(hyper_config["curveFee"])),
        flat_fee_multiple=int(FixedPoint(hyper_config["flatFee"])),
        governance_fee_multiple=int(FixedPoint(hyper_config["governanceFee"])),
        longs_outstanding=int(FixedPoint(pool_state["longsOutstanding"])),
        shorts_outstanding=int(FixedPoint(pool_state["shortsOutstanding"])),
        long_average_maturity_time=int(FixedPoint(pool_state["longAverageMaturityTime"])),
        short_average_maturity_time=int(FixedPoint(pool_state["shortAverageMaturityTime"])),
        long_base_volume=int(FixedPoint(pool_state["longBaseVolume"])),
        short_base_volume=int(FixedPoint(pool_state["shortBaseVolume"])),
        # TODO: checkpoints=defaultdict
        checkpoint_duration=hyper_config["checkpointDuration"],
        total_supply_longs=defaultdict(float, {0: int(FixedPoint(pool_state["longsOutstanding"]))}),
        total_supply_shorts=defaultdict(float, {0: int(FixedPoint(pool_state["shortsOutstanding"]))}),
        total_supply_withdraw_shares=int(FixedPoint(total_supply_withdraw_shares)),
        withdraw_shares_ready_to_withdraw=int(FixedPoint(pool_state["withdrawalSharesReadyToWithdraw"])),
        withdraw_capital=int(FixedPoint(pool_state["capital"])),
        withdraw_interest=int(FixedPoint(pool_state["interest"])),
    )


OnChainTradeInfo = namedtuple(
    "OnChainTradeInfo", ["trades", "unique_maturities", "unique_ids", "unique_block_numbers", "share_price"]
)


def get_on_chain_trade_info(hyperdrive: ContractInstance) -> OnChainTradeInfo:
    """Get all trades from hyperdrive contract.

    Parameters
    ----------
    hyperdrive: `ape.contracts.base.ContractInstance <https://docs.apeworx.io/ape/stable/methoddocs/contracts.html#ape.contracts.base.ContractInstance>`_
        Contract pointing to the initialized Hyperdrive (or MockHyperdriveTestnet) smart contract.

    Returns
    -------
    OnChainTradeInfo
        Named tuple containing the following fields:
        - trades: pd.DataFrame
            DataFrame containing all trades from the Hyperdrive contract.
        - unique_maturities: list
            List of unique maturity timestamps across all assets.
        - unique_ids: list
            List of unique ids across all assets.
        - unique_block_numbers_: list
            List of unique block numbers across all trades.
        - share_price_
            Map of share price to block number.
    """
    trades = hyperdrive.TransferSingle.query("*")  # get all trades
    trades = pd.concat(  # flatten event_arguments
        [
            trades.loc[:, [c for c in trades.columns if c != "event_arguments"]],
            pd.DataFrame((dict(i) for i in trades["event_arguments"])),
        ],
        axis=1,
    )
    tuple_series = trades.apply(func=lambda x: hyperdrive_assets.decode_asset_id(int(x["id"])), axis=1)
    trades["prefix"], trades["maturity_timestamp"] = zip(*tuple_series)  # split into two columns
    trades["trade_type"] = trades["prefix"].apply(lambda x: hyperdrive_assets.AssetIdPrefix(x).name)
    trades["value"] = trades["value"]

    unique_maturities_ = trades["maturity_timestamp"].unique()
    unique_maturities_ = unique_maturities_[unique_maturities_ != 0]

    unique_ids_: np.ndarray = trades["id"].unique()
    unique_ids_ = unique_ids_[unique_ids_ != 0]

    unique_block_numbers_ = trades["block_number"].unique()

    # map share price to block number
    share_price_ = {}
    for block_number_ in unique_block_numbers_:
        share_price_ |= {block_number_: hyperdrive.getPoolInfo(block_identifier=int(block_number_))["sharePrice"]}
    for block_number_, price in share_price_.items():
        logging.debug(("block_number_={}, price={}", block_number_, price))

    return OnChainTradeInfo(trades, unique_maturities_, unique_ids_, unique_block_numbers_, share_price_)


def get_wallet_from_onchain_trade_info(
    address_: str, index: int, info: OnChainTradeInfo, hyperdrive: ContractInstance, base: ContractInstance
):
    """Construct wallet balances from on-chain trade info.

    Parameters
    ----------
    address_: str
        Address of the wallet.
    index: int
        Index of the wallet.
    on_chain_trade_info: OnChainTradeInfo
        On-chain trade info.

    Returns
    -------
    Wallet
        Wallet with Short, Long, and LP positions.
    """
    # TODO: remove restriction forcing Wallet index to be an int (issue #415)
    wallet = Wallet(address=index, balance=types.Quantity(amount=base.balanceOf(address_), unit=types.TokenType.BASE))
    for position_id in info.unique_ids:
        trades_in_position = (info.trades["operator"] == address_) & (info.trades["id"] == position_id)
        balance = info.trades.loc[trades_in_position, "value"].sum()
        asset_prefix, maturity = hyperdrive_assets.decode_asset_id(position_id)
        asset_type = hyperdrive_assets.AssetIdPrefix(asset_prefix).name
        assert abs(balance - hyperdrive.balanceOf(position_id, address_)) <= elfpy.MAXIMUM_BALANCE_MISMATCH_IN_WEI, (
            f"events {balance=} and {hyperdrive.balanceOf(position_id, address_)=} disagree"
            f"by more than {elfpy.MAXIMUM_BALANCE_MISMATCH_IN_WEI} wei for {address_}"
        )

        # check if there's an outstanding balance
        if balance != 0 or hyperdrive.balanceOf(position_id, address_) != 0:
            # loop across all the positions owned by this wallet
            for specific_trade in trades_in_position.index[trades_in_position]:
                if asset_type == "SHORT":
                    open_share_price = info.share_price[info.trades.loc[specific_trade, "block_number"]]
                    wallet.shorts |= {
                        maturity - elfpy.SECONDS_IN_YEAR: Short(balance=balance, open_share_price=open_share_price)
                    }
                elif asset_type == "LONG":
                    wallet.longs |= {maturity - elfpy.SECONDS_IN_YEAR: Long(balance=balance)}
                elif asset_type == "LP":
                    wallet.lp_tokens += balance
    return wallet


def get_gas_fees(block: BlockAPI) -> tuple[list[float], list[float]]:
    """Get the max and priority fees from a block (type 2 transactions only).

    Parameters
    ----------
    block: `ape.eth2.BlockAPI <https://docs.apeworx.io/ape/stable/methoddocs/api.html#ape.api.providers.BlockAPI>`_
        Block to get gas fees from.

    Returns
    -------
    tuple[list[float], list[float]]
        Tuple containing the max and priority fees.
    """
    # Pick out only type 2 transactions (EIP-1559). They have a max fee and priority fee.
    type2_transactions = [txn for txn in block.transactions if txn.type == 2]
    if len(type2_transactions) <= 0:
        raise ValueError("No type 2 transactions in block")

    # Pull out max_fee and priority_fee for each transaction, zipping them into two lists
    max_fees, priority_fees = zip(*[(txn.max_fee, txn.max_priority_fee) for txn in type2_transactions])

    # Exclude None values solely for typechecking, then convert from wei to gwei (1 gwei = 1e9 wei)
    max_fees = [max_fee / 1e9 for max_fee in max_fees if max_fee is not None]
    priority_fees = [priority_fee / 1e9 for priority_fee in priority_fees if priority_fee is not None]

    return max_fees, priority_fees


def get_gas_stats(block: BlockAPI) -> tuple[float, float, float, float]:
    """Get gas stats for a given block: maximum and average of max and priority fees (type 2 transactions only).

    Parameters
    ----------
    block: `ape.eth2.BlockAPI <https://docs.apeworx.io/ape/stable/methoddocs/api.html#ape.api.providers.BlockAPI>`_
        Block to get gas fees from.

    Returns
    -------
    tuple[float, float, float, float]
        Tuple containing the max and avg max and priority fees.
    """
    # Pull out max_fee and priority_fee for each transaction, zipping them into two lists
    max_fees, priority_fees = get_gas_fees(block)

    # Calculate max and avg for max_fees
    _max_max_fee = max(max_fees)
    _avg_max_fee = sum(max_fees) / len(max_fees)

    # Calculate max and avg for priority_fees
    _max_priority_fee = max(priority_fees)
    _avg_priority_fee = sum(priority_fees) / len(priority_fees)

    return _max_max_fee, _avg_max_fee, _max_priority_fee, _avg_priority_fee


def get_transfer_single_event(tx_receipt: ReceiptAPI) -> ContractLog:
    r"""Parse the transaction receipt to get the "transfer single" trade event

    Arguments
    ---------
    tx_receipt : `ape.api.transactions.ReceiptAPI <https://docs.apeworx.io/ape/stable/methoddocs/api.html#ape.api.transactions.ReceiptAPI>`_
        Ape transaction abstract class to represent a transaction receipt.


    Returns
    -------
    single_event : `ape.types.ContractLog <https://docs.apeworx.io/ape/stable/methoddocs/types.html#ape.types.ContractLog>`_
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
    Return everything returned by `getPoolInfo()` in the smart contracts.

    Arguments
    ---------
    tx_receipt : `ape.api.transactions.ReceiptAPI <https://docs.apeworx.io/ape/stable/methoddocs/api.html#ape.api.transactions.ReceiptAPI>`_
        Ape transaction abstract class to represent a transaction receipt.
    hyperdrive_contract : `ape.contracts.base.ContractInstance <https://docs.apeworx.io/ape/stable/methoddocs/contracts.html#ape.contracts.base.ContractInstance>`_
        Ape interactive instance of the initialized MockHyperdriveTestnet smart contract.

    Returns
    -------
    pool_state : dict
        An update dictionary for the Hyperdrive pool state.

    Notes
    -----
    Additional information includes:

    * `token_id` : the id of the TransferSingle event (that isn't mint or burn), returned by `get_transfer_single_event`
    * `block_number_` : the block number of the transaction
    * `prefix_` : the prefix of the trade (LP, long, or short)
    * `maturity_timestamp` : the maturity time of the trade
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


PoolInfo = namedtuple("PoolInfo", ["start_time", "block_time", "term_length", "market_state"])


# TODO: remove commenets after verifying the accuracy of this function through more testing (issue #423)
def get_agent_deltas(tx_receipt: ReceiptAPI, trade, addresses, trade_type, pool_info: PoolInfo):
    """Get the change in an agent's wallet from a transaction receipt."""
    agent = tx_receipt.operator
    event_args = tx_receipt.event_arguments
    event_args |= {k: v for k, v in tx_receipt.items() if k in ["block_number", "event_name"]}
    # txn_events = [e.dict() for e in tx_receipt.events if agent in [e.get("from"), e.get("to")]]
    dai_events = [e.dict() for e in tx_receipt.events if agent in [e.get("src"), e.get("dst")]]
    dai_in = sum(int(e["event_arguments"]["wad"]) for e in dai_events if e["event_arguments"]["src"] == agent) / 1e18
    # dai_out = sum(int(e["event_arguments"]["wad"]) for e in dai_events if e["event_arguments"]["dst"] == agent) / 1e18
    _, maturity_timestamp = hyperdrive_assets.decode_asset_id(int(trade["id"]))
    mint_time = (
        (maturity_timestamp - elfpy.SECONDS_IN_YEAR * pool_info.term_length) - pool_info.start_time
    ) / elfpy.SECONDS_IN_YEAR
    # token_type = hyperdrive_assets.AssetIdPrefix(prefix)  # look up prefix in AssetIdPrefix
    if trade_type == "addLiquidity":  # sourcery skip: lift-return-into-if, switch
        # agent_deltas = wallet.Wallet(
        #     address=wallet_address,
        #     balance=-types.Quantity(amount=d_base_reserves, unit=types.TokenType.BASE),
        #     lp_tokens=lp_out,
        # )
        agent_deltas = Wallet(
            address=addresses.index(agent),
            balance=-types.Quantity(amount=trade["_contribution"], unit=types.TokenType.BASE),
            lp_tokens=trade["value"],  # trade output
        )
    elif trade_type == "removeLiquidity":
        # agent_deltas = wallet.Wallet(
        #     address=wallet_address,
        #     balance=types.Quantity(amount=delta_base, unit=types.TokenType.BASE),
        #     lp_tokens=-lp_shares,
        #     withdraw_shares=withdraw_shares,
        # )
        agent_deltas = Wallet(
            address=addresses.index(agent),
            balance=types.Quantity(amount=trade["value"], unit=types.TokenType.BASE),  # trade output
            lp_tokens=-trade["_shares"],  # negative, decreasing
            withdraw_shares=trade["_shares"],  # positive, increasing
        )
    elif trade_type == "openLong":
        # agent_deltas = wallet.Wallet(
        #     address=wallet_address,
        #     balance=types.Quantity(amount=trade_result.user_result.d_base, unit=types.TokenType.BASE),
        #     longs={market.latest_checkpoint_time: wallet.Long(trade_result.user_result.d_bonds)},
        #     fees_paid=trade_result.breakdown.fee,
        # )
        agent_deltas = Wallet(
            address=addresses.index(agent),
            balance=types.Quantity(amount=-trade["_baseAmount"], unit=types.TokenType.BASE),  # negative, decreasing
            longs={pool_info.block_time: Long(trade["value"])},  # trade output, increasing
        )
    elif trade_type == "closeLong":
        # agent_deltas = wallet.Wallet(
        #     address=wallet_address,
        #     balance=types.Quantity(amount=base_proceeds, unit=types.TokenType.BASE),
        #     longs={mint_time: wallet.Long(-bond_amount)},
        #     fees_paid=fee,
        # )
        agent_deltas = Wallet(
            address=addresses.index(agent),
            balance=types.Quantity(amount=trade["value"], unit=types.TokenType.BASE),  # trade output
            longs={mint_time: Long(-trade["_bondAmount"])},  # negative, decreasing
        )
    elif trade_type == "openShort":
        # agent_deltas = wallet.Wallet(
        #     address=wallet_address,
        #     balance=-types.Quantity(amount=trader_deposit, unit=types.TokenType.BASE),
        #     shorts={
        #         market.latest_checkpoint_time: wallet.Short(
        #             balance=bond_amount, open_share_price=market.market_state.share_price
        #         )
        #     },
        #     fees_paid=trade_result.breakdown.fee,
        # )
        agent_deltas = Wallet(
            address=addresses.index(agent),
            balance=types.Quantity(amount=-dai_in, unit=types.TokenType.BASE),  # negative, decreasing
            shorts={
                pool_info.block_time: Short(
                    balance=trade["value"],  # trade output
                    open_share_price=pool_info.market_state.share_price,
                )
            },
        )
    else:
        assert trade_type == "closeShort", f"Unknown trade type: {trade_type}"
        # agent_deltas = wallet.Wallet(
        #     address=wallet_address,
        #     balance=types.Quantity(
        #         amount=(market.market_state.share_price / open_share_price) * bond_amount + trade_result.user_result.d_base,
        #         unit=types.TokenType.BASE,
        #     ),  # see CLOSING SHORT LOGIC above
        #     shorts={
        #         mint_time: wallet.Short(
        #             balance=-bond_amount,
        #             open_share_price=0,
        #         )
        #     },
        #     fees_paid=trade_result.breakdown.fee,
        # )
        agent_deltas = Wallet(
            address=addresses.index(agent),
            balance=types.Quantity(amount=trade["value"], unit=types.TokenType.BASE),
            shorts={
                mint_time: Short(
                    balance=-trade["_bondAmount"],  # negative, decreasing
                    open_share_price=0,
                )
            },
        )
    return agent_deltas


def select_abi(
    method: Callable, params: Optional[dict] = None, args: Optional[Tuple] = None
) -> tuple[MethodABI, Tuple]:
    """
    Select the correct ABI for a method based on the provided parameters:

    * If `params` is provided, the ABI will be matched by keyword arguments
    * If `args` is provided, the ABI will be matched by the number of arguments.

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
    log_and_show(lstr)
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
    hyperdrive : `ape.contracts.base.ContractInstance <https://docs.apeworx.io/ape/stable/methoddocs/contracts.html#ape.contracts.base.ContractInstance>`_
        Ape interactive instance of the initialized MockHyperdriveTestnet smart contract.
    agent : `ape.api.accounts.AccountAPI <https://docs.apeworx.io/ape/stable/methoddocs/api.html#ape.api.accounts.AccountAPI>`_
        The account that will execute the trade.
    amount : int
        Unsigned int-256 representation of the trade amount (base if not LP, otherwise LP tokens)
    maturity_time : int, optional
        The maturity time of the trade. Only used for `CLOSE_LONG`, and `CLOSE_SHORT`.

    Returns
    -------
    pool_state : dict, optional
        The Hyperdrive pool state after the trade.
    tx_receipt : `ape.api.transactions.ReceiptAPI <https://docs.apeworx.io/ape/stable/methoddocs/api.html#ape.api.transactions.ReceiptAPI>`_
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
    agent : `ape.api.accounts.AccountAPI <https://docs.apeworx.io/ape/stable/methoddocs/api.html#ape.api.accounts.AccountAPI>`_
        Account that will execute the trade.
    contract_txn : `ape.contracts.base.ContractTransaction <https://docs.apeworx.io/ape/stable/methoddocs/contracts.html#ape.contracts.base.ContractTransaction>`_ | `ape.contracts.base.ContractTransactionHandler <https://docs.apeworx.io/ape/stable/methoddocs/contracts.html#ape.contracts.base.ContractTransactionHandler>`_
        Contract to execute.
    *args : Any
        Positional arguments to pass to the contract transaction.
    **kwargs : Any
        Keyword arguments to pass to the contract transaction.

    Returns
    -------
    tx_receipt : `ape.api.transactions.ReceiptAPI <https://docs.apeworx.io/ape/stable/methoddocs/api.html#ape.api.transactions.ReceiptAPI>`_, optional
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
        log_and_show(f"txn attempt {attempt} of {mult} with {kwargs=}")
        serial_txn: TransactionAPI = contract_txn.serialize_transaction(*args, **kwargs)
        prepped_txn: TransactionAPI = agent.prepare_transaction(serial_txn)
        signed_txn: Optional[TransactionAPI] = agent.sign_transaction(prepped_txn)
        log_and_show(f" => sending {signed_txn=}")
        if signed_txn is None:
            raise ValueError("Failed to sign transaction")
        try:
            tx_receipt: ReceiptAPI = agent.provider.send_transaction(signed_txn)
            tx_receipt.await_confirmations()
            return tx_receipt
        except TransactionError as exc:
            if "replacement transaction underpriced" not in str(exc):
                raise exc
            log_and_show(f"Failed to send transaction: {exc}")
            continue
    return None

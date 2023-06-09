"""Helper functions for integrating the sim repo with solidity contracts via Apeworx."""
from __future__ import annotations

import json
import logging
import os
import re
from collections import namedtuple
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

import ape
import numpy as np
import pandas as pd
from ape import Contract
from ape.api import BlockAPI, ProviderAPI, ReceiptAPI, TransactionAPI
from ape.contracts import ContractContainer
from ape.contracts.base import ContractTransaction, ContractTransactionHandler
from ape.exceptions import TransactionError, TransactionNotFoundError
from ape.managers.project import ProjectManager
from ape.types import AddressType, ContractType
from ape_accounts.accounts import KeyfileAccount

from elfpy import MAXIMUM_BALANCE_MISMATCH_IN_WEI, SECONDS_IN_YEAR, WEI, simulators, time, types
from elfpy.markets.hyperdrive import AssetIdPrefix, HyperdriveMarketState, HyperdrivePricingModel, hyperdrive_assets
from elfpy.markets.hyperdrive.hyperdrive_market import HyperdriveMarket
from elfpy.math import FixedPoint
from elfpy.simulators.config import Config
from elfpy.utils import outputs as output_utils
from elfpy.utils import sim_utils
from elfpy.wallet.wallet import Long, Short, Wallet

if TYPE_CHECKING:
    from ape.api.accounts import AccountAPI
    from ape.contracts.base import ContractInstance
    from ape.types import ContractLog
    from ethpm_types.abi import MethodABI

# pylint: disable=too-many-locals, too-many-lines
# pyright: reportOptionalMemberAccess=false, reportGeneralTypeIssues=false


class HyperdriveProject(ProjectManager):
    """Hyperdrive project class, to provide static typing for the Hyperdrive contract."""

    hyperdrive_address: str = "0xB311B825171AF5A60d69aAD590B857B1E5ed23a2"  # goerli deployment from April 2023

    def __init__(self, path: Path, hyperdrive_address: str = None) -> None:
        """Initialize the project, loading the Hyperdrive contract."""
        if path.name == "examples":  # if in examples folder, move up a level
            path = path.parent
        if hyperdrive_address is not None:
            self.hyperdrive_address = hyperdrive_address
        super().__init__(path)

    def __post_init__(self):
        """Set up contracts after init"""
        self.load_contracts()
        try:
            self.hyperdrive_container: ContractContainer = self.get_contract("Hyperdrive")
        except AttributeError as err:
            raise AttributeError("Hyperdrive contract not found") from err

    def get_hyperdrive_contract(self) -> ContractInstance:
        """Get the Hyperdrive contract instance."""
        return self.hyperdrive_container.at(self.conversion_manager.convert(self.hyperdrive_address, AddressType))


@dataclass
class DefaultHyperdriveConfig:
    """Configuration variables to setup hyperdrive fixtures."""

    # pylint: disable=too-many-instance-attributes

    initial_apr: FixedPoint = FixedPoint("0.05")
    share_price: FixedPoint = FixedPoint(1)
    checkpoint_duration_seconds: int = 86400
    checkpoints: int = 182
    time_stretch: int = 22186877016851913475
    curve_fee: FixedPoint = FixedPoint(0)
    flat_fee: FixedPoint = FixedPoint(0)
    gov_fee: FixedPoint = FixedPoint(0)
    position_duration_seconds: int = checkpoint_duration_seconds * checkpoints
    target_liquidity = FixedPoint(1 * 10**6)


def get_hyperdrive_config(hyperdrive_instance) -> dict:
    """Get the hyperdrive config from a deployed hyperdrive contract.

    Parameters
    ----------
    hyperdrive_instance : ContractInstance
        The deployed hyperdrive contract instance.

    Returns
    -------
    hyperdrive_config : dict
        The hyperdrive config.
    """
    hyperdrive_config: dict = hyperdrive_instance.getPoolConfig().__dict__
    hyperdrive_config["timeStretch"] = 1 / (hyperdrive_config["timeStretch"] / 1e18)
    logging.info("Hyperdrive config deployed at %s: ", hyperdrive_instance.address)
    logging.info("Hyperdrive config: %s", hyperdrive_config)
    hyperdrive_config["term_length"] = hyperdrive_config["positionDuration"] / 60 / 60 / 24  # in days
    return hyperdrive_config


def deploy_hyperdrive(
    experiment_config: Config,
    base_instance: ContractInstance,
    deployer_account: KeyfileAccount,
    pricing_model: HyperdrivePricingModel,
    project: HyperdriveProject,
) -> ContractInstance:
    """Deploy Hyperdrive when operating on a fresh fork.

    Parameters
    ----------
    experiment_config : simulators.Config
        The experiment configuration object.
    base_instance : ContractInstance
        The base token contract instance.
    deployer_account : Account
        The account used to deploy smart contracts.
    pricing_model : HyperdrivePricingModel
        The elf-simulations pricing model.
    project : HyperdriveProject
        The Ape project that contains a Hyperdrive contract.

    Returns
    -------
    hyperdrive : ContractInstance
        The deployed Hyperdrive contract instance.
    """
    initial_supply = FixedPoint(experiment_config.target_liquidity)
    initial_apr = FixedPoint(experiment_config.target_fixed_apr)
    market, _, _ = sim_utils.get_initialized_hyperdrive_market(
        pricing_model=pricing_model, block_time=time.BlockTime(), config=experiment_config
    )
    simulator = simulators.Simulator(experiment_config, market, time.BlockTime())
    base_instance.mint(
        initial_supply.scaled_value,
        sender=deployer_account,  # minted amount goes to sender
    )
    hyperdrive_config = DefaultHyperdriveConfig()
    hyperdrive_data_provider_contract = deployer_account.deploy(
        project.MockHyperdriveDataProviderTestnet,  # type: ignore
        base_instance,
        hyperdrive_config.initial_apr.scaled_value,
        hyperdrive_config.share_price.scaled_value,
        hyperdrive_config.position_duration_seconds,
        hyperdrive_config.checkpoint_duration_seconds,
        hyperdrive_config.time_stretch,
        (
            hyperdrive_config.curve_fee.scaled_value,
            hyperdrive_config.flat_fee.scaled_value,
            hyperdrive_config.gov_fee.scaled_value,
        ),
        deployer_account.address,
    )
    hyperdrive: ContractInstance = deployer_account.deploy(
        project.get_contract("MockHyperdriveTestnet"),
        hyperdrive_data_provider_contract.address,
        base_instance,
        initial_apr.scaled_value,
        FixedPoint(experiment_config.init_share_price).scaled_value,
        365,  # checkpoints per term
        86400,  # checkpoint duration in seconds (1 day)
        (
            FixedPoint("1.0") / (simulator.market.time_stretch_constant)
        ).scaled_value,  # time stretch in solidity format (inverted)
        (
            FixedPoint(experiment_config.curve_fee_multiple).scaled_value,
            FixedPoint(experiment_config.flat_fee_multiple).scaled_value,
            FixedPoint(experiment_config.governance_fee_multiple).scaled_value,
        ),
        deployer_account,
    )
    with ape.accounts.use_sender(deployer_account):
        base_instance.approve(hyperdrive, initial_supply.scaled_value)
        hyperdrive.initialize(
            initial_supply.scaled_value,
            initial_apr.scaled_value,
            deployer_account,
            True,
        )
    return hyperdrive


def get_market_state_from_contract(hyperdrive_contract: ContractInstance, **kwargs) -> HyperdriveMarketState:
    r"""Return the current market state from the smart contract.

    Arguments
    ---------
    hyperdrive_contract : `ape.contracts.base.ContractInstance <https://docs.apeworx.io/ape/stable/methoddocs/contracts.html#ape.contracts.base.ContractInstance>`_
        Contract pointing to the initialized MockHyperdriveTestnet smart contract.
    **kwargs : `dict`
        Keyword arguments to pass to the smart contract.

    Returns
    -------
    HyperdriveMarketState
    """
    pool_state = hyperdrive_contract.getPoolInfo(**kwargs).__dict__
    hyper_config = hyperdrive_contract.getPoolConfig(**kwargs).__dict__
    hyper_config["timeStretch"] = 1 / (hyper_config["timeStretch"] / 1e18)  # convert to elf-sims format
    hyper_config["term_length"] = hyper_config["positionDuration"] / (60 * 60 * 24)  # in days
    asset_id = hyperdrive_assets.encode_asset_id(AssetIdPrefix.WITHDRAWAL_SHARE, hyper_config["positionDuration"])
    total_supply_withdraw_shares = hyperdrive_contract.balanceOf(asset_id, hyperdrive_contract.address)

    return HyperdriveMarketState(
        lp_total_supply=FixedPoint(scaled_value=pool_state["lpTotalSupply"]),
        share_reserves=FixedPoint(scaled_value=pool_state["shareReserves"]),
        bond_reserves=FixedPoint(scaled_value=pool_state["bondReserves"]),
        base_buffer=FixedPoint(scaled_value=pool_state["longsOutstanding"]),  # so do we not need any buffers now?
        variable_apr=FixedPoint(0.01),  # TODO: insert real value
        share_price=FixedPoint(scaled_value=pool_state["sharePrice"]),
        init_share_price=FixedPoint(scaled_value=hyper_config["initialSharePrice"]),
        curve_fee_multiple=FixedPoint(scaled_value=hyper_config["fees"]["curve"]),
        flat_fee_multiple=FixedPoint(scaled_value=hyper_config["fees"]["flat"]),
        governance_fee_multiple=FixedPoint(scaled_value=hyper_config["fees"]["governance"]),
        longs_outstanding=FixedPoint(scaled_value=pool_state["longsOutstanding"]),
        shorts_outstanding=FixedPoint(scaled_value=pool_state["shortsOutstanding"]),
        long_average_maturity_time=FixedPoint(scaled_value=pool_state["longAverageMaturityTime"]),
        short_average_maturity_time=FixedPoint(scaled_value=pool_state["shortAverageMaturityTime"]),
        short_base_volume=FixedPoint(scaled_value=pool_state["shortBaseVolume"]),
        # TODO: checkpoints=dict
        checkpoint_duration=FixedPoint(hyper_config["checkpointDuration"]),
        total_supply_longs={FixedPoint(0): FixedPoint(scaled_value=pool_state["longsOutstanding"])},
        total_supply_shorts={FixedPoint(0): FixedPoint(scaled_value=pool_state["shortsOutstanding"])},
        total_supply_withdraw_shares=FixedPoint(scaled_value=total_supply_withdraw_shares),
        withdraw_shares_ready_to_withdraw=FixedPoint(scaled_value=pool_state["withdrawalSharesReadyToWithdraw"]),
        withdraw_capital=FixedPoint(0),
    )


OnChainTradeInfo = namedtuple(
    "OnChainTradeInfo", ["trades", "unique_maturities", "unique_ids", "unique_block_numbers", "share_price"]
)


def get_on_chain_trade_info(hyperdrive_contract: ContractInstance, block_number: int | None = None) -> OnChainTradeInfo:
    r"""Get all trades from hyperdrive contract.

    Arguments
    ---------
    hyperdrive_contract : `ape.contracts.base.ContractInstance <https://docs.apeworx.io/ape/stable/methoddocs/contracts.html#ape.contracts.base.ContractInstance>`_
        Contract pointing to the initialized Hyperdrive (or MockHyperdriveTestnet) smart contract.

    Returns
    -------
    OnChainTradeInfo
        Named tuple containing the following fields:
        - trades : pd.DataFrame
            DataFrame containing all trades from the Hyperdrive contract.
        - unique_maturities : list
            List of unique maturity timestamps across all assets.
        - unique_ids : list
            List of unique ids across all assets.
        - unique_block_numbers_ : list
            List of unique block numbers across all trades.
        - share_price_
            Map of share price to block number.
    """
    trades = hyperdrive_contract.TransferSingle.query("*", start_block=block_number or 0, stop_block=block_number)
    trades = pd.concat(  # flatten event_arguments
        [
            trades.loc[:, [c for c in trades.columns if c != "event_arguments"]],
            pd.DataFrame((dict(i) for i in trades["event_arguments"])),
        ],
        axis=1,
    )
    tuple_series = trades.apply(func=lambda x: hyperdrive_assets.decode_asset_id(int(x["id"])), axis=1)  # type: ignore
    trades["prefix"], trades["maturity_timestamp"] = zip(*tuple_series)  # split into two columns
    trades["trade_type"] = trades["prefix"].apply(lambda x: AssetIdPrefix(x).name)

    unique_maturities_ = trades["maturity_timestamp"].unique()
    unique_maturities_ = unique_maturities_[unique_maturities_ != 0]

    unique_ids_: np.ndarray = trades["id"].unique()
    unique_ids_ = unique_ids_[unique_ids_ != 0]

    unique_block_numbers_ = trades["block_number"].unique()

    share_price_ = {
        block_number_: hyperdrive_contract.getPoolInfo(block_identifier=int(block_number_))["sharePrice"]
        for block_number_ in unique_block_numbers_
    }
    for block_number_, price in share_price_.items():
        logging.debug(("block_number_={}, price={}", block_number_, price))

    return OnChainTradeInfo(trades, unique_maturities_, unique_ids_, unique_block_numbers_, share_price_)


def get_wallet_from_onchain_trade_info(
    address: str,
    info: OnChainTradeInfo,
    hyperdrive_contract: ContractInstance,
    base_contract: ContractInstance,
    index: int = 0,
    add_to_existing_wallet: Wallet | None = None,
) -> Wallet:
    # pylint: disable=too-many-arguments, too-many-branches

    r"""Construct wallet balances from on-chain trade info.

    Arguments
    ---------
    address : str
        Address of the wallet.
    info : OnChainTradeInfo
        On-chain trade info.
    hyperdrive_contract : `ape.contracts.base.ContractInstance <https://docs.apeworx.io/ape/stable/methoddocs/contracts.html#ape.contracts.base.ContractInstance>`_
        Contract pointing to the initialized Hyperdrive (or MockHyperdriveTestnet) smart contract.
    base_contract : `ape.contracts.base.ContractInstance <https://docs.apeworx.io/ape/stable/methoddocs/contracts.html#ape.contracts.base.ContractInstance>`_
        Contract pointing to the base currency (e.g. ERC20)
    index : int
        Index of the wallet among ALL agents.

    Returns
    -------
    Wallet
        Wallet with Short, Long, and LP positions.
    """
    # TODO: remove restriction forcing Wallet index to be an int (issue #415)
    if add_to_existing_wallet is None:
        wallet = Wallet(
            address=index,
            balance=types.Quantity(
                amount=FixedPoint(scaled_value=base_contract.balanceOf(address)), unit=types.TokenType.BASE
            ),
        )
    else:
        wallet = add_to_existing_wallet
    for position_id in info.unique_ids:  # loop across all unique positions
        trades_in_position = ((info.trades["from"] == address) | (info.trades["to"] == address)) & (
            info.trades["id"] == position_id
        )
        logging.info("found %s trades for %s in position %s", sum(trades_in_position), address[:8], position_id)
        positive_balance = int(info.trades.loc[(trades_in_position) & (info.trades["to"] == address), "value"].sum())
        negative_balance = int(info.trades.loc[(trades_in_position) & (info.trades["from"] == address), "value"].sum())
        balance = positive_balance - negative_balance
        logging.debug(
            "balance %s = positive_balance %s - negative_balance %s", balance, positive_balance, negative_balance
        )
        asset_prefix, maturity = hyperdrive_assets.decode_asset_id(position_id)
        asset_type = AssetIdPrefix(asset_prefix).name
        mint_time = maturity - SECONDS_IN_YEAR
        logging.info(" => %s(%s) maturity=%s mint_time=%s", asset_type, asset_prefix, maturity, mint_time)

        on_chain_balance = 0
        # verify our calculation against the onchain balance
        if add_to_existing_wallet is None:
            on_chain_balance = hyperdrive_contract.balanceOf(position_id, address)
            # only do balance checks if not marignal update
            if abs(balance - on_chain_balance) > MAXIMUM_BALANCE_MISMATCH_IN_WEI:
                raise ValueError(
                    f"events {balance=} and {on_chain_balance=} disagree by "
                    f"more than {MAXIMUM_BALANCE_MISMATCH_IN_WEI} wei for {address}"
                )
            logging.info(" => calculated balance = on_chain = %s", output_utils.str_with_precision(balance))
        # check if there's an outstanding balance
        if balance != 0 or on_chain_balance != 0:
            if asset_type == "SHORT":
                # loop across all the positions owned by this wallet
                sum_product_of_open_share_price_and_value, sum_value = 0, 0
                for specific_trade in trades_in_position.index[trades_in_position]:
                    value = info.trades.loc[specific_trade, "value"]
                    value *= -1 if info.trades.loc[specific_trade, "from"] == address else 1
                    sum_value += value
                    sum_product_of_open_share_price_and_value += (
                        value * info.share_price[info.trades.loc[specific_trade, "block_number"]]
                    )
                open_share_price = int(sum_product_of_open_share_price_and_value / sum_value)
                assert (
                    abs(balance - sum_value) <= MAXIMUM_BALANCE_MISMATCH_IN_WEI
                ), "weighted average open share price calculation is wrong"
                logging.debug("calculated weighted average open share price of %s", open_share_price)
                previous_balance = wallet.shorts[mint_time].balance if mint_time in wallet.shorts else 0
                new_balance = previous_balance + FixedPoint(scaled_value=balance)
                if new_balance == 0:
                    # remove key of "mint_time" from the "wallet.shorts" dict
                    wallet.shorts.pop(mint_time, None)
                else:
                    wallet.shorts.update(
                        {
                            mint_time: Short(
                                balance=new_balance,
                                open_share_price=FixedPoint(scaled_value=open_share_price),
                            )
                        }
                    )
                    logging.debug(
                        "storing in wallet as %s",
                        {
                            mint_time: Short(
                                balance=new_balance, open_share_price=FixedPoint(scaled_value=open_share_price)
                            )
                        },
                    )
            elif asset_type == "LONG":
                previous_balance = wallet.longs[mint_time].balance if mint_time in wallet.longs else 0
                new_balance = previous_balance + FixedPoint(scaled_value=balance)
                if new_balance == 0:
                    # remove key of "mint_time" from the "wallet.longs" dict
                    wallet.longs.pop(mint_time, None)
                wallet.longs.update({mint_time: Long(balance=new_balance)})
                logging.debug("storing in wallet as %s", {mint_time: Long(balance=balance)})
            elif asset_type == "LP":
                wallet.lp_tokens += FixedPoint(scaled_value=balance)
    return wallet


def create_elfpy_market(
    pricing_model: HyperdrivePricingModel,
    hyperdrive_instance: ContractInstance,
    hyperdrive_config: dict,
    block_number: int,
    block_timestamp: int,
    start_timestamp: int,
) -> HyperdriveMarket:
    """Create an elfpy market.

    Parameters
    ----------
    pricing_model : HyperdrivePricingModel
        The pricing model to use.
    hyperdrive_instance : ContractInstance
        The deployed Hyperdrive instance.
    hyperdrive_config : dict
        The configuration of the deployed Hyperdrive instance
    block_number : int
        The block number of the latest block.
    block_timestamp : int
        The timestamp of the latest block.
    start_timestamp : int
        The timestamp for when we started the simulation.

    Returns
    -------
    hyperdrive_market.Market
        The elfpy market.
    """
    # pylint: disable=too-many-arguments
    return HyperdriveMarket(
        pricing_model=pricing_model,
        market_state=get_market_state_from_contract(hyperdrive_contract=hyperdrive_instance),
        position_duration=time.StretchedTime(
            days=FixedPoint(hyperdrive_config["term_length"]),
            time_stretch=FixedPoint(hyperdrive_config["timeStretch"]),
            normalizing_constant=FixedPoint(hyperdrive_config["term_length"]),
        ),
        block_time=time.BlockTime(
            _time=FixedPoint((block_timestamp - start_timestamp) / 365),
            _block_number=FixedPoint(block_number),
            _step_size=FixedPoint("1.0") / FixedPoint("365.0"),
        ),
    )


def dump_agent_info(sim_agents, experiment_config):
    """Dump bot info to bots.json."""
    # save bot info to bots.json
    variables_to_save_to_bots_json = ["project_dir", "louie", "frida", "random", "bot_names"]
    # build json
    json_dict = {
        key: str(value) for key, value in experiment_config.scratch.items() if key in variables_to_save_to_bots_json
    }
    for agent_name, agent in sim_agents.items():
        json_dict[agent_name] = str(agent)
    # make folder if it doesn't exist
    if not os.path.exists(f"{experiment_config.scratch['project_dir']}/artifacts"):
        os.makedirs(f"{experiment_config.scratch['project_dir']}/artifacts")
    # write to file
    with open(f"{experiment_config.scratch['project_dir']}/artifacts/bots.json", "w", encoding="utf-8") as file:
        json.dump(json_dict, file, indent=4)


def get_gas_fees(block: BlockAPI) -> tuple[list[float], list[float]]:
    r"""Get the max and priority fees from a block (type 2 transactions only).

    Arguments
    ---------
    block : `ape.eth2.BlockAPI <https://docs.apeworx.io/ape/stable/methoddocs/api.html#ape.api.providers.BlockAPI>`_
        Block to get gas fees from.

    Returns
    -------
    tuple[list[float], list[float]]
        Tuple containing the max and priority fees.
    """
    # Pick out only type 2 transactions (EIP-1559). They have a max fee and priority fee.
    type2_transactions = [txn for txn in block.transactions if txn.type == 2]  # noqa: PLR2004
    if len(type2_transactions) <= 0:  # No type 2 transactions in block
        return [], []
    # Pull out max_fee and priority_fee for each transaction, zipping them into two lists
    max_fees, priority_fees = zip(*[(txn.max_fee, txn.max_priority_fee) for txn in type2_transactions])
    # Exclude None values solely for typechecking, then convert from wei to gwei (1 gwei = 1e9 wei)
    max_fees = [max_fee / 1e9 for max_fee in max_fees if max_fee is not None]
    priority_fees = [priority_fee / 1e9 for priority_fee in priority_fees if priority_fee is not None]
    return max_fees, priority_fees


def get_gas_stats(block: BlockAPI) -> tuple[float, float, float, float]:
    r"""Get gas stats for a given block: maximum and average of max and priority fees (type 2 transactions only).

    Arguments
    ---------
    block: `ape.eth2.BlockAPI <https://docs.apeworx.io/ape/stable/methoddocs/api.html#ape.api.providers.BlockAPI>`_
        Block to get gas fees from.

    Returns
    -------
    tuple[float, float, float, float]
        Tuple containing the max and avg max and priority fees.
    """
    # Pull out max_fee and priority_fee for each transaction, zipping them into two lists
    max_fees, priority_fees = get_gas_fees(block)
    if len(max_fees) <= 0:  # No type 2 transactions in block
        return np.nan, np.nan, np.nan, np.nan
    # Calculate max and avg for max_fees
    _max_max_fee = max(max_fees)
    _avg_max_fee = sum(max_fees) / len(max_fees)
    # Calculate max and avg for priority_fees
    _max_priority_fee = max(priority_fees)
    _avg_priority_fee = sum(priority_fees) / len(priority_fees)
    return _max_max_fee, _avg_max_fee, _max_priority_fee, _avg_priority_fee


def get_transfer_single_event(txn_receipt: ReceiptAPI) -> ContractLog:
    r"""Parse the transaction receipt to get the "transfer single" trade event.

    Arguments
    ---------
    txn_receipt : `ape.api.transactions.ReceiptAPI <https://docs.apeworx.io/ape/stable/methoddocs/api.html#ape.api.transactions.ReceiptAPI>`_
        Ape transaction abstract class to represent a transaction receipt.


    Returns
    -------
    single_event : `ape.types.ContractLog <https://docs.apeworx.io/ape/stable/methoddocs/types.html#ape.types.ContractLog>`_
        The primary emitted trade (a "TransferSingle") event, excluding peripheral events.
    """
    single_events = [tx_event for tx_event in txn_receipt.events if tx_event.event_name == "TransferSingle"]
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


def get_pool_state(txn_receipt: ReceiptAPI, hyperdrive_contract: ContractInstance) -> PoolState:
    r"""Return everything returned by `getPoolInfo()` in the smart contracts.

    Arguments
    ---------
    txn_receipt : `ape.api.transactions.ReceiptAPI <https://docs.apeworx.io/ape/stable/methoddocs/api.html#ape.api.transactions.ReceiptAPI>`_
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
    transfer_single_event = get_transfer_single_event(txn_receipt)
    # The ID is a concatenation of the current share price and the maturity time of the trade
    token_id = int(transfer_single_event["id"])
    prefix, maturity_timestamp = hyperdrive_assets.decode_asset_id(token_id)
    hyper_dict = hyperdrive_contract.getPoolInfo().__dict__
    hyper_dict["block_number"] = txn_receipt.block_number
    hyper_dict["token_id"] = token_id
    hyper_dict["prefix"] = prefix
    hyper_dict["maturity_timestamp"] = maturity_timestamp  # in seconds
    logging.debug("hyperdrive_pool_state=%s", hyper_dict)
    return PoolState(**hyper_dict)


def snake_to_camel(_snake):
    """Convert snake_case to camelCase"""
    return "".join(word.capitalize() for word in _snake.split("_"))


def camel_to_snake(camel_string: str) -> str:
    """Convert camelCase to snake_case"""
    snake_string = re.sub(r"(?<!^)(?=[A-Z])", "_", camel_string)
    return snake_string.lower()


@dataclass
class PoolState:
    """A dataclass to hold the state of the pool at a given block."""

    # pylint: disable=invalid-name, too-many-instance-attributes
    shareReserves: int
    bondReserves: int
    lpTotalSupply: int
    sharePrice: int
    longsOutstanding: int
    longAverageMaturityTime: int
    shortsOutstanding: int
    shortAverageMaturityTime: int
    shortBaseVolume: int
    withdrawalSharesReadyToWithdraw: int
    withdrawalSharesProceeds: int
    block_number: int
    token_id: int
    prefix: str
    maturity_timestamp: int

    def __getattribute__(self, __snake: str) -> Any:
        """Convert from snake_case to camelCase for the dataclass."""
        return super().__getattribute__(snake_to_camel(__snake))

    def __setattr__(self, __snake: str, __value: Any) -> None:
        super().__setattr__(snake_to_camel(__snake), __value)


PoolInfo = namedtuple("PoolInfo", ["start_time", "block_time", "term_length", "market_state"])


def get_agent_deltas(txn_receipt: ReceiptAPI, trade, addresses, trade_type, pool_info: PoolInfo):
    """Get the change in an agent's wallet from a transaction receipt."""
    # TODO: verify the accuracy of this function through more testing
    # issue #423
    agent = txn_receipt.operator
    event_args = txn_receipt.event_arguments
    event_args.update({key: value for key, value in txn_receipt.items() if key in ["block_number", "event_name"]})
    dai_events = [e.dict() for e in txn_receipt.events if agent in [e.get("src"), e.get("dst")]]
    dai_in = sum(int(e["event_arguments"]["wad"]) for e in dai_events if e["event_arguments"]["src"] == agent) / 1e18
    _, maturity_timestamp = hyperdrive_assets.decode_asset_id(int(trade["id"]))
    mint_time = ((maturity_timestamp - int(SECONDS_IN_YEAR) * pool_info.term_length) - pool_info.start_time) / int(
        SECONDS_IN_YEAR
    )
    if trade_type == "addLiquidity":  # sourcery skip: lift-return-into-if, switch
        agent_deltas = Wallet(
            address=addresses.index(agent),
            balance=-types.Quantity(amount=trade["_contribution"], unit=types.TokenType.BASE),
            lp_tokens=trade["value"],  # trade output
        )
    elif trade_type == "removeLiquidity":
        agent_deltas = Wallet(
            address=addresses.index(agent),
            balance=types.Quantity(amount=trade["value"], unit=types.TokenType.BASE),  # trade output
            lp_tokens=-trade["_shares"],  # negative, decreasing
            withdraw_shares=trade["_shares"],  # positive, increasing
        )
    elif trade_type == "openLong":
        agent_deltas = Wallet(
            address=addresses.index(agent),
            balance=types.Quantity(amount=-trade["_baseAmount"], unit=types.TokenType.BASE),  # negative, decreasing
            longs={pool_info.block_time: Long(trade["value"])},  # trade output, increasing
        )
    elif trade_type == "closeLong":
        agent_deltas = Wallet(
            address=addresses.index(agent),
            balance=types.Quantity(amount=trade["value"], unit=types.TokenType.BASE),  # trade output
            longs={mint_time: Long(-trade["_bondAmount"])},  # negative, decreasing
        )
    elif trade_type == "openShort":
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
        if trade_type != "closeShort":
            raise ValueError(f"Unknown trade type: {trade_type}")
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


def get_instance(address: str, provider: ProviderAPI, contract_type: ContractType | None = None) -> ContractInstance:
    r"""Instantiate Contract at a specific address, explicitly using the cache (where Ape refuses to).

    Arguments
    ---------
    address : str
        Address of the contract to instantiate.
    provider : ` ape.api.providers.ProviderAPI <https://docs.apeworx.io/ape/stable/methoddocs/api.html#ape.api.providers.ProviderAPI>`_
        Ape Provider object represents a connection to a blockchain network.
    contract_type : ` ape.api.contract.ContractType <https://docs.apeworx.io/ape/stable/methoddocs/api.html#ape.api.contract.ContractType>`_
        Contract type to instantiate. Default is None, in which case the contract type is inferred from the address.

    Example
    -------
    >>> faucet = ape_utils.get_instance(FAUCET_ADDRESS, provider=provider)

    Returns
    -------
    ContractInstance
        Contract instance at the specified address.
    """
    if contract_type is None:
        contract_type = get_contract_type(address, provider=provider)
    return Contract(address=address, contract_type=contract_type)


def get_contract_type(address: str, provider: ProviderAPI) -> ContractType:
    r"""Get contract type from cache. Used for devnet, where Ape refuses to check the cache.

    Arguments
    ---------
    address : str
        Address of the contract to instantiate.
    provider : ` ape.api.providers.ProviderAPI <https://docs.apeworx.io/ape/stable/methoddocs/api.html#ape.api.providers.ProviderAPI>`_
        Ape Provider object represents a connection to a blockchain network.

    Example
    -------
    >>> faucet = Contract(FAUCET_ADDRESS, contract_type=ape_utils.get_contract_type(FAUCET_ADDRESS, provider=provider))

    Returns
    -------
    ContractType
        Contract type at the specified address.
    """
    # pylint: disable=protected-access
    address_key: AddressType = provider.chain_manager.contracts.conversion_manager.convert(address, AddressType)
    # try to get contract from local cache on disk
    contract_type = provider.chain_manager.contracts._get_contract_type_from_disk(address_key)
    if not contract_type:  # we don't have it locally, try to get it from the explorer
        contract_type = provider.chain_manager.contracts._get_contract_type_from_explorer(address_key)
    if contract_type:  # Cache locally for faster in-session look-up
        provider.chain_manager.contracts._local_contract_types[address_key] = contract_type
    assert isinstance(contract_type, ContractType), f"Contract type not found for address: {address}"
    return contract_type


def select_abi(method: Callable, params: dict | None = None, args: tuple | None = None) -> tuple[MethodABI, tuple]:
    r"""Select the correct ABI for a method based on the provided parameters.

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
    selected_abi: MethodABI | None = None
    method_abis: list[MethodABI] = method.abis
    missing_args = set()
    for abi in method_abis:  # loop through all the ABIs
        if params is not None:  # we try to match on keywords!
            found_args = [inpt.name for inpt in abi.inputs if inpt.name in params]
            if len(found_args) == len(abi.inputs):  # check if the selected args match the number of inputs
                selected_abi = abi  # we found all the arguments by name!
                args = tuple(params[arg] for arg in found_args)  # get the values for the arguments
                break
            missing_args = {inpt.name for inpt in abi.inputs if inpt.name not in params}
        elif len(args) == len(abi.inputs):  # check if the number of arguments matches the number of inputs
            selected_abi = abi  # pick this ABI because it has the right number of arguments, hope for the best
            break
    if selected_abi is None:
        raise ValueError(
            f"Could not find matching ABI for {method}"
            + (f" with missing arguments: {missing_args}" if missing_args else "")
        )
    lstr = f" => {selected_abi.name}({', '.join(f'{inpt.name}={arg}' for arg, inpt in zip(args, selected_abi.inputs))})"
    logging.info(lstr)
    return selected_abi, args


Info = namedtuple("Info", ["method", "prefix"])


def create_trade(
    trade_type: str,
    hyperdrive_contract: ContractInstance,
    agent: AccountAPI,
    amount: int,
    maturity_time: int | None = None,
) -> tuple[ContractTransaction, tuple, MethodABI]:
    r"""Creates a trade on the Hyperdrive contract.

    Arguments
    ---------
    trade_type : str
        The type of trade to execute. One of `ADD_LIQUIDITY,
        REMOVE_LIQUIDITY, OPEN_LONG, CLOSE_LONG, OPEN_SHORT, CLOSE_SHORT`
    hyperdrive_contract : `ape.contracts.base.ContractInstance <https://docs.apeworx.io/ape/stable/methoddocs/contracts.html#ape.contracts.base.ContractInstance>`_
        Ape interactive instance of the initialized MockHyperdriveTestnet smart contract.
    agent : `ape.api.accounts.AccountAPI <https://docs.apeworx.io/ape/stable/methoddocs/api.html#ape.api.accounts.AccountAPI>`_
        The account that will execute the trade.
    amount : int
        Unsigned int-256 representation of the trade amount (base if not LP, otherwise LP tokens)
    maturity_time : int, optional
        The maturity time of the trade. Only used for `CLOSE_LONG`, and `CLOSE_SHORT`.
    kwargs : dict, optional
        Additional keyword arguments to pass to the trade method.

    Returns
    -------
    pool_state : dict, optional
        The Hyperdrive pool state after the trade.
    args : list
        The matching keyword arguments, or the original arguments if no keywords were provided.
    """
    # predefine which methods to call based on the trade type, and the corresponding asset ID prefix
    info = {
        "OPEN_LONG": Info(method=hyperdrive_contract.openLong, prefix=AssetIdPrefix.LONG),
        "CLOSE_LONG": Info(method=hyperdrive_contract.closeLong, prefix=AssetIdPrefix.LONG),
        "OPEN_SHORT": Info(method=hyperdrive_contract.openShort, prefix=AssetIdPrefix.SHORT),
        "CLOSE_SHORT": Info(method=hyperdrive_contract.closeShort, prefix=AssetIdPrefix.SHORT),
        "ADD_LIQUIDITY": Info(method=hyperdrive_contract.addLiquidity, prefix=AssetIdPrefix.LP),
        "REMOVE_LIQUIDITY": Info(method=hyperdrive_contract.removeLiquidity, prefix=AssetIdPrefix.LP),
    }
    if trade_type in {"CLOSE_LONG", "CLOSE_SHORT"}:  # get the specific asset we're closing
        assert maturity_time is not None, "Maturity time must be provided to close a long or short trade"
        trade_asset_id = hyperdrive_assets.encode_asset_id(info[trade_type].prefix, maturity_time)
        assert amount != 0, "trade amount is zero, this is not allowed"
        amount = max(WEI, min(amount, hyperdrive_contract.balanceOf(trade_asset_id, agent)))
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
        "_maturityTime": maturity_time,
    }
    # check the specified method for an ABI that we have all the parameters for
    selected_abi, args = select_abi(params=params, method=info[trade_type].method)
    # create a transaction with the selected ABI
    contract_txn: ContractTransaction = ContractTransaction(abi=selected_abi, address=hyperdrive_contract.address)
    return contract_txn, args, selected_abi


def ape_trade(
    trade_type: str,
    hyperdrive_contract: ContractInstance,
    agent: AccountAPI,
    amount: int,
    maturity_time: int | None = None,
    **kwargs: Any,
) -> tuple[dict[str, Any] | None, ReceiptAPI | None]:
    r"""Execute a trade on the Hyperdrive contract.

    Arguments
    ---------
    trade_type : str
        The type of trade to execute. One of `ADD_LIQUIDITY,
        REMOVE_LIQUIDITY, OPEN_LONG, CLOSE_LONG, OPEN_SHORT, CLOSE_SHORT`
    hyperdrive_contract : `ape.contracts.base.ContractInstance <https://docs.apeworx.io/ape/stable/methoddocs/contracts.html#ape.contracts.base.ContractInstance>`_
        Ape interactive instance of the initialized MockHyperdriveTestnet smart contract.
    agent : `ape.api.accounts.AccountAPI <https://docs.apeworx.io/ape/stable/methoddocs/api.html#ape.api.accounts.AccountAPI>`_
        The account that will execute the trade.
    amount : int
        Unsigned int-256 representation of the trade amount (base if not LP, otherwise LP tokens)
    maturity_time : int, optional
        The maturity time of the trade. Only used for `CLOSE_LONG`, and `CLOSE_SHORT`.
    kwargs : dict, optional
        Additional keyword arguments to pass to the trade method.

    Returns
    -------
    pool_state : dict, optional
        The Hyperdrive pool state after the trade.
    txn_receipt : `ape.api.transactions.ReceiptAPI <https://docs.apeworx.io/ape/stable/methoddocs/api.html#ape.api.transactions.ReceiptAPI>`_
        The Ape transaction receipt.
    """
    contract_txn, args, _ = create_trade(
        trade_type=trade_type,
        hyperdrive_contract=hyperdrive_contract,
        agent=agent,
        amount=amount,
        maturity_time=maturity_time,
    )
    try:  # attempt to execute the transaction, allowing for a specified number of retries (default is 1)
        if args:
            txn_receipt = attempt_txn(agent, contract_txn, *args, **kwargs)
        else:
            txn_receipt = attempt_txn(agent, contract_txn, **kwargs)
        if txn_receipt is None:
            return None, None
        return get_pool_state(txn_receipt=txn_receipt, hyperdrive_contract=hyperdrive_contract), txn_receipt
    except TransactionError as exc:
        logging.error(
            "Failed to execute %s: %s\n =>  Amount: %s\n => Agent: %s\n => Pool: %s\n",
            trade_type,
            exc,
            output_utils.str_with_precision(amount),
            agent,
            hyperdrive_contract.getPoolInfo().__dict__,
        )
        raise exc


def attempt_txn(
    agent: AccountAPI, contract_txn: ContractTransaction | ContractTransactionHandler, *args, **kwargs
) -> ReceiptAPI | None:
    r"""Execute a transaction using fallback logic when a transaction fails due to gas price being too low.

    Max gas is 2x the last block base fee, increasing to 3x on the second attempt.
    Priority fee is 1x the recommended priority fee, increasing to (1+priorirty_fee_multiple) on the second attempt.
    Priority_fee_multiple defaults to 5, but can be overriden as a keyword argument.

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
    txn_receipt : `ape.api.transactions.ReceiptAPI <https://docs.apeworx.io/ape/stable/methoddocs/api.html#ape.api.transactions.ReceiptAPI>`_
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
    # allow inconsistent return, since we throw an error if the transaction fails after all attempts
    # pylint: disable=inconsistent-return-statements
    mult = kwargs.pop("mult") if hasattr(kwargs, "mult") else 2
    priority_fee_multiple = kwargs.pop("priority_fee_multiple") if hasattr(kwargs, "priority_fee_multiple") else 5
    if isinstance(contract_txn, ContractTransactionHandler):
        abi, args = select_abi(method=contract_txn, args=args)
        contract_txn = ContractTransaction(abi=abi, address=contract_txn.contract.address)
    # begin attempts, indexing attempt from 1 to mult (for the sake of easy calculation)
    for attempt in range(1, mult + 1):
        latest = agent.provider.get_block("latest")
        if latest is None:
            raise ValueError("latest block not found")
        if not hasattr(latest, "base_fee"):
            raise ValueError("latest block does not have base_fee")
        base_fee = getattr(latest, "base_fee")
        logging.debug(
            "latest block %s has base_fee %s",
            output_utils.str_with_precision(getattr(latest, "number")),
            output_utils.str_with_precision(base_fee / 1e9, min_digits=3),
        )
        kwargs["max_priority_fee_per_gas"] = int(
            agent.provider.priority_fee * (1 + priority_fee_multiple * (attempt - 1))
        )
        kwargs["max_fee_per_gas"] = int(base_fee * (1 + attempt)) + kwargs["max_priority_fee_per_gas"]
        kwargs["sender"] = agent.address
        kwargs["nonce"] = agent.provider.get_nonce(agent.address)
        kwargs["gas_limit"] = 1_000_000
        # if you want a "STATIC" transaction type, uncomment the following line
        # kwargs["gas_price"] = kwargs["max_fee_per_gas"]
        formatted_items = []
        for key, value in kwargs.items():
            value = (
                output_utils.str_with_precision(value / 1e9) if "fee" in key else output_utils.str_with_precision(value)
            )
            formatted_items.append(f"{key}={value}")
        logging.debug("txn attempt %s of %s with %s", attempt, mult, ", ".join(formatted_items))
        serial_txn: TransactionAPI = contract_txn.serialize_transaction(*args, **kwargs)
        prepped_txn: TransactionAPI = agent.prepare_transaction(serial_txn)
        signed_txn: TransactionAPI | None = agent.sign_transaction(prepped_txn)
        logging.debug(" => sending signed_txn %s", signed_txn)
        if signed_txn is None:
            raise ValueError("Failed to sign transaction")
        try:
            txn_receipt: ReceiptAPI = agent.provider.send_transaction(signed_txn)
            txn_receipt.await_confirmations()
            return txn_receipt
        except TransactionError as exc:
            if "replacement transaction underpriced" not in str(exc) or not isinstance(exc, TransactionNotFoundError):
                logging.info("Txn failed in unexpected way on attempt %s of %s: %s", attempt, mult, exc)
                raise exc
            logging.info("Txn failed in expected way: %s", exc)
            if attempt == mult:
                logging.info(" => max attempts reached, raising exception")
                raise exc
            logging.info(" => retrying with higher gas price: %s of %s", attempt + 1, mult)
            continue
    raise TimeoutError("Failed to execute transaction")

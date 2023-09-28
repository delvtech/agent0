"""Helper functions for interfacing with hyperdrive"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from elfpy import time as elftime
from elfpy.markets.hyperdrive import HyperdriveMarket, HyperdriveMarketState, HyperdrivePricingModel
from eth_typing import BlockNumber, ChecksumAddress
from eth_utils import address
from ethpy.base import UnknownBlockError, get_transaction_logs, smart_contract_read
from fixedpointmath import FixedPoint
from web3 import Web3
from web3.contract.contract import Contract
from web3.types import BlockData, TxReceipt

from .addresses import HyperdriveAddresses
from .assets import AssetIdPrefix, encode_asset_id
from .receipt_breakdown import ReceiptBreakdown


def get_hyperdrive_pool_config(hyperdrive_contract: Contract) -> dict[str, Any]:
    """Get the hyperdrive config from a deployed hyperdrive contract.

    Arguments
    ----------
    hyperdrive_contract : Contract
        The deployed hyperdrive contract instance.

    Returns
    -------
    dict[str, Any]
        The hyperdrive pool config.
    """
    return smart_contract_read(hyperdrive_contract, "getPoolConfig")


def process_hyperdrive_pool_config(pool_config: dict[str, Any], hyperdrive_address: ChecksumAddress) -> dict[str, Any]:
    """Convert pool_config to python-friendly (FixedPoint, integer, str) types and add some computed values.

    Arguments
    ----------
    pool_config : dict[str, Any]
        The hyperdrive pool config.
    hyperdrive_address : ChecksumAddress
        The deployed hyperdrive contract instance address.

    Returns
    -------
    dict[str, Any]
        The hyperdrive pool config with modified types.
    """
    # convert values to FixedPoint
    fixedpoint_keys = ["initialSharePrice", "minimumShareReserves", "timeStretch"]
    for key in pool_config:
        if key in fixedpoint_keys:
            pool_config[key] = FixedPoint(scaled_value=pool_config[key])
    pool_config["fees"] = (FixedPoint(scaled_value=fee) for fee in pool_config["fees"])
    # new attributes
    pool_config["contractAddress"] = hyperdrive_address
    curve_fee, flat_fee, governance_fee = pool_config["fees"]
    pool_config["curveFee"] = curve_fee
    pool_config["flatFee"] = flat_fee
    pool_config["governanceFee"] = governance_fee
    pool_config["invTimeStretch"] = FixedPoint(1) / pool_config["timeStretch"]
    return pool_config


def get_hyperdrive_pool_info(hyperdrive_contract: Contract, block_number: BlockNumber) -> dict[str, Any]:
    """Return the block pool info from the Hyperdrive contract.

    Arguments
    ---------
    hyperdrive_contract: Contract
        The contract to query the pool info from.
    block_number: BlockNumber
        The block number to query from the chain.

    Returns
    -------
    dict[str, Any]
        The hyperdrive pool info returned from the smart contract.
    """
    return smart_contract_read(hyperdrive_contract, "getPoolInfo", block_identifier=block_number)


def process_hyperdrive_pool_info(
    pool_info: dict[str, Any],
    web3: Web3,
    hyperdrive_contract: Contract,
    position_duration: int,
    block_number: BlockNumber,
) -> dict[str, Any]:
    """Convert pool_info to python-friendly (FixedPoint, integer, str) types and add some computed values.

    Arguments
    ---------
    pool_info : dict[str, Any]
        The hyperdrive pool info.
    web3: Web3
        Web3 provider object.
    hyperdrive_contract: Contract
        The contract to query the pool info from.
    position_duration: int
        The position duration for the hyperdrive pool (supplied by pool_config).
    block_number: BlockNumber
        The block number used to query the pool info from the chain.

    Returns
    -------
    dict
        The hyperdrive pool info with modified types.
        This output can be inserted into the Postgres PoolInfo schema.
    """
    # convert values to fixedpoint
    pool_info = {str(key): FixedPoint(scaled_value=value) for (key, value) in pool_info.items()}
    # get current block information & add to pool info
    current_block: BlockData = web3.eth.get_block(block_number)
    current_block_timestamp = current_block.get("timestamp")
    if current_block_timestamp is None:
        raise AssertionError("Current block has no timestamp")
    pool_info.update({"timestamp": datetime.utcfromtimestamp(current_block_timestamp)})
    pool_info.update({"blockNumber": int(block_number)})
    # add position duration to the data dict
    # TODO get position duration from existing config passed in instead of from the chain
    asset_id = encode_asset_id(AssetIdPrefix.WITHDRAWAL_SHARE, position_duration)
    pool_info["totalSupplyWithdrawalShares"] = smart_contract_read(
        hyperdrive_contract, "balanceOf", asset_id, hyperdrive_contract.address
    )["value"]
    return pool_info


def get_hyperdrive_checkpoint(hyperdrive_contract: Contract, block_number: BlockNumber) -> dict[str, int]:
    """Returns the checkpoint info for the Hyperdrive contract at a given block.

    Arguments
    ---------
    hyperdrive_contract: Contract
        The contract to query the pool info from
    block_number: BlockNumber
        The block number to query from the chain

    Returns
    -------
    dict[str, int]
        A dictionary containing the checkpoint details.
    """
    return smart_contract_read(hyperdrive_contract, "getCheckpoint", block_number)


def process_hyperdrive_checkpoint(checkpoint: dict[str, int], web3: Web3, block_number: BlockNumber) -> dict[str, Any]:
    """Returns the checkpoint info of Hyperdrive contract for the given block.

    Arguments
    ---------
    checkpoint : dict[str, int]
        A dictionary containing the checkpoint details.
    web3 : Web3
        web3 provider object.
    block_number : BlockNumber
        The block number to query from the chain.

    Returns
    -------
    dict[str, Any]
        A dict containing the checkpoint with some additional fields.
        This is what is expected by the chainsync db conversion function.
    """
    out_checkpoint: dict[str, Any] = {}
    out_checkpoint.update(checkpoint)
    current_block: BlockData = web3.eth.get_block(block_number)
    current_block_timestamp = current_block.get("timestamp")
    if current_block_timestamp is None:
        raise AssertionError("Current block has no timestamp")
    out_checkpoint["blockNumber"] = int(block_number)
    # TODO: change "timestamp" to use exact current_block_timestamp,
    # and anytime we need the datetime we do it there
    out_checkpoint["timestamp"] = datetime.fromtimestamp(int(current_block_timestamp))
    out_checkpoint["sharePrice"] = FixedPoint(scaled_value=checkpoint["sharePrice"])
    out_checkpoint["longSharePrice"] = FixedPoint(scaled_value=checkpoint["longSharePrice"])
    # TODO: Pull this out when you update the hyperdrive abi
    if "longExposure" in checkpoint:
        out_checkpoint["longExposure"] = FixedPoint(scaled_value=checkpoint["longExposure"])
    return out_checkpoint


def get_hyperdrive_market(web3: Web3, hyperdrive_contract: Contract) -> HyperdriveMarket:
    """Constructs an elfpy HyperdriveMarket from the onchain hyperdrive constract state."""
    earliest_block = web3.eth.get_block("earliest")
    current_block = web3.eth.get_block("latest")
    pool_config = process_hyperdrive_pool_config(
        get_hyperdrive_pool_config(hyperdrive_contract), hyperdrive_contract.address
    )
    current_block_number = current_block.get("number", None)
    if current_block_number is None:
        raise AssertionError("Current block number should not be None")
    pool_info = process_hyperdrive_pool_info(
        get_hyperdrive_pool_info(hyperdrive_contract, current_block_number),
        web3,
        hyperdrive_contract,
        pool_config["positionDuration"],
        current_block_number,
    )
    market_state = HyperdriveMarketState(
        base_buffer=FixedPoint(pool_info["longsOutstanding"]),
        bond_reserves=FixedPoint(pool_info["bondReserves"]),
        checkpoint_duration=FixedPoint(pool_config["checkpointDuration"]),
        curve_fee_multiple=FixedPoint(pool_config["curveFee"]),
        flat_fee_multiple=FixedPoint(pool_config["flatFee"]),
        governance_fee_multiple=FixedPoint(pool_config["governanceFee"]),
        init_share_price=FixedPoint(pool_config["initialSharePrice"]),
        long_average_maturity_time=FixedPoint(pool_info["longAverageMaturityTime"]),
        longs_outstanding=FixedPoint(pool_info["longsOutstanding"]),
        lp_total_supply=FixedPoint(pool_info["lpTotalSupply"]),
        share_price=FixedPoint(pool_info["sharePrice"]),
        share_reserves=FixedPoint(pool_info["shareReserves"]),
        minimum_share_reserves=FixedPoint(pool_config["minimumShareReserves"]),
        short_average_maturity_time=FixedPoint(pool_info["shortAverageMaturityTime"]),
        shorts_outstanding=FixedPoint(pool_info["shortsOutstanding"]),
        # TODO: We don't have checkpoint information, so the next two fields are indexed by 0
        total_supply_longs={FixedPoint(0): FixedPoint(pool_info["longsOutstanding"])},
        total_supply_shorts={FixedPoint(0): FixedPoint(pool_info["shortsOutstanding"])},
        total_supply_withdraw_shares=FixedPoint(pool_info["totalSupplyWithdrawalShares"]),
        variable_apr=FixedPoint("0.01"),  # TODO: insert real value
        withdraw_shares_ready_to_withdraw=FixedPoint(pool_info["withdrawalSharesReadyToWithdraw"]),
        withdraw_capital=FixedPoint(0),
        withdraw_interest=FixedPoint(0),
    )
    # TODO: Would it be safe to assume that earliest_block.timestamp always equals zero?
    time_elapsed = (
        datetime.utcfromtimestamp(current_block.get("timestamp", None))
        - datetime.utcfromtimestamp(earliest_block.get("timestamp", None))
    ).total_seconds()
    years_elapsed = FixedPoint(time_elapsed) / 60 / 60 / 24 / 365
    return HyperdriveMarket(
        pricing_model=HyperdrivePricingModel(),
        market_state=market_state,
        position_duration=elftime.StretchedTime(
            days=FixedPoint(pool_config["positionDuration"]) / FixedPoint(86_400),
            time_stretch=FixedPoint(pool_config["invTimeStretch"]),  # inverted from what solidity returns
            normalizing_constant=FixedPoint(pool_config["positionDuration"]) / FixedPoint(86_400),
        ),
        block_time=elftime.BlockTime(
            _time=years_elapsed,
            _block_number=FixedPoint(current_block.get("number", None)),
            _step_size=FixedPoint(1) / FixedPoint(365),  # TODO: Should get the anvil increment time
        ),
    )


def get_hyperdrive_contract(web3: Web3, abis: dict, addresses: HyperdriveAddresses) -> Contract:
    """Get the hyperdrive contract given abis.

    Arguments
    ---------
    web3: Web3
        web3 provider object
    abis: dict
        A dictionary that contains all abis keyed by the abi name, returned from `load_all_abis`
    addresses: HyperdriveAddressesJson
        The block number to query from the chain

    Returns
    -------
    Contract
        The contract object returned from the query
    """
    if "IHyperdrive" not in abis:
        raise AssertionError("IHyperdrive ABI was not provided")
    state_abi = abis["IHyperdrive"]
    # get contract instance of hyperdrive
    hyperdrive_contract: Contract = web3.eth.contract(
        address=address.to_checksum_address(addresses.mock_hyperdrive), abi=state_abi
    )
    return hyperdrive_contract


def parse_logs(tx_receipt: TxReceipt, hyperdrive_contract: Contract, fn_name: str) -> ReceiptBreakdown:
    """Decode a Hyperdrive contract transaction receipt to get the changes to the agent's funds.

    Arguments
    ---------
    TxReceipt
        a TypedDict; success can be checked via tx_receipt["status"]
    hyperdrive_contract : Contract
        Any deployed web3 contract
    fn_name : str
        This function must exist in the compiled contract's ABI

    Returns
    -------
    ReceiptBreakdown
        A dataclass containing the maturity time and the absolute values for token quantities changed
    """
    # Sometimes, smart contract transact fails with status 0 with no error message
    # We throw custom error to catch in trades loop, ignore, and move on
    # TODO need to track down why this call fails and handle better
    status = tx_receipt.get("status", None)
    if status is None:
        raise AssertionError("Receipt did not return status")
    if status == 0:
        raise UnknownBlockError(f"Receipt has no status or status is 0 \n {tx_receipt=}")
    hyperdrive_event_logs = get_transaction_logs(
        hyperdrive_contract,
        tx_receipt,
        event_names=[fn_name[0].capitalize() + fn_name[1:]],
    )
    if len(hyperdrive_event_logs) == 0:
        raise AssertionError(f"Transaction receipt had no logs\ntx_receipt=\n{tx_receipt}")
    if len(hyperdrive_event_logs) > 1:
        raise AssertionError("Too many logs found")
    log_args = hyperdrive_event_logs[0]["args"]
    trade_result = ReceiptBreakdown()
    if "assetId" in log_args:
        trade_result.asset_id = log_args["assetId"]
    if "maturityTime" in log_args:
        trade_result.maturity_time_seconds = log_args["maturityTime"]
    if "baseAmount" in log_args:
        trade_result.base_amount = FixedPoint(scaled_value=log_args["baseAmount"])
    if "bondAmount" in log_args:
        trade_result.bond_amount = FixedPoint(scaled_value=log_args["bondAmount"])
    if "lpAmount" in log_args:
        trade_result.lp_amount = FixedPoint(scaled_value=log_args["lpAmount"])
    if "withdrawalShareAmount" in log_args:
        trade_result.withdrawal_share_amount = FixedPoint(scaled_value=log_args["withdrawalShareAmount"])
    return trade_result


def get_event_history_from_chain(
    hyperdrive_contract: Contract, from_block: int, to_block: int, wallet_addr: str | None = None
) -> dict:
    """Helper function to query event logs directly from the chain.
    Useful for debugging open positions of wallet addresses.
    This might be creating unnecessary filters if ran, so only use for debugging

    Arguments
    ---------
    hyperdrive_contract : Contract
        The deployed hyperdrive contract instance.
    from_block: int
        The starting block to query
    to_block: int
        The end block to query. If from_block == to_block, will query the specified block number
    wallet_addr: str | None
        The wallet address to filter events on. If None, will return all.

    Returns
    -------
    A dictionary of event logs, keyed by the event name. Specifically:
        # TODO figure out return type of web3 call
        "addLiquidity": list[Unknown]
        "removeLiquidity": list[Unknown]
        "redeemWithdrawalShares": list[Unknown]
        "openLong": list[Unknown]
        "closeLong": list[Unknown]
        "openShort": list[Unknown]
        "closeShort": list[Unknown]
        "total_events": int
    """
    # TODO clean up this function
    # pylint: disable=too-many-locals

    # Build arguments
    lp_addr_filter = {}
    trade_addr_filter = {}
    if wallet_addr is not None:
        lp_addr_filter = {"provider": wallet_addr}
        trade_addr_filter = {"trader": wallet_addr}
    lp_filter_args = {"fromBlock": from_block, "toBlock": to_block, "argument_filters": lp_addr_filter}
    trade_filter_args = {"fromBlock": from_block, "toBlock": to_block, "argument_filters": trade_addr_filter}

    # Create filter on events
    # Typing doesn't know about create_filter function with various events
    add_lp_event_filter = hyperdrive_contract.events.AddLiquidity.create_filter(**lp_filter_args)  # type: ignore
    remove_lp_event_filter = hyperdrive_contract.events.RemoveLiquidity.create_filter(**lp_filter_args)  # type:ignore
    withdraw_event_filter = hyperdrive_contract.events.RedeemWithdrawalShares.create_filter(  # type:ignore
        **lp_filter_args
    )
    open_long_event_filter = hyperdrive_contract.events.OpenLong.create_filter(**trade_filter_args)  # type:ignore
    close_long_event_filter = hyperdrive_contract.events.CloseLong.create_filter(**trade_filter_args)  # type:ignore
    open_short_event_filter = hyperdrive_contract.events.OpenShort.create_filter(**trade_filter_args)  # type:ignore
    close_short_event_filter = hyperdrive_contract.events.CloseShort.create_filter(**trade_filter_args)  # type:ignore

    # Retrieve all entries
    add_lp_events = add_lp_event_filter.get_all_entries()
    remove_lp_events = remove_lp_event_filter.get_all_entries()
    withdraw_events = withdraw_event_filter.get_all_entries()
    open_long_events = open_long_event_filter.get_all_entries()
    close_long_events = close_long_event_filter.get_all_entries()
    open_short_events = open_short_event_filter.get_all_entries()
    close_short_events = close_short_event_filter.get_all_entries()

    # Calculate total events on chain
    total_events = (
        len(add_lp_events)
        + len(remove_lp_events)
        + len(withdraw_events)
        + len(open_long_events)
        + len(close_long_events)
        + len(open_short_events)
        + len(close_short_events)
    )

    return {
        "addLiquidity": add_lp_events,
        "removeLiquidity": remove_lp_events,
        "redeemWithdrawalShares": withdraw_events,
        "openLong": open_long_events,
        "closeLong": close_long_events,
        "openShort": open_short_events,
        "closeShort": close_short_events,
        "total_events": total_events,
    }

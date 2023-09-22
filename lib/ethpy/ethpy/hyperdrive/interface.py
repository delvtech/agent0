"""Helper functions for interfacing with hyperdrive"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from elfpy import time as elftime
from elfpy.markets.hyperdrive import HyperdriveMarket, HyperdriveMarketState, HyperdrivePricingModel
from eth_typing import BlockNumber
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
    """Get the hyperdrive config from a deployed hyperdrive contract. This function converts all contract returns as
    FixedPoints (i.e., contract call returned a scaled value), integer (i.e., contract call returned an unscaled value),
    or a string (i.e., contract call returned a string)

    Arguments
    ----------
    hyperdrive_contract : Contract
        The deployed hyperdrive contract instance.

    Returns
    -------
    hyperdrive_config : PoolConfig
        The hyperdrive config.
    """
    pool_config = smart_contract_read(hyperdrive_contract, "getPoolConfig")
    # convert values to FixedPoint
    non_int_keys = ["baseToken", "governance", "feeCollector", "fees"]
    pool_config: dict[str, Any] = {
        str(key): FixedPoint(scaled_value=value) for (key, value) in pool_config.items() if key not in non_int_keys
    }
    pool_config["fees"] = (FixedPoint(fee) for fee in pool_config["fees"])
    # new attributes
    pool_config["contractAddress"] = hyperdrive_contract.address
    curve_fee, flat_fee, governance_fee = pool_config["fees"]
    pool_config["curveFee"] = curve_fee
    pool_config["flatFee"] = flat_fee
    pool_config["governanceFee"] = governance_fee
    pool_config["invTimeStretch"] = FixedPoint(1) / pool_config["timeStretch"]
    return pool_config


def get_hyperdrive_pool_info(web3: Web3, hyperdrive_contract: Contract, block_number: BlockNumber) -> dict[str, Any]:
    """Return the block pool info from the Hyperdrive contract.

    Arguments
    ---------
    web3: Web3
        web3 provider object
    hyperdrive_contract: Contract
        The contract to query the pool info from
    block_number: BlockNumber
        The block number to query from the chain

    Returns
    -------
    dict
        A pool_info dict ready to be inserted into the Postgres PoolInfo schema
    """
    # get pool info from smart contract
    pool_info = smart_contract_read(hyperdrive_contract, "getPoolInfo", block_identifier=block_number)
    # convert values to fixedpoint
    pool_info: dict[str, Any] = {str(key): FixedPoint(scaled_value=value) for (key, value) in pool_info.items()}
    # get current block information & add to pool info
    current_block: BlockData = web3.eth.get_block(block_number)
    current_block_timestamp = current_block.get("timestamp")
    if current_block_timestamp is None:
        raise AssertionError("Current block has no timestamp")
    pool_info.update({"timestamp": datetime.utcfromtimestamp(current_block_timestamp)})
    pool_info.update({"blockNumber": int(block_number)})
    # add position duration to the data dict
    # TODO get position duration from existing config passed in instead of from the chain
    position_duration = smart_contract_read(hyperdrive_contract, "getPoolConfig")["positionDuration"]
    asset_id = encode_asset_id(AssetIdPrefix.WITHDRAWAL_SHARE, position_duration)
    pool_info["totalSupplyWithdrawalShares"] = smart_contract_read(
        hyperdrive_contract, "balanceOf", asset_id, hyperdrive_contract.address
    )["value"]
    return pool_info


def get_hyperdrive_checkpoint_info(
    web3: Web3, hyperdrive_contract: Contract, block_number: BlockNumber
) -> dict[str, Any]:
    """Returns the checkpoint info of Hyperdrive contract for the given block.

    Arguments
    ---------
    web3: Web3
        web3 provider object
    hyperdrive_contract: Contract
        The contract to query the pool info from
    block_number: BlockNumber
        The block number to query from the chain

    Returns
    -------
    Checkpoint
        A Checkpoint object ready to be inserted into Postgres
    """
    current_block: BlockData = web3.eth.get_block(block_number)
    current_block_timestamp = current_block.get("timestamp")
    if current_block_timestamp is None:
        raise AssertionError("Current block has no timestamp")
    checkpoint_data: dict[str, int] = smart_contract_read(hyperdrive_contract, "getCheckpoint", block_number)
    return {
        "blockNumber": int(block_number),
        "timestamp": datetime.fromtimestamp(current_block_timestamp),
        "sharePrice": FixedPoint(scaled_value=checkpoint_data["sharePrice"]),
        "longSharePrice": FixedPoint(scaled_value=checkpoint_data["longSharePrice"]),
        "longExposure": FixedPoint(scaled_value=checkpoint_data["longExposure"]),
    }


def get_hyperdrive_market(web3: Web3, hyperdrive_contract: Contract) -> HyperdriveMarket:
    """Constructs an elfpy HyperdriveMarket from the onchain hyperdrive constract state"""
    earliest_block = web3.eth.get_block("earliest")
    current_block = web3.eth.get_block("latest")
    pool_config = get_hyperdrive_pool_config(hyperdrive_contract)
    current_block_number = current_block.get("number", None)
    if current_block_number is None:
        raise AssertionError("Current block number should not be None")
    pool_info = get_hyperdrive_pool_info(web3, hyperdrive_contract, current_block_number)
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
        short_base_volume=FixedPoint(pool_info["shortBaseVolume"]),
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

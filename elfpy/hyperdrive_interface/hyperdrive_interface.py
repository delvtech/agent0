"""Helper functions for interfacing with hyperdrive"""
from __future__ import annotations

import logging
import re
import time
from datetime import datetime
from typing import Any

import requests
from eth_typing import BlockNumber
from eth_utils import address
from fixedpointmath import FixedPoint
from web3 import Web3
from web3.contract.contract import Contract
from web3.types import BlockData

from elfpy import eth, hyperdrive_interface
from elfpy import time as elftime
from elfpy.markets.hyperdrive import HyperdriveMarket, HyperdriveMarketState, HyperdrivePricingModel

from .hyperdrive_addresses import HyperdriveAddresses

RETRY_COUNT = 10


def fetch_hyperdrive_address_from_url(contracts_url: str) -> HyperdriveAddresses:
    """Fetch addresses for deployed contracts in the Hyperdrive system."""
    response = None
    for _ in range(100):
        response = requests.get(contracts_url, timeout=60)
        # Check the status code and retry the request if it fails
        if response.status_code != 200:
            logging.warning("Request failed with status code %s @ %s", response.status_code, time.ctime())
            time.sleep(10)
            continue
        # If successful, exit attempt loop
        break

    if response is None:
        raise ConnectionError("Request failed, returning status `None`")
    if response.status_code != 200:
        raise ConnectionError(f"Request failed with status code {response.status_code} @ {time.ctime()}")
    addresses_json = response.json()

    def camel_to_snake(snake_string: str) -> str:
        return re.sub(r"(?<!^)(?=[A-Z])", "_", snake_string).lower()

    addresses = HyperdriveAddresses(**{camel_to_snake(key): value for key, value in addresses_json.items()})
    return addresses


def get_hyperdrive_contract(web3: Web3, abis: dict, addresses: HyperdriveAddresses) -> Contract:
    """Get the hyperdrive contract given abis

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
    pool_info = eth.smart_contract_read(hyperdrive_contract, "getPoolInfo", block_identifier=block_number)
    # convert values to float
    pool_info: dict[str, Any] = {str(key): eth.convert_scaled_value(value) for (key, value) in pool_info.items()}
    # get current block information & add to pool info
    current_block: BlockData = web3.eth.get_block(block_number)
    current_block_timestamp = current_block.get("timestamp")
    if current_block_timestamp is None:
        raise AssertionError("Current block has no timestamp")
    pool_info.update({"timestamp": datetime.fromtimestamp(current_block_timestamp)})
    pool_info.update({"blockNumber": block_number})
    # add position duration to the data dict
    position_duration = eth.smart_contract_read(hyperdrive_contract, "getPoolConfig").get("positionDuration", None)
    if position_duration is not None:
        asset_id = hyperdrive_interface.encode_asset_id(
            hyperdrive_interface.AssetIdPrefix.WITHDRAWAL_SHARE, position_duration
        )
        pool_info["totalSupplyWithdrawalShares"] = eth.smart_contract_read(
            hyperdrive_contract, "balanceOf", asset_id, hyperdrive_contract.address
        )["value"]
    else:
        pool_info["totalSupplyWithdrawalShares"] = None
    return pool_info


def get_hyperdrive_checkpoint_info(
    web3: Web3, hyperdrive_contract: Contract, block_number: BlockNumber
) -> dict[str, Any]:
    """Returns the checkpoitn info of Hyperdrive contract for the given block.

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
    checkpoint_data: dict[str, int] = eth.smart_contract_read(hyperdrive_contract, "getCheckpoint", block_number)
    return {
        "blockNumber": int(block_number),
        "timestamp": datetime.fromtimestamp(current_block_timestamp),
        "sharePrice": eth.convert_scaled_value(checkpoint_data["sharePrice"]),
        "longSharePrice": eth.convert_scaled_value(checkpoint_data["longSharePrice"]),
        "shortBaseVolume": eth.convert_scaled_value(checkpoint_data["shortBaseVolume"]),
    }


def get_hyperdrive_config(hyperdrive_contract: Contract) -> dict[str, Any]:
    """Get the hyperdrive config from a deployed hyperdrive contract.

    Arguments
    ----------
    hyperdrive_contract : Contract
        The deployed hyperdrive contract instance.

    Returns
    -------
    hyperdrive_config : PoolConfig
        The hyperdrive config.
    """
    hyperdrive_config: dict[str, Any] = eth.smart_contract_read(hyperdrive_contract, "getPoolConfig")
    pool_config = {}
    pool_config["contractAddress"] = hyperdrive_contract.address
    pool_config["baseToken"] = hyperdrive_config.get("baseToken", None)
    pool_config["initialSharePrice"] = eth.convert_scaled_value(hyperdrive_config.get("initialSharePrice", None))
    pool_config["minimumShareReserves"] = eth.convert_scaled_value(hyperdrive_config.get("minimumShareReserves", None))
    pool_config["positionDuration"] = hyperdrive_config.get("positionDuration", None)
    pool_config["checkpointDuration"] = hyperdrive_config.get("checkpointDuration", None)
    # Ok so, the contracts store the time stretch constant in an inverted manner from the python.
    # In order to not break the world, we save the contract version as 'invTimeStretch' and invert
    # that to get the python version 'timeStretch'
    pool_config["invTimeStretch"] = hyperdrive_config.get("timeStretch", None)
    pool_config["timeStretch"] = (
        FixedPoint(1) / FixedPoint(scaled_value=hyperdrive_config.get("timeStretch", FixedPoint(1)))
    ).scaled_value
    pool_config["governance"] = hyperdrive_config.get("governance", None)
    pool_config["feeCollector"] = hyperdrive_config.get("feeCollector", None)
    curve_fee, flat_fee, governance_fee = hyperdrive_config.get("fees", (None, None, None))
    pool_config["curveFee"] = eth.convert_scaled_value(curve_fee)
    pool_config["flatFee"] = eth.convert_scaled_value(flat_fee)
    pool_config["governanceFee"] = eth.convert_scaled_value(governance_fee)
    pool_config["oracleSize"] = eth.convert_scaled_value(hyperdrive_config.get("oracleSize", None))
    pool_config["updateGap"] = hyperdrive_config.get("updateGap", None)
    return pool_config


def get_hyperdrive_market(web3: Web3, hyperdrive_contract: Contract) -> HyperdriveMarket:
    """Constructs an elfpy HyperdriveMarket from the onchain hyperdrive constract state"""
    earliest_block = web3.eth.get_block("earliest")
    current_block = web3.eth.get_block("latest")
    pool_config = get_hyperdrive_config(hyperdrive_contract)
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
        variable_apr=FixedPoint(0.01),  # TODO: insert real value
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
            time_stretch=FixedPoint(scaled_value=pool_config["timeStretch"]),
            normalizing_constant=FixedPoint(pool_config["positionDuration"]) / FixedPoint(86_400),
        ),
        block_time=elftime.BlockTime(
            _time=years_elapsed,
            _block_number=FixedPoint(current_block.get("number", None)),
            _step_size=FixedPoint(1) / FixedPoint(365),  # FIXME: Should get the anvil increment time
        ),
    )

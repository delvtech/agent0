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

from elfpy import eth
from elfpy import time as elftime
from elfpy.data.db_schema import PoolInfo, Transaction, WalletInfo
from elfpy.markets.hyperdrive import HyperdriveMarket, HyperdriveMarketState, HyperdrivePricingModel, hyperdrive_assets

from .hyperdrive_addresses import HyperdriveAddresses

RETRY_COUNT = 10


def fetch_hyperdrive_address_from_url(contracts_url: str) -> HyperdriveAddresses:
    """Fetch addresses for deployed contracts in the Hyperdrive system."""
    attempt_num = 0
    response = None
    while attempt_num < 100:
        response = requests.get(contracts_url, timeout=60)
        # Check the status code and retry the request if it fails
        if response.status_code != 200:
            logging.warning("Request failed with status code %s @ %s", response.status_code, time.ctime())
            time.sleep(10)
            continue
        attempt_num += 1
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
    """
    Returns the block pool info from the Hyperdrive contract

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
    pool_info_data_dict = eth.smart_contract_read(hyperdrive_contract, "getPoolInfo", block_identifier=block_number)
    pool_info_data_dict: dict[str, Any] = {
        str(key): eth.convert_scaled_value(value) for (key, value) in pool_info_data_dict.items()
    }
    current_block: BlockData = web3.eth.get_block(block_number)
    current_block_timestamp = current_block.get("timestamp")
    if current_block_timestamp is None:
        raise AssertionError("Current block has no timestamp")
    pool_info_data_dict.update({"timestamp": current_block_timestamp})
    pool_info_data_dict.update({"blockNumber": block_number})
    pool_info_dict = {}
    for key in PoolInfo.__annotations__.keys():
        # Required keys
        if key == "timestamp":
            pool_info_dict[key] = datetime.fromtimestamp(pool_info_data_dict[key])
        elif key == "blockNumber":
            pool_info_dict[key] = pool_info_data_dict[key]
        # Otherwise default to None if not exist
        else:
            pool_info_dict[key] = pool_info_data_dict.get(key, None)
    position_duration = eth.smart_contract_read(hyperdrive_contract, "getPoolConfig").get("positionDuration", None)
    if position_duration is not None:
        asset_id = hyperdrive_assets.encode_asset_id(
            hyperdrive_assets.AssetIdPrefix.WITHDRAWAL_SHARE, position_duration
        )
        pool_info_dict["total_supply_withdraw_shares"] = eth.smart_contract_read(
            hyperdrive_contract, "balanceOf", asset_id, hyperdrive_contract.address
        )
    else:
        pool_info_dict["total_supply_withdraw_shares"] = None
    return pool_info_dict


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
    pool_config["timeStretch"] = hyperdrive_config.get("timeStretch", None)
    if pool_config["timeStretch"]:
        pool_config["invTimeStretch"] = float(FixedPoint(1) / FixedPoint(scaled_value=pool_config["timeStretch"]))
    else:
        pool_config["invTimeStretch"] = None
    pool_config["governance"] = hyperdrive_config.get("governance", None)
    pool_config["feeCollector"] = hyperdrive_config.get("feeCollector", None)
    curve_fee, flat_fee, governance_fee = hyperdrive_config.get("fees", (None, None, None))
    pool_config["curveFee"] = eth.convert_scaled_value(curve_fee)
    pool_config["flatFee"] = eth.convert_scaled_value(flat_fee)
    pool_config["governanceFee"] = eth.convert_scaled_value(governance_fee)
    pool_config["oracleSize"] = eth.convert_scaled_value(hyperdrive_config.get("oracleSize", None))
    pool_config["updateGap"] = hyperdrive_config.get("updateGap", None)
    if pool_config["positionDuration"] is not None:
        pool_config["termLength"] = pool_config["positionDuration"] / 60 / 60 / 24  # in days
    else:
        pool_config["termLength"] = None
    return pool_config


def get_hyperdrive_market(web3: Web3, hyperdrive_contract: Contract) -> HyperdriveMarket:
    """Constructs an elfpy HyperdriveMarket from the onchain hyperdrive constract state"""
    earliest_block = web3.eth.get_block("earliest")
    current_block = web3.eth.get_block("latest")
    pool_config = get_hyperdrive_config(hyperdrive_contract)
    pool_info = get_hyperdrive_pool_info(web3, hyperdrive_contract, current_block.number)
    market_state = HyperdriveMarketState(
        base_buffer=FixedPoint(pool_info["longsOutstanding"]),
        bond_reserves=FixedPoint(pool_info["bondReserves"]),
        checkpoint_duration=FixedPoint(pool_config["checkpointDuration"]),
        curve_fee_multiple=FixedPoint(pool_config["curveFee"]),
        flat_fee_multiple=FixedPoint(pool_config["flatFee"]),
        governance_fee_multiple=FixedPoint(pool_config["governanceFee"]),
        init_share_price=FixedPoint(pool_config["initializeSharePrice"]),
        long_average_maturity_time=FixedPoint(pool_info["longAverageMaturityTime"]),
        longs_outstanding=FixedPoint(pool_info["longsOutstanding"]),
        lp_total_supply=FixedPoint(pool_info["lpTotalSupply"]),
        share_price=FixedPoint(pool_info["sharePrice"]),
        share_reserves=FixedPoint(pool_info["shareReserves"]),
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
    # FIXME: Would it be safe to assume that earliest_block.timestamp always equals zero?
    time_elapsed = (
        datetime.utcfromtimestamp(current_block.timestamp) - datetime.utcfromtimestamp(earliest_block.timestamp)
    ).total_seconds()
    years_elapsed = FixedPoint(time_elapsed) / 60 / 60 / 24 / 365
    return HyperdriveMarket(
        pricing_model=HyperdrivePricingModel(),
        market_state=market_state,
        position_duration=elftime.StretchedTime(
            days=FixedPoint(pool_config["termLength"]),
            time_stretch=FixedPoint(scaled_value=pool_config["timeStretch"]),
            normalizing_constant=FixedPoint(pool_config["termLength"]),
        ),
        block_time=elftime.BlockTime(
            _time=years_elapsed,
            _block_number=FixedPoint(current_block.number),
            _step_size=FixedPoint(1) / FixedPoint(365),
        ),
    )


def get_wallet_info(
    hyperdrive_contract: Contract,
    base_contract: Contract,
    block_number: BlockNumber,
    transactions: list[Transaction],
    poolinfo: PoolInfo,
) -> list[WalletInfo]:
    """Retrieves wallet information at a given block given a transaction
    Transactions are needed here to get
    (1) the wallet address of a transaction, and
    (2) the token id of the transaction

    Arguments
    ----------
    hyperdrive_contract : Contract
        The deployed hyperdrive contract instance.
    base_contract : Contract
        The deployed base contract instance
    block_number : BlockNumber
        The block number to query
    transactions : list[Transaction]
        The list of transactions to get events from

    Returns
    -------
    list[WalletInfo]
        The list of WalletInfo objects ready to be inserted into postgres
    """
    # pylint: disable=too-many-locals
    out_wallet_info = []
    for transaction in transactions:
        wallet_addr = transaction.event_operator
        token_id = transaction.event_id
        token_prefix = transaction.event_prefix
        token_maturity_time = transaction.event_maturity_time
        if wallet_addr is None:
            continue
        # Query and add base tokens to walletinfo
        num_base_token_scaled = None
        for _ in range(RETRY_COUNT):
            try:
                num_base_token_scaled = base_contract.functions.balanceOf(wallet_addr).call(
                    block_identifier=block_number
                )
                break
            except ValueError:
                logging.warning("Error in getting base token balance, retrying")
                time.sleep(1)
                continue
        num_base_token = eth.convert_scaled_value(num_base_token_scaled)
        if (num_base_token is not None) and (wallet_addr is not None):
            out_wallet_info.append(
                WalletInfo(
                    blockNumber=block_number,
                    walletAddress=wallet_addr,
                    baseTokenType="BASE",
                    tokenType="BASE",
                    tokenValue=num_base_token,
                )
            )
        # Query and add hyperdrive tokens to walletinfo
        if (token_id is not None) and (token_prefix is not None):
            base_token_type = hyperdrive_assets.AssetIdPrefix(token_prefix).name
            if (token_maturity_time is not None) and (token_maturity_time > 0):
                token_type = base_token_type + "-" + str(token_maturity_time)
                maturity_time = token_maturity_time
            else:
                token_type = base_token_type
                maturity_time = None
            num_custom_token_scaled = None
            for _ in range(RETRY_COUNT):
                try:
                    num_custom_token_scaled = hyperdrive_contract.functions.balanceOf(int(token_id), wallet_addr).call(
                        block_identifier=block_number
                    )
                except ValueError:
                    logging.warning("Error in getting custom token balance, retrying")
                    time.sleep(1)
                    continue
            num_custom_token = eth.convert_scaled_value(num_custom_token_scaled)
            if num_custom_token is not None:
                # Check here if token is short
                # If so, add share price from pool info to data
                share_price = None
                if (base_token_type) == "SHORT":
                    share_price = poolinfo.sharePrice
                out_wallet_info.append(
                    WalletInfo(
                        blockNumber=block_number,
                        walletAddress=wallet_addr,
                        baseTokenType=base_token_type,
                        tokenType=token_type,
                        tokenValue=num_custom_token,
                        maturityTime=maturity_time,
                        sharePrice=share_price,
                    )
                )
    return out_wallet_info

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
from web3.contract.contract import Contract
from web3 import Web3
from web3.types import BlockData

from elfpy import eth as evm
from elfpy.data.db_schema import PoolConfig, PoolInfo, Transaction, WalletInfo
from elfpy.markets.hyperdrive import hyperdrive_assets

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


def get_hyperdrive_pool_info(web3: Web3, hyperdrive_contract: Contract, block_number: BlockNumber) -> PoolInfo:
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
    PoolInfo
        A PoolInfo object ready to be inserted into Postgres
    """
    pool_info_data_dict = evm.smart_contract_read(hyperdrive_contract, "getPoolInfo", block_identifier=block_number)
    pool_info_data_dict: dict[Any, Any] = {
        key: evm.convert_scaled_value(value) for (key, value) in pool_info_data_dict.items()
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
    # Populating the dataclass from the dictionary
    pool_info = PoolInfo(**pool_info_dict)
    return pool_info


def get_hyperdrive_config(hyperdrive_contract: Contract) -> PoolConfig:
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
    hyperdrive_config: dict[str, Any] = evm.smart_contract_read(hyperdrive_contract, "getPoolConfig")
    out_config = {}
    out_config["contractAddress"] = hyperdrive_contract.address
    out_config["baseToken"] = hyperdrive_config.get("baseToken", None)
    out_config["initializeSharePrice"] = evm.convert_scaled_value(hyperdrive_config.get("initializeSharePrice", None))
    out_config["positionDuration"] = hyperdrive_config.get("positionDuration", None)
    out_config["checkpointDuration"] = hyperdrive_config.get("checkpointDuration", None)
    config_time_stretch = hyperdrive_config.get("timeStretch", None)
    if config_time_stretch:
        fp_time_stretch = FixedPoint(scaled_value=config_time_stretch)
        time_stretch = float(fp_time_stretch)
        inv_time_stretch = float(1 / fp_time_stretch)
    else:
        time_stretch = None
        inv_time_stretch = None
    out_config["timeStretch"] = time_stretch
    out_config["governance"] = hyperdrive_config.get("governance", None)
    out_config["feeCollector"] = hyperdrive_config.get("feeCollector", None)
    curve_fee, flat_fee, governance_fee = hyperdrive_config.get("fees", (None, None, None))
    out_config["curveFee"] = evm.convert_scaled_value(curve_fee)
    out_config["flatFee"] = evm.convert_scaled_value(flat_fee)
    out_config["governanceFee"] = evm.convert_scaled_value(governance_fee)
    out_config["oracleSize"] = hyperdrive_config.get("oracleSize", None)
    out_config["updateGap"] = hyperdrive_config.get("updateGap", None)
    out_config["invTimeStretch"] = inv_time_stretch
    if out_config["positionDuration"] is not None:
        term_length = out_config["positionDuration"] / 60 / 60 / 24  # in days
    else:
        term_length = None
    out_config["termLength"] = term_length
    return PoolConfig(**out_config)


def get_wallet_info(
    hyperdrive_contract: Contract,
    base_contract: Contract,
    block_number: BlockNumber,
    transactions: list[Transaction],
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
        num_base_token = evm.convert_scaled_value(num_base_token_scaled)
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
        # Handle cases where these fields don't exist
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
            num_custom_token = evm.convert_scaled_value(num_custom_token_scaled)
            if num_custom_token is not None:
                out_wallet_info.append(
                    WalletInfo(
                        blockNumber=block_number,
                        walletAddress=wallet_addr,
                        baseTokenType=base_token_type,
                        tokenType=token_type,
                        tokenValue=num_custom_token,
                        maturityTime=maturity_time,
                    )
                )
    return out_wallet_info

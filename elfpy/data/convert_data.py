"""Script to format on-chain hyperdrive pool, config, and transaction data post-processing."""
from __future__ import annotations

import logging
import time
from typing import Any

from eth_typing import BlockNumber
from fixedpointmath import FixedPoint
from hexbytes import HexBytes
from web3 import Web3
from web3.contract.contract import Contract
from web3.types import BlockData

from elfpy import eth, hyperdrive_interface
from elfpy.data import db_schema

# pylint: disable=too-many-arguments

# TODO fix too many branches by splitting out various things into functions
# pylint: disable=too-many-branches

RETRY_COUNT = 10


def _convert_scaled_value(input_val: int | None) -> float | None:
    """
    Given a scaled value int, converts it to a float, while supporting Nones

    Arguments
    ----------
    input_val: int | None
        The scaled integer value to unscale and convert to float

    Returns
    -------
    float | None
        The unscaled floating point value

    Note
    ----
    We cast to FixedPoint, then to floats to keep noise to a minimum.
    There is no loss of precision when going from Fixedpoint to float.
    Once this is fed into postgres, postgres will use the fixed-precision Numeric type.
    """
    if input_val is not None:
        return float(FixedPoint(scaled_value=input_val))
    return None


# TODO move this function to hyperdrive_interface and return a list of dictionaries
def fetch_contract_transactions_for_block(
    web3: Web3, contract: Contract, block_number: BlockNumber
) -> list[db_schema.Transaction]:
    """Fetch transactions related to the contract.

    Returns the block pool info from the Hyperdrive contract

    Arguments
    ---------
    web3: Web3
        web3 provider object
    contract: Contract
        The contract to query the pool info from
    block_number: BlockNumber
        The block number to query from the chain

    Returns
    -------
    list[Transaction]
        A list of Transaction objects ready to be inserted into Postgres
    """
    block: BlockData = web3.eth.get_block(block_number, full_transactions=True)
    transactions = block.get("transactions")
    if not transactions:
        logging.info("no transactions in block %s", block.get("number"))
        return []
    out_transactions = []
    for transaction in transactions:
        if isinstance(transaction, HexBytes):
            logging.warning("transaction HexBytes")
            continue
        if transaction.get("to") != contract.address:
            logging.warning("transaction not from contract")
            continue
        transaction_dict: dict[str, Any] = dict(transaction)
        # Convert the HexBytes fields to their hex representation
        tx_hash = transaction.get("hash") or HexBytes("")
        transaction_dict["hash"] = tx_hash.hex()
        # Decode the transaction input
        try:
            method, params = contract.decode_function_input(transaction["input"])
            transaction_dict["input"] = {"method": method.fn_name, "params": params}
        except ValueError:  # if the input is not meant for the contract, ignore it
            continue
        tx_receipt = web3.eth.get_transaction_receipt(tx_hash)
        logs = eth.get_transaction_logs(web3, contract, tx_receipt)
        receipt: dict[str, Any] = _recursive_dict_conversion(tx_receipt)  # type: ignore
        out_transactions.append(_build_hyperdrive_transaction_object(transaction_dict, logs, receipt))
    return out_transactions


def _build_hyperdrive_transaction_object(
    transaction_dict: dict[str, Any],
    logs: list[dict[str, Any]],
    receipt: dict[str, Any],
) -> db_schema.Transaction:
    """Conversion function to translate output of chain queries to the Transaction object.

    Arguments
    ----------
    transaction_dict : dict[str, Any]
        A dictionary representing the decoded transactions from the query
    logs: list[str, Any]
        A dictionary representing the decoded logs from the query
    receipt: dict[str, Any]
        A dictionary representing the transaction receipt from the query

    Returns
    -------
    Transaction
        A transaction object to be inserted into postgres
    """
    # Build output obj dict incrementally to be passed into Transaction
    # i.e., Transaction(**out_dict)
    # Base transaction fields
    out_dict: dict[str, Any] = {
        "blockNumber": transaction_dict["blockNumber"],
        "transactionIndex": transaction_dict["transactionIndex"],
        "nonce": transaction_dict["nonce"],
        "transactionHash": transaction_dict["hash"],
        "txn_to": transaction_dict["to"],
        "txn_from": transaction_dict["from"],
        "gasUsed": receipt["gasUsed"],
    }
    # Input solidity methods and parameters
    # TODO can the input field ever be empty or not exist?
    out_dict["input_method"] = transaction_dict["input"]["method"]
    input_params = transaction_dict["input"]["params"]
    out_dict["input_params_contribution"] = _convert_scaled_value(input_params.get("_contribution", None))
    out_dict["input_params_apr"] = _convert_scaled_value(input_params.get("_apr", None))
    out_dict["input_params_destination"] = input_params.get("_destination", None)
    out_dict["input_params_asUnderlying"] = input_params.get("_asUnderlying", None)
    out_dict["input_params_baseAmount"] = _convert_scaled_value(input_params.get("_baseAmount", None))
    out_dict["input_params_minOutput"] = _convert_scaled_value(input_params.get("_minOutput", None))
    out_dict["input_params_bondAmount"] = _convert_scaled_value(input_params.get("_bondAmount", None))
    out_dict["input_params_maxDeposit"] = _convert_scaled_value(input_params.get("_maxDeposit", None))
    out_dict["input_params_maturityTime"] = input_params.get("_maturityTime", None)
    out_dict["input_params_minApr"] = _convert_scaled_value(input_params.get("_minApr", None))
    out_dict["input_params_maxApr"] = _convert_scaled_value(input_params.get("_maxApr", None))
    out_dict["input_params_shares"] = _convert_scaled_value(input_params.get("_shares", None))
    # Assuming one TransferSingle per transfer
    # TODO Fix this below eventually
    # There can be two transfer singles
    # Currently grab first transfer single (e.g., Minting hyperdrive long, so address 0 to agent)
    # Eventually need grabbing second transfer single (e.g., DAI from agent to hyperdrive)
    event_logs = [log for log in logs if log["event"] == "TransferSingle"]
    if len(event_logs) == 0:
        event_args: dict[str, Any] = {}
        # Set args as None
    elif len(event_logs) == 1:
        event_args: dict[str, Any] = event_logs[0]["args"]
    else:
        logging.warning("Tranfer event contains multiple TransferSingle logs, selecting first")
        event_args: dict[str, Any] = event_logs[0]["args"]
    out_dict["event_value"] = _convert_scaled_value(event_args.get("value", None))
    out_dict["event_from"] = event_args.get("from", None)
    out_dict["event_to"] = event_args.get("to", None)
    out_dict["event_operator"] = event_args.get("operator", None)
    out_dict["event_id"] = event_args.get("id", None)
    # Decode logs here
    if out_dict["event_id"] is not None:
        event_prefix, event_maturity_time = hyperdrive_interface.decode_asset_id(out_dict["event_id"])
        out_dict["event_prefix"] = event_prefix
        out_dict["event_maturity_time"] = event_maturity_time
    transaction = db_schema.Transaction(**out_dict)
    return transaction


def _recursive_dict_conversion(obj: Any) -> Any:
    """Recursively converts a dictionary to convert objects to hex values.

    Arguments
    ---------
    obj : Any
        Could be a HexBytes, dict, or any object with the `items` attribute

    Returns
    -------
    Any
        A nested dictionary containing the decoded object values


    .. todo::
        This function needs to be better constrained & typed, or avoided all together?
    """
    if isinstance(obj, HexBytes):
        return obj.hex()
    if isinstance(obj, dict):
        return {key: _recursive_dict_conversion(value) for key, value in obj.items()}
    if hasattr(obj, "items"):  # any other type with "items" attr, e.g. TypedDict and OrderedDict
        return {key: _recursive_dict_conversion(value) for key, value in obj.items()}
    return obj


def _query_contract_for_balance(
    contract: Contract, wallet_addr: str, block_number: BlockNumber, token_id: int | None = None
) -> float | None:
    """Queries the given contract for the balance of token_id

    Arguments
    ---------
    contract : Contract
        The contract to query.
    wallet_addr: str
        The wallet address to use for query
    block_number: BlockNumber
        The block number to query
    token_id: int | None
        The given token id. If none, assuming we're calling base contract

    Returns
    -------
    float | None
        The amount token_id in wallet_addr. None if failed
    """

    num_token_scaled = None
    for _ in range(RETRY_COUNT):
        try:
            if token_id is None:
                num_token_scaled = contract.functions.balanceOf(wallet_addr).call(block_identifier=block_number)
            else:
                num_token_scaled = contract.functions.balanceOf(token_id, wallet_addr).call(
                    block_identifier=block_number
                )
            break
        except ValueError:
            logging.warning("Error in getting token balance, retrying")
            time.sleep(1)
            continue
    return _convert_scaled_value(num_token_scaled)


# TODO: move this function to hyperdrive_interface and return a list of dictionaries
def get_wallet_info(
    hyperdrive_contract: Contract,
    base_contract: Contract,
    block_number: BlockNumber,
    transactions: list[db_schema.Transaction],
    pool_info: db_schema.PoolInfo,
) -> list[db_schema.WalletInfo]:
    """Retrieve wallet information at a given block given a transaction.

    Transactions are needed here to get
    (1) the wallet address of a transaction, and
    (2) the token id of the transaction

    Arguments
    ---------
    hyperdrive_contract : Contract
        The deployed hyperdrive contract instance.
    base_contract : Contract
        The deployed base contract instance
    block_number : BlockNumber
        The block number to query
    transactions : list[db_schema.Transaction]
        The list of transactions to get events from
    pool_info : db_schema.PoolInfo
        The associated pool info, used to extract share price

    Returns
    -------
    list[db_schema.WalletInfo]
        The list of WalletInfo objects ready to be inserted into postgres
    """
    # pylint: disable=too-many-locals
    out_wallet_info = []
    for transaction in transactions:
        wallet_addr = transaction.event_operator
        if wallet_addr is None:
            continue

        # Query and add base tokens to walletinfo
        num_base_token = _query_contract_for_balance(base_contract, wallet_addr, block_number)
        if num_base_token is not None:
            out_wallet_info.append(
                db_schema.WalletInfo(
                    blockNumber=block_number,
                    walletAddress=wallet_addr,
                    baseTokenType="BASE",
                    tokenType="BASE",
                    tokenValue=num_base_token,
                )
            )

        # Query and add LP tokens to wallet info
        lp_token_prefix = int(hyperdrive_interface.AssetIdPrefix.LP)
        lp_token_id = hyperdrive_interface.encode_asset_id(lp_token_prefix, 0)
        num_lp_token = _query_contract_for_balance(hyperdrive_contract, wallet_addr, block_number, lp_token_id)
        if num_lp_token is not None:
            out_wallet_info.append(
                db_schema.WalletInfo(
                    blockNumber=block_number,
                    walletAddress=wallet_addr,
                    baseTokenType="LP",
                    tokenType="LP",
                    tokenValue=num_lp_token,
                    maturityTime=None,
                    sharePrice=None,
                )
            )

        # Query and add withdraw tokens to wallet info
        withdrawl_token_prefix = int(hyperdrive_interface.AssetIdPrefix.WITHDRAWAL_SHARE)
        withdrawl_token_id = hyperdrive_interface.encode_asset_id(withdrawl_token_prefix, 0)
        num_withdrawl_token = _query_contract_for_balance(
            hyperdrive_contract, wallet_addr, block_number, withdrawl_token_id
        )
        if num_withdrawl_token is not None:
            out_wallet_info.append(
                db_schema.WalletInfo(
                    blockNumber=block_number,
                    walletAddress=wallet_addr,
                    baseTokenType="WITHDRAWL_SHARE",
                    tokenType="WITHDRAWL_SHARE",
                    tokenValue=num_withdrawl_token,
                    maturityTime=None,
                    sharePrice=None,
                )
            )

        # Query and add shorts and/or longs if they exist in transaction
        token_id = transaction.event_id
        token_prefix = transaction.event_prefix
        token_maturity_time = transaction.event_maturity_time
        if (token_id is not None) and (token_prefix is not None):
            base_token_type = hyperdrive_interface.AssetIdPrefix(token_prefix).name
            if (base_token_type == "LONG") or (base_token_type == "SHORT"):
                token_type = base_token_type + "-" + str(token_maturity_time)
                maturity_time = token_maturity_time
                # Check here if token is short
                # If so, add share price from pool info to data
                share_price = None
                if (base_token_type) == "SHORT":
                    share_price = pool_info.sharePrice

                num_custom_token = _query_contract_for_balance(
                    hyperdrive_contract, wallet_addr, block_number, int(token_id)
                )
                if num_custom_token is not None:
                    out_wallet_info.append(
                        db_schema.WalletInfo(
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


def convert_pool_config(pool_config_dict: dict[str, Any]) -> db_schema.PoolConfig:
    """Converts a pool_config_dict from a call in hyperdrive_interface to the postgres data type

    Arguments
    ---------
    pool_config_dict: dict[str, Any]
        The dictionary returned from hyperdrive_instance.get_hyperdrive_config

    Returns
    -------
    db_schema.PoolConfig
        The db object for pool config
    """
    args_dict = {}
    for key in db_schema.PoolConfig.__annotations__:
        if key not in pool_config_dict:
            logging.warning("Missing %s from pool config", key)
            value = None
        else:
            value = pool_config_dict[key]
            if isinstance(value, FixedPoint):
                value = float(value)
        args_dict[key] = value
    pool_config = db_schema.PoolConfig(**args_dict)
    return pool_config


def convert_pool_info(pool_info_dict: dict[str, Any]) -> db_schema.PoolInfo:
    """Converts a pool_info_dict from a call in hyperdrive_interface to the postgres data type

    Arguments
    ---------
    pool_info_dict: dict[str, Any]
        The dictionary returned from hyperdrive_instance.get_hyperdrive_pool_info

    Returns
    -------
    db_schema.PoolInfo
        The db object for pool info
    """
    args_dict = {}
    for key in db_schema.PoolInfo.__annotations__:
        if key not in pool_info_dict:
            logging.warning("Missing %s from pool info", key)
            value = None
        else:
            value = pool_info_dict[key]
            if isinstance(value, FixedPoint):
                value = float(value)
        args_dict[key] = value
    block_pool_info = db_schema.PoolInfo(**args_dict)
    return block_pool_info


def convert_checkpoint_info(checkpoint_info_dict: dict[str, Any]) -> db_schema.CheckpointInfo:
    """Converts a checkpoint_info_dict from a call in hyperdrive_interface to the postgres data type

    Arguments
    ---------
    checkpoint_info_dict: dict[str, Any]
        The dictionary returned from hyperdrive_instance.get_hyperdrive_checkpoint_info

    Returns
    -------
    db_schema.CheckpointInfo
        The db object for checkpoints
    """
    args_dict = {}
    for key in db_schema.CheckpointInfo.__annotations__:
        # Keys must match
        if key not in checkpoint_info_dict:
            logging.warning("Missing %s from checkpoint info", key)
            value = None
        else:
            value = checkpoint_info_dict[key]
            if isinstance(value, FixedPoint):
                value = float(value)
        args_dict[key] = value
    block_checkpoint_info = db_schema.CheckpointInfo(**args_dict)
    return block_checkpoint_info

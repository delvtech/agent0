"""Utilities to convert hyperdrive related things to database schema objects."""

import logging
from decimal import Decimal
from typing import Any

from eth_typing import BlockNumber
from fixedpointmath import FixedPoint
from hexbytes import HexBytes
from web3 import Web3
from web3.contract.contract import Contract
from web3.types import TxData

import elf_simulations.data.hyperdrive.db_schema
from elf_simulations import eth, hyperdrive
from elf_simulations.data import db_schema
from elf_simulations.data.conversions import convert_scaled_value_to_decimal
from elf_simulations.eth.contract.token import get_token_balance


def convert_hyperdrive_transactions_for_block(
    hyperdrive_contract: Contract, transactions: list[TxData]
) -> tuple[list[db_schema.Transaction], list[src.data.hyperdrive.db_schema.WalletDelta]]:
    """Fetch transactions related to the contract.

    Arguments
    ---------
    transactions: TxData
        A list of hyperdrive transactions for a given block.

    Returns
    -------
    tuple[list[Transaction], list[WalletDelta]]
        A list of Transaction objects ready to be inserted into Postgres, and
        a list of wallet delta objects ready to be inserted into Postgres
    """

    out_transactions: list[db_schema.Transaction] = []
    out_wallet_deltas: list[src.data.hyperdrive.db_schema.WalletDelta] = []
    for transaction in transactions:
        transaction_dict = dict(transaction)
        # Convert the HexBytes fields to their hex representation
        tx_hash = transaction.get("hash") or HexBytes("")
        transaction_dict["hash"] = tx_hash.hex()
        # Decode the transaction input
        try:
            method, params = hyperdrive_contract.decode_function_input(transaction["input"])
            transaction_dict["input"] = {"method": method.fn_name, "params": params}
        except ValueError:  # if the input is not meant for the contract, ignore it
            continue
        tx_receipt = Web3.eth.get_transaction_receipt(tx_hash)
        logs = eth.get_transaction_logs(hyperdrive_contract, tx_receipt)
        receipt: dict[str, Any] = _convert_object_hexbytes_to_strings(tx_receipt)  # type: ignore
        out_transactions.append(_build_hyperdrive_transaction_object(transaction_dict, logs, receipt))
        # Build wallet deltas based on transaction logs
        out_wallet_deltas.extend(_build_wallet_deltas(logs, transaction_dict["hash"], transaction_dict["blockNumber"]))
    return out_transactions, out_wallet_deltas


def _convert_object_hexbytes_to_strings(obj: Any) -> Any:
    """Recursively converts all HexBytes in an object to strings.

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
        return {key: _convert_object_hexbytes_to_strings(value) for key, value in obj.items()}
    if hasattr(obj, "items"):  # any other type with "items" attr, e.g. TypedDict and OrderedDict
        return {key: _convert_object_hexbytes_to_strings(value) for key, value in obj.items()}
    return obj


# TODO move this function to hyperdrive_interface and return a list of dictionaries
def get_wallet_info(
    hyperdrive_contract: Contract,
    base_contract: Contract,
    block_number: BlockNumber,
    transactions: list[db_schema.Transaction],
    pool_info: src.data.hyperdrive.db_schema.PoolInfo,
) -> list[src.data.hyperdrive.db_schema.WalletInfo]:
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
        num_base_token = get_token_balance(base_contract, wallet_addr, block_number, None)
        if num_base_token is not None:
            out_wallet_info.append(
                src.data.hyperdrive.db_schema.WalletInfo(
                    blockNumber=block_number,
                    walletAddress=wallet_addr,
                    baseTokenType="BASE",
                    tokenType="BASE",
                    tokenValue=convert_scaled_value_to_decimal(num_base_token),
                )
            )

        # Query and add LP tokens to wallet info
        lp_token_prefix = hyperdrive.AssetIdPrefix.LP.value
        # LP tokens always have 0 maturity
        lp_token_id = hyperdrive.encode_asset_id(lp_token_prefix, timestamp=0)
        num_lp_token = get_token_balance(hyperdrive_contract, wallet_addr, block_number, lp_token_id)
        if num_lp_token is not None:
            out_wallet_info.append(
                src.data.hyperdrive.db_schema.WalletInfo(
                    blockNumber=block_number,
                    walletAddress=wallet_addr,
                    baseTokenType="LP",
                    tokenType="LP",
                    tokenValue=convert_scaled_value_to_decimal(num_lp_token),
                    maturityTime=None,
                    sharePrice=None,
                )
            )

        # Query and add withdraw tokens to wallet info
        withdrawal_token_prefix = hyperdrive.AssetIdPrefix.WITHDRAWAL_SHARE.value
        # Withdrawal tokens always have 0 maturity
        withdrawal_token_id = hyperdrive.encode_asset_id(withdrawal_token_prefix, timestamp=0)
        num_withdrawal_token = get_token_balance(hyperdrive_contract, wallet_addr, block_number, withdrawal_token_id)
        if num_withdrawal_token is not None:
            out_wallet_info.append(
                src.data.hyperdrive.db_schema.WalletInfo(
                    blockNumber=block_number,
                    walletAddress=wallet_addr,
                    baseTokenType="WITHDRAWAL_SHARE",
                    tokenType="WITHDRAWAL_SHARE",
                    tokenValue=convert_scaled_value_to_decimal(num_withdrawal_token),
                    maturityTime=None,
                    sharePrice=None,
                )
            )

        # Query and add shorts and/or longs if they exist in transaction
        token_id = transaction.event_id
        token_prefix = transaction.event_prefix
        token_maturity_time = transaction.event_maturity_time
        if (token_id is not None) and (token_prefix is not None):
            base_token_type = hyperdrive.AssetIdPrefix(token_prefix).name
            if base_token_type in ("LONG", "SHORT"):
                token_type = base_token_type + "-" + str(token_maturity_time)
                # Check here if token is short
                # If so, add share price from pool info to data
                share_price = None
                if (base_token_type) == "SHORT":
                    share_price = pool_info.sharePrice

                num_custom_token = get_token_balance(hyperdrive_contract, wallet_addr, block_number, int(token_id))
                if num_custom_token is not None:
                    out_wallet_info.append(
                        src.data.hyperdrive.db_schema.WalletInfo(
                            blockNumber=block_number,
                            walletAddress=wallet_addr,
                            baseTokenType=base_token_type,
                            tokenType=token_type,
                            tokenValue=convert_scaled_value_to_decimal(num_custom_token),
                            maturityTime=token_maturity_time,
                            sharePrice=share_price,
                        )
                    )
    return out_wallet_info


def convert_pool_config(pool_config_dict: dict[str, Any]) -> src.data.hyperdrive.db_schema.PoolConfig:
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
    for key in src.data.hyperdrive.db_schema.PoolConfig.__annotations__:
        if key not in pool_config_dict:
            logging.warning("Missing %s from pool config", key)
            value = None
        else:
            value = pool_config_dict[key]
            if isinstance(value, FixedPoint):
                value = Decimal(str(value))
        args_dict[key] = value
    pool_config = src.data.hyperdrive.db_schema.PoolConfig(**args_dict)
    return pool_config


def convert_pool_info(pool_info_dict: dict[str, Any]) -> src.data.hyperdrive.db_schema.PoolInfo:
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
    for key in src.data.hyperdrive.db_schema.PoolInfo.__annotations__:
        if key not in pool_info_dict:
            logging.warning("Missing %s from pool info", key)
            value = None
        else:
            value = pool_info_dict[key]
            if isinstance(value, FixedPoint):
                value = Decimal(str(value))
        args_dict[key] = value
    block_pool_info = src.data.hyperdrive.db_schema.PoolInfo(**args_dict)
    return block_pool_info


def convert_checkpoint_info(checkpoint_info_dict: dict[str, Any]) -> src.data.hyperdrive.db_schema.CheckpointInfo:
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
    for key in src.data.hyperdrive.db_schema.CheckpointInfo.__annotations__:
        # Keys must match
        if key not in checkpoint_info_dict:
            logging.warning("Missing %s from checkpoint info", key)
            value = None
        else:
            value = checkpoint_info_dict[key]
            if isinstance(value, FixedPoint):
                value = Decimal(str(value))
        args_dict[key] = value
    block_checkpoint_info = src.data.hyperdrive.db_schema.CheckpointInfo(**args_dict)
    return block_checkpoint_info


# TODO this function likely should be decoupled from postgres and added into
# hyperdrive interface returning a list of dictionaries, with a conversion function to translate
# into postgres
def _build_wallet_deltas(
    logs: list[dict], tx_hash: str, block_number
) -> list[src.data.hyperdrive.db_schema.WalletDelta]:
    """From decoded transaction logs, we look at the log that contains the trade summary

    Arguments
    ---------
    logs: list[dict]
        The list of dictionaries that was decoded from `eth.get_transaction_logs`
    tx_hash: str
        The transaction hash that resulted in this wallet delta
    block_number: BlockNumber
        The current block number of the log

    Returns
    -------
    list[Transaction]
        A list of Transaction objects ready to be inserted into Postgres
    """
    wallet_deltas = []
    # We iterate through the logs looking for specific events that describe the transaction
    # We then create a WalletDelta object with their corresponding token and base deltas for
    # each action
    for log in logs:
        if log["event"] == "AddLiquidity":
            wallet_addr = log["args"]["provider"]
            token_delta = convert_scaled_value_to_decimal(log["args"]["lpAmount"])
            base_delta = convert_scaled_value_to_decimal(-log["args"]["baseAmount"])
            wallet_deltas.extend(
                [
                    src.data.hyperdrive.db_schema.WalletDelta(
                        transactionHash=tx_hash,
                        blockNumber=block_number,
                        walletAddress=wallet_addr,
                        baseTokenType="LP",
                        tokenType="LP",
                        delta=token_delta,
                    ),
                    src.data.hyperdrive.db_schema.WalletDelta(
                        transactionHash=tx_hash,
                        blockNumber=block_number,
                        walletAddress=wallet_addr,
                        baseTokenType="BASE",
                        tokenType="BASE",
                        delta=base_delta,
                    ),
                ]
            )

        elif log["event"] == "OpenLong":
            wallet_addr = log["args"]["trader"]
            token_delta = convert_scaled_value_to_decimal(log["args"]["bondAmount"])
            base_delta = convert_scaled_value_to_decimal(-log["args"]["baseAmount"])
            maturity_time = log["args"]["maturityTime"]
            wallet_deltas.extend(
                [
                    src.data.hyperdrive.db_schema.WalletDelta(
                        transactionHash=tx_hash,
                        blockNumber=block_number,
                        walletAddress=wallet_addr,
                        baseTokenType="LONG",
                        tokenType="LONG-" + str(maturity_time),
                        delta=token_delta,
                        maturityTime=maturity_time,
                    ),
                    src.data.hyperdrive.db_schema.WalletDelta(
                        transactionHash=tx_hash,
                        blockNumber=block_number,
                        walletAddress=wallet_addr,
                        baseTokenType="BASE",
                        tokenType="BASE",
                        delta=base_delta,
                    ),
                ]
            )

        elif log["event"] == "OpenShort":
            wallet_addr = log["args"]["trader"]
            token_delta = convert_scaled_value_to_decimal(log["args"]["bondAmount"])
            base_delta = convert_scaled_value_to_decimal(-log["args"]["baseAmount"])
            maturity_time = log["args"]["maturityTime"]
            wallet_deltas.extend(
                [
                    src.data.hyperdrive.db_schema.WalletDelta(
                        transactionHash=tx_hash,
                        blockNumber=block_number,
                        walletAddress=wallet_addr,
                        baseTokenType="SHORT",
                        tokenType="SHORT-" + str(maturity_time),
                        delta=token_delta,
                        maturityTime=maturity_time,
                    ),
                    src.data.hyperdrive.db_schema.WalletDelta(
                        transactionHash=tx_hash,
                        blockNumber=block_number,
                        walletAddress=wallet_addr,
                        baseTokenType="BASE",
                        tokenType="BASE",
                        delta=base_delta,
                    ),
                ]
            )

        elif log["event"] == "RemoveLiquidity":
            wallet_addr = log["args"]["provider"]
            # Two deltas, one for withdrawal shares, one for lp tokens
            lp_delta = convert_scaled_value_to_decimal(-log["args"]["lpAmount"])
            withdrawal_delta = convert_scaled_value_to_decimal(log["args"]["withdrawalShareAmount"])
            base_delta = convert_scaled_value_to_decimal(log["args"]["baseAmount"])
            wallet_deltas.extend(
                [
                    src.data.hyperdrive.db_schema.WalletDelta(
                        transactionHash=tx_hash,
                        blockNumber=block_number,
                        walletAddress=wallet_addr,
                        baseTokenType="LP",
                        tokenType="LP",
                        delta=lp_delta,
                    ),
                    src.data.hyperdrive.db_schema.WalletDelta(
                        transactionHash=tx_hash,
                        blockNumber=block_number,
                        walletAddress=wallet_addr,
                        baseTokenType="WITHDRAWAL_SHARE",
                        tokenType="WITHDRAWAL_SHARE",
                        delta=withdrawal_delta,
                    ),
                    src.data.hyperdrive.db_schema.WalletDelta(
                        transactionHash=tx_hash,
                        blockNumber=block_number,
                        walletAddress=wallet_addr,
                        baseTokenType="BASE",
                        tokenType="BASE",
                        delta=base_delta,
                    ),
                ]
            )

        elif log["event"] == "CloseLong":
            wallet_addr = log["args"]["trader"]
            token_delta = convert_scaled_value_to_decimal(-log["args"]["bondAmount"])
            base_delta = convert_scaled_value_to_decimal(log["args"]["baseAmount"])
            maturity_time = log["args"]["maturityTime"]
            wallet_deltas.extend(
                [
                    src.data.hyperdrive.db_schema.WalletDelta(
                        transactionHash=tx_hash,
                        blockNumber=block_number,
                        walletAddress=wallet_addr,
                        baseTokenType="LONG",
                        tokenType="LONG-" + str(maturity_time),
                        delta=token_delta,
                        maturityTime=maturity_time,
                    ),
                    src.data.hyperdrive.db_schema.WalletDelta(
                        transactionHash=tx_hash,
                        blockNumber=block_number,
                        walletAddress=wallet_addr,
                        baseTokenType="BASE",
                        tokenType="BASE",
                        delta=base_delta,
                    ),
                ]
            )

        elif log["event"] == "CloseShort":
            wallet_addr = log["args"]["trader"]
            token_delta = convert_scaled_value_to_decimal(-log["args"]["bondAmount"])
            base_delta = convert_scaled_value_to_decimal(log["args"]["baseAmount"])
            maturity_time = log["args"]["maturityTime"]
            wallet_deltas.extend(
                [
                    src.data.hyperdrive.db_schema.WalletDelta(
                        transactionHash=tx_hash,
                        blockNumber=block_number,
                        walletAddress=wallet_addr,
                        baseTokenType="SHORT",
                        tokenType="SHORT-" + str(maturity_time),
                        delta=token_delta,
                        maturityTime=maturity_time,
                    ),
                    src.data.hyperdrive.db_schema.WalletDelta(
                        transactionHash=tx_hash,
                        blockNumber=block_number,
                        walletAddress=wallet_addr,
                        baseTokenType="BASE",
                        tokenType="BASE",
                        delta=base_delta,
                    ),
                ]
            )

        elif log["event"] == "RedeemWithdrawalShares":
            wallet_addr = log["args"]["provider"]
            maturity_time = None
            token_delta = convert_scaled_value_to_decimal(-log["args"]["withdrawalShareAmount"])
            base_delta = convert_scaled_value_to_decimal(log["args"]["baseAmount"])
            wallet_deltas.extend(
                [
                    src.data.hyperdrive.db_schema.WalletDelta(
                        transactionHash=tx_hash,
                        blockNumber=block_number,
                        walletAddress=wallet_addr,
                        baseTokenType="WITHDRAWAL_SHARE",
                        tokenType="WITHDRAWAL_SHARE",
                        delta=token_delta,
                        maturityTime=maturity_time,
                    ),
                    src.data.hyperdrive.db_schema.WalletDelta(
                        transactionHash=tx_hash,
                        blockNumber=block_number,
                        walletAddress=wallet_addr,
                        baseTokenType="BASE",
                        tokenType="BASE",
                        delta=base_delta,
                    ),
                ]
            )
    # Every log should have either 0 (no op), 2(two deltas per transaction), or 3(in the case of remove liquidity)
    # entries in the wallet delta
    assert len(wallet_deltas) in (0, 2, 3)
    return wallet_deltas


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
    out_dict["input_params_contribution"] = convert_scaled_value_to_decimal(input_params.get("_contribution", None))
    out_dict["input_params_apr"] = convert_scaled_value_to_decimal(input_params.get("_apr", None))
    out_dict["input_params_destination"] = input_params.get("_destination", None)
    out_dict["input_params_asUnderlying"] = input_params.get("_asUnderlying", None)
    out_dict["input_params_baseAmount"] = convert_scaled_value_to_decimal(input_params.get("_baseAmount", None))
    out_dict["input_params_minOutput"] = convert_scaled_value_to_decimal(input_params.get("_minOutput", None))
    out_dict["input_params_bondAmount"] = convert_scaled_value_to_decimal(input_params.get("_bondAmount", None))
    out_dict["input_params_maxDeposit"] = convert_scaled_value_to_decimal(input_params.get("_maxDeposit", None))
    out_dict["input_params_maturityTime"] = input_params.get("_maturityTime", None)
    out_dict["input_params_minApr"] = convert_scaled_value_to_decimal(input_params.get("_minApr", None))
    out_dict["input_params_maxApr"] = convert_scaled_value_to_decimal(input_params.get("_maxApr", None))
    out_dict["input_params_shares"] = convert_scaled_value_to_decimal(input_params.get("_shares", None))
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
    out_dict["event_value"] = _convert_object_hexbytes_to_strings(event_args.get("value", None))
    out_dict["event_from"] = event_args.get("from", None)
    out_dict["event_to"] = event_args.get("to", None)
    out_dict["event_operator"] = event_args.get("operator", None)
    out_dict["event_id"] = event_args.get("id", None)
    # Decode logs here
    if out_dict["event_id"] is not None:
        event_prefix, event_maturity_time = hyperdrive.decode_asset_id(out_dict["event_id"])
        out_dict["event_prefix"] = event_prefix
        out_dict["event_maturity_time"] = event_maturity_time
    transaction = db_schema.Transaction(**out_dict)
    return transaction

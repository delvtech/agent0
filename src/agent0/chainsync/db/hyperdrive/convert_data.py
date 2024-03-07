"""Utilities to convert hyperdrive related things to database schema objects."""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from fixedpointmath import FixedPoint
from hexbytes import HexBytes
from web3 import Web3
from web3.contract.contract import Contract
from web3.types import TxData

from agent0.ethpy.base import get_transaction_logs
from agent0.ethpy.hyperdrive import BASE_TOKEN_SYMBOL, HyperdriveAddresses, decode_asset_id
from agent0.hypertypes.utilities.conversions import camel_to_snake

from .schema import CheckpointInfo, HyperdriveTransaction, PoolConfig, PoolInfo, WalletDelta


def convert_hyperdrive_transactions_for_block(
    web3: Web3, hyperdrive_contract: Contract, transactions: list[TxData]
) -> tuple[list[HyperdriveTransaction], list[WalletDelta]]:
    """Fetch transactions related to the contract.

    Arguments
    ---------
    web3: Web3
        web3 provider object
    hyperdrive_contract: Contract
        The contract to query the transactions from
    transactions: TxData
        A list of hyperdrive transactions for a given block.

    Returns
    -------
    tuple[list[HyperdriveTransaction], list[WalletDelta]]
        A list of HyperdriveTransaction objects ready to be inserted into Postgres, and
        a list of wallet delta objects ready to be inserted into Postgres
    """
    out_transactions: list[HyperdriveTransaction] = []
    out_wallet_deltas: list[WalletDelta] = []
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
        tx_receipt = web3.eth.get_transaction_receipt(tx_hash)
        logs = get_transaction_logs(hyperdrive_contract, tx_receipt)
        receipt: dict[str, Any] = _convert_object_hexbytes_to_strings(tx_receipt)  # type: ignore
        out_transactions.append(_build_hyperdrive_transaction_object(transaction_dict, logs, receipt))
        # Build wallet deltas based on transaction logs
        out_wallet_deltas.extend(_build_wallet_deltas(logs, transaction_dict["hash"], transaction_dict["blockNumber"]))
    return out_transactions, out_wallet_deltas


def _convert_object_hexbytes_to_strings(obj: Any) -> Any:
    """Recursively converts all HexBytes in an object to strings.

    Arguments
    ---------
    obj: Any
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


def _convert_scaled_value_to_decimal(input_val: int | None) -> Decimal | None:
    """Given a scaled value int, converts it to a Decimal, while supporting Nones

    Arguments
    ---------
    input_val: int | None
        The scaled integer value to unscale and convert to Decimal

    Returns
    -------
    Decimal | None
        The unscaled Decimal value
    """
    if input_val is not None:
        # TODO add this cast within fixedpoint
        fp_val = FixedPoint(scaled_value=input_val)
        str_val = str(fp_val)
        return Decimal(str_val)
    return None


def convert_pool_config(pool_config_dict: dict[str, Any]) -> PoolConfig:
    """Converts a pool_config_dict from a call in hyperdrive_interface to the postgres data type

    Arguments
    ---------
    pool_config_dict: dict[str, Any]
        A dicitonary containing the required pool_config keys.

    Returns
    -------
    PoolConfig
        The db object for pool config
    """
    args_dict = {}
    for key in PoolConfig.__annotations__:
        if key not in pool_config_dict:
            logging.warning("Missing %s from pool config", key)
            value = None
        else:
            value = pool_config_dict[key]
            if isinstance(value, FixedPoint):
                value = Decimal(str(value))
            # Pool config contains many addresses, the DB only needs the mock hyperdrive address
            if isinstance(value, HyperdriveAddresses):
                value = value.erc4626_hyperdrive
        args_dict[camel_to_snake(key)] = value
    pool_config = PoolConfig(**args_dict)
    return pool_config


def convert_pool_info(pool_info_dict: dict[str, Any]) -> PoolInfo:
    """Converts a pool_info_dict from a call in hyperdrive interface to the postgres data type

    Arguments
    ---------
    pool_info_dict: dict[str, Any]
        The dictionary returned from hyperdrive_instance.get_hyperdrive_pool_info

    Returns
    -------
    PoolInfo
        The db object for pool info
    """
    args_dict = {}
    for key in PoolInfo.__annotations__:
        if key not in pool_info_dict:
            logging.warning("Missing %s from pool info", key)
            value = None
        else:
            value = pool_info_dict[key]
            if isinstance(value, FixedPoint):
                value = Decimal(str(value))
        args_dict[camel_to_snake(key)] = value
    block_pool_info = PoolInfo(**args_dict)
    return block_pool_info


def convert_checkpoint_info(checkpoint_info_dict: dict[str, Any]) -> CheckpointInfo:
    """Converts a checkpoint_info_dict from a call in hyperdrive interface to the postgres data type

    Arguments
    ---------
    checkpoint_info_dict: dict[str, Any]
        The dictionary returned from hyperdrive_instance.get_hyperdrive_checkpoint_info

    Returns
    -------
    CheckpointInfo
        The db object for checkpoints
    """
    args_dict = {}
    for key in CheckpointInfo.__annotations__:
        # Keys must match
        if key not in checkpoint_info_dict:
            logging.warning("Missing %s from checkpoint info", key)
            value = None
        else:
            value = checkpoint_info_dict[key]
            if isinstance(value, FixedPoint):
                value = Decimal(str(value))
        args_dict[camel_to_snake(key)] = value
    block_checkpoint_info = CheckpointInfo(**args_dict)
    return block_checkpoint_info


# TODO this function likely should be decoupled from postgres and added into
# hyperdrive interface returning a list of dictionaries, with a conversion function to translate
# into postgres
def _build_wallet_deltas(logs: list[dict], tx_hash: str, block_number) -> list[WalletDelta]:
    """From decoded transaction logs, we look at the log that contains the trade summary

    Arguments
    ---------
    logs: list[dict]
        The list of dictionaries that was decoded from `get_transaction_logs`
    tx_hash: str
        The transaction hash that resulted in this wallet delta
    block_number: BlockNumber
        The current block number of the log

    Returns
    -------
    list[HyperdriveTransaction]
        A list of HyperdriveTransaction objects ready to be inserted into Postgres
    """
    wallet_deltas = []
    # We iterate through the logs looking for specific events that describe the transaction
    # We then create a WalletDelta object with their corresponding token and base deltas for
    # each action
    for log in logs:
        if log["event"] == "AddLiquidity":
            wallet_addr = log["args"]["provider"]
            token_delta = _convert_scaled_value_to_decimal(log["args"]["lpAmount"])
            base_delta = _convert_scaled_value_to_decimal(-log["args"]["baseAmount"])
            wallet_deltas.extend(
                [
                    WalletDelta(
                        transaction_hash=tx_hash,
                        block_number=block_number,
                        wallet_address=wallet_addr,
                        base_token_type="LP",
                        token_type="LP",
                        delta=token_delta,
                    ),
                    WalletDelta(
                        transaction_hash=tx_hash,
                        block_number=block_number,
                        wallet_address=wallet_addr,
                        base_token_type=BASE_TOKEN_SYMBOL,
                        token_type=BASE_TOKEN_SYMBOL,
                        delta=base_delta,
                    ),
                ]
            )

        elif log["event"] == "OpenLong":
            wallet_addr = log["args"]["trader"]
            token_delta = _convert_scaled_value_to_decimal(log["args"]["bondAmount"])
            base_delta = _convert_scaled_value_to_decimal(-log["args"]["baseAmount"])
            maturity_time = log["args"]["maturityTime"]
            wallet_deltas.extend(
                [
                    WalletDelta(
                        transaction_hash=tx_hash,
                        block_number=block_number,
                        wallet_address=wallet_addr,
                        base_token_type="LONG",
                        token_type="LONG-" + str(maturity_time),
                        delta=token_delta,
                        maturity_time=maturity_time,
                    ),
                    WalletDelta(
                        transaction_hash=tx_hash,
                        block_number=block_number,
                        wallet_address=wallet_addr,
                        base_token_type=BASE_TOKEN_SYMBOL,
                        token_type=BASE_TOKEN_SYMBOL,
                        delta=base_delta,
                    ),
                ]
            )

        elif log["event"] == "OpenShort":
            wallet_addr = log["args"]["trader"]
            token_delta = _convert_scaled_value_to_decimal(log["args"]["bondAmount"])
            base_delta = _convert_scaled_value_to_decimal(-log["args"]["baseAmount"])
            maturity_time = log["args"]["maturityTime"]
            wallet_deltas.extend(
                [
                    WalletDelta(
                        transaction_hash=tx_hash,
                        block_number=block_number,
                        wallet_address=wallet_addr,
                        base_token_type="SHORT",
                        token_type="SHORT-" + str(maturity_time),
                        delta=token_delta,
                        maturity_time=maturity_time,
                    ),
                    WalletDelta(
                        transaction_hash=tx_hash,
                        block_number=block_number,
                        wallet_address=wallet_addr,
                        base_token_type=BASE_TOKEN_SYMBOL,
                        token_type=BASE_TOKEN_SYMBOL,
                        delta=base_delta,
                    ),
                ]
            )

        elif log["event"] == "RemoveLiquidity":
            wallet_addr = log["args"]["provider"]
            # Two deltas, one for withdrawal shares, one for lp tokens
            lp_delta = _convert_scaled_value_to_decimal(-log["args"]["lpAmount"])
            withdrawal_delta = _convert_scaled_value_to_decimal(log["args"]["withdrawalShareAmount"])
            base_delta = _convert_scaled_value_to_decimal(log["args"]["baseAmount"])
            wallet_deltas.extend(
                [
                    WalletDelta(
                        transaction_hash=tx_hash,
                        block_number=block_number,
                        wallet_address=wallet_addr,
                        base_token_type="LP",
                        token_type="LP",
                        delta=lp_delta,
                    ),
                    WalletDelta(
                        transaction_hash=tx_hash,
                        block_number=block_number,
                        wallet_address=wallet_addr,
                        base_token_type="WITHDRAWAL_SHARE",
                        token_type="WITHDRAWAL_SHARE",
                        delta=withdrawal_delta,
                    ),
                    WalletDelta(
                        transaction_hash=tx_hash,
                        block_number=block_number,
                        wallet_address=wallet_addr,
                        base_token_type=BASE_TOKEN_SYMBOL,
                        token_type=BASE_TOKEN_SYMBOL,
                        delta=base_delta,
                    ),
                ]
            )

        elif log["event"] == "CloseLong":
            wallet_addr = log["args"]["trader"]
            token_delta = _convert_scaled_value_to_decimal(-log["args"]["bondAmount"])
            base_delta = _convert_scaled_value_to_decimal(log["args"]["baseAmount"])
            maturity_time = log["args"]["maturityTime"]
            wallet_deltas.extend(
                [
                    WalletDelta(
                        transaction_hash=tx_hash,
                        block_number=block_number,
                        wallet_address=wallet_addr,
                        base_token_type="LONG",
                        token_type="LONG-" + str(maturity_time),
                        delta=token_delta,
                        maturity_time=maturity_time,
                    ),
                    WalletDelta(
                        transaction_hash=tx_hash,
                        block_number=block_number,
                        wallet_address=wallet_addr,
                        base_token_type=BASE_TOKEN_SYMBOL,
                        token_type=BASE_TOKEN_SYMBOL,
                        delta=base_delta,
                    ),
                ]
            )

        elif log["event"] == "CloseShort":
            wallet_addr = log["args"]["trader"]
            token_delta = _convert_scaled_value_to_decimal(-log["args"]["bondAmount"])
            base_delta = _convert_scaled_value_to_decimal(log["args"]["baseAmount"])
            maturity_time = log["args"]["maturityTime"]
            wallet_deltas.extend(
                [
                    WalletDelta(
                        transaction_hash=tx_hash,
                        block_number=block_number,
                        wallet_address=wallet_addr,
                        base_token_type="SHORT",
                        token_type="SHORT-" + str(maturity_time),
                        delta=token_delta,
                        maturity_time=maturity_time,
                    ),
                    WalletDelta(
                        transaction_hash=tx_hash,
                        block_number=block_number,
                        wallet_address=wallet_addr,
                        base_token_type=BASE_TOKEN_SYMBOL,
                        token_type=BASE_TOKEN_SYMBOL,
                        delta=base_delta,
                    ),
                ]
            )

        elif log["event"] == "RedeemWithdrawalShares":
            wallet_addr = log["args"]["provider"]
            maturity_time = None
            token_delta = _convert_scaled_value_to_decimal(-log["args"]["withdrawalShareAmount"])
            base_delta = _convert_scaled_value_to_decimal(log["args"]["baseAmount"])
            wallet_deltas.extend(
                [
                    WalletDelta(
                        transaction_hash=tx_hash,
                        block_number=block_number,
                        wallet_address=wallet_addr,
                        base_token_type="WITHDRAWAL_SHARE",
                        token_type="WITHDRAWAL_SHARE",
                        delta=token_delta,
                        maturity_time=maturity_time,
                    ),
                    WalletDelta(
                        transaction_hash=tx_hash,
                        block_number=block_number,
                        wallet_address=wallet_addr,
                        base_token_type=BASE_TOKEN_SYMBOL,
                        token_type=BASE_TOKEN_SYMBOL,
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
) -> HyperdriveTransaction:
    """Conversion function to translate output of chain queries to the HyperdriveTransaction object.

    Arguments
    ---------
    transaction_dict: dict[str, Any]
        A dictionary representing the decoded transactions from the query
    logs: list[str, Any]
        A dictionary representing the decoded logs from the query
    receipt: dict[str, Any]
        A dictionary representing the transaction receipt from the query

    Returns
    -------
    HyperdriveTransaction
        A transaction object to be inserted into postgres
    """
    # Build output obj dict incrementally to be passed into HyperdriveTransaction
    # i.e., HyperdriveTransaction(**out_dict)
    # Base transaction fields
    out_dict: dict[str, Any] = {
        "block_number": transaction_dict["blockNumber"],
        "transaction_index": transaction_dict["transactionIndex"],
        "nonce": transaction_dict["nonce"],
        "transaction_hash": transaction_dict["hash"],
        "txn_to": transaction_dict["to"],
        "txn_from": transaction_dict["from"],
        "gas_used": _convert_scaled_value_to_decimal(receipt["gasUsed"]),
    }
    # Input solidity methods and parameters
    # TODO can the input field ever be empty or not exist?
    out_dict["input_method"] = transaction_dict["input"]["method"]
    input_params = transaction_dict["input"]["params"]
    out_dict["input_params_contribution"] = _convert_scaled_value_to_decimal(input_params.get("_contribution", None))
    out_dict["input_params_apr"] = _convert_scaled_value_to_decimal(input_params.get("_apr", None))
    out_dict["input_params_amount"] = _convert_scaled_value_to_decimal(input_params.get("_amount", None))
    out_dict["input_params_min_output"] = _convert_scaled_value_to_decimal(input_params.get("_minOutput", None))
    out_dict["input_params_min_vault_share_price"] = _convert_scaled_value_to_decimal(
        input_params.get("_minVaultSharePrice", None)
    )
    out_dict["input_params_bond_amount"] = _convert_scaled_value_to_decimal(input_params.get("_bondAmount", None))
    out_dict["input_params_max_deposit"] = _convert_scaled_value_to_decimal(input_params.get("_maxDeposit", None))
    out_dict["input_params_maturity_time"] = input_params.get("_maturityTime", None)
    out_dict["input_params_min_lp_share_price"] = _convert_scaled_value_to_decimal(
        input_params.get("_minLpSharePrice", None)
    )
    out_dict["input_params_min_apr"] = _convert_scaled_value_to_decimal(input_params.get("_minApr", None))
    out_dict["input_params_max_apr"] = _convert_scaled_value_to_decimal(input_params.get("_maxApr", None))
    out_dict["input_params_lp_shares"] = _convert_scaled_value_to_decimal(input_params.get("_lpShares", None))
    out_dict["input_params_min_output_per_share"] = _convert_scaled_value_to_decimal(
        input_params.get("_minOutputPerShare", None)
    )
    out_dict["input_params_withdrawal_shares"] = _convert_scaled_value_to_decimal(
        input_params.get("_withdrawalShares", None)
    )

    input_params_options = input_params.get("_options", None)
    if input_params_options is not None:
        out_dict["input_params_options_destination"] = input_params_options.get("_destination", None)
        out_dict["input_params_options_as_base"] = input_params_options.get("_asBase", None)
    else:
        out_dict["input_params_options_destination"] = None
        out_dict["input_params_options_as_base"] = None

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
        event_args: dict[str, Any] = event_logs[0]["args"]
    out_dict["event_value"] = _convert_object_hexbytes_to_strings(event_args.get("value", None))
    out_dict["event_from"] = event_args.get("from", None)
    out_dict["event_to"] = event_args.get("to", None)
    out_dict["event_operator"] = event_args.get("operator", None)
    out_dict["event_id"] = event_args.get("id", None)
    # Decode logs here
    if out_dict["event_id"] is not None:
        event_prefix, event_maturity_time = decode_asset_id(out_dict["event_id"])
        out_dict["event_prefix"] = event_prefix
        out_dict["event_maturity_time"] = event_maturity_time
    transaction = HyperdriveTransaction(**out_dict)
    return transaction

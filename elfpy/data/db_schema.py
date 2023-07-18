"""Pool info struct retured from hyperdrive contract"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Union

from eth_typing import BlockNumber
from hexbytes import HexBytes
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass, mapped_column
from web3 import Web3
from web3.contract.contract import Contract, ContractEvent
from web3.types import ABIEvent, BlockData, EventData, LogReceipt, TxReceipt

from elfpy import eth
from elfpy.markets.hyperdrive import hyperdrive_assets

# Schema file doesn't need any methods in these dataclasses
# pylint: disable=too-few-public-methods

# solidity returns things in camelCase.  Keeping the formatting to indicate the source.
# pylint: disable=invalid-name

# Ideally, we'd use `Mapped[str | None]`, but this breaks using Python 3.9:
# https://github.com/sqlalchemy/sqlalchemy/issues/9110
# Currently using `Mapped[Union[str, None]]` for backwards compatibility


class Base(MappedAsDataclass, DeclarativeBase):
    """Base class to subclass from to define the schema"""


# TODO: Rename this to something more accurate to what is happening, e.g. HyperdriveTransactions
class WalletInfo(Base):
    """
    Table/dataclass schema for wallet information
    """

    __tablename__ = "walletinfo"

    # Default table primary key
    # Note that we use postgres in production and sqlite in testing, but sqlite has issues with
    # autoincrement with BigIntegers. Hence, we use the Integer variant when using sqlite in tests
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, init=False, autoincrement=True
    )

    blockNumber: Mapped[int] = mapped_column(BigInteger, ForeignKey("poolinfo.blockNumber"), index=True)
    walletAddress: Mapped[Union[str, None]] = mapped_column(String, index=True, default=None)
    # baseTokenType can be BASE, LONG, SHORT, LP, or WITHDRAWAL_SHARE
    baseTokenType: Mapped[Union[str, None]] = mapped_column(String, index=True, default=None)
    # tokenType is the baseTokenType appended with "-<maturity_time>" for LONG and SHORT
    tokenType: Mapped[Union[str, None]] = mapped_column(String, default=None)
    tokenValue: Mapped[Union[float, None]] = mapped_column(Numeric, default=None)
    maturityTime: Mapped[Union[float, None]] = mapped_column(Numeric, default=None)
    sharePrice: Mapped[Union[float, None]] = mapped_column(Numeric, default=None)


class PoolConfig(Base):
    """
    Table/dataclass schema for pool config
    """

    # pylint: disable=too-many-instance-attributes

    __tablename__ = "poolconfig"

    contractAddress: Mapped[str] = mapped_column(String, primary_key=True)
    baseToken: Mapped[Union[str, None]] = mapped_column(String, default=None)
    initialSharePrice: Mapped[Union[float, None]] = mapped_column(Numeric, default=None)
    minimumShareReserves: Mapped[Union[float, None]] = mapped_column(Numeric, default=None)
    positionDuration: Mapped[Union[int, None]] = mapped_column(Integer, default=None)
    checkpointDuration: Mapped[Union[int, None]] = mapped_column(Integer, default=None)
    timeStretch: Mapped[Union[float, None]] = mapped_column(Numeric, default=None)
    governance: Mapped[Union[str, None]] = mapped_column(String, default=None)
    feeCollector: Mapped[Union[str, None]] = mapped_column(String, default=None)
    curveFee: Mapped[Union[float, None]] = mapped_column(Numeric, default=None)
    flatFee: Mapped[Union[float, None]] = mapped_column(Numeric, default=None)
    governanceFee: Mapped[Union[float, None]] = mapped_column(Numeric, default=None)
    oracleSize: Mapped[Union[float, None]] = mapped_column(Numeric, default=None)
    updateGap: Mapped[Union[int, None]] = mapped_column(Integer, default=None)
    invTimeStretch: Mapped[Union[float, None]] = mapped_column(Numeric, default=None)
    termLength: Mapped[Union[float, None]] = mapped_column(Numeric, default=None)


class PoolInfo(Base):
    """
    Table/dataclass schema for pool info
    Mapped class that is a data class on the python side, and an declarative base on the sql side.
    """

    # pylint: disable=too-many-instance-attributes

    __tablename__ = "poolinfo"

    blockNumber: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    shareReserves: Mapped[Union[float, None]] = mapped_column(Numeric, default=None)
    bondReserves: Mapped[Union[float, None]] = mapped_column(Numeric, default=None)
    lpTotalSupply: Mapped[Union[float, None]] = mapped_column(Numeric, default=None)
    sharePrice: Mapped[Union[float, None]] = mapped_column(Numeric, default=None)
    longsOutstanding: Mapped[Union[float, None]] = mapped_column(Numeric, default=None)
    longAverageMaturityTime: Mapped[Union[float, None]] = mapped_column(Numeric, default=None)
    shortsOutstanding: Mapped[Union[float, None]] = mapped_column(Numeric, default=None)
    shortAverageMaturityTime: Mapped[Union[float, None]] = mapped_column(Numeric, default=None)
    shortBaseVolume: Mapped[Union[float, None]] = mapped_column(Numeric, default=None)
    withdrawalSharesReadyToWithdraw: Mapped[Union[float, None]] = mapped_column(Numeric, default=None)
    withdrawalSharesProceeds: Mapped[Union[float, None]] = mapped_column(Numeric, default=None)
    totalSupplyWithdrawalShares: Mapped[Union[float, None]] = mapped_column(Numeric, default=None)


class Transaction(Base):
    """
    Table/dataclass schema for Transactions
    Mapped class that is a data class on the python side, and an declarative base on the sql side.
    """

    __tablename__ = "transactions"

    # Default table primary key
    # Note that we use postgres in production and sqlite in testing, but sqlite has issues with
    # autoincrement with BigIntegers. Hence, we use the Integer variant when using sqlite in tests
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, init=False, autoincrement=True
    )

    #### Fields from base transactions ####
    blockNumber: Mapped[int] = mapped_column(BigInteger, ForeignKey("poolinfo.blockNumber"), index=True)
    transactionIndex: Mapped[Union[int, None]] = mapped_column(Integer, default=None)
    nonce: Mapped[Union[int, None]] = mapped_column(Integer, default=None)
    transactionHash: Mapped[Union[str, None]] = mapped_column(String, default=None)
    # Transaction receipt to/from
    # Almost always from wallet address to smart contract address
    txn_to: Mapped[Union[str, None]] = mapped_column(String, default=None)
    txn_from: Mapped[Union[str, None]] = mapped_column(String, default=None)
    gasUsed: Mapped[Union[int, None]] = mapped_column(Numeric, default=None)

    #### Fields from solidity function calls ####
    # These fields map solidity function calls and their corresponding arguments
    # The params list is exhaustive against all possible methods
    input_method: Mapped[Union[str, None]] = mapped_column(String, default=None)

    # Method: initialize
    input_params_contribution: Mapped[Union[float, None]] = mapped_column(Numeric, default=None)
    input_params_apr: Mapped[Union[float, None]] = mapped_column(Numeric, default=None)
    input_params_destination: Mapped[Union[str, None]] = mapped_column(String, default=None)
    input_params_asUnderlying: Mapped[Union[bool, None]] = mapped_column(Boolean, default=None)

    # Method: openLong
    input_params_baseAmount: Mapped[Union[float, None]] = mapped_column(Numeric, default=None)
    input_params_minOutput: Mapped[Union[float, None]] = mapped_column(Numeric, default=None)
    # input_params_destination
    # input_params_asUnderlying

    # Method: openShort
    input_params_bondAmount: Mapped[Union[float, None]] = mapped_column(Numeric, default=None)
    input_params_maxDeposit: Mapped[Union[float, None]] = mapped_column(Numeric, default=None)
    # input_params_destination
    # input_params_asUnderlying

    # Method: closeLong
    input_params_maturityTime: Mapped[Union[int, None]] = mapped_column(Numeric, default=None)
    # input_params_bondAmount
    # input_params_minOutput
    # input_params_destination
    # input_params_asUnderlying

    # Method: closeShort
    # input_params_maturityTime
    # input_params_bondAmount
    # input_params_minOutput
    # input_params_destination
    # input_params_asUnderlying

    # Method: addLiquidity
    # input_params_contribution
    input_params_minApr: Mapped[Union[float, None]] = mapped_column(Numeric, default=None)
    input_params_maxApr: Mapped[Union[float, None]] = mapped_column(Numeric, default=None)
    # input_params_destination
    # input_params_asUnderlying

    # Method: removeLiquidity
    input_params_shares: Mapped[Union[float, None]] = mapped_column(Numeric, default=None)
    # input_params_minOutput
    # input_params_destination
    # input_params_asUnderlying

    #### Fields from event logs ####
    # Addresses in event logs
    event_from: Mapped[Union[str, None]] = mapped_column(String, default=None)
    event_to: Mapped[Union[str, None]] = mapped_column(String, default=None)
    # args_owner
    # args_spender
    # args_id
    event_value: Mapped[Union[float, None]] = mapped_column(Numeric, default=None)
    event_operator: Mapped[Union[str, None]] = mapped_column(String, default=None)
    event_id: Mapped[Union[int, None]] = mapped_column(Numeric, default=None)
    # Fields calculated from base
    event_prefix: Mapped[Union[int, None]] = mapped_column(Integer, default=None)
    event_maturity_time: Mapped[Union[int, None]] = mapped_column(Numeric, default=None)

    # Fields not used by postprocessing

    # blockHash
    # hash
    # value
    # gasPrice
    # gas
    # v
    # r
    # s
    # type
    # accessList
    # maxPriorityFeePerGas
    # maxFeePerGas
    # chainId
    # logIndex
    # address
    # cumulativeGasUsed
    # contractAddress
    # status
    # logsBloom
    # effectiveGasPrice


class UserMap(Base):
    """
    Table/dataclass schema for pool config
    """

    __tablename__ = "usermap"

    # Default table primary key
    # Note that we use postgres in production and sqlite in testing, but sqlite has issues with
    # autoincrement with BigIntegers. Hence, we use the Integer variant when using sqlite in tests
    address: Mapped[str] = mapped_column(String, primary_key=True)
    username: Mapped[str] = mapped_column(String, index=True)


def fetch_transactions_for_block(web3: Web3, contract: Contract, block_number: BlockNumber) -> list[Transaction]:
    """
    Fetch transactions related to the contract
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
        logs = _fetch_and_decode_logs(web3, contract, tx_receipt)
        receipt: dict[str, Any] = _recursive_dict_conversion(tx_receipt)  # type: ignore
        out_transactions.append(_build_transaction_object(transaction_dict, logs, receipt))
    return out_transactions


def _build_transaction_object(
    transaction_dict: dict[str, Any],
    logs: list[dict[str, Any]],
    receipt: dict[str, Any],
) -> Transaction:
    """
    Conversion function to translate output of chain queries to the Transaction object

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
    out_dict["input_params_contribution"] = eth.convert_scaled_value(input_params.get("_contribution", None))
    out_dict["input_params_apr"] = eth.convert_scaled_value(input_params.get("_apr", None))
    out_dict["input_params_destination"] = input_params.get("_destination", None)
    out_dict["input_params_asUnderlying"] = input_params.get("_asUnderlying", None)
    out_dict["input_params_baseAmount"] = eth.convert_scaled_value(input_params.get("_baseAmount", None))
    out_dict["input_params_minOutput"] = eth.convert_scaled_value(input_params.get("_minOutput", None))
    out_dict["input_params_bondAmount"] = eth.convert_scaled_value(input_params.get("_bondAmount", None))
    out_dict["input_params_maxDeposit"] = eth.convert_scaled_value(input_params.get("_maxDeposit", None))
    out_dict["input_params_maturityTime"] = input_params.get("_maturityTime", None)
    out_dict["input_params_minApr"] = eth.convert_scaled_value(input_params.get("_minApr", None))
    out_dict["input_params_maxApr"] = eth.convert_scaled_value(input_params.get("_maxApr", None))
    out_dict["input_params_shares"] = eth.convert_scaled_value(input_params.get("_shares", None))
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
    out_dict["event_value"] = eth.convert_scaled_value(event_args.get("value", None))
    out_dict["event_from"] = event_args.get("from", None)
    out_dict["event_to"] = event_args.get("to", None)
    out_dict["event_operator"] = event_args.get("operator", None)
    out_dict["event_id"] = event_args.get("id", None)
    # Decode logs here
    if out_dict["event_id"] is not None:
        event_prefix, event_maturity_time = hyperdrive_assets.decode_asset_id(out_dict["event_id"])
        out_dict["event_prefix"] = event_prefix
        out_dict["event_maturity_time"] = event_maturity_time
    transaction = Transaction(**out_dict)
    return transaction


def _fetch_and_decode_logs(web3: Web3, contract: Contract, tx_receipt: TxReceipt) -> list[dict[Any, Any]]:
    """Decode logs from a transaction receipt"""
    logs = []
    if tx_receipt.get("logs"):
        for log in tx_receipt["logs"]:
            event_data, event = _get_event_object(web3, contract, log, tx_receipt)
            if event_data and event:
                formatted_log = dict(event_data)
                formatted_log["event"] = event.get("name")
                formatted_log["args"] = dict(event_data["args"])
                logs.append(formatted_log)
    return logs


def _get_event_object(
    web3: Web3, contract: Contract, log: LogReceipt, tx_receipt: TxReceipt
) -> tuple[EventData, ABIEvent] | tuple[None, None]:
    """Retrieves the event object and anonymous types for a  given contract and log"""
    abi_events = [abi for abi in contract.abi if abi["type"] == "event"]  # type: ignore
    for event in abi_events:  # type: ignore
        # Get event signature components
        name = event["name"]  # type: ignore
        inputs = [param["type"] for param in event["inputs"]]  # type: ignore
        inputs = ",".join(inputs)
        # Hash event signature
        event_signature_text = f"{name}({inputs})"
        event_signature_hex = web3.keccak(text=event_signature_text).hex()
        # Find match between log's event signature and ABI's event signature
        receipt_event_signature_hex = log["topics"][0].hex()
        if event_signature_hex == receipt_event_signature_hex:
            # Decode matching log
            contract_event: ContractEvent = contract.events[event["name"]]()  # type: ignore
            event_data: EventData = contract_event.process_receipt(tx_receipt)[0]
            return event_data, event  # type: ignore
    return (None, None)


def _recursive_dict_conversion(obj):
    """Recursively converts a dictionary to convert objects to hex values"""
    if isinstance(obj, HexBytes):
        return obj.hex()
    if isinstance(obj, dict):
        return {key: _recursive_dict_conversion(value) for key, value in obj.items()}
    if hasattr(obj, "items"):
        return {key: _recursive_dict_conversion(value) for key, value in obj.items()}
    return obj

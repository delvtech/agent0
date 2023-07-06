"""Pool info struct retured from hyperdrive contract"""
from __future__ import annotations

from datetime import datetime
from typing import Union

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass, mapped_column

# Schema file doesn't need any methods in these dataclasses
# pylint: disable=too-few-public-methods

# solidity returns things in camelCase.  Keeping the formatting to indicate the source.
# pylint: disable=invalid-name

# Ideally, we'd use `Mapped[str | None]`, but this breaks using Python 3.9:
# https://github.com/sqlalchemy/sqlalchemy/issues/9110
# Currently using `Mapped[Union[str, None]]` for backwards compatibility


class Base(MappedAsDataclass, DeclarativeBase):
    """Base class to subclass from to define the schema"""


class WalletInfo(Base):
    """
    Table/dataclass schema for pool config
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


class PoolConfig(Base):
    """
    Table/dataclass schema for pool config
    """

    __tablename__ = "poolconfig"

    contractAddress: Mapped[str] = mapped_column(String, primary_key=True)
    baseToken: Mapped[Union[str, None]] = mapped_column(String, default=None)
    initializeSharePrice: Mapped[Union[float, None]] = mapped_column(Numeric, default=None)
    positionDuration: Mapped[Union[int, None]] = mapped_column(Integer, default=None)
    checkpointDuration: Mapped[Union[int, None]] = mapped_column(Integer, default=None)
    timeStretch: Mapped[Union[float, None]] = mapped_column(Numeric, default=None)
    governance: Mapped[Union[str, None]] = mapped_column(String, default=None)
    feeCollector: Mapped[Union[str, None]] = mapped_column(String, default=None)
    curveFee: Mapped[Union[float, None]] = mapped_column(Numeric, default=None)
    flatFee: Mapped[Union[float, None]] = mapped_column(Numeric, default=None)
    governanceFee: Mapped[Union[float, None]] = mapped_column(Numeric, default=None)
    oracleSize: Mapped[Union[int, None]] = mapped_column(Integer, default=None)
    updateGap: Mapped[Union[int, None]] = mapped_column(Integer, default=None)
    invTimeStretch: Mapped[Union[float, None]] = mapped_column(Numeric, default=None)
    termLength: Mapped[Union[float, None]] = mapped_column(Numeric, default=None)


class PoolInfo(Base):
    """
    Table/dataclass schema for pool info
    Mapped class that is a data class on the python side, and an declarative base on the sql side.
    """

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

"""Database Schemas for the Hyperdrive Contract."""

from datetime import datetime
from decimal import Decimal
from typing import Union

from chainsync.base.db_schema import Base
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

# pylint: disable=invalid-name


class PoolConfig(Base):
    """Table/dataclass schema for pool config."""

    __tablename__ = "poolconfig"

    contractAddress: Mapped[str] = mapped_column(String, primary_key=True)
    baseToken: Mapped[Union[str, None]] = mapped_column(String, default=None)
    initialSharePrice: Mapped[Union[Decimal, None]] = mapped_column(Numeric, default=None)
    minimumShareReserves: Mapped[Union[Decimal, None]] = mapped_column(Numeric, default=None)
    positionDuration: Mapped[Union[int, None]] = mapped_column(Integer, default=None)
    checkpointDuration: Mapped[Union[int, None]] = mapped_column(Integer, default=None)
    timeStretch: Mapped[Union[Decimal, None]] = mapped_column(Numeric, default=None)
    governance: Mapped[Union[str, None]] = mapped_column(String, default=None)
    feeCollector: Mapped[Union[str, None]] = mapped_column(String, default=None)
    curveFee: Mapped[Union[Decimal, None]] = mapped_column(Numeric, default=None)
    flatFee: Mapped[Union[Decimal, None]] = mapped_column(Numeric, default=None)
    governanceFee: Mapped[Union[Decimal, None]] = mapped_column(Numeric, default=None)
    oracleSize: Mapped[Union[Decimal, None]] = mapped_column(Numeric, default=None)
    updateGap: Mapped[Union[int, None]] = mapped_column(Integer, default=None)
    invTimeStretch: Mapped[Union[Decimal, None]] = mapped_column(Numeric, default=None)
    termLength: Mapped[Union[Decimal, None]] = mapped_column(Numeric, default=None)


class CheckpointInfo(Base):
    """Table/dataclass schema for checkpoint information"""

    __tablename__ = "checkpointinfo"

    blockNumber: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    sharePrice: Mapped[Union[Decimal, None]] = mapped_column(Numeric, default=None)
    longSharePrice: Mapped[Union[Decimal, None]] = mapped_column(Numeric, default=None)
    shortBaseVolume: Mapped[Union[Decimal, None]] = mapped_column(Numeric, default=None)


class PoolInfo(Base):
    """Table/dataclass schema for pool info.

    Mapped class that is a data class on the python side, and an declarative base on the sql side.
    """

    __tablename__ = "poolinfo"

    blockNumber: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    shareReserves: Mapped[Union[Decimal, None]] = mapped_column(Numeric, default=None)
    bondReserves: Mapped[Union[Decimal, None]] = mapped_column(Numeric, default=None)
    lpTotalSupply: Mapped[Union[Decimal, None]] = mapped_column(Numeric, default=None)
    sharePrice: Mapped[Union[Decimal, None]] = mapped_column(Numeric, default=None)
    lpSharePrice: Mapped[Union[Decimal, None]] = mapped_column(Numeric, default=None)
    longsOutstanding: Mapped[Union[Decimal, None]] = mapped_column(Numeric, default=None)
    longAverageMaturityTime: Mapped[Union[Decimal, None]] = mapped_column(Numeric, default=None)
    shortsOutstanding: Mapped[Union[Decimal, None]] = mapped_column(Numeric, default=None)
    shortAverageMaturityTime: Mapped[Union[Decimal, None]] = mapped_column(Numeric, default=None)
    shortBaseVolume: Mapped[Union[Decimal, None]] = mapped_column(Numeric, default=None)
    withdrawalSharesReadyToWithdraw: Mapped[Union[Decimal, None]] = mapped_column(Numeric, default=None)
    withdrawalSharesProceeds: Mapped[Union[Decimal, None]] = mapped_column(Numeric, default=None)
    totalSupplyWithdrawalShares: Mapped[Union[Decimal, None]] = mapped_column(Numeric, default=None)


# TODO: Rename this to something more accurate to what is happening, e.g. HyperdriveTransactions
class WalletInfo(Base):
    """Table/dataclass schema for wallet information."""

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
    tokenValue: Mapped[Union[Decimal, None]] = mapped_column(Numeric, default=None)
    maturityTime: Mapped[Union[int, None]] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), default=None)
    sharePrice: Mapped[Union[Decimal, None]] = mapped_column(Numeric, default=None)


# TODO: either make a more general TokenDelta, or rename this to HyperdriveDelta
class WalletDelta(Base):
    """Table/dataclass schema for wallet information."""

    __tablename__ = "walletdelta"

    # Default table primary key
    # Note that we use postgres in production and sqlite in testing, but sqlite has issues with
    # autoincrement with BigIntegers. Hence, we use the Integer variant when using sqlite in tests
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, init=False, autoincrement=True
    )
    transactionHash: Mapped[str] = mapped_column(String, ForeignKey("transactions.transactionHash"), index=True)
    blockNumber: Mapped[int] = mapped_column(BigInteger, ForeignKey("poolinfo.blockNumber"), index=True)
    walletAddress: Mapped[Union[str, None]] = mapped_column(String, index=True, default=None)
    # baseTokenType can be BASE, LONG, SHORT, LP, or WITHDRAWAL_SHARE
    baseTokenType: Mapped[Union[str, None]] = mapped_column(String, index=True, default=None)
    # tokenType is the baseTokenType appended with "-<maturity_time>" for LONG and SHORT
    tokenType: Mapped[Union[str, None]] = mapped_column(String, default=None)
    delta: Mapped[Union[Decimal, None]] = mapped_column(Numeric, default=None)
    maturityTime: Mapped[Union[Decimal, None]] = mapped_column(Numeric, default=None)


class HyperdriveTransaction(Base):
    """Table/dataclass schema for Transactions.

    Mapped class that is a data class on the python side, and an declarative base on the sql side.
    """

    __tablename__ = "transactions"

    # Default table primary key
    # Note that we use postgres in production and sqlite in testing, but sqlite has issues with
    # autoincrement with BigIntegers. Hence, we use the Integer variant when using sqlite in tests
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, init=False, autoincrement=True
    )
    transactionHash: Mapped[str] = mapped_column(String, index=True, unique=True)

    #### Fields from base transactions ####
    blockNumber: Mapped[int] = mapped_column(BigInteger, ForeignKey("poolinfo.blockNumber"), index=True)
    transactionIndex: Mapped[Union[int, None]] = mapped_column(Integer, default=None)
    nonce: Mapped[Union[int, None]] = mapped_column(Integer, default=None)
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
    input_params_contribution: Mapped[Union[Decimal, None]] = mapped_column(Numeric, default=None)
    input_params_apr: Mapped[Union[Decimal, None]] = mapped_column(Numeric, default=None)
    input_params_destination: Mapped[Union[str, None]] = mapped_column(String, default=None)
    input_params_asUnderlying: Mapped[Union[bool, None]] = mapped_column(Boolean, default=None)

    # Method: openLong
    input_params_baseAmount: Mapped[Union[Decimal, None]] = mapped_column(Numeric, default=None)
    input_params_minOutput: Mapped[Union[Decimal, None]] = mapped_column(Numeric, default=None)
    # input_params_destination
    # input_params_asUnderlying

    # Method: openShort
    input_params_bondAmount: Mapped[Union[Decimal, None]] = mapped_column(Numeric, default=None)
    input_params_maxDeposit: Mapped[Union[Decimal, None]] = mapped_column(Numeric, default=None)
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
    input_params_minApr: Mapped[Union[Decimal, None]] = mapped_column(Numeric, default=None)
    input_params_maxApr: Mapped[Union[Decimal, None]] = mapped_column(Numeric, default=None)
    # input_params_destination
    # input_params_asUnderlying

    # Method: removeLiquidity
    input_params_shares: Mapped[Union[Decimal, None]] = mapped_column(Numeric, default=None)
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
    event_value: Mapped[Union[Decimal, None]] = mapped_column(Numeric, default=None)
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

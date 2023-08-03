"""Database Schemas for the Hyperdrive Contract."""

from datetime import datetime
from decimal import Decimal
from typing import Union

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from src.data.db_schema import Base


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

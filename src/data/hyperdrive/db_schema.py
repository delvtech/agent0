from datetime import datetime
from decimal import Decimal
from typing import Union

from sqlalchemy import BigInteger, DateTime, Integer, Numeric, String
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

"""Pool info struct retured from hyperdrive contract"""
from __future__ import annotations

from datetime import datetime

from fixedpointmath import FixedPoint
from sqlalchemy import BIGINT, DateTime, Numeric
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass, mapped_column, registry


class Base(MappedAsDataclass, DeclarativeBase):
    """Base class to subclass from to define the schema"""


class PoolInfo(Base):
    """Mapped class that is a data class on the python side, and an declarative base on the sql side"""

    # solidity returns things in camelCase.  Keeping the formatting to indicate the source.

    __tablename__ = "poolinfo"

    blockNumber: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    shareReserves: Mapped[float | None] = mapped_column(Numeric, default=None)
    bondReserves: Mapped[float | None] = mapped_column(Numeric, default=None)
    lpTotalSupply: Mapped[float | None] = mapped_column(Numeric, default=None)
    sharePrice: Mapped[float | None] = mapped_column(Numeric, default=None)
    longsOutstanding: Mapped[float | None] = mapped_column(Numeric, default=None)
    longAverageMaturityTime: Mapped[float | None] = mapped_column(Numeric, default=None)
    shortsOutstanding: Mapped[float | None] = mapped_column(Numeric, default=None)
    shortAverageMaturityTime: Mapped[float | None] = mapped_column(Numeric, default=None)
    shortBaseVolume: Mapped[float | None] = mapped_column(Numeric, default=None)
    withdrawalSharesReadyToWithdraw: Mapped[float | None] = mapped_column(Numeric, default=None)
    withdrawalSharesProceeds: Mapped[float | None] = mapped_column(Numeric, default=None)


# @dataclass
# class PoolInfo:
#    """Pool info struct returned from hyperdrive contract"""
#
#    # pylint: disable=invalid-name
#    # this is what is returned from the contract, no choice here
#    # pylint: disable=too-many-instance-attributes

"""Pool info struct retured from hyperdrive contract"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BIGINT, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass, mapped_column


class Base(MappedAsDataclass, DeclarativeBase):
    """Base class to subclass from to define the schema"""


class PoolInfo(Base):
    """
    Table/dataclass schema for pool info
    Mapped class that is a data class on the python side, and an declarative base on the sql side.
    """

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


class Transaction(Base):
    """
    Table/dataclass schema for Transactions
    Mapped class that is a data class on the python side, and an declarative base on the sql side.
    """

    __tablename__ = "transactions"

    # Fields used by postprocessing
    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, init=False, autoincrement=True)
    blockNumber: Mapped[int] = mapped_column(BIGINT, ForeignKey("poolinfo.blockNumber"))
    transactionIndex: Mapped[int | None] = mapped_column(Integer, default=None)
    input_method: Mapped[str | None] = mapped_column(String, default=None)
    args_value: Mapped[float | None] = mapped_column(Numeric, default=None)
    args_operator: Mapped[str | None] = mapped_column(String, default=None)
    args_id: Mapped[int | None] = mapped_column(Numeric, default=None)
    args_event: Mapped[str | None] = mapped_column(String, default=None)

    # Fields calculated from base
    args_prefix: Mapped[int | None] = mapped_column(Integer, default=None)
    args_maturity_time: Mapped[int | None] = mapped_column(Numeric, default=None)

    ## Fields not used by postprocessing
    # blockHash
    # args_from
    # args_to
    # hash
    # nonce
    # from
    # to
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
    # input_params_baseAmount
    # input_params_minOutput
    # input_params_destination
    # input_params_asUnderlying
    # input_params_contribution
    # input_params_minApr
    # input_params_maxApr
    # input_params_maturityTime
    # input_params_bondAmount
    # input_params_maxDeposit
    # logIndex
    # transactionHash
    # address
    # args_owner
    # args_spender
    # args_id
    # cumulativeGasUsed
    # gasUsed
    # contractAddress
    # status
    # logsBloom
    # effectiveGasPrice

"""Pool info struct retured from hyperdrive contract"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass, mapped_column

# Schema file doesn't need any methods in these dataclasses
# pylint: disable=too-few-public-methods

# solidity returns things in camelCase.  Keeping the formatting to indicate the source.
# pylint: disable=invalid-name


class Base(MappedAsDataclass, DeclarativeBase):
    """Base class to subclass from to define the schema"""


class PoolInfo(Base):
    """
    Table/dataclass schema for pool info
    Mapped class that is a data class on the python side, and an declarative base on the sql side.
    """

    __tablename__ = "poolinfo"

    blockNumber: Mapped[int] = mapped_column(BigInteger, primary_key=True)
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

    # Default table primary key
    # Note that we use postgres in production and sqlite in testing, but sqlite has issues with
    # autoincrement with BigIntegers. Hence, we use the Integer variant when using sqlite in tests
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, init=False, autoincrement=True
    )

    #### Fields from base transactions ####
    blockNumber: Mapped[int] = mapped_column(BigInteger, ForeignKey("poolinfo.blockNumber"))
    transactionIndex: Mapped[int | None] = mapped_column(Integer, default=None)
    nonce: Mapped[int | None] = mapped_column(Integer, default=None)
    transactionHash: Mapped[str | None] = mapped_column(String, default=None)
    # Transaction receipt to/from
    # Almost always from wallet address to smart contract address
    txn_to: Mapped[str | None] = mapped_column(String, default=None)
    txn_from: Mapped[str | None] = mapped_column(String, default=None)
    gasUsed: Mapped[int | None] = mapped_column(Numeric, default=None)

    #### Fields from solidity function calls ####
    # These fields map solidity function calls and their corresponding arguments
    # The params list is exhaustive against all possible methods
    input_method: Mapped[str | None] = mapped_column(String, default=None)

    # Method: initialize
    input_params_contribution: Mapped[float | None] = mapped_column(Numeric, default=None)
    input_params_apr: Mapped[float | None] = mapped_column(Numeric, default=None)
    input_params_destination: Mapped[str | None] = mapped_column(String, default=None)
    input_params_asUnderlying: Mapped[bool | None] = mapped_column(Boolean, default=None)

    # Method: openLong
    input_params_baseAmount: Mapped[float | None] = mapped_column(Numeric, default=None)
    input_params_minOutput: Mapped[float | None] = mapped_column(Numeric, default=None)
    # input_params_destination
    # input_params_asUnderlying

    # Method: openShort
    input_params_bondAmount: Mapped[float | None] = mapped_column(Numeric, default=None)
    input_params_maxDeposit: Mapped[float | None] = mapped_column(Numeric, default=None)
    # input_params_destination
    # input_params_asUnderlying

    # Method: closeLong
    input_params_maturityTime: Mapped[int | None] = mapped_column(Numeric, default=None)
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
    input_params_minApr: Mapped[float | None] = mapped_column(Numeric, default=None)
    input_params_maxApr: Mapped[float | None] = mapped_column(Numeric, default=None)
    # input_params_destination
    # input_params_asUnderlying

    # Method: removeLiquidity
    input_params_shares: Mapped[float | None] = mapped_column(Numeric, default=None)
    # input_params_minOutput
    # input_params_destination
    # input_params_asUnderlying

    #### Fields from event logs ####
    # Addresses in event logs
    event_from: Mapped[str | None] = mapped_column(String, default=None)
    event_to: Mapped[str | None] = mapped_column(String, default=None)
    # args_owner
    # args_spender
    # args_id
    event_value: Mapped[float | None] = mapped_column(Numeric, default=None)
    event_operator: Mapped[str | None] = mapped_column(String, default=None)
    event_id: Mapped[int | None] = mapped_column(Numeric, default=None)
    # Fields calculated from base
    event_prefix: Mapped[int | None] = mapped_column(Integer, default=None)
    event_maturity_time: Mapped[int | None] = mapped_column(Numeric, default=None)

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

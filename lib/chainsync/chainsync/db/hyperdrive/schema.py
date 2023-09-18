"""Database Schemas for the Hyperdrive Contract."""

from datetime import datetime
from decimal import Decimal
from typing import Union

from chainsync.db.base import Base
from sqlalchemy import ARRAY, BigInteger, Boolean, DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

# pylint: disable=invalid-name

# Postgres numeric type that matches fixedpoint
# Precision here indicates the total number of significant digits to store,
# while scale indicates the number of digits to the right of the decimal
# The high precision doesn't actually allocate memory in postgres, as numeric is variable size
# https://stackoverflow.com/questions/40686571/performance-of-numeric-type-with-high-precisions-and-scales-in-postgresql
FIXED_NUMERIC = Numeric(precision=1000, scale=18)


## Base schemas for raw data


class PoolConfig(Base):
    """Table/dataclass schema for pool config."""

    __tablename__ = "pool_config"

    contractAddress: Mapped[str] = mapped_column(String, primary_key=True)
    baseToken: Mapped[Union[str, None]] = mapped_column(String, default=None)
    initialSharePrice: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    minimumShareReserves: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    positionDuration: Mapped[Union[int, None]] = mapped_column(Integer, default=None)
    checkpointDuration: Mapped[Union[int, None]] = mapped_column(Integer, default=None)
    timeStretch: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    governance: Mapped[Union[str, None]] = mapped_column(String, default=None)
    feeCollector: Mapped[Union[str, None]] = mapped_column(String, default=None)
    curveFee: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    flatFee: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    governanceFee: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    oracleSize: Mapped[Union[int, None]] = mapped_column(Integer, default=None)
    updateGap: Mapped[Union[int, None]] = mapped_column(Integer, default=None)
    invTimeStretch: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    updateGap: Mapped[Union[int, None]] = mapped_column(Integer, default=None)


class CheckpointInfo(Base):
    """Table/dataclass schema for checkpoint information"""

    __tablename__ = "checkpoint_info"

    blockNumber: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    sharePrice: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    longSharePrice: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    longExposure: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)


class PoolInfo(Base):
    """Table/dataclass schema for pool info.

    Mapped class that is a data class on the python side, and an declarative base on the sql side.
    """

    __tablename__ = "pool_info"

    blockNumber: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    shareReserves: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    bondReserves: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    lpTotalSupply: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    sharePrice: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    lpSharePrice: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    longsOutstanding: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    longAverageMaturityTime: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    shortsOutstanding: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    shortAverageMaturityTime: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    shortBaseVolume: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    withdrawalSharesReadyToWithdraw: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    withdrawalSharesProceeds: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    totalSupplyWithdrawalShares: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)


# TODO: Rename this to something more accurate to what is happening, e.g. HyperdriveTransactions
# TODO deprecate this schema
class WalletInfoFromChain(Base):
    """Table/dataclass schema for wallet information."""

    __tablename__ = "wallet_info_from_chain"

    # Default table primary key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, init=False, autoincrement=True)
    blockNumber: Mapped[int] = mapped_column(BigInteger, index=True)
    walletAddress: Mapped[Union[str, None]] = mapped_column(String, index=True, default=None)
    # baseTokenType can be BASE, LONG, SHORT, LP, or WITHDRAWAL_SHARE
    baseTokenType: Mapped[Union[str, None]] = mapped_column(String, index=True, default=None)
    # tokenType is the baseTokenType appended with "-<maturity_time>" for LONG and SHORT
    tokenType: Mapped[Union[str, None]] = mapped_column(String, default=None)
    tokenValue: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    # While time here is in epoch seconds, we use Numeric to allow for (1) lossless storage and (2) allow for NaNs
    maturityTime: Mapped[Union[int, None]] = mapped_column(Numeric, default=None)
    sharePrice: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)


# TODO: either make a more general TokenDelta, or rename this to HyperdriveDelta
class WalletDelta(Base):
    """Table/dataclass schema for wallet deltas."""

    __tablename__ = "wallet_delta"

    # Default table primary key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, init=False, autoincrement=True)
    transactionHash: Mapped[str] = mapped_column(String, index=True)
    blockNumber: Mapped[int] = mapped_column(BigInteger, index=True)
    walletAddress: Mapped[Union[str, None]] = mapped_column(String, index=True, default=None)
    # baseTokenType can be BASE, LONG, SHORT, LP, or WITHDRAWAL_SHARE
    baseTokenType: Mapped[Union[str, None]] = mapped_column(String, index=True, default=None)
    # tokenType is the baseTokenType appended with "-<maturity_time>" for LONG and SHORT
    tokenType: Mapped[Union[str, None]] = mapped_column(String, default=None)
    delta: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    # While time here is in epoch seconds, we use Numeric to allow for (1) lossless storage and (2) allow for NaNs
    maturityTime: Mapped[Union[int, None]] = mapped_column(Numeric, default=None)


class HyperdriveTransaction(Base):
    """Table/dataclass schema for Transactions.

    Mapped class that is a data class on the python side, and an declarative base on the sql side.
    """

    __tablename__ = "transactions"

    # Default table primary key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, init=False, autoincrement=True)
    transactionHash: Mapped[str] = mapped_column(String, index=True, unique=True)

    #### Fields from base transactions ####
    blockNumber: Mapped[int] = mapped_column(BigInteger, index=True)
    transactionIndex: Mapped[Union[int, None]] = mapped_column(Integer, default=None)
    nonce: Mapped[Union[int, None]] = mapped_column(Integer, default=None)
    # Transaction receipt to/from
    # Almost always from wallet address to smart contract address
    txn_to: Mapped[Union[str, None]] = mapped_column(String, default=None)
    txn_from: Mapped[Union[str, None]] = mapped_column(String, default=None)
    gasUsed: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)

    #### Fields from solidity function calls ####
    # These fields map solidity function calls and their corresponding arguments
    # The params list is exhaustive against all possible methods
    input_method: Mapped[Union[str, None]] = mapped_column(String, default=None)

    # Method: initialize
    input_params_contribution: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    input_params_apr: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    input_params_destination: Mapped[Union[str, None]] = mapped_column(String, default=None)
    input_params_asUnderlying: Mapped[Union[bool, None]] = mapped_column(Boolean, default=None)

    # Method: openLong
    input_params_baseAmount: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    input_params_minOutput: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    # input_params_destination
    # input_params_asUnderlying

    # Method: openShort
    input_params_bondAmount: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    input_params_maxDeposit: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    # input_params_destination
    # input_params_asUnderlying

    # Method: closeLong
    input_params_maturityTime: Mapped[Union[int, None]] = mapped_column(BigInteger, default=None)
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
    input_params_minApr: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    input_params_maxApr: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    # input_params_destination
    # input_params_asUnderlying

    # Method: removeLiquidity
    input_params_shares: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
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
    event_value: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    event_operator: Mapped[Union[str, None]] = mapped_column(String, default=None)
    event_id: Mapped[Union[int, None]] = mapped_column(
        Numeric, default=None
    )  # Integer too small here to store event_id, so we use Numeric instead
    # Fields calculated from base
    event_prefix: Mapped[Union[int, None]] = mapped_column(Integer, default=None)
    event_maturity_time: Mapped[Union[int, None]] = mapped_column(BigInteger, default=None)

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


## Analysis schemas


class PoolAnalysis(Base):
    """Table/dataclass schema for pool info analysis.

    Mapped class that is a data class on the python side, and an declarative base on the sql side.
    """

    __tablename__ = "pool_analysis"

    blockNumber: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    spot_price: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    fixed_rate: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    base_buffer: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)


class CurrentWallet(Base):
    """Table/dataclass schema for current wallet positions."""

    __tablename__ = "current_wallet"

    # Default table primary key
    id: Mapped[int] = mapped_column(BigInteger(), primary_key=True, init=False, autoincrement=True)
    blockNumber: Mapped[int] = mapped_column(BigInteger, index=True)
    walletAddress: Mapped[Union[str, None]] = mapped_column(String, index=True, default=None)
    # baseTokenType can be BASE, LONG, SHORT, LP, or WITHDRAWAL_SHARE
    baseTokenType: Mapped[Union[str, None]] = mapped_column(String, index=True, default=None)
    # tokenType is the baseTokenType appended with "-<maturity_time>" for LONG and SHORT
    tokenType: Mapped[Union[str, None]] = mapped_column(String, default=None)
    value: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    # While time here is in epoch seconds, we use Numeric to allow for (1) lossless storage and (2) allow for NaNs
    maturityTime: Mapped[Union[int, None]] = mapped_column(Numeric, default=None)


class Ticker(Base):
    """Table/dataclass schema for the live ticker.

    Mapped class that is a data class on the python side, and an declarative base on the sql side.
    """

    __tablename__ = "ticker"

    id: Mapped[int] = mapped_column(BigInteger(), primary_key=True, init=False, autoincrement=True)
    blockNumber: Mapped[int] = mapped_column(BigInteger, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    walletAddress: Mapped[Union[str, None]] = mapped_column(String, index=True, default=None)
    trade_type: Mapped[Union[str, None]] = mapped_column(String, default=None)
    token_diffs: Mapped[Union[list[str], None]] = mapped_column(ARRAY(String), default=None)


class WalletPNL(Base):
    """Table/dataclass schema for pnl data
    This table differs from CurrentWallet by (1) including the PNL, and (2) contains all wallet positions
    for a given block.

    Mapped class that is a data class on the python side, and an declarative base on the sql side.
    """

    __tablename__ = "wallet_pnl"

    # Default table primary key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, init=False, autoincrement=True)
    blockNumber: Mapped[int] = mapped_column(BigInteger, index=True)
    walletAddress: Mapped[Union[str, None]] = mapped_column(String, index=True, default=None)
    # baseTokenType can be BASE, LONG, SHORT, LP, or WITHDRAWAL_SHARE
    baseTokenType: Mapped[Union[str, None]] = mapped_column(String, index=True, default=None)
    # tokenType is the baseTokenType appended with "-<maturity_time>" for LONG and SHORT
    tokenType: Mapped[Union[str, None]] = mapped_column(String, default=None)
    value: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    # While time here is in epoch seconds, we use Numeric to allow for (1) lossless storage and (2) allow for NaNs
    maturityTime: Mapped[Union[int, None]] = mapped_column(Numeric, default=None)
    latest_block_update: Mapped[Union[int, None]] = mapped_column(BigInteger, default=None)
    pnl: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)

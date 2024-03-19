"""Database Schemas for the Hyperdrive Contract."""

from datetime import datetime
from decimal import Decimal
from typing import Union

from sqlalchemy import ARRAY, BigInteger, Boolean, DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from agent0.chainsync.db.base import Base

# pylint: disable=invalid-name

# Postgres numeric type that matches fixedpoint
# Precision here indicates the total number of significant digits to store,
# while scale indicates the number of digits to the right of the decimal
# The high precision doesn't actually allocate memory in postgres, as numeric is variable size
# https://stackoverflow.com/questions/40686571/performance-of-numeric-type-with-high-precisions-and-scales-in-postgresql
FIXED_NUMERIC = Numeric(precision=1000, scale=18)


## Base schemas for raw data
# TODO add column for timestamp in seconds in db


class PoolConfig(Base):
    """Table/dataclass schema for pool config."""

    __tablename__ = "pool_config"

    contract_address: Mapped[str] = mapped_column(String, primary_key=True)
    base_token: Mapped[Union[str, None]] = mapped_column(String, default=None)
    linker_factory: Mapped[Union[str, None]] = mapped_column(String, default=None)
    # Ignoring linker_code_hash field
    initial_vault_share_price: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    minimum_share_reserves: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    minimum_transaction_amount: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    position_duration: Mapped[Union[int, None]] = mapped_column(Integer, default=None)
    checkpoint_duration: Mapped[Union[int, None]] = mapped_column(Integer, default=None)
    time_stretch: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    governance: Mapped[Union[str, None]] = mapped_column(String, default=None)
    fee_collector: Mapped[Union[str, None]] = mapped_column(String, default=None)
    sweep_collector: Mapped[Union[str, None]] = mapped_column(String, default=None)
    curve_fee: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    flat_fee: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    governance_lp_fee: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    governance_zombie_fee: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    inv_time_stretch: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)


class CheckpointInfo(Base):
    """Table/dataclass schema for checkpoint information"""

    __tablename__ = "checkpoint_info"

    checkpoint_time: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    vault_share_price: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    # TODO we'd like to add the checkpoint id here as a field as well


class PoolInfo(Base):
    """Table/dataclass schema for pool info.

    Mapped class that is a data class on the python side, and an declarative base on the sql side.
    """

    __tablename__ = "pool_info"

    block_number: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    share_reserves: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    share_adjustment: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    zombie_base_proceeds: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    zombie_share_reserves: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    bond_reserves: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    lp_total_supply: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    vault_share_price: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    longs_outstanding: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    long_average_maturity_time: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    shorts_outstanding: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    short_average_maturity_time: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    withdrawal_shares_ready_to_withdraw: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    withdrawal_shares_proceeds: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    lp_share_price: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    long_exposure: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    # Added fields from pool_state
    epoch_timestamp: Mapped[Union[int, None]] = mapped_column(BigInteger, default=None)
    total_supply_withdrawal_shares: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    gov_fees_accrued: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    hyperdrive_base_balance: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    hyperdrive_eth_balance: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    variable_rate: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    vault_shares: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)


# TODO: either make a more general TokenDelta, or rename this to HyperdriveDelta
class WalletDelta(Base):
    """Table/dataclass schema for wallet deltas."""

    __tablename__ = "wallet_delta"

    # Default table primary key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, init=False, autoincrement=True)
    transaction_hash: Mapped[str] = mapped_column(String, index=True)
    block_number: Mapped[int] = mapped_column(BigInteger, index=True)
    wallet_address: Mapped[Union[str, None]] = mapped_column(String, index=True, default=None)
    # base_token_type can be BASE, LONG, SHORT, LP, or WITHDRAWAL_SHARE
    base_token_type: Mapped[Union[str, None]] = mapped_column(String, index=True, default=None)
    # token_type is the base_token_type appended with "-<maturity_time>" for LONG and SHORT
    token_type: Mapped[Union[str, None]] = mapped_column(String, default=None)
    delta: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    # While time here is in epoch seconds, we use Numeric to allow for (1) lossless storage and (2) allow for NaNs
    maturity_time: Mapped[Union[int, None]] = mapped_column(Numeric, default=None)


class HyperdriveTransaction(Base):
    """Table/dataclass schema for Transactions.

    Mapped class that is a data class on the python side, and an declarative base on the sql side.
    """

    __tablename__ = "transactions"

    # Default table primary key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, init=False, autoincrement=True)
    transaction_hash: Mapped[str] = mapped_column(String, index=True, unique=True)

    #### Fields from base transactions ####
    block_number: Mapped[int] = mapped_column(BigInteger, index=True)
    transaction_index: Mapped[Union[int, None]] = mapped_column(Integer, default=None)
    nonce: Mapped[Union[int, None]] = mapped_column(Integer, default=None)
    # Transaction receipt to/from
    # Almost always from wallet address to smart contract address
    txn_to: Mapped[Union[str, None]] = mapped_column(String, default=None)
    txn_from: Mapped[Union[str, None]] = mapped_column(String, default=None)
    gas_used: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)

    #### Fields from solidity function calls ####
    # These fields map solidity function calls and their corresponding arguments
    # The params list is exhaustive against all possible methods
    input_method: Mapped[Union[str, None]] = mapped_column(String, default=None)

    # Call data options
    input_params_options_destination: Mapped[Union[str, None]] = mapped_column(String, default=None)
    input_params_options_as_base: Mapped[Union[bool, None]] = mapped_column(Boolean, default=None)

    # Method: initialize
    input_params_contribution: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    input_params_apr: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)

    # Method: openLong
    input_params_amount: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    input_params_min_output: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    input_params_min_vault_share_price: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)

    # Method: openShort
    input_params_bond_amount: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    input_params_max_deposit: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    # input_params_min_vault_share_price

    # Method: closeLong
    input_params_maturity_time: Mapped[Union[int, None]] = mapped_column(BigInteger, default=None)
    # input_params_bond_amount
    # input_params_min_output

    # Method: closeShort
    # input_params_maturity_time
    # input_params_bond_amount
    # input_params_min_output

    # Method: addLiquidity
    # input_params_contribution
    input_params_min_lp_share_price: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    input_params_min_apr: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    input_params_max_apr: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)

    # Method: removeLiquidity
    input_params_lp_shares: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    input_params_min_output_per_share: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    # input_params_min_output
    # input_params_destination
    # input_params_as_underlying

    # Method: redeemWithdrawawlShares
    input_params_withdrawal_shares: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    # input_params_min_output_per_share

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
    # contract_address
    # status
    # logsBloom
    # effectiveGasPrice


## Analysis schemas


class PoolAnalysis(Base):
    """Table/dataclass schema for pool info analysis.

    Mapped class that is a data class on the python side, and an declarative base on the sql side.
    """

    __tablename__ = "pool_analysis"

    block_number: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    spot_price: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    fixed_rate: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    base_buffer: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    # TODO add gov fees accrued, vault shares


class CurrentWallet(Base):
    """Table/dataclass schema for current wallet positions."""

    __tablename__ = "current_wallet"

    # Default table primary key
    id: Mapped[int] = mapped_column(BigInteger(), primary_key=True, init=False, autoincrement=True)
    block_number: Mapped[int] = mapped_column(BigInteger, index=True)
    wallet_address: Mapped[Union[str, None]] = mapped_column(String, index=True, default=None)
    # base_token_type can be BASE, LONG, SHORT, LP, or WITHDRAWAL_SHARE
    base_token_type: Mapped[Union[str, None]] = mapped_column(String, index=True, default=None)
    # token_type is the base_token_type appended with "-<maturity_time>" for LONG and SHORT
    token_type: Mapped[Union[str, None]] = mapped_column(String, default=None)
    value: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    # While time here is in epoch seconds, we use Numeric to allow for (1) lossless storage and (2) allow for NaNs
    maturity_time: Mapped[Union[int, None]] = mapped_column(Numeric, default=None)


class Ticker(Base):
    """Table/dataclass schema for the live ticker.

    Mapped class that is a data class on the python side, and an declarative base on the sql side.
    """

    __tablename__ = "ticker"

    id: Mapped[int] = mapped_column(BigInteger(), primary_key=True, init=False, autoincrement=True)
    block_number: Mapped[int] = mapped_column(BigInteger, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    wallet_address: Mapped[Union[str, None]] = mapped_column(String, index=True, default=None)
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
    block_number: Mapped[int] = mapped_column(BigInteger, index=True)
    wallet_address: Mapped[Union[str, None]] = mapped_column(String, index=True, default=None)
    # base_token_type can be BASE, LONG, SHORT, LP, or WITHDRAWAL_SHARE
    base_token_type: Mapped[Union[str, None]] = mapped_column(String, index=True, default=None)
    # token_type is the base_token_type appended with "-<maturity_time>" for LONG and SHORT
    token_type: Mapped[Union[str, None]] = mapped_column(String, default=None)
    value: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    # While time here is in epoch seconds, we use Numeric to allow for (1) lossless storage and (2) allow for NaNs
    maturity_time: Mapped[Union[int, None]] = mapped_column(Numeric, default=None)
    latest_block_update: Mapped[Union[int, None]] = mapped_column(BigInteger, default=None)
    pnl: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)

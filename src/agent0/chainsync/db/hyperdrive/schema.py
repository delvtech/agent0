"""Database Schemas for the Hyperdrive Contract."""

from datetime import datetime
from decimal import Decimal
from typing import Union

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, Numeric, String
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


class HyperdriveAddrToName(Base):
    """Maps a hyperdrive address to a logical name."""

    __tablename__ = "hyperdrive_addr_to_name"

    hyperdrive_address: Mapped[str] = mapped_column(String, primary_key=True)
    """The hyperdrive address"""
    name: Mapped[str] = mapped_column(String, index=True)
    """The logical name of the hyperdrive address."""


class PoolConfig(Base):
    """Table/dataclass schema for pool config."""

    __tablename__ = "pool_config"

    # Indices
    hyperdrive_address: Mapped[str] = mapped_column(String, primary_key=True)

    # Pool config parameters
    base_token: Mapped[Union[str, None]] = mapped_column(String, default=None)
    vault_shares_token: Mapped[Union[str, None]] = mapped_column(String, default=None)
    linker_factory: Mapped[Union[str, None]] = mapped_column(String, default=None)
    # Ignoring linker_code_hash field
    initial_vault_share_price: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    minimum_share_reserves: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    minimum_transaction_amount: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    circuit_breaker_delta: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
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
    """Table/dataclass schema for checkpoint information."""

    __tablename__ = "checkpoint_info"

    # Indices
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, init=False, autoincrement=True)
    """The unique identifier for the entry to the table."""
    hyperdrive_address: Mapped[str] = mapped_column(String, index=True)
    """The hyperdrive address for the entry."""
    block_number: Mapped[int] = mapped_column(BigInteger, index=True)
    """The block number on which the event was emitted."""
    checkpoint_time: Mapped[int] = mapped_column(BigInteger, index=True)
    """The seconds epoch time index for this checkpoint."""

    # Fields
    checkpoint_vault_share_price: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    """The share price that was checkpointed in this checkpoint."""
    vault_share_price: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    """The vault share price at the time of checkpoint creation."""
    matured_shorts: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    """The amount of shorts that matured within this checkpoint."""
    matured_longs: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    """The amount of longs that matured within this checkpoint."""
    lp_share_price: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    """The lp share price at the checkpoint."""


# TODO change this table to allow for missing data in block time.
class PoolInfo(Base):
    """Table/dataclass schema for pool info.

    Mapped class that is a data class on the python side, and an declarative base on the sql side.
    """

    __tablename__ = "pool_info"

    # Indices
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, init=False, autoincrement=True)
    hyperdrive_address: Mapped[str] = mapped_column(String, index=True)
    block_number: Mapped[int] = mapped_column(BigInteger, index=True)

    # Time
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    epoch_timestamp: Mapped[Union[int, None]] = mapped_column(BigInteger, default=None)

    # Pool Info Fields
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
    total_supply_withdrawal_shares: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    gov_fees_accrued: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    hyperdrive_base_balance: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    hyperdrive_eth_balance: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    variable_rate: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    vault_shares: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    spot_price: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    fixed_rate: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)


class TradeEvent(Base):
    """Table for storing any transfer events emitted by the Hyperdrive contract.
    This table only contains events of "registered" wallet addresses, which are any agents
    that are managed by agent0. This table does not store all wallet addresses that have
    interacted with all Hyperdrive contracts.
    TODO this table would take the place of the `WalletDelta` table with the following updates:
    - We explicitly fill this table with all addresses that have interacted with all hyperdrive pools.
        - This is very slow on existing pools, which makes it useful for simulations and
          any managed chains to run a dashboard on, but not so much for connections to remote chains
          to execute trades.
    """

    __tablename__ = "trade_event"
    # Indices
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, init=False, autoincrement=True)
    """The unique identifier for the entry to the table."""
    hyperdrive_address: Mapped[str] = mapped_column(String, index=True)
    """The hyperdrive address for the entry."""
    transaction_hash: Mapped[str] = mapped_column(String, index=True)
    """The transaction hash for the entry."""
    block_number: Mapped[int] = mapped_column(BigInteger, index=True)
    """The block number for the entry."""
    wallet_address: Mapped[str] = mapped_column(String, index=True)
    """The wallet address for the entry."""

    # Fields
    event_type: Mapped[Union[str, None]] = mapped_column(String, index=True, default=None)
    """
    The underlying event type for the entry. Can be one of the following:
    `Initialize`, `AddLiquidity`, `RemoveLiquidity`, `RedeemWithdrawalShares`, 
    `OpenLong`, `OpenShort`, `CloseLong`, `CloseShort`, or `TransferSingle`.
    """
    token_type: Mapped[Union[str, None]] = mapped_column(String, index=True, default=None)
    """
    The underlying token type for the entry. Can be one of the following:
    `LONG`, `SHORT, `LP`, or `WITHDRAWAL_SHARE`.
    """
    # While time here is in epoch seconds, we use Numeric to allow for
    # (1) lossless storage and (2) allow for NaNs
    maturity_time: Mapped[Union[int, None]] = mapped_column(Numeric, default=None)
    """The maturity time of the token for LONG and SHORT tokens."""
    token_id: Mapped[Union[str, None]] = mapped_column(String, default=None)
    """
    The id for the token itself, which consists of the `token_type`, appended 
    with `maturity_time` for LONG and SHORT. For example, `LONG-1715126400`.
    """
    token_delta: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    """
    The change in tokens with respect to the wallet address.
    """
    base_delta: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    """
    The change in base tokens for the event with respect to the wallet address.
    """
    vault_share_delta: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    """
    The change in vault share tokens for the event with respect to the wallet address.
    """
    as_base: Mapped[Union[bool, None]] = mapped_column(Boolean, default=None)
    """
    A flag defining if the trade was made in units of base or vault shares.
    """
    vault_share_price: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    """
    The vault share price at the time of the emitted event.
    """


## Analysis schemas


class PositionSnapshot(Base):
    """Table/dataclass schema for snapshots of positions
    This table takes snapshots of open positions and calculates the value and pnl of
    positions every snapshot.

    Mapped class that is a data class on the python side, and an declarative base on the sql side.
    """

    __tablename__ = "wallet_pnl"

    # Indices
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, init=False, autoincrement=True)
    """The unique identifier for the entry to the table."""
    hyperdrive_address: Mapped[str] = mapped_column(String, index=True)
    """The hyperdrive address for the entry."""
    block_number: Mapped[int] = mapped_column(BigInteger, index=True)
    """The block number for the entry."""
    wallet_address: Mapped[Union[str, None]] = mapped_column(String, index=True, default=None)
    """The wallet address for the entry."""

    # Fields
    token_type: Mapped[Union[str, None]] = mapped_column(String, default=None)
    """
    The underlying token type for the entry. Can be one of the following:
    `LONG`, `SHORT, `LP`, or `WITHDRAWAL_SHARE`.
    """
    # While time here is in epoch seconds, we use Numeric to allow for (1) lossless storage and (2) allow for NaNs
    maturity_time: Mapped[Union[int, None]] = mapped_column(Numeric, default=None)
    """The maturity time of the token for LONG and SHORT tokens."""
    token_id: Mapped[Union[str, None]] = mapped_column(String, default=None)
    """
    The id for the token itself, which consists of the `token_type`, appended 
    with `maturity_time` for LONG and SHORT. For example, `LONG-1715126400`.
    """
    token_balance: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    """
    The absolute balance of the position.
    """
    unrealized_value: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    """
    The unrealized value of the tokens in units of base, calculated if the position is closed at this block.
    """
    realized_value: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    """
    The total change in base for opening/closing this position.
    NOTE: this doesn't take into account any transfers of tokens outside of hyperdrive trades.
    """
    pnl: Mapped[Union[Decimal, None]] = mapped_column(FIXED_NUMERIC, default=None)
    """
    The pnl of the position in units of base.
    `unrealized_value` + `realized_value` = `pnl`.
    """
    last_balance_update_block: Mapped[Union[int, None]] = mapped_column(BigInteger, default=None)
    """
    The last block number that this position's balance was updated.
    """

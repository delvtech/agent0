"""Fixed point versions of common structs from the hyperdrive contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from fixedpointmath import FixedPoint


# TODO: These dataclasses are similar to pypechain except for
#  - snake_case attributes instead of camelCase
#  - FixedPoint types instead of int
#  - nested dataclasses (PoolConfig) include a __post_init__ that allows for
#  instantiation with a nested dictionary
#
# We'd like to rely on the pypechain classes as much as possible.
# One solution could be to build our own interface wrapper that pulls in the pypechain
# dataclass and makes this fixed set of changes?
# pylint: disable=too-many-instance-attributes
@dataclass
class FeesFP:
    """Fees struct."""

    curve: FixedPoint
    flat: FixedPoint
    governance_lp: FixedPoint
    governance_zombie: FixedPoint


@dataclass
class PoolInfoFP:
    """PoolInfo struct."""

    share_reserves: FixedPoint
    share_adjustment: FixedPoint
    zombie_base_proceeds: FixedPoint
    zombie_share_reserves: FixedPoint
    bond_reserves: FixedPoint
    lp_total_supply: FixedPoint
    vault_share_price: FixedPoint
    longs_outstanding: FixedPoint
    long_average_maturity_time: FixedPoint
    shorts_outstanding: FixedPoint
    short_average_maturity_time: FixedPoint
    withdrawal_shares_ready_to_withdraw: FixedPoint
    withdrawal_shares_proceeds: FixedPoint
    lp_share_price: FixedPoint
    long_exposure: FixedPoint


@dataclass
class PoolConfigFP:
    """PoolConfig struct."""

    base_token: str
    vault_shares_token: str
    linker_factory: str
    linker_code_hash: bytes
    initial_vault_share_price: FixedPoint
    minimum_share_reserves: FixedPoint
    minimum_transaction_amount: FixedPoint
    circuit_breaker_delta: FixedPoint
    position_duration: int
    checkpoint_duration: int
    time_stretch: FixedPoint
    governance: str
    fee_collector: str
    sweep_collector: str
    checkpoint_rewarder: str
    # TODO: Pyright:
    # Declaration "fees" is obscured by a declaration of the same name here but not elsewhere
    fees: FeesFP | Sequence  # type: ignore

    def __post_init__(self):
        if isinstance(self.fees, Sequence):
            self.fees: FeesFP = FeesFP(*self.fees)


@dataclass
class CheckpointFP:
    """Checkpoint struct."""

    weighted_spot_price: FixedPoint
    last_weighted_spot_price_update_time: int
    vault_share_price: FixedPoint

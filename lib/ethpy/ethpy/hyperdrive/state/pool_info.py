"""Functions for storing Hyperdrive state."""
from __future__ import annotations

from dataclasses import dataclass

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
class PoolInfo:
    """PoolInfo struct."""

    share_reserves: FixedPoint
    share_adjustment: FixedPoint
    bond_reserves: FixedPoint
    lp_total_supply: FixedPoint
    share_price: FixedPoint
    longs_outstanding: FixedPoint
    long_average_maturity_time: FixedPoint
    shorts_outstanding: FixedPoint
    short_average_maturity_time: FixedPoint
    withdrawal_shares_ready_to_withdraw: FixedPoint
    withdrawal_shares_proceeds: FixedPoint
    lp_share_price: FixedPoint
    long_exposure: FixedPoint

"""Class for for storing the delta values for MarketState"""
from __future__ import annotations

from dataclasses import dataclass, field

from fixedpoint import FixedPoint

import elfpy.types as types
from elfpy.markets.base import BaseMarketDeltas


@types.freezable(frozen=True, no_new_attribs=True)
@dataclass
class HyperdriveMarketDeltas(BaseMarketDeltas):
    r"""Specifies changes to values in the market"""
    # pylint: disable=too-many-instance-attributes
    d_base_asset: FixedPoint = field(default_factory=FixedPoint)
    d_bond_asset: FixedPoint =field(default_factory=FixedPoint)
    d_base_buffer: FixedPoint = field(default_factory=FixedPoint)
    d_bond_buffer: FixedPoint = field(default_factory=FixedPoint)
    d_lp_total_supply: FixedPoint = field(default_factory=FixedPoint)
    d_share_price: FixedPoint = field(default_factory=FixedPoint)
    longs_outstanding: FixedPoint =field(default_factory=FixedPoint)
    shorts_outstanding: FixedPoint =field(default_factory=FixedPoint)
    long_average_maturity_time: FixedPoint =field(default_factory=FixedPoint)
    short_average_maturity_time: FixedPoint =field(default_factory=FixedPoint)
    long_base_volume: FixedPoint = field(default_factory=FixedPoint)
    short_base_volume: FixedPoint =field(default_factory=FixedPoint)
    total_supply_withdraw_shares: FixedPoint = field(default_factory=FixedPoint)
    withdraw_shares_ready_to_withdraw: FixedPoint =field(default_factory=FixedPoint)
    withdraw_capital: FixedPoint =field(default_factory=FixedPoint)
    withdraw_interest: FixedPoint =field(default_factory=FixedPoint)
    long_checkpoints: dict[FixedPoint, FixedPoint] = field(default_factory=dict)
    short_checkpoints: dict[FixedPoint, FixedPoint] = field(default_factory=dict)
    total_supply_longs: dict[FixedPoint, FixedPoint] = field(default_factory=dict)
    total_supply_shorts: dict[FixedPoint, FixedPoint] = field(default_factory=dict)

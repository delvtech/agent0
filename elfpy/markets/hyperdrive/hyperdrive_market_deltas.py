"""Class for for storing the delta values for MarketState"""
from __future__ import annotations
from dataclasses import dataclass, field

import elfpy.types as types

from elfpy.math import FixedPoint
from elfpy.markets.base.base_market import BaseMarketDeltas


@types.freezable(frozen=True, no_new_attribs=True)
@dataclass
class HyperdriveMarketDeltas(BaseMarketDeltas):
    r"""Specifies changes to values in the market"""
    # pylint: disable=too-many-instance-attributes
    d_base_asset: FixedPoint = FixedPoint(0)
    d_bond_asset: FixedPoint = FixedPoint(0)
    d_base_buffer: FixedPoint = FixedPoint(0)
    d_bond_buffer: FixedPoint = FixedPoint(0)
    d_lp_total_supply: FixedPoint = FixedPoint(0)
    d_share_price: FixedPoint = FixedPoint(0)
    longs_outstanding: FixedPoint = FixedPoint(0)
    shorts_outstanding: FixedPoint = FixedPoint(0)
    long_average_maturity_time: FixedPoint = FixedPoint(0)
    short_average_maturity_time: FixedPoint = FixedPoint(0)
    long_base_volume: FixedPoint = FixedPoint(0)
    short_base_volume: FixedPoint = FixedPoint(0)
    total_supply_withdraw_shares: FixedPoint = FixedPoint(0)
    withdraw_shares_ready_to_withdraw: FixedPoint = FixedPoint(0)
    withdraw_capital: FixedPoint = FixedPoint(0)
    withdraw_interest: FixedPoint = FixedPoint(0)
    long_checkpoints: dict[FixedPoint, FixedPoint] = field(default_factory=dict)
    short_checkpoints: dict[FixedPoint, FixedPoint] = field(default_factory=dict)
    total_supply_longs: dict[FixedPoint, FixedPoint] = field(default_factory=dict)
    total_supply_shorts: dict[FixedPoint, FixedPoint] = field(default_factory=dict)

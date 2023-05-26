"""The resulting deltas of a market action"""
# Please enter the commit message for your changes. Lines starting
from __future__ import annotations

from dataclasses import dataclass

from elfpy import types
from elfpy.math import FixedPoint
from elfpy.markets import base as base_market


@types.freezable(frozen=True, no_new_attribs=True)
@dataclass
class MarketActionResultFP(base_market.MarketActionResult):
    r"""The result to a market of performing a trade"""
    d_base: FixedPoint
    d_bonds: FixedPoint

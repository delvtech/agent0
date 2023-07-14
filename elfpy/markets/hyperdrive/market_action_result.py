"""The resulting deltas of a market action"""
# Please enter the commit message for your changes. Lines starting
from __future__ import annotations

from dataclasses import dataclass

from fixedpoint import FixedPoint

from elfpy import types
from elfpy.markets.base import BaseMarketActionResult


@types.freezable(frozen=True, no_new_attribs=True)
@dataclass
class MarketActionResult(BaseMarketActionResult):
    r"""The result to a market of performing a trade"""
    d_base: FixedPoint
    d_bonds: FixedPoint

"""The resulting deltas of a market action"""
# Please enter the commit message for your changes. Lines starting
from __future__ import annotations

from dataclasses import dataclass

from agent0.base import freezable
from elfpy.markets.base import BaseMarketActionResult
from fixedpointmath import FixedPoint


@freezable(frozen=True, no_new_attribs=True)
@dataclass
class HyperdriveActionResult(BaseMarketActionResult):
    r"""The result to a market of performing a trade"""
    d_base: FixedPoint
    d_bonds: FixedPoint

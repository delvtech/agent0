"""Agent trade results"""
from dataclasses import dataclass

from fixedpoint import FixedPoint

import elfpy.types as types


@types.freezable(frozen=True, no_new_attribs=True)
@dataclass
class AgentTradeResult:
    r"""The result to a user of performing a trade"""

    d_base: FixedPoint
    d_bonds: FixedPoint

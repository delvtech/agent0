"""Agent trade results"""
from dataclasses import dataclass

import elfpy.types as types
from elfpy.math import FixedPoint


@types.freezable(frozen=True, no_new_attribs=True)
@dataclass
class AgentTradeResultFP:
    r"""The result to a user of performing a trade"""

    d_base: FixedPoint
    d_bonds: FixedPoint

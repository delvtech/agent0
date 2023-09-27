"""Policy that takes no actions."""
from __future__ import annotations

from typing import TYPE_CHECKING

from fixedpointmath import FixedPoint

from .base import BasePolicy, Wallet

if TYPE_CHECKING:
    from elfpy.types import Trade
    from ethpy.hyperdrive import HyperdriveInterface
    from numpy.random._generator import Generator as NumpyGenerator


# pylint: disable=too-few-public-methods


class NoActionPolicy(BasePolicy[Wallet]):
    """NoOp class policy"""

    def __init__(self, budget: FixedPoint | None = None, rng: NumpyGenerator | None = None):
        if budget is None:
            super().__init__(FixedPoint("0.0"), rng)
        else:
            super().__init__(budget, rng)

    def action(self, interface: HyperdriveInterface, wallet: Wallet) -> list[Trade]:
        """Returns an empty list, indicating no action"""
        # pylint: disable=unused-argument
        return []

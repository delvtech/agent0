"""Base policy class. Subclasses of BasicPolicy will implement trade actions."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from numpy.random import default_rng
from elfpy.math import FixedPoint

if TYPE_CHECKING:
    from numpy.random._generator import Generator as NumpyGenerator

    from elfpy.agents.wallet import Wallet
    from elfpy.markets.hyperdrive.hyperdrive_market import Market as HyperdriveMarket
    from elfpy.types import Trade

# pylint: disable=too-few-public-methods


class BasePolicy:
    """Base class policy"""

    def __init__(self, budget: FixedPoint, rng: NumpyGenerator | None = None):
        if not isinstance(budget, FixedPoint):
            raise TypeError(f"{budget=} must be of type `FixedPoint`")
        self.budget: FixedPoint = budget
        if rng is None:
            logging.warning("Policy random number generator (rng) argument not set, using seed of `123`.")
            self.rng: NumpyGenerator = default_rng(123)
        else:
            self.rng: NumpyGenerator = rng

    def action(self, market: HyperdriveMarket, wallet: Wallet) -> list[Trade]:
        """Returns an empty list, indicating no action"""
        raise NotImplementedError

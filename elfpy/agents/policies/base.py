"""Base policy class. Subclasses of BasicPolicy will implement trade actions."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fixedpointmath import FixedPoint
from numpy.random import default_rng

if TYPE_CHECKING:
    from numpy.random._generator import Generator as NumpyGenerator

    from elfpy.markets.base import BaseMarket
    from elfpy.types import Trade
    from elfpy.wallet.wallet import Wallet


class BasePolicy:
    """Base class policy"""

    def __init__(self, budget: FixedPoint, rng: NumpyGenerator | None = None):
        if not isinstance(budget, FixedPoint):
            raise TypeError(f"{budget=} must be of type `FixedPoint`")
        self.budget: FixedPoint = budget
        if rng is None:  # TODO: Check that multiple agent.rng derefs to the same rng object
            logging.warning("Policy random number generator (rng) argument not set, using seed of `123`.")
            self.rng: NumpyGenerator = default_rng(123)
        else:
            self.rng: NumpyGenerator = rng

    @property
    def name(self):
        """Return the class name"""
        return self.__class__.__name__

    def action(self, market: BaseMarket, wallet: Wallet) -> list[Trade]:
        """Returns an empty list, indicating no action"""
        raise NotImplementedError

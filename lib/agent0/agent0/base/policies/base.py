"""Base policy class. Subclasses of BasicPolicy will implement trade actions."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Generic, Tuple, TypeVar

from fixedpointmath import FixedPoint
from numpy.random import default_rng

if TYPE_CHECKING:
    from agent0.base.state import EthWallet
    from elfpy.types import Trade
    from ethpy.base import BaseInterface
    from numpy.random._generator import Generator as NumpyGenerator

Wallet = TypeVar("Wallet", bound="EthWallet")
MarketInterface = TypeVar("MarketInterface", bound="BaseInterface")


class BasePolicy(Generic[MarketInterface, Wallet]):
    """Base class policy."""

    def __init__(
        self, budget: FixedPoint, rng: NumpyGenerator | None = None, slippage_tolerance: FixedPoint | None = None
    ):
        # TODO budget should have a flag to allow for "the budget is however much this wallet has"
        # https://github.com/delvtech/elf-simulations/issues/827
        if not isinstance(budget, FixedPoint):
            raise TypeError(f"{budget=} must be of type `FixedPoint`")
        self.budget: FixedPoint = budget
        self.slippage_tolerance = slippage_tolerance
        if rng is None:  # TODO: Check that multiple agent.rng derefs to the same rng object
            logging.warning("Policy random number generator (rng) argument not set, using seed of `123`.")
            self.rng: NumpyGenerator = default_rng(123)
        else:
            self.rng: NumpyGenerator = rng

    @property
    def name(self):
        """Return the class name"""
        return self.__class__.__name__

    def action(self, interface: MarketInterface, wallet: Wallet) -> Tuple[list[Trade], bool]:
        """Returns an empty list, indicating no action"""
        raise NotImplementedError

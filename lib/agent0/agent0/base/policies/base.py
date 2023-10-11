"""Base policy class. Subclasses of BasicPolicy will implement trade actions."""
from __future__ import annotations

import logging
from textwrap import dedent, indent
from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, TypeVar

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

    @dataclass
    class Config:
        """Config data class for policy specific configuration"""

    def __init__(
        self,
        budget: FixedPoint,
        rng: NumpyGenerator | None = None,
        slippage_tolerance: FixedPoint | None = None,
        # TODO should we pass in policy_config here in the base class constructor?
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

    def action(self, interface: MarketInterface, wallet: Wallet) -> tuple[list[Trade], bool]:
        """Specify actions.

        Arguments
        ---------
        market : HyperdriveMarketState
            the trading market
        wallet : HyperdriveWallet
            agent's wallet

        Returns
        -------
        tuple[list[MarketAction], bool]
            A tuple where the first element is a list of actions,
            and the second element defines if the agent is done trading
        """
        raise NotImplementedError

    @classmethod
    def describe(cls, raw_description: str | None = None) -> str:
        """Describe the policy in a user friendly manner that allows newcomers to decide whether to use it.

        Returns
        -------
        str
            A description of the policy"""
        if raw_description is None:
            raise NotImplementedError("This is a base policy. Subclasses should provide their own descriptions.")
        dedented_text = dedent(raw_description).strip()
        indented_text = indent(dedented_text, "  ")  # Adding 2-space indent
        return indented_text

"""Base policy class. Subclasses of BasicPolicy will implement trade actions."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from textwrap import dedent, indent
from typing import TYPE_CHECKING, Generic, TypeVar

from fixedpointmath import FixedPoint
from numpy.random import default_rng

if TYPE_CHECKING:
    from numpy.random._generator import Generator as NumpyGenerator

    from agent0.base import Trade
    from agent0.base.state import EthWallet

Wallet = TypeVar("Wallet", bound="EthWallet")
MarketInterface = TypeVar("MarketInterface")


class BasePolicy(Generic[MarketInterface, Wallet]):
    """Base class policy."""

    @dataclass
    class Config:
        """Config data class for policy specific configuration"""

    def __init__(
        self,
        rng: NumpyGenerator | None = None,
        slippage_tolerance: FixedPoint | None = None,
        # TODO should we pass in policy_config here in the base class constructor?
    ):
        """Instantiate the policy."""
        self.slippage_tolerance = slippage_tolerance
        if rng is None:  # TODO: Check that multiple agent.rng derefs to the same rng object
            logging.warning("Policy random number generator (rng) argument not set, using seed of `123`.")
            self.rng: NumpyGenerator = default_rng(123)
        else:
            self.rng: NumpyGenerator = rng

    @property
    def name(self) -> str:
        """Return the class name.

        Returns
        -------
        str
            The class name.
        """
        return self.__class__.__name__

    def action(self, interface: MarketInterface, wallet: Wallet) -> tuple[list[Trade], bool]:
        """Specify actions.

        Arguments
        ---------
        interface: MarketInterface
            The trading market interface.
        wallet: Wallet
            The agent's wallet.

        Returns
        -------
        tuple[list[Trade], bool]
            A tuple where the first element is a list of actions,
            and the second element defines if the agent is done trading.
        """
        raise NotImplementedError

    @classmethod
    def describe(cls, raw_description: str) -> str:
        """Describe the policy in a user friendly manner that allows newcomers to decide whether to use it.

        Arguments
        ---------
        raw_description: str
            The description of the policy's action plan.

        Returns
        -------
        str
            A description of the policy.
        """
        dedented_text = dedent(raw_description).strip()
        indented_text = indent(dedented_text, "  ")  # Adding 2-space indent
        return indented_text

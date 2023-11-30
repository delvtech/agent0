"""Base policy class. Subclasses of BasicPolicy will implement trade actions."""
from __future__ import annotations

from dataclasses import dataclass
from textwrap import dedent, indent
from typing import TYPE_CHECKING, Generic, TypeVar

from fixedpointmath import FixedPoint
from numpy.random import default_rng

if TYPE_CHECKING:
    from numpy.random._generator import Generator

    from agent0.base import Trade
    from agent0.base.state import EthWallet

Wallet = TypeVar("Wallet", bound="EthWallet")
MarketInterface = TypeVar("MarketInterface")


class BasePolicy(Generic[MarketInterface, Wallet]):
    """Base class policy."""

    # Because we're inheriting from this config, we need to set
    # kw_only so that we can mix and match defaults and non-defaults
    @dataclass(kw_only=True)
    class Config:
        """Config data class for policy specific configuration
        Attributes
        ----------
        rng_seed: int
        rng: Generator | None, optional
            The experiment's stateful random number generator. Defaults to using seed 123
        """

        rng_seed: int | None = None
        rng: Generator | None = None
        slippage_tolerance: FixedPoint | None = None

        def __post_init__(self):
            if self.rng is None:
                # If seed is None, should just be random
                self.rng = default_rng(self.rng_seed)

    def __init__(self, config: Config):
        self.slippage_tolerance = config.slippage_tolerance
        # config.rng should be set in post_init in config
        assert config.rng is not None
        self.rng: Generator = config.rng

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

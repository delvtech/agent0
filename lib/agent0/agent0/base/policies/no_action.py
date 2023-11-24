"""Policy that takes no actions."""
from __future__ import annotations

from typing import TYPE_CHECKING

from fixedpointmath import FixedPoint

from .base import BasePolicy, MarketInterface, Wallet

if TYPE_CHECKING:
    from numpy.random._generator import Generator as NumpyGenerator

    from agent0.base import Trade


# pylint: disable=too-few-public-methods


class NoActionPolicy(BasePolicy[MarketInterface, Wallet]):
    """NoOp class policy"""

    def __init__(self, budget: FixedPoint | None = None, rng: NumpyGenerator | None = None):
        if budget is None:
            super().__init__(FixedPoint("0.0"), rng)
        else:
            super().__init__(budget, rng)

    def action(self, interface: MarketInterface, wallet: Wallet) -> tuple[list[Trade], bool]:
        """Returns an empty list, indicating no action

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
        # pylint: disable=unused-argument
        return [], False

    @classmethod
    def description(cls) -> str:
        """Describe the policy in a user friendly manner that allows newcomers to decide whether to use it.

        Returns
        -------
        str
            A description of the policy.
        """
        raw_description = "Take no actions."
        return super().describe(raw_description)

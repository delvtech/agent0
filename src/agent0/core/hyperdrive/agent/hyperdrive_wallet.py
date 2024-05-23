"""Empty accounts for engaging with smart contracts."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field

from fixedpointmath import FixedPoint

from agent0.core.base import EthWallet


@dataclass
class Long:
    r"""An open long position.

    .. todo:: make balance a Quantity to enforce units
    """

    balance: FixedPoint  # bonds
    """The amount of bonds that the position is long."""
    maturity_time: int
    """The maturity time of the long."""


@dataclass
class Short:
    r"""An open short position."""

    balance: FixedPoint
    """The amount of bonds that the position is short."""
    maturity_time: int
    """The maturity time of the short."""


@dataclass(kw_only=True)
class HyperdriveWallet(EthWallet):
    r"""Stateful variable for storing what is in the agent's wallet."""

    # dataclasses can have many attributes
    # pylint: disable=too-many-instance-attributes
    lp_tokens: FixedPoint = FixedPoint(0)
    """The LP tokens held by the trader."""
    withdraw_shares: FixedPoint = FixedPoint(0)
    """The amount of unclaimed withdraw shares held by the agent."""
    longs: dict[int, Long] = field(default_factory=dict)
    """
    The long positions held by the trader.
    The dictionary is keyed by the maturity time in seconds.
    """
    shorts: dict[int, Short] = field(default_factory=dict)
    """
    The short positions held by the trader.
    The dictionary is keyed by the maturity time in seconds.
    """

    def copy(self) -> HyperdriveWallet:
        """Return a new copy of self.

        Returns
        -------
        HyperdriveWallet
            A deep copy of the wallet.
        """
        return HyperdriveWallet(**copy.deepcopy(self.__dict__))

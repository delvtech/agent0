"""Empty accounts for engaging with smart contracts."""

from __future__ import annotations

import copy
import logging
from dataclasses import dataclass, field
from typing import Iterable

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

    def _update_longs(self, longs: Iterable[tuple[int, Long]]) -> None:
        """Update the data about Longs contained in the Agent's Wallet.

        Arguments
        ---------
        longs: Iterable[tuple[int, Long]]
            A list (or other Iterable type) of tuples that contain a Long object
            and its market-relative maturity time
        """
        for maturity_time, long in longs:
            if long.balance != FixedPoint(0):
                logging.debug(
                    "agent %s trade longs, maturity_time = %g\npre-trade amount = %s\ntrade delta = %s",
                    self.address.hex(),
                    maturity_time,
                    self.longs,
                    long,
                )
                if maturity_time in self.longs:  #  entry already exists for this maturity_time, so add to it
                    self.longs[maturity_time].balance += long.balance
                else:
                    self.longs.update({maturity_time: long})
            if self.longs[maturity_time].balance == FixedPoint(0):
                # Removing the empty dictionary entries allows us to check existance
                # of open longs using `if wallet.longs`
                del self.longs[maturity_time]
            if maturity_time in self.longs and self.longs[maturity_time].balance < FixedPoint(0):
                raise AssertionError(f"ERROR: Wallet balance should be >= 0, not {self.longs[maturity_time]}.")

    def _update_shorts(self, shorts: Iterable[tuple[int, Short]]) -> None:
        """Update the data about Shorts contained in the Agent's Wallet.

        Arguments
        ---------
        shorts: Iterable[tuple[int, Short]]
            A list (or other Iterable type) of tuples that contain a Short object
            and its market-relative mint time
        """
        for maturity_time, short in shorts:
            if short.balance != FixedPoint(0):
                logging.debug(
                    "agent %s trade shorts, maturity_time = %s\npre-trade amount = %s\ntrade delta = %s",
                    self.address.hex(),
                    maturity_time,
                    self.shorts,
                    short,
                )
                if maturity_time in self.shorts:  #  entry already exists for this maturity_time, so add to it
                    self.shorts[maturity_time].balance += short.balance
                else:
                    self.shorts.update({maturity_time: short})
            if self.shorts[maturity_time].balance == FixedPoint(0):
                # Removing the empty dictionary entries allows us to check existance
                # of open shorts using `if wallet.shorts`
                del self.shorts[maturity_time]
            if maturity_time in self.shorts and self.shorts[maturity_time].balance < FixedPoint(0):
                raise AssertionError(f"wallet balance should be >= 0, not {self.shorts[maturity_time]}")

    def copy(self) -> HyperdriveWallet:
        """Return a new copy of self.

        Returns
        -------
        HyperdriveWallet
            A deep copy of the wallet.
        """
        return HyperdriveWallet(**copy.deepcopy(self.__dict__))

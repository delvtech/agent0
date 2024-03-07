"""Empty accounts for engaging with smart contracts."""

from __future__ import annotations

import copy
import logging
from dataclasses import dataclass, field
from typing import Iterable

from fixedpointmath import FixedPoint

from agent0.core.base import EthWallet, EthWalletDeltas, freezable


@freezable()
@dataclass()
class HyperdriveWalletDeltas(EthWalletDeltas):
    r"""Stores changes for an agent's wallet"""

    # dataclasses can have many attributes
    # pylint: disable=too-many-instance-attributes

    lp_tokens: FixedPoint = FixedPoint(0)
    """The LP tokens held by the trader."""
    # non-fungible (identified by key=maturity_time, stored as dict)
    longs: dict[int, Long] = field(default_factory=dict)
    """The long positions held by the trader."""
    shorts: dict[int, Short] = field(default_factory=dict)
    """The short positions held by the trader."""
    withdraw_shares: FixedPoint = FixedPoint(0)
    """The withdraw shares held by the trader."""

    def copy(self) -> HyperdriveWalletDeltas:
        """Returns a new copy of self.

        Returns
        -------
        HyperdriveWalletDeltas
            A deepcopy of the wallet deltas.
        """
        return HyperdriveWalletDeltas(**copy.deepcopy(self.__dict__))


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
class HyperdriveWallet(EthWallet[HyperdriveWalletDeltas]):
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
        """Helper internal function that updates the data about Longs contained in the Agent's Wallet.

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
        """Helper internal function that updates the data about Shorts contained in the Agent's Wallet.

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
        """Returns a new copy of self.

        Returns
        -------
        HyperdriveWallet
            A deep copy of the wallet.
        """
        return HyperdriveWallet(**copy.deepcopy(self.__dict__))

    def update(self, wallet_deltas: HyperdriveWalletDeltas) -> None:
        """Update the agent's wallet in-place.

        Arguments
        ---------
        wallet_deltas: AgentDeltas
            The agent's wallet that tracks the amount of assets this agent holds
        """
        # track over time the agent's weighted average spend, for return calculation
        for key, value_or_dict in wallet_deltas.copy().__dict__.items():
            if value_or_dict is None:
                continue
            match key:
                case "frozen" | "no_new_attribs" | "borrows":
                    continue
                case "lp_tokens" | "withdraw_shares":
                    logging.debug(
                        "agent %s %s pre-trade = %.0g\npost-trade = %1g\ndelta = %1g",
                        self.address.hex(),
                        key,
                        getattr(self, key),
                        getattr(self, key) + value_or_dict,
                        value_or_dict,
                    )
                    self[key] += value_or_dict
                # handle updating a Quantity
                case "balance":
                    logging.debug(
                        "agent %s %s pre-trade = %.0g\npost-trade = %1g\ndelta = %1g",
                        self.address.hex(),
                        key,
                        float(getattr(self, key).amount),
                        float(getattr(self, key).amount + value_or_dict.amount),
                        float(value_or_dict.amount),
                    )
                    getattr(self, key).amount += value_or_dict.amount
                # handle updating a dict, which have maturity_time attached
                case "longs":
                    self._update_longs(value_or_dict.items())
                case "shorts":
                    self._update_shorts(value_or_dict.items())
                case _:
                    raise ValueError(f"wallet_{key=} is not allowed.")
            self.check_valid_wallet_state(self.__dict__)

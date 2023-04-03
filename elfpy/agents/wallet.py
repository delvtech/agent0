"""Implements abstract classes that control user behavior"""
from __future__ import annotations  # types will be strings by default in 3.11

import copy
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import elfpy
import elfpy.markets.hyperdrive.hyperdrive_actions as hyperdrive_actions
import elfpy.types as types

if TYPE_CHECKING:
    from typing import Any, Iterable


@dataclass
class Long:
    r"""An open long position.

    Parameters
    ----------
    balance : float
        The amount of bonds that the position is long.

    .. todo:: make balance a Quantity to enforce units
    """

    balance: float  # bonds


@dataclass
class Short:
    r"""An open short position.

    Parameters
    ----------
    balance : float
        The amount of bonds that the position is short.
    open_share_price: float
        The share price at the time the short was opened.
    """

    balance: float
    open_share_price: float


@dataclass
class Borrow:
    r"""An open borrow position

    Parameters
    ----------
    borrow_token : TokenType
    .. todo: add explanation
    borrow_amount : float
    .. todo: add explanation
    collateral_token : TokenType
    .. todo: add explanation
    collateral_amount: float
    .. todo: add explanation
    start_time : float
    .. todo: add explanation
    """
    borrow_token: types.TokenType
    borrow_amount: float
    borrow_shares: float
    collateral_token: types.TokenType
    collateral_amount: float
    start_time: float


@dataclass()
class Wallet:
    r"""Stores what is in the agent's wallet

    Parameters
    ----------
    address : int
        The trader's address.
    balance : Quantity
        The base assets that held by the trader.
    lp_tokens : float
        The LP tokens held by the trader.
    longs : Dict[float, Long]
        The long positions held by the trader.
    shorts : Dict[float, Short]
        The short positions held by the trader.
    fees_paid : float
        The fees paid by the wallet.
    """

    # pylint: disable=too-many-instance-attributes
    # dataclasses can have many attributes

    # agent identifier
    address: int

    # fungible
    balance: types.Quantity = field(default_factory=lambda: types.Quantity(amount=0, unit=types.TokenType.BASE))
    # TODO: Support multiple typed balances:
    #     balance: Dict[types.TokenType, types.Quantity] = field(default_factory=dict)
    lp_tokens: float = 0

    # non-fungible (identified by key=mint_time, stored as dict)
    longs: dict[float, Long] = field(default_factory=dict)
    shorts: dict[float, Short] = field(default_factory=dict)
    withdraw_shares: float = 0
    # borrow and  collateral have token type, which is not represented here
    # this therefore assumes that only one token type can be used at any given mint time
    borrows: dict[float, Borrow] = field(default_factory=dict)
    fees_paid: float = 0

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)

    def copy(self) -> Wallet:
        """Returns a new copy of self"""
        return Wallet(**copy.deepcopy(self.__dict__))

    def update(self, wallet_deltas: Wallet) -> None:
        """Update the agent's wallet

        Parameters
        ----------
        wallet_deltas : Wallet
            The agent's wallet that tracks the amount of assets this agent holds

        Returns
        -------
        This method has no returns. It updates the Agent's Wallet according to the passed parameters
        """
        # track over time the agent's weighted average spend, for return calculation
        for key, value_or_dict in wallet_deltas.copy().__dict__.items():
            if value_or_dict is None or key in ["fees_paid", "address", "frozen", "no_new_attribs"]:
                continue
            if key in ["lp_tokens", "fees_paid", "withdraw_shares"]:
                logging.debug(
                    "agent #%g %s pre-trade = %.0g\npost-trade = %1g\ndelta = %1g",
                    self.address,
                    key,
                    getattr(self, key),
                    getattr(self, key) + value_or_dict,
                    value_or_dict,
                )
                self[key] += value_or_dict
            # handle updating a Quantity
            elif key == "balance":
                logging.debug(
                    "agent #%g %s pre-trade = %.0g\npost-trade = %1g\ndelta = %1g",
                    self.address,
                    key,
                    getattr(self, key).amount,
                    getattr(self, key).amount + value_or_dict.amount,
                    value_or_dict.amount,
                )
                getattr(self, key).amount += value_or_dict.amount
            # handle updating a dict, which have mint_time attached
            elif key == "borrows":
                if value_or_dict:  # could be empty
                    self._update_borrows(value_or_dict.items())
            elif key == "longs":
                self._update_longs(value_or_dict.items())
            elif key == "shorts":
                self._update_shorts(value_or_dict.items())
            else:
                raise ValueError(f"wallet_key={key} is not allowed.")
            elfpy.check_non_zero(self)

    def _update_borrows(self, borrows: Iterable[tuple[float, Borrow]]) -> None:
        for mint_time, borrow_summary in borrows:
            if mint_time != borrow_summary.start_time:
                raise ValueError(
                    f"The borrow summary key, {mint_time=}, must equal the start time, {borrow_summary.start_time=}"
                )
            if borrow_summary.start_time in self.borrows:  #  entry already exists for this mint_time, so add to it
                self.borrows[borrow_summary.start_time].borrow_amount += borrow_summary.borrow_amount
            else:
                self.borrows.update({borrow_summary.start_time: borrow_summary})
            if self.borrows[borrow_summary.start_time].borrow_amount == 0:
                # Removing the empty borrows allows us to check existance
                # of open borrows using `if self.borrows`
                del self.borrows[borrow_summary.start_time]

    def _update_longs(self, longs: Iterable[tuple[float, Long]]) -> None:
        """Helper internal function that updates the data about Longs contained in the Agent's Wallet object

        Parameters
        ----------
        shorts : Iterable[tuple[float, Short]]
            A list (or other Iterable type) of tuples that contain a Long object
            and its market-relative mint time
        """
        for mint_time, long in longs:
            if long.balance != 0:
                logging.debug(
                    "agent #%g trade longs, mint_time = %g\npre-trade amount = %s\ntrade delta = %s",
                    self.address,
                    mint_time,
                    self.longs,
                    long,
                )
                if mint_time in self.longs:  #  entry already exists for this mint_time, so add to it
                    self.longs[mint_time].balance += long.balance
                else:
                    self.longs.update({mint_time: long})
            if self.longs[mint_time].balance == 0:
                # Removing the empty borrows allows us to check existance
                # of open longs using `if wallet.longs`
                del self.longs[mint_time]
            if mint_time in self.longs and self.longs[mint_time].balance < 0:
                raise AssertionError(f"ERROR: Wallet balance should be >= 0, not {self.longs[mint_time]}.")

    def _update_shorts(self, shorts: Iterable[tuple[float, Short]]) -> None:
        """Helper internal function that updates the data about Shortscontained in the Agent's Wallet object

        Parameters
        ----------
        shorts : Iterable[tuple[float, Short]]
            A list (or other Iterable type) of tuples that contain a Short object
            and its market-relative mint time
        """
        for mint_time, short in shorts:
            if short.balance != 0:
                logging.debug(
                    "agent #%g trade shorts, mint_time = %g\npre-trade amount = %s\ntrade delta = %s",
                    self.address,
                    mint_time,
                    self.shorts,
                    short,
                )
                if mint_time in self.shorts:  #  entry already exists for this mint_time, so add to it
                    self.shorts[mint_time].balance += short.balance
                    old_balance = self.shorts[mint_time].balance

                    # if the balance is positive, we are opening a short, therefore do a weighted
                    # mean for the open share price.  this covers an edge case where two shorts are
                    # opened for the same account in the same block.  if the balance is negative, we
                    # don't want to update the open_short_price
                    if short.balance > 0:
                        old_share_price = self.shorts[mint_time].open_share_price
                        self.shorts[mint_time].open_share_price = (
                            short.open_share_price * short.balance + old_share_price * old_balance
                        ) / (short.balance + old_balance)
                else:
                    self.shorts.update({mint_time: short})
            if self.shorts[mint_time].balance == 0:
                # Removing the empty borrows allows us to check existance
                # of open shorts using `if wallet.shorts`
                del self.shorts[mint_time]
            if mint_time in self.shorts and self.shorts[mint_time].balance < 0:
                raise AssertionError(f"ERROR: Wallet balance should be >= 0, not {self.shorts[mint_time]}.")

    def get_state_keys(self) -> tuple[str, ...]:
        """Get state keys for a wallet."""
        return (
            f"agent_{self.address}_base",
            f"agent_{self.address}_lp_tokens",
            f"agent_{self.address}_num_longs",
            f"agent_{self.address}_num_shorts",
            f"agent_{self.address}_total_longs",
            f"agent_{self.address}_total_shorts",
            f"agent_{self.address}_total_longs_no_mock",
            f"agent_{self.address}_total_shorts_no_mock",
        )

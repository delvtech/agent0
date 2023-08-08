"""Implements abstract classes that control user behavior"""
from __future__ import annotations

import copy
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from fixedpointmath import FixedPoint

from elfpy import check_non_zero
from elfpy.types import Quantity, TokenType, freezable
from elfpy.wallet.wallet_deltas import WalletDeltas

if TYPE_CHECKING:
    from typing import Any, Iterable


@dataclass
class Long:
    r"""An open long position.

    Arguments
    ----------
    balance : FixedPoint
        The amount of bonds that the position is long.

    .. todo:: make balance a Quantity to enforce units
    """

    balance: FixedPoint  # bonds


@dataclass
class Short:
    r"""An open short position.

    Arguments
    ----------
    balance : FixedPoint
        The amount of bonds that the position is short.
    open_share_price : FixedPoint
        The share price at the time the short was opened.
    """

    balance: FixedPoint
    open_share_price: FixedPoint


@dataclass
class Borrow:
    r"""An open borrow position

    Arguments
    ----------
    borrow_token : TokenType
    .. todo: add explanation
    borrow_amount : FixedPoint
    .. todo: add explanation
    collateral_token : TokenType
    .. todo: add explanation
    collateral_amount : FixedPoint
    .. todo: add explanation
    start_time : FixedPoint
    .. todo: add explanation
    """
    borrow_token: TokenType
    borrow_amount: FixedPoint
    borrow_shares: FixedPoint
    collateral_token: TokenType
    collateral_amount: FixedPoint
    start_time: FixedPoint


@freezable()
@dataclass()
class Wallet:
    r"""Stores what is in the agent's wallet

    Arguments
    ----------
    address : int
        The trader's address.
    balance : Quantity
        The base assets that held by the trader.
    lp_tokens : FixedPoint
        The LP tokens held by the trader.
    longs : Dict[FixedPoint, Long]
        The long positions held by the trader.
    shorts : Dict[FixedPoint, Short]
        The short positions held by the trader.
    borrows : Dict[FixedPoint, Borrow]
        The borrow positions held by the trader.
    """

    # dataclasses can have many attributes
    # pylint: disable=too-many-instance-attributes

    # agent identifier
    address: int

    # fungible
    balance: Quantity = field(default_factory=lambda: Quantity(amount=FixedPoint(0), unit=TokenType.BASE))
    # TODO: Support multiple typed balances:
    #     balance: Dict[TokenType, Quantity] = field(default_factory=dict)
    lp_tokens: FixedPoint = FixedPoint(0)

    # non-fungible (identified by key=mint_time, stored as dict)
    longs: dict[FixedPoint, Long] = field(default_factory=dict)
    shorts: dict[FixedPoint, Short] = field(default_factory=dict)
    withdraw_shares: FixedPoint = FixedPoint(0)
    # borrow and  collateral have token type, which is not represented here
    # this therefore assumes that only one token type can be used at any given mint time
    borrows: dict[FixedPoint, Borrow] = field(default_factory=dict)

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)

    def _update_borrows(self, borrows: Iterable[tuple[FixedPoint, Borrow]]) -> None:
        for mint_time, borrow_summary in borrows:
            if mint_time != borrow_summary.start_time:
                raise ValueError(
                    f"The borrow summary key, {mint_time=}, must equal the start time, {borrow_summary.start_time=}"
                )
            if borrow_summary.start_time in self.borrows:  #  entry already exists for this mint_time, so add to it
                self.borrows[borrow_summary.start_time].borrow_amount += borrow_summary.borrow_amount
            else:
                self.borrows.update({borrow_summary.start_time: borrow_summary})
            if self.borrows[borrow_summary.start_time].borrow_amount == FixedPoint(0):
                # Removing the empty borrows allows us to check existance
                # of open borrows using `if self.borrows`
                del self.borrows[borrow_summary.start_time]

    def _update_longs(self, longs: Iterable[tuple[FixedPoint, Long]]) -> None:
        """Helper internal function that updates the data about Longs contained in the Agent's Wallet object

        Arguments
        ----------
        shorts : Iterable[tuple[FixedPoint, Short]]
            A list (or other Iterable type) of tuples that contain a Long object
            and its market-relative mint time
        """
        for mint_time, long in longs:
            if long.balance != FixedPoint(0):
                logging.debug(
                    "agent #%g trade longs, mint_time = %g\npre-trade amount = %s\ntrade delta = %s",
                    self.address,
                    mint_time,
                    self.longs,
                    long,
                )
                if mint_time in self.longs:  #  entry already exists for this mint_time, so add to it
                    old_balance = self.longs[mint_time].balance
                    self.longs[mint_time].balance = old_balance + long.balance
                else:
                    self.longs.update({mint_time: long})
                logging.debug(
                    "agent #%g longs, pre-trade = %s post-trade = %s delta = %s",
                    self.address,
                    old_balance or 0,
                    self.longs[mint_time].balance,
                    self.longs[mint_time].balance - (old_balance or 0),
                )
            if self.longs[mint_time].balance == FixedPoint(0):
                # Removing the empty borrows allows us to check existance
                # of open longs using `if wallet.longs`
                del self.longs[mint_time]
            if mint_time in self.longs and self.longs[mint_time].balance < FixedPoint(0):
                raise AssertionError(f"ERROR: Wallet balance should be >= 0, not {self.longs[mint_time]}.")

    def _update_shorts(self, shorts: Iterable[tuple[FixedPoint, Short]]) -> None:
        """Helper internal function that updates the data about Shortscontained in the Agent's Wallet object

        Arguments
        ----------
        shorts : Iterable[tuple[FixedPoint, Short]]
            A list (or other Iterable type) of tuples that contain a Short object
            and its market-relative mint time
        """
        for mint_time, short in shorts:
            if short.balance != FixedPoint(0):
                old_balance = None
                if mint_time in self.shorts:  #  entry already exists for this mint_time, so add to it
                    self.shorts[mint_time].balance += short.balance
                    old_balance = self.shorts[mint_time].balance
                    self.shorts[mint_time].balance = old_balance + short.balance

                    # if the balance is positive, we are opening a short, therefore do a weighted
                    # mean for the open share price.  this covers an edge case where two shorts are
                    # opened for the same account in the same block.  if the balance is negative, we
                    # don't want to update the open_short_price
                    if short.balance > FixedPoint(0):
                        old_share_price = self.shorts[mint_time].open_share_price
                        self.shorts[mint_time].open_share_price = (
                            short.open_share_price * short.balance + old_share_price * old_balance
                        ) / (short.balance + old_balance)
                else:
                    self.shorts.update({mint_time: short})
                logging.debug(
                    "agent #%g shorts, pre-trade = %s post-trade = %s delta = %s",
                    self.address,
                    old_balance or 0,
                    self.shorts[mint_time].balance,
                    self.shorts[mint_time].balance - (old_balance or 0),
                )
            if self.shorts[mint_time].balance == FixedPoint(0):
                # Removing the empty borrows allows us to check existance
                # of open shorts using `if wallet.shorts`
                del self.shorts[mint_time]
            if mint_time in self.shorts and self.shorts[mint_time].balance < FixedPoint(0):
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

    def check_valid_wallet_state(self, dictionary: dict | None = None) -> None:
        """Test that all wallet state variables are greater than zero"""
        if dictionary is None:
            dictionary = self.__dict__
        check_non_zero(dictionary)

    def copy(self) -> Wallet:
        """Returns a new copy of self"""
        return Wallet(**copy.deepcopy(self.__dict__))

    def update(self, wallet_deltas: WalletDeltas) -> None:
        """Update the agent's wallet

        Arguments
        ----------
        wallet_deltas : AgentDeltas
            The agent's wallet that tracks the amount of assets this agent holds

        Returns
        -------
        This method has no returns. It updates the Agent's Wallet according to the passed parameters
        """
        # track over time the agent's weighted average spend, for return calculation
        for key, value_or_dict in wallet_deltas.copy().__dict__.items():
            if value_or_dict is None or key in ["frozen", "no_new_attribs"]:
                continue
            if key in ["lp_tokens", "withdraw_shares"]:
                logging.debug(
                    "agent #%g %s pre-trade = %g post-trade = %g delta = %g",
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
                    "agent #%g %s pre-trade = %g post-trade = %g delta = %g",
                    self.address,
                    key,
                    float(getattr(self, key).amount),
                    float(getattr(self, key).amount + value_or_dict.amount),
                    float(value_or_dict.amount),
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
            self.check_valid_wallet_state(self.__dict__)

"""Empty accounts for engaging with smart contracts"""
from __future__ import annotations

import copy
import logging
from dataclasses import dataclass, field
from typing import Any, Iterable

from fixedpointmath import FixedPoint
from hexbytes import HexBytes

from elfpy import check_non_zero
from elfpy.types import Quantity, TokenType
from elfpy.wallet.wallet import Long, Short
from elfpy.wallet.wallet_deltas import WalletDeltas


@dataclass()
class EthWallet:
    r"""Stateful variable for storing what is in the agent's wallet

    Arguments
    ----------
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
    address: HexBytes

    # fungible
    balance: Quantity = field(default_factory=lambda: Quantity(amount=FixedPoint(0), unit=TokenType.BASE))
    # TODO: Support multiple typed balances:
    #     balance: Dict[TokenType, Quantity] = field(default_factory=dict)
    lp_tokens: FixedPoint = FixedPoint(0)

    # non-fungible (identified by key=mint_time, stored as dict)
    longs: dict[FixedPoint, Long] = field(default_factory=dict)
    shorts: dict[FixedPoint, Short] = field(default_factory=dict)
    withdraw_shares: FixedPoint = FixedPoint(0)

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)

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
                    self.longs[mint_time].balance += long.balance
                else:
                    self.longs.update({mint_time: long})
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
                logging.debug(
                    "agent #%g trade shorts, mint_time = %s\npre-trade amount = %s\ntrade delta = %s",
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
                    if short.balance > FixedPoint(0):
                        old_share_price = self.shorts[mint_time].open_share_price
                        self.shorts[mint_time].open_share_price = (
                            short.open_share_price * short.balance + old_share_price * old_balance
                        ) / (short.balance + old_balance)
                else:
                    self.shorts.update({mint_time: short})
            if self.shorts[mint_time].balance == FixedPoint(0):
                # Removing the empty borrows allows us to check existance
                # of open shorts using `if wallet.shorts`
                del self.shorts[mint_time]
            if mint_time in self.shorts and self.shorts[mint_time].balance < FixedPoint(0):
                raise AssertionError(f"ERROR: Wallet balance should be >= 0, not {self.shorts[mint_time]}.")

    def check_valid_wallet_state(self, dictionary: dict | None = None) -> None:
        """Test that all wallet state variables are greater than zero"""
        if dictionary is None:
            dictionary = self.__dict__
        check_non_zero(dictionary)

    def copy(self) -> EthWallet:
        """Returns a new copy of self"""
        return EthWallet(**copy.deepcopy(self.__dict__))

    def update(self, wallet_deltas: WalletDeltas) -> None:
        """Update the agent's wallet in-place

        Arguments
        ----------
        wallet_deltas : AgentDeltas
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
                        "agent #%g %s pre-trade = %.0g\npost-trade = %1g\ndelta = %1g",
                        self.address,
                        key,
                        getattr(self, key),
                        getattr(self, key) + value_or_dict,
                        value_or_dict,
                    )
                    self[key] += value_or_dict
                # handle updating a Quantity
                case "balance":
                    logging.debug(
                        "agent #%g %s pre-trade = %.0g\npost-trade = %1g\ndelta = %1g",
                        self.address,
                        key,
                        float(getattr(self, key).amount),
                        float(getattr(self, key).amount + value_or_dict.amount),
                        float(value_or_dict.amount),
                    )
                    getattr(self, key).amount += value_or_dict.amount
                # handle updating a dict, which have mint_time attached
                case "longs":
                    self._update_longs(value_or_dict.items())
                case "shorts":
                    self._update_shorts(value_or_dict.items())
                case _:
                    raise ValueError(f"wallet_{key=} is not allowed.")
            self.check_valid_wallet_state(self.__dict__)

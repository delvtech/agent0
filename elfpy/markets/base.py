"""Market simulators store state information when interfacing AMM pricing models with users."""
from __future__ import annotations
from abc import ABC, abstractmethod

import logging
from enum import Enum
from typing import TYPE_CHECKING, Generic, TypeVar
from dataclasses import dataclass

import numpy as np

import elfpy
import elfpy.agents.wallet as wallet
import elfpy.types as types

if TYPE_CHECKING:
    import elfpy.markets.pricing_models.base_pm as base_pm
    import elfpy.time as time

# all 1subclasses of Market need to pass subclasses of MarketAction, MarketState and MarketDeltas
class MarketTypes(Enum):
    """The types of markets that exist"""

    HYPERDRIVE = "hyperdrive"
    BORROW = "borrow"


class MarketActionType(Enum):
    r"""
    The descriptor of an action in a market
    """
    NULL_ACTION = "null action"


@types.freezable(frozen=False, no_new_attribs=True)
@dataclass
class MarketAction:
    r"""Market action specification"""

    # these two variables are required to be set by the strategy
    action_type: Enum
    # the agent's wallet
    wallet: wallet.Wallet


@types.freezable(frozen=True, no_new_attribs=True)
@dataclass
class MarketDeltas:
    r"""Specifies changes to values in the market"""


@types.freezable(frozen=True, no_new_attribs=True)
@dataclass
class MarketTradeResult:
    r"""The result to a market of performing a trade"""


@types.freezable(frozen=False, no_new_attribs=False)
@dataclass
class BaseMarketState:
    r"""The state of an AMM

    Implements a class for all that that an AMM smart contract would hold or would have access to
    For example, reserve numbers are local state variables of the AMM.
    """

    # TODO: have this be generic enough that any subclass can apply deltas?
    def apply_delta(self, delta: MarketDeltas) -> None:
        r"""Applies a delta to the market state."""
        raise NotImplementedError

    # TODO: have this be generic enough that any subclass can copy?
    def copy(self) -> BaseMarketState:
        """Returns a new copy of self"""
        raise NotImplementedError

    def check_market_non_zero(self):
        r"""Checks that all market variables are non-zero within a precision threshold"""
        # TODO: issue #146
        # this is an imperfect solution to rounding errors, but it works for now
        for key, value in self.__dict__.items():
            if 0 > value > -elfpy.PRECISION_THRESHOLD:
                logging.debug(
                    ("%s=%s is negative within PRECISION_THRESHOLD=%f, setting it to 0"),
                    key,
                    value,
                    elfpy.PRECISION_THRESHOLD,
                )
                setattr(self, key, 0)
            else:
                assert (
                    value > -elfpy.PRECISION_THRESHOLD
                ), f"MarketState values must be > {-elfpy.PRECISION_THRESHOLD}. Error on {key} = {value}"


# TODO: see if we can't restrict these types to MarketAction, MarketState and MarketDeltas such that all
# subclasses of Market need to pass subclasses of MarketAction, MarketState and MarketDeltas
Action = TypeVar("Action", bound="MarketAction")
State = TypeVar("State", bound="BaseMarketState")
Deltas = TypeVar("Deltas", bound="MarketDeltas")


class Market(ABC, Generic[State, Deltas]):
    r"""Market state simulator

    Holds state variables for market simulation and executes trades.
    The Market class executes trades by updating market variables according to the given pricing model.
    It also has some helper variables for assessing pricing model values given market conditions.
    """

    @property
    @abstractmethod
    def name(self) -> types.MarketType:
        """Returns the name of the Market"""

    def __init__(
        self,
        market_state: State,
        pricing_model: base_pm.PricingModel,
        global_time: time.Time,
    ):
        self.market_state = market_state
        self.pricing_model = pricing_model
        self._time = global_time

    @abstractmethod
    def perform_action(self, action_details: types.Trade) -> tuple[int, wallet.Wallet, Deltas]:
        """Performs an action in the market without updating it."""
        raise NotImplementedError

    @property
    def time(self) -> float:
        """Returns the global time"""
        return self._time.time

    def tick(self, delta_time: float) -> None:
        """Increments the time member variable"""
        self._time.time += delta_time

    def get_market_state_string(self) -> str:
        """Returns a formatted string containing all of the Market class member variables"""
        strings = [f"{attribute} = {value}" for attribute, value in self.__dict__.items()]
        return "\n".join(strings)

    def check_market_updates(self, market_deltas: MarketDeltas) -> None:
        """Check market update values to make sure they are valid"""
        for key, value in market_deltas.__dict__.items():
            if value:  # check that it's instantiated and non-empty
                print(f"check_market_updateS(): key = {key}, value = {value}")
                value_to_check = value
                if isinstance(value, types.Quantity):
                    value_to_check = value.amount
                else:
                    assert np.isfinite(
                        value_to_check
                    ), f"markets.update_market: ERROR: market delta key {key} is not finite."

    def update_market(self, market_deltas: MarketDeltas) -> None:
        """
        Increments member variables to reflect current market conditions
        """
        self.check_market_updates(market_deltas)  # check that market deltas are valid
        self.market_state.apply_delta(market_deltas)
        self.market_state.check_market_non_zero()  # check reserves are non-zero within precision threshold

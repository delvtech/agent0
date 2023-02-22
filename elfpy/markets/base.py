"""Market simulators store state information when interfacing AMM pricing models with users."""
from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Generic, TypeVar
from dataclasses import dataclass

import elfpy.agents.wallet as wallet
import elfpy.types as types

if TYPE_CHECKING:
    from elfpy.pricing_models.base import PricingModel


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

    def __str__(self):
        r"""Return a description of the Action"""
        output_string = f"AGENT ACTION:\nagent #{self.wallet.address:03.0f}"
        for key, value in self.__dict__.items():
            if key == "action_type":
                output_string += f" execute {value}()"
            elif key in ["trade_amount", "mint_time"] or key not in [
                "wallet_address",
                "agent",
            ]:
                output_string += f" {key}: {value}"
        return output_string


@types.freezable(frozen=True, no_new_attribs=True)
@dataclass
class MarketDeltas:
    r"""Specifies changes to values in the market"""
    d_lp_total_supply: float = 0.0

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __str__(self):
        output_string = f"BaseMarketDeltas(\n\t{self.d_lp_total_supply=})"
        return output_string


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

    Attributes
    ----------
    lp_total_supply: float
        Amount of lp tokens
    """

    # lp reserves
    lp_total_supply: float = 0.0

    # TODO: have this be generic enough that any subclass can apply deltas?
    def apply_delta(self, delta: MarketDeltas) -> None:
        r"""Applies a delta to the market state."""
        raise NotImplementedError

    # TODO: have this be generic enough that any subclass can copy?
    def copy(self) -> BaseMarketState:
        """Returns a new copy of self"""
        return BaseMarketState(lp_total_supply=self.lp_total_supply)

    def __str__(self):
        output_string = "MarketState(\n" "\tlp_total_supply(\n" f"\t\t{self.lp_total_supply=},\n" "\t),\n" ")"
        return output_string


# TODO: see if we can't restrict these types to MarketState and MarketDeltas such that all
# subclasses of Market need to pass subclasses of MarketState and MarketDeltas
State = TypeVar("State")
Deltas = TypeVar("Deltas")


class Market(Generic[State, Deltas]):
    r"""Market state simulator

    Holds state variables for market simulation and executes trades.
    The Market class executes trades by updating market variables according to the given pricing model.
    It also has some helper variables for assessing pricing model values given market conditions.
    """

    def __init__(
        self,
        pricing_model: PricingModel,
        market_state: State,
    ):
        # market state variables
        self.pricing_model = pricing_model
        self.market_state = market_state
        self.time: float = 0  # t: time normalized to 1 year, i.e. 0.5 = 1/2 year

    def perform_action(self, action_details: tuple[int, Enum]) -> tuple[int, wallet.Wallet, Deltas]:
        """Performs an action in the market without updating it."""
        raise NotImplementedError

    def update_market(self, market_deltas: Deltas) -> None:
        """
        Updates the market with market deltas.
        """
        raise NotImplementedError

    def get_market_state_string(self) -> str:
        """Returns a formatted string containing all of the Market class member variables"""
        strings = [f"{attribute} = {value}" for attribute, value in self.__dict__.items()]
        state_string = "\n".join(strings)
        return state_string

    def tick(self, delta_time: float) -> None:
        """Increments the time member variable"""
        self.time += delta_time

"""Market simulators store state information when interfacing AMM pricing models with users."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Generic, TypeVar

import elfpy.types as types
from elfpy.math import FixedPoint

if TYPE_CHECKING:
    from elfpy.wallet.wallet_deltas import WalletDeltas
    from elfpy.wallet.wallet import Wallet
    from elfpy.markets.base.base_pricing_model import BasePricingModel
    import elfpy.time as time


class MarketActionType(Enum):
    r"""
    The descriptor of an action in a market
    """
    NULL_ACTION = "null action"


# all subclasses of Market need to pass subclasses of MarketAction, MarketState and MarketDeltas
Action = TypeVar("Action", bound="BaseMarketAction")
Deltas = TypeVar("Deltas", bound="BaseMarketDeltas")
State = TypeVar("State", bound="BaseMarketState")
PricingModel = TypeVar("PricingModel", bound="BasePricingModel")


@types.freezable(frozen=False, no_new_attribs=True)
@dataclass
class BaseMarketAction(Generic[Action]):
    r"""Market action specification"""

    action_type: Enum  # these two variables are required to be set by the strategy
    wallet: Wallet  # the agent's wallet


@types.freezable(frozen=True, no_new_attribs=True)
@dataclass
class BaseMarketDeltas:
    r"""Specifies changes to values in the market"""


@types.freezable(frozen=True, no_new_attribs=True)
@dataclass
class BaseMarketActionResult:
    r"""The result to a market of performing a trade"""


@types.freezable(frozen=False, no_new_attribs=False)
@dataclass
class BaseMarketState:
    r"""The state of an AMM

    Implements a class for all that an AMM smart contract would hold or would have access to.
    For example, reserve numbers are local state variables of the AMM.
    """

    def apply_delta(self, delta: BaseMarketDeltas) -> None:
        r"""Applies a delta to the market state."""
        raise NotImplementedError

    def copy(self) -> BaseMarketState:
        """Returns a new copy of self"""
        raise NotImplementedError

    def check_valid_market_state(self, dictionary: dict | None = None) -> BaseMarketState:
        """Returns a new copy of self"""
        raise NotImplementedError


class BaseMarket(Generic[State, Deltas, PricingModel]):
    r"""Market state simulator

    Holds state variables for market simulation and executes trades.
    The Market class executes trades by updating market variables according to the given pricing model.
    It also has some helper variables for assessing pricing model values given market conditions.
    """

    def __init__(
        self,
        pricing_model: PricingModel,
        market_state: State,
        block_time: time.BlockTime,
    ):
        self.pricing_model = pricing_model
        self.market_state = market_state
        self.block_time = block_time

    @property
    def latest_checkpoint_time(self) -> FixedPoint:
        """Gets the most recent checkpoint time."""
        raise NotImplementedError

    def perform_action(self, action_details: tuple[int, Enum]) -> tuple[int, WalletDeltas, Deltas]:
        """Performs an action in the market without updating it."""
        raise NotImplementedError

    def update_market(self, market_deltas: Deltas) -> None:
        """Increments member variables to reflect current market conditions."""
        self.market_state.apply_delta(market_deltas)
        self.market_state.check_valid_market_state(self.market_state.__dict__)

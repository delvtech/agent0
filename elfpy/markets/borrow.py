"""Market simulators store state information when interfacing AMM pricing models with users."""
from __future__ import annotations  # types will be strings by default in 3.11

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any

import numpy as np

import elfpy.markets.base as base_market

import elfpy.types as types


class MarketActionType(Enum):
    r"""
    Enumerate actions available in this market
    """

    OPEN_BORROW = "open_borrow"
    CLOSE_BORROW = "close_borrow"


@types.freezable(frozen=True, no_new_attribs=True)
@dataclass
class MarketDeltas(base_market.MarketDeltas):
    r"""Specifies changes to values in the market"""

    d_borrow_shares: float = 0.0  # borrow is always in DAI
    d_collateral: types.Quantity = field(default_factory=lambda: types.Quantity(amount=0, unit=types.TokenType.PT))
    d_borrow_outstanding: float = 0.0  # changes based on borrow_shares * borrow_share_price
    d_borrow_closed_interest: float = 0.0  # realized interest from closed borrows


@types.freezable(frozen=True, no_new_attribs=True)
@dataclass
class AgentDeltas:
    r"""Specifies changes to values in the agent's wallet"""

    # agent identifier
    address: int

    # fungible assets, but collateral can be two TokenTypes
    borrow: float = 0
    collateral: types.Quantity = field(default_factory=lambda: types.Quantity(unit=types.TokenType.PT, amount=0))

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)


@types.freezable(frozen=False, no_new_attribs=False)
@dataclass
class MarketState(base_market.BaseMarketState):
    r"""The state of an AMM

    Implements a class for all that that an AMM smart contract would hold or would have access to
    For example, reserve numbers are local state variables of the AMM.  The vault_apr will most
    likely be accessible through the AMM as well.

    Attributes
    ----------
    loan_to_value_ratio: float
        The maximum loan to value ratio a collateral can have before liquidations occur.
    borrow_shares: float
        Quantity of borrow asset that has been lent out by the market
    deposit_shares: float
        Quantity of deposit asset that has been deposited into the market
    borrow_share_price: float
        The "share price" of the borrowed asset tracks the cumulative amount owed over time, indexed to 1 at the start
    deposit_share_price: float
        The "share price" of the deposited asset tracks the cumulative amount owed over time, indexed to 1 at the start
    lending_rate: float
        The rate a user receives when lending out assets
    spread_ratio: float
        The ratio of the borrow rate to the lending rate
    """

    # dataclasses can have many attributes
    # pylint: disable=too-many-instance-attributes

    # borrow ratios
    loan_to_value_ratio: Dict[types.TokenType, float] = field(
        default_factory=dict
    )  # 99% loan to value ratio corresponds to 1% haircut

    # trading reserves
    borrow_shares: float = field(default=0.0)  # allows tracking the increasing value of loans over time
    collateral: Dict[types.TokenType, float] = field(default_factory=dict)

    borrow_outstanding: float = field(default=0.0)  # sum of Dai that went out the door
    borrow_closed_interest: float = field(default=0.0)  # interested collected from closed borrows

    # share prices used to track amounts owed
    borrow_share_price: float = field(default=1.0)
    # number of TokenA between t=0 and t=1
    deposit_share_price: Dict[types.TokenType, float] = field(
        default_factory=lambda: {types.TokenType.BASE: 1.0, types.TokenType.PT: 1.0}
    )
    # number of TokenA you get for TokenB
    deposit_spot_price: Dict[types.TokenType, float] = field(default_factory=dict)

    # borrow and lending rates
    lending_rate: float = field(default=0.01)  # 1% per year
    # borrow rate is lending_rate * spread_ratio
    spread_ratio: float = field(default=1.25)

    @property
    def borrow_amount(self) -> float:
        """The amount of borrowed asset in the market"""
        return self.borrow_shares * self.borrow_share_price

    @property
    def deposit_amount(self) -> dict[types.TokenType, float]:
        """The amount of deposited asset in the market"""
        return {key: value * self.deposit_spot_price[key] for key, value in self.collateral.items()}

    @property
    def total_market_profit(self) -> float:
        """
        From the market's perspective, the profit is the difference between the borrowed and deposited assets
        """
        # how do we calcualte this?
        # return self.borrow_asset - self.deposit_asset
        # the profit is the borrow_shares * borrow_share_price - borrow_outstanding
        # TEST: when borrow goes down, what happens? => correctly captured by borrow_closed_interest
        # TEST: do we pay out interest on collateral?

        # uncollected profit = borrow_shares * share_price - borrow_outstanding
        # collected profit = borrow_closed_interest

        return self.borrow_shares * self.borrow_share_price - self.borrow_outstanding + self.borrow_closed_interest

    @property
    def borrow_rate(self) -> float:
        """The borrow rate is the lending rate multiplied by the spread ratio"""
        return self.lending_rate * self.spread_ratio

    def apply_delta(self, delta: MarketDeltas) -> None:
        r"""Applies a delta to the market state."""
        self.borrow_shares += delta.d_borrow_shares
        deposit_unit = delta.d_collateral.unit
        self.collateral[deposit_unit] += delta.d_collateral.amount
        assert self.borrow_shares > 0, f"BorrowMarket:MarketState borrow shares must be > 0, not {self.borrow_shares=}."
        assert (
            self.collateral[deposit_unit] > 0
        ), f"BorrowMarket:MarketState deposit shares must be > 0, not {self.collateral[deposit_unit]=}."


@types.freezable(frozen=False, no_new_attribs=True)
@dataclass
class MarketAction(base_market.MarketAction):
    r"""Market action specification"""

    # these two variables are required to be set by the strategy
    action_type: MarketActionType
    # amount to supply for the action
    collateral: types.Quantity
    spot_price: Optional[float] = None


class Market:
    r"""Market state simulator

    Holds state variables for market simulation and executes trades.
    The Market class executes trades by updating market variables according to the given pricing model.
    It also has some helper variables for assessing pricing model values given market conditions.


    available_actions: list[MarketActionType]
        List of actions available in this market (used by simulator to determine which actions to offer to the agent)
    """

    available_actions = [MarketActionType.OPEN_BORROW, MarketActionType.CLOSE_BORROW]

    def __init__(
        self,
        market_state: MarketState,
    ):
        # market state variables
        self.time: float = 0  # t: timefrac unit is time normalized to 1 year, i.e. 0.5 = 1/2 year
        self.market_state: MarketState = market_state

    def check_action(self, agent_action: MarketAction) -> None:
        r"""Ensure that the agent action is an allowed action for this market

        Parameters
        ----------
        agent_action : MarketAction
            Checks if the agent_action.action_type is in the list of all available actions for this market

        Returns
        -------
        None
        """
        if agent_action.action_type not in self.available_actions:
            raise ValueError(f"ERROR: agent_action.action_type must be in {self.available_actions=}")

    def perform_action(self, action_details: tuple[int, MarketAction]) -> tuple[int, AgentDeltas, MarketDeltas]:
        r"""
        Execute a trade in the Borrow Market

        open_borrow
            value the collateral being offered and return a borrow amount of the maximum amount that can be borrowed

        close_borrow
            value the collateral being asked to be withdrawn and offer it back in exchange for the value owed

        .. todo: change agent deltas from Wallet type to its own type
        """
        agent_id, agent_action = action_details
        # TODO: add use of the Quantity type to enforce units while making it clear what units are being used
        # issue 216
        self.check_action(agent_action)
        market_deltas = MarketDeltas()
        # for each position, specify how to formulate trade and then execute
        # current assumption is that the user will borrow the maximum LTV against the collateral they are offering
        if agent_action.action_type == MarketActionType.OPEN_BORROW:  # open a borrow position
            market_deltas, agent_deltas = self.open_borrow(
                wallet_address=agent_action.wallet.address,
                collateral=agent_action.collateral,  # in BASE or PT, the collateral being offered
            )
        elif agent_action.action_type == MarketActionType.CLOSE_BORROW:  # close a borrow position
            market_deltas, agent_deltas = self.close_borrow(
                wallet_address=agent_action.wallet.address,
                collateral=agent_action.collateral,  # in BASE or PT, the collateral being asked for
            )
        else:
            raise ValueError(f'ERROR: Unknown trade type "{agent_action.action_type}".')
        logging.debug(
            "%s\n%s\nagent_deltas = %s\npre_trade_market = %s",
            agent_action,
            market_deltas,
            agent_deltas,
            self.market_state,
        )
        return agent_id, agent_deltas, market_deltas

    def open_borrow(
        self,
        wallet_address: int,
        collateral: types.Quantity,  # in amount of collateral type (BASE or PT)
        spot_price: Optional[float] = None,
    ) -> tuple[MarketDeltas, AgentDeltas]:
        """
        execute a borrow as requested by the agent, return the market and agent deltas
        agents decides what COLLATERAL to put IN then we calculate how much BASE OUT to give them
        """
        _, borrow_amount_in_base = self.value_collateral(collateral, spot_price)

        # market reserves are stored in shares, so we need to convert the amount to shares
        # borrow asset increases because it's being lent out
        # collateral increases because it's being deposited
        market_deltas = MarketDeltas(
            d_borrow_shares=borrow_amount_in_base / self.market_state.borrow_share_price,
            d_collateral=types.Quantity(
                unit=collateral.unit,
                amount=collateral.amount / self.market_state.deposit_share_price[collateral.unit],
            ),
        )

        # agent wallet is stored in token units (BASE or PT) so we pass back the deltas in those units
        agent_deltas = AgentDeltas(address=wallet_address, borrow=borrow_amount_in_base, collateral=collateral)
        return market_deltas, agent_deltas

    def close_borrow(
        self,
        wallet_address: int,
        collateral: types.Quantity,  # in amount of collateral type (BASE or PT)
        spot_price: Optional[float] = None,
    ) -> tuple[MarketDeltas, AgentDeltas]:
        """
        close a borrow as requested by the agent, return the market and agent deltas
        agent asks for COLLATERAL OUT and we tell them how much BASE to put IN (then check if they have it)
        """
        _, borrow_amount_in_base = self.value_collateral(collateral, spot_price)

        # market reserves are stored in shares, so we need to convert the amount to shares
        # borrow asset increases because it's being lent out
        # deposit asset increases because it's being deposited
        market_deltas = MarketDeltas(
            d_borrow_shares=borrow_amount_in_base / self.market_state.borrow_share_price,
            d_collateral=types.Quantity(
                unit=collateral.unit,
                amount=collateral.amount / self.market_state.deposit_share_price[collateral.unit],
            ),
        )

        # agent wallet is stored in token units (BASE or PT) so we pass back the deltas in those units
        agent_deltas = AgentDeltas(address=wallet_address, borrow=borrow_amount_in_base, collateral=-collateral)
        return market_deltas, agent_deltas

    def value_collateral(self, collateral: types.Quantity, spot_price: Optional[float]):
        """Values collateral and returns how much the agent can borrow against it"""
        collateral_value_in_base = collateral.amount  # if collateral is BASE
        if collateral.unit == types.TokenType.PT:
            collateral_value_in_base = collateral.amount * (spot_price or 1)
        print(f"returning {collateral.unit=} from {collateral=}")
        borrow_amount_in_base = collateral_value_in_base * self.market_state.loan_to_value_ratio[collateral.unit]
        return collateral_value_in_base, borrow_amount_in_base

    def update_market(self, market_deltas: MarketDeltas) -> None:
        """
        Increments member variables to reflect current market conditions

        .. todo:: This order is weird. We should move everything in apply_update to update_market,
            and then make a new function called check_update that runs these checks
        """
        self.check_market_updates(market_deltas)
        self.market_state.apply_delta(market_deltas)

    def check_market_updates(self, market_deltas: MarketDeltas) -> None:
        """Check market update values to make sure they are valid"""
        for key, value in market_deltas.__dict__.items():
            if value:  # check that it's instantiated and non-empty
                assert np.isfinite(value), f"markets.update_market: ERROR: market delta key {key} is not finite."

    def log_market_step_string(self) -> None:
        """Logs the current market step"""
        # TODO: This is a HACK to prevent test_sim from failing on market shutdown
        # when the market closes, the share_reserves are 0 (or negative & close to 0) and several logging steps break
        logging.debug(
            ("t = %g\nborrow_asset = %g\ndeposit_assets = %g\nborrow_rate = %g"),
            self.time,
            self.market_state.borrow_amount,
            self.market_state.deposit_amount,
            self.market_state.borrow_rate,
        )

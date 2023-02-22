"""Market simulators store state information when interfacing AMM pricing models with users."""
from __future__ import annotations  # types will be strings by default in 3.11

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any

import elfpy.markets.base as base_market
import numpy as np
from elfpy.wallet import Wallet

import elfpy.types as types
from elfpy.types import freezable, TokenType


class MarketActionType(Enum):
    r"""
    Enumerate actions available in this market
    """

    OPEN_BORROW = "open_borrow"
    CLOSE_BORROW = "close_borrow"


@freezable(frozen=True, no_new_attribs=True)
@dataclass
class MarketDeltas(base_market.MarketDeltas):
    r"""Specifies changes to values in the market"""

    d_borrow_shares: float = 0.0
    d_deposit_shares: types.Quantity = field(default_factory=lambda: types.Quantity(unit=TokenType.PT, amount=0))

    def __str__(self):
        return f"MarketDeltas(\n\t{self.d_borrow_asset=},\n\t{self.d_deposit_shares=},\n)"


@freezable(frozen=True, no_new_attribs=True)
@dataclass
class BorrowDeltas:
    r"""Specifies changes to values in the agent's wallet"""

    # agent identifier
    address: int

    # fungible assets, but collateral can be two TokenTypes
    base: float = 0
    collateral: types.Quantity = field(default_factory=lambda: types.Quantity(unit=TokenType.PT, amount=0))

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)

    def __str__(self) -> str:
        return "BorrowDeltas(\n" f"\t{self.address=},\n" f"\t{self.base=},\n" f"\t{self.collateral=},\n" ")"


@freezable(frozen=False, no_new_attribs=False)
@dataclass
class MarketState(base_market.BaseMarketState):
    r"""The state of an AMM

    Implements a class for all that that an AMM smart contract would hold or would have access to
    For example, reserve numbers are local state variables of the AMM.  The vault_apr will most
    likely be accessible through the AMM as well.

    Attributes
    ----------
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
    haircut: float
        Amount of the deposited asset that is not available for borrowing
    """

    # dataclasses can have many attributes
    # pylint: disable=too-many-instance-attributes

    # trading reserves
    borrow_shares: float = 0.0
    deposit_shares: Dict[TokenType, float] = field(default_factory=dict)

    # share prices used to track amounts owed
    borrow_share_price: float = 1.0
    deposit_share_price: Dict[TokenType, float] = field(default_factory=dict)

    # borrow and lending rates
    lending_rate: float = 0.01  # 1% per year
    spread_ratio = 1.25

    # borrow ratios
    haircut: float = 0.03  # 3% haircut equates to 97% loan to value ratio

    @property
    def borrow_amount(self) -> float:
        """The amount of borrowed asset in the market"""
        return self.borrow_shares * self.borrow_share_price

    @property
    def deposit_amount(self) -> dict[TokenType, float]:
        """The amount of deposited asset in the market"""
        return {k: v * self.deposit_share_price[k] for k, v in self.deposit_shares.items()}

    @property
    def profit(self) -> float:
        """The profit is the difference between the borrowed and deposited assets"""
        # how do we calcualte this?
        # return self.borrow_asset - self.deposit_asset
        return 0

    @property
    def loan_to_value_ratio(self) -> float:
        """The loan to value ratio defines how much someone can borrow as a ratio of their deposited asset"""
        return 1 - self.haircut

    @property
    def borrow_rate(self) -> float:
        """The borrow rate is the lending rate multiplied by the spread ratio"""
        return self.lending_rate * self.spread_ratio

    def apply_delta(self, delta: MarketDeltas) -> None:
        r"""Applies a delta to the market state."""
        self.borrow_shares += delta.d_borrow_shares
        deposit_unit = delta.unit
        self.deposit_shares[deposit_unit] += delta.d_deposit_shares
        assert (
            self.borrow_shares > 0
        ), f"BorrowMarket:MarketState borrow shares must be > 0. Error on {self.borrow_shares=}"
        assert (
            self.deposit_shares[deposit_unit] > 0
        ), f"BorrowMarket:MarketState deposit shares must be > 0. Error on {self.deposit_shares[deposit_unit]=}"

    def __str__(self):
        return (
            "BorrowMarket:MarketState(\n"
            "\treserves(\n"
            f"\t\t{self.borrow_amount=},\n"
            f"\t\t{self.deposit_amount=},\n"
            "\t),\n"
            "\tvariables(\n"
            f"\t\t{self.lending_rate=},\n"
            f"\t\t{self.spread_ratio=},\n"
            f"\t\t{self.haircut=},\n"
            "\t)\n"
            ")"
        )


@freezable(frozen=False, no_new_attribs=True)
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

    def value_collateral(self, collateral: types.Quantity, spot_price: Optional[float]):
        """Values collateral and returns how much the agent can borrow against it"""
        collateral_value_in_base = collateral.amount  # if collateral is BASE
        if collateral.unit == TokenType.PT:
            collateral_value_in_base = collateral.amount * (spot_price or 0)
        borrow_amount_in_base = collateral_value_in_base * self.market_state.loan_to_value_ratio
        return collateral_value_in_base, borrow_amount_in_base

    def trade_and_update(self, action_details: tuple[int, MarketAction]) -> tuple[int, Wallet, MarketDeltas]:
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
        agent_deltas = Wallet()
        # for each position, specify how to formulate trade and then execute
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
    ) -> tuple[MarketDeltas, BorrowDeltas]:
        """
        execute a borrow as requested by the agent, return the market and agent deltas
        agents decides what COLLATERAL to put IN then we calculate how much BASE OUT to give them
        """
        collateral_amount_in_base, borrow_amount_in_base = self.value_collateral(collateral, spot_price)

        # market reserves are stored in shares, so we need to convert the amount to shares
        # borrow asset increases because it's being lent out
        # deposit asset increases because it's being deposited
        market_deltas = MarketDeltas(
            d_borrow_shares=borrow_amount_in_base / self.borrow_share_price,
            d_deposit_shares=types.Quantity(
                unit=collateral.unit,
                amount=collateral.amount / self.deposit_share_price[collateral.unit],
            ),
        )

        # agent wallet is stored in token units (BASE or PT) so we pass back the deltas in those units
        agent_deltas = BorrowDeltas(address=wallet_address, base=borrow_amount_in_base, collateral=-collateral)
        return market_deltas, agent_deltas

    def close_borrow(
        self,
        wallet_address: int,
        collateral: types.Quantity,  # in amount of collateral type (BASE or PT)
        spot_price: Optional[float] = None,
    ) -> tuple[MarketDeltas, BorrowDeltas]:
        """
        close a borrow as requested by the agent, return the market and agent deltas
        agent asks for COLLATERAL OUT and we tell them how much BASE to put IN (then check if they have it)
        """
        collateral_value_in_base, borrow_amount_in_base = self.value_collateral(collateral, spot_price)

        # market reserves are stored in shares, so we need to convert the amount to shares
        # borrow asset increases because it's being lent out
        # deposit asset increases because it's being deposited
        market_deltas = MarketDeltas(
            d_borrow_shares=borrow_amount_in_base / self.market_state.borrow_share_price,
            d_deposit_shares=types.Quantity(
                unit=collateral.unit,
                amount=collateral.amount / self.deposit_share_price[collateral.unit],
            ),
        )

        # agent wallet is stored in token units (BASE or PT) so we pass back the deltas in those units
        agent_deltas = BorrowDeltas(address=wallet_address, base=borrow_amount_in_base, collateral=-collateral)
        return market_deltas, agent_deltas

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
            (
                "t = %g"
                "\nborrow_asset = %g"
                "\ndeposit_assets = %g"
                "\nborrow_rate = %g"
                "\nz = %g"
                "\nx_b = %g"
                "\ny_b = %g"
                "\np = %s"
                "\npool apr = %s"
            ),
            self.time,
            self.market_state.borrow_amount,
            self.market_state.deposit_amount,
            self.market_state.borrow_rate,
        )

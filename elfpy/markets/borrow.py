"""Market simulators store state information when interfacing AMM pricing models with users."""
from __future__ import annotations  # types will be strings by default in 3.11

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, Union

import elfpy.markets.base as base_market
from elfpy.pricing_models.base import PricingModel
import elfpy.agents.wallet as wallet

import elfpy.types as types

# TODO: for now...
# pylint: disable=duplicate-code


class MarketActionType(Enum):
    r"""Enumerate actions available in this market"""

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
    d_borrow_share_price: float = 0.0  # used only when time ticks and interest accrues


@types.freezable(frozen=True, no_new_attribs=True)
@dataclass
class AgentDeltas:
    r"""Specifies changes to values in the agent's wallet

    Attributes
    ----------
    address: int
        agent address
    borrow: float
        how much base asset has been borrowed
    collateral: Quantity
        how much has been offerd as collateral
    """

    # agent identifier
    address: int

    # fungible assets, but collateral can be two TokenTypes
    borrows: wallet.Borrow
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
    For example, reserve numbers are local state variables of the AMM.  The borrow_rate will most
    likely be accessible through the AMM as well.

    Attributes
    ----------
    loan_to_value_ratio: float
        The maximum loan to value ratio a collateral can have before liquidations occur.
    borrow_shares: float
        Accounting units for borrow assets that has been lent out by the market, allows tracking of interest
    collateral: dict[TokenType, float]
        Amount of collateral that has been deposited into the market
    borrow_outstanding: float
        The amount of borrowed asset that has been lent out by the market, without accounting for interest
    borrow_share_price: float
        The "share price" of the borrowed asset tracks the cumulative amount owed over time, indexed to 1 at the start
    borrow_closed_interest: float
        The interest that has been collected from closed borrows, to capture realized profit
    collateral_spot_price: float
        The spot price of the collateral asset, to allow updating valuation across time
    lending_rate: float
        The rate a user receives when lending out assets
    spread_ratio: float
        The ratio of the borrow rate to the lending rate
    """

    # dataclasses can have many attributes
    # pylint: disable=too-many-instance-attributes

    # borrow ratios
    loan_to_value_ratio: Union[Dict[types.TokenType, float], float] = field(
        default_factory=lambda: {token_type: 0.97 for token_type in types.TokenType}
    )

    # trading reserves
    borrow_shares: float = field(default=0.0)  # allows tracking the increasing value of loans over time
    collateral: Dict[types.TokenType, float] = field(default_factory=dict)

    borrow_outstanding: float = field(default=0.0)  # sum of Dai that went out the door
    borrow_closed_interest: float = field(default=0.0)  # interested collected from closed borrows

    # share prices used to track amounts owed
    borrow_share_price: float = field(default=1.0)
    init_borrow_share_price: float = field(default=borrow_share_price)  # allow not setting init_share_price
    # number of TokenA you get for TokenB
    collateral_spot_price: Dict[types.TokenType, float] = field(default_factory=dict)

    # borrow and lending rates
    lending_rate: float = field(default=0.01)  # 1% per year
    # borrow rate is lending_rate * spread_ratio
    spread_ratio: float = field(default=1.25)

    def __post_init__(self) -> None:
        r"""Initialize the market state"""
        # initialize loan to value ratios if a float is passed
        if isinstance(self.loan_to_value_ratio, float):
            self.loan_to_value_ratio = {token_type: self.loan_to_value_ratio for token_type in types.TokenType}

    @property
    def borrow_amount(self) -> float:
        """The amount of borrowed asset in the market"""
        return self.borrow_shares * self.borrow_share_price

    @property
    def deposit_amount(self) -> dict[types.TokenType, float]:
        """The amount of deposited asset in the market"""
        return {key: value * self.collateral_spot_price[key] for key, value in self.collateral.items()}

    def apply_delta(self, delta: MarketDeltas) -> None:
        r"""Applies a delta to the market state."""
        self.borrow_shares += delta.d_borrow_shares
        collateral_unit = delta.d_collateral.unit
        if collateral_unit not in self.collateral:  # key doesn't exist
            self.collateral[collateral_unit] = delta.d_collateral.amount
        else:  # key exists
            self.collateral[collateral_unit] += delta.d_collateral.amount

        self.check_market_non_zero()

    def copy(self) -> MarketState:
        """Returns a new copy of self"""
        return MarketState(
            loan_to_value_ratio=self.loan_to_value_ratio,
            borrow_shares=self.borrow_shares,
            collateral=self.collateral,
            borrow_outstanding=self.borrow_outstanding,
            borrow_closed_interest=self.borrow_closed_interest,
            borrow_share_price=self.borrow_share_price,
            collateral_spot_price=self.collateral_spot_price,
            lending_rate=self.lending_rate,
            spread_ratio=self.spread_ratio,
        )


@types.freezable(frozen=False, no_new_attribs=True)
@dataclass
class MarketAction(base_market.MarketAction):
    r"""Market action specification"""

    # these two variables are required to be set by the strategy
    action_type: MarketActionType
    # amount to supply for the action
    collateral: types.Quantity
    spot_price: Optional[float] = None


class BorrowPricingModel(PricingModel):
    """stores calculation functions use for the borrow market"""

    def value_collateral(self, market_state: MarketState, collateral: types.Quantity, spot_price: Optional[float]):
        """Values collateral and returns how much the agent can borrow against it"""
        collateral_value_in_base = collateral.amount  # if collateral is BASE
        if collateral.unit == types.TokenType.PT:
            collateral_value_in_base = collateral.amount * (spot_price or 1)
        borrow_amount_in_base = (
            collateral_value_in_base * market_state.loan_to_value_ratio[collateral.unit]  # type: ignore
        )
        return collateral_value_in_base, borrow_amount_in_base


class Market(base_market.Market[MarketState, MarketDeltas]):
    r"""Market state simulator

    Holds state variables for market simulation and executes trades.
    The Market class executes trades by updating market variables according to the given pricing model.
    It also has some helper variables for assessing pricing model values given market conditions.


    available_actions: list[MarketActionType]
        List of actions available in this market (used by simulator to determine which actions to offer to the agent)
    """

    available_actions = [MarketActionType.OPEN_BORROW, MarketActionType.CLOSE_BORROW]
    pricing_model = BorrowPricingModel()

    def __init__(
        self,
        market_state: MarketState,
    ):
        # market state variables
        self.time: float = 0  # t: time unit is time normalized to 1 year, i.e. 0.5 = 1/2 year
        self.market_state: MarketState = market_state
        super().__init__(pricing_model=self.pricing_model, market_state=market_state)

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
        _, borrow_amount_in_base = self.pricing_model.value_collateral(
            market_state=self.market_state, collateral=collateral, spot_price=spot_price
        )

        # market reserves are stored in shares, so we need to convert the amount to shares
        # borrow shares increase because they're being lent out
        # collateral increases because it's being deposited
        market_deltas = MarketDeltas(
            d_borrow_shares=borrow_amount_in_base / self.market_state.borrow_share_price,
            d_collateral=types.Quantity(
                unit=collateral.unit,
                amount=collateral.amount,
            ),
        )

        borrow_summary = wallet.Borrow(
            borrow_token=types.TokenType.BASE,
            borrow_amount=borrow_amount_in_base,
            start_time=self.time,
            loan_token=collateral.unit,
            loan_amount=0,  # FIXME: What is this?
        )

        # agent wallet is stored in token units (BASE or PT) so we pass back the deltas in those units
        agent_deltas = AgentDeltas(address=wallet_address, borrows=borrow_summary, collateral=collateral)
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
        _, borrow_amount_in_base = self.pricing_model.value_collateral(
            market_state=self.market_state, collateral=collateral, spot_price=spot_price
        )

        # market reserves are stored in shares, so we need to convert the amount to shares
        # borrow shares increases because it's being repaid
        # collateral decreases because it's being sent back to the agent
        market_deltas = MarketDeltas(
            d_borrow_shares=-borrow_amount_in_base / self.market_state.borrow_share_price, d_collateral=-collateral
        )

        # agent wallet is stored in token units (BASE or PT) so we pass back the deltas in those units
        agent_deltas = AgentDeltas(address=wallet_address, borrows=-borrow_amount_in_base, collateral=-collateral)
        return market_deltas, agent_deltas

    def update_share_prices(self, compound_vault_apr=True) -> None:
        """Increment share price to account for accrued interest based on the current borrow rate"""
        if compound_vault_apr:  # Apply return to latest price (full compounding)
            price_multiplier = self.market_state.borrow_share_price
        else:  # Apply return to starting price (no compounding)
            price_multiplier = self.market_state.init_borrow_share_price
        delta = MarketDeltas(
            d_borrow_share_price=(
                self.borrow_rate / 365 * price_multiplier  # current day's apy  # convert annual yield to daily
            )
        )
        self.update_market(delta)  # save the delta of borrow share price into the market

    @property
    def total_profit(self) -> float:
        """
        From the market's perspective, the profit is the difference between the borrowed and deposited assets
        This is composed of two parts:
            uncollected profit = borrow_shares * share_price - borrow_outstanding
            collected profit = borrow_closed_interest
        """
        return (
            self.market_state.borrow_shares * self.market_state.borrow_share_price
            - self.market_state.borrow_outstanding
            + self.market_state.borrow_closed_interest
        )

    @property
    def borrow_rate(self) -> float:
        """The borrow rate is the lending rate multiplied by the spread ratio"""
        return self.market_state.lending_rate * self.market_state.spread_ratio

    def log_market_step_string(self) -> None:
        """Logs the current market step"""
        logging.debug(
            ("t = %g\nborrow_asset = %g\ndeposit_assets = %g\nborrow_rate = %g"),
            self.time,
            self.market_state.borrow_amount,
            self.market_state.deposit_amount,
            self.borrow_rate,
        )

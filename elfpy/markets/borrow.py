"""Market simulators store state information when interfacing AMM pricing models with users."""
from __future__ import annotations  # types will be strings by default in 3.11

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict

import elfpy.markets.base as base_market
import elfpy.agents.wallet as wallet
import elfpy.pricing_models.base as base_pm
import elfpy.types as types
from elfpy.utils.math import FixedPoint


# TODO: remove this after FixedPoint PRs are finished
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

    # TODO: Should we be tracking the last time the dsr changed to evaluate the payout amount correctly?

    # borrow ratios
    loan_to_value_ratio: Dict[types.TokenType, float] = field(
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

    def copy(self) -> MarketState:
        """Returns a new copy of self"""
        return MarketState(**self.__dict__)


@types.freezable(frozen=False, no_new_attribs=True)
@dataclass
class MarketAction(base_market.MarketAction):
    r"""Market action specification"""

    # these two variables are required to be set by the strategy
    action_type: MarketActionType
    # amount to supply for the action
    collateral: types.Quantity
    spot_price: Optional[float] = None


class PricingModel(base_pm.PricingModel):
    """stores calculation functions use for the borrow market"""

    def value_collateral(
        self,
        loan_to_value_ratio: Dict[types.TokenType, float],
        collateral: types.Quantity,
        spot_price: Optional[float] = None,
    ):
        """Values collateral and returns how much the agent can borrow against it"""
        collateral_value_in_base = collateral.amount  # if collateral is BASE
        if collateral.unit == types.TokenType.PT:
            collateral_value_in_base = collateral.amount * (spot_price or 1)
        borrow_amount_in_base = collateral_value_in_base * loan_to_value_ratio[collateral.unit]  # type: ignore
        return collateral_value_in_base, borrow_amount_in_base


class Market(base_market.Market[MarketState, MarketDeltas, PricingModel]):
    r"""Market state simulator

    Holds state variables for market simulation and executes trades.
    The Market class executes trades by updating market variables according to the given pricing model.
    It also has some helper variables for assessing pricing model values given market conditions.


    available_actions: list[MarketActionType]
        List of actions available in this market (used by simulator to determine which actions to offer to the agent)
    """

    available_actions = [MarketActionType.OPEN_BORROW, MarketActionType.CLOSE_BORROW]

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

    @property
    def latest_checkpoint_time(self) -> float:
        """Gets the most recent checkpoint time."""
        raise NotImplementedError

    def initialize(
        self,
        wallet_address: int,
    ) -> tuple[MarketDeltas, wallet.Wallet]:
        """Construct a borrow market."""
        market_deltas = MarketDeltas()
        borrow_summary = wallet.Borrow(
            borrow_token=types.TokenType.BASE,
            borrow_amount=0,
            borrow_shares=0,
            collateral_token=types.TokenType.BASE,
            collateral_amount=0,
            start_time=0,
        )
        agent_deltas = wallet.Wallet(address=wallet_address, borrows={0: borrow_summary})
        return market_deltas, agent_deltas

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

    def perform_action(self, action_details: tuple[int, MarketAction]) -> tuple[int, wallet.Wallet, MarketDeltas]:
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
                agent_wallet=agent_action.wallet,
                collateral=agent_action.collateral,  # in BASE or PT, the collateral being offered
            )
        elif agent_action.action_type == MarketActionType.CLOSE_BORROW:  # close a borrow position
            market_deltas, agent_deltas = self.close_borrow(
                agent_wallet=agent_action.wallet,
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

    def calc_open_borrow(
        self,
        wallet_address: int,
        collateral: types.Quantity,  # in amount of collateral type (BASE or PT)
        spot_price: Optional[float] = None,
    ) -> tuple[MarketDeltas, wallet.Wallet]:
        """
        execute a borrow as requested by the agent, return the market and agent deltas
        agents decides what COLLATERAL to put IN then we calculate how much BASE OUT to give them
        """
        _, borrow_amount_in_base = self.pricing_model.value_collateral(
            loan_to_value_ratio=self.market_state.loan_to_value_ratio,
            collateral=collateral,
            spot_price=spot_price,
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
            borrow_shares=borrow_amount_in_base / self.market_state.borrow_share_price,
            collateral_token=collateral.unit,
            collateral_amount=collateral.amount,
            start_time=self.block_time.time,
        )
        # agent wallet is stored in token units (BASE or PT) so we pass back the deltas in those units
        agent_deltas = wallet.Wallet(
            address=wallet_address,
            borrows={self.block_time.time: borrow_summary},
        )
        return market_deltas, agent_deltas

    def open_borrow(
        self,
        agent_wallet: wallet.Wallet,
        collateral: types.Quantity,  # in amount of collateral type (BASE or PT)
        spot_price: Optional[float] = None,
    ) -> tuple[MarketDeltas, wallet.Wallet]:
        """Execute a borrow as requested by the agent and return the market and agent deltas.
        Agents decides what COLLATERAL to put IN then we calculate how much BASE OUT to give them.
        """
        market_deltas, agent_deltas = self.calc_open_borrow(agent_wallet.address, collateral, spot_price)
        self.market_state.apply_delta(market_deltas)
        agent_wallet.update(agent_deltas)
        return market_deltas, agent_deltas

    def calc_close_borrow(
        self,
        wallet_address: int,
        collateral: types.Quantity,  # in amount of collateral type (BASE or PT)
        spot_price: Optional[float] = None,
    ) -> tuple[MarketDeltas, wallet.Wallet]:
        """
        close a borrow as requested by the agent, return the market and agent deltas
        agent asks for COLLATERAL OUT and we tell them how much BASE to put IN (then check if they have it)
        """
        _, borrow_amount_in_base = self.pricing_model.value_collateral(
            loan_to_value_ratio=self.market_state.loan_to_value_ratio,
            collateral=collateral,
            spot_price=spot_price,
        )
        # market reserves are stored in shares, so we need to convert the amount to shares
        # borrow shares increases because it's being repaid
        # collateral decreases because it's being sent back to the agent
        # TODO: why don't we decrease collateral amount?
        market_deltas = MarketDeltas(
            d_borrow_shares=-borrow_amount_in_base / self.market_state.borrow_share_price, d_collateral=-collateral
        )
        borrow_summary = wallet.Borrow(
            borrow_token=types.TokenType.BASE,
            borrow_amount=-borrow_amount_in_base,
            borrow_shares=-borrow_amount_in_base / self.market_state.borrow_share_price,
            collateral_token=collateral.unit,
            collateral_amount=-collateral.amount,
            start_time=self.block_time.time,
        )
        # agent wallet is stored in token units (BASE or PT) so we pass back the deltas in those units
        agent_deltas = wallet.Wallet(
            address=wallet_address,
            borrows={self.block_time.time: borrow_summary},
        )
        return market_deltas, agent_deltas

    def close_borrow(
        self,
        agent_wallet: wallet.Wallet,
        collateral: types.Quantity,  # in amount of collateral type (BASE or PT)
        spot_price: Optional[float] = None,
    ) -> tuple[MarketDeltas, wallet.Wallet]:
        """Close a borrow as requested by the agent and return the market and agent deltas.
        Agent asks for COLLATERAL OUT and we tell them how much BASE to put IN (then check if they have it).
        """
        market_deltas, agent_deltas = self.calc_close_borrow(agent_wallet.address, collateral, spot_price)
        self.market_state.apply_delta(market_deltas)
        agent_wallet.update(agent_deltas)
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

    def log_market_step_string(self) -> None:
        """Logs the current market step"""
        logging.debug(
            ("t = %g\nborrow_asset = %g\ndeposit_assets = %g\nborrow_rate = %g"),
            self.block_time.time,
            self.market_state.borrow_amount,
            self.market_state.deposit_amount,
            self.borrow_rate,
        )


@types.freezable(frozen=True, no_new_attribs=True)
@dataclass
class MarketDeltasFP(base_market.MarketDeltasFP):
    r"""Specifies changes to values in the market"""

    d_borrow_shares: FixedPoint = FixedPoint("0.0")  # borrow is always in DAI
    d_collateral: types.QuantityFP = field(
        default_factory=lambda: types.QuantityFP(amount=FixedPoint("0.0"), unit=types.TokenType.PT)
    )
    d_borrow_outstanding: FixedPoint = FixedPoint("0.0")  # changes based on borrow_shares * borrow_share_price
    d_borrow_closed_interest: FixedPoint = FixedPoint("0.0")  # realized interest from closed borrows
    d_borrow_share_price: FixedPoint = FixedPoint("0.0")  # used only when time ticks and interest accrues


@types.freezable(frozen=False, no_new_attribs=False)
@dataclass
class MarketStateFP(base_market.BaseMarketStateFP):
    r"""The state of an AMM

    Implements a class for all that that an AMM smart contract would hold or would have access to
    For example, reserve numbers are local state variables of the AMM.  The borrow_rate will most
    likely be accessible through the AMM as well.

    Attributes
    ----------
    loan_to_value_ratio: FixedPoint
        The maximum loan to value ratio a collateral can have before liquidations occur.
    borrow_shares: FixedPoint
        Accounting units for borrow assets that has been lent out by the market, allows tracking of interest
    collateral: dict[TokenType, FixedPoint]
        Amount of collateral that has been deposited into the market
    borrow_outstanding: FixedPoint
        The amount of borrowed asset that has been lent out by the market, without accounting for interest
    borrow_share_price: FixedPoint
        The "share price" of the borrowed asset tracks the cumulative amount owed over time, indexed to 1 at the start
    borrow_closed_interest: FixedPoint
        The interest that has been collected from closed borrows, to capture realized profit
    collateral_spot_price: FixedPoint
        The spot price of the collateral asset, to allow updating valuation across time
    lending_rate: FixedPoint
        The rate a user receives when lending out assets
    spread_ratio: FixedPoint
        The ratio of the borrow rate to the lending rate
    """

    # dataclasses can have many attributes
    # pylint: disable=too-many-instance-attributes

    # TODO: Should we be tracking the last time the dsr changed to evaluate the payout amount correctly?

    # borrow ratios
    loan_to_value_ratio: Dict[types.TokenType, FixedPoint] = field(
        default_factory=lambda: {token_type: FixedPoint("0.97") for token_type in types.TokenType}
    )

    # trading reserves
    borrow_shares: FixedPoint = FixedPoint("0.0")  # allows tracking the increasing value of loans over time
    collateral: Dict[types.TokenType, FixedPoint] = field(default_factory=dict)

    borrow_outstanding: FixedPoint = FixedPoint("0.0")  # sum of Dai that went out the door
    borrow_closed_interest: FixedPoint = FixedPoint("0.0")  # interested collected from closed borrows

    # share prices used to track amounts owed
    borrow_share_price: FixedPoint = FixedPoint("1.0")
    init_borrow_share_price: FixedPoint = field(default=borrow_share_price)  # allow not setting init_share_price
    # number of TokenA you get for TokenB
    collateral_spot_price: Dict[types.TokenType, FixedPoint] = field(default_factory=dict)

    # borrow and lending rates
    lending_rate: FixedPoint = FixedPoint("0.01")  # 1% per year
    # borrow rate is lending_rate * spread_ratio
    spread_ratio: FixedPoint = FixedPoint("1.25")

    @property
    def borrow_amount(self) -> FixedPoint:
        """The amount of borrowed asset in the market"""
        return self.borrow_shares * self.borrow_share_price

    @property
    def deposit_amount(self) -> dict[types.TokenType, FixedPoint]:
        """The amount of deposited asset in the market"""
        return {key: value * self.collateral_spot_price[key] for key, value in self.collateral.items()}

    def apply_delta(self, delta: MarketDeltasFP) -> None:
        r"""Applies a delta to the market state."""
        self.borrow_shares += delta.d_borrow_shares
        collateral_unit = delta.d_collateral.unit
        if collateral_unit not in self.collateral:  # key doesn't exist
            self.collateral[collateral_unit] = delta.d_collateral.amount
        else:  # key exists
            self.collateral[collateral_unit] += delta.d_collateral.amount

    def copy(self) -> MarketStateFP:
        """Returns a new copy of self"""
        return MarketStateFP(**self.__dict__)


@types.freezable(frozen=False, no_new_attribs=True)
@dataclass
class MarketActionFP(base_market.MarketActionFP):
    r"""Market action specification"""

    # these two variables are required to be set by the strategy
    action_type: MarketActionType
    # amount to supply for the action
    collateral: types.QuantityFP
    spot_price: FixedPoint | None = None


class PricingModelFP(base_pm.PricingModelFP):
    """stores calculation functions use for the borrow market"""

    def value_collateral(
        self,
        loan_to_value_ratio: Dict[types.TokenType, FixedPoint],
        collateral: types.QuantityFP,
        spot_price: Optional[FixedPoint] = None,
    ):
        """Values collateral and returns how much the agent can borrow against it"""
        collateral_value_in_base = collateral.amount  # if collateral is BASE
        if collateral.unit == types.TokenType.PT:
            collateral_value_in_base = collateral.amount * (spot_price or FixedPoint("1.0"))
        borrow_amount_in_base = collateral_value_in_base * loan_to_value_ratio[collateral.unit]  # type: ignore
        return collateral_value_in_base, borrow_amount_in_base


class MarketFP(base_market.MarketFP[MarketStateFP, MarketDeltasFP, PricingModelFP]):
    r"""Market state simulator

    Holds state variables for market simulation and executes trades.
    The Market class executes trades by updating market variables according to the given pricing model.
    It also has some helper variables for assessing pricing model values given market conditions.


    available_actions: list[MarketActionType]
        List of actions available in this market (used by simulator to determine which actions to offer to the agent)
    """

    available_actions = [MarketActionType.OPEN_BORROW, MarketActionType.CLOSE_BORROW]

    @property
    def total_profit(self) -> FixedPoint:
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
    def borrow_rate(self) -> FixedPoint:
        """The borrow rate is the lending rate multiplied by the spread ratio"""
        return self.market_state.lending_rate * self.market_state.spread_ratio

    @property
    def latest_checkpoint_time(self) -> FixedPoint:
        """Gets the most recent checkpoint time."""
        raise NotImplementedError

    def initialize(
        self,
        wallet_address: int,
    ) -> tuple[MarketDeltasFP, wallet.WalletFP]:
        """Construct a borrow market."""
        market_deltas = MarketDeltasFP()
        borrow_summary = wallet.BorrowFP(
            borrow_token=types.TokenType.BASE,
            borrow_amount=FixedPoint(0),
            borrow_shares=FixedPoint(0),
            collateral_token=types.TokenType.BASE,
            collateral_amount=FixedPoint(0),
            start_time=FixedPoint(0),
        )
        agent_deltas = wallet.WalletFP(address=wallet_address, borrows={0: borrow_summary})
        return market_deltas, agent_deltas

    def check_action(self, agent_action: MarketActionFP) -> None:
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

    def perform_action(self, action_details: tuple[int, MarketActionFP]) -> tuple[int, wallet.WalletFP, MarketDeltasFP]:
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
        market_deltas = MarketDeltasFP()
        # for each position, specify how to formulate trade and then execute
        # current assumption is that the user will borrow the maximum LTV against the collateral they are offering
        if agent_action.action_type == MarketActionType.OPEN_BORROW:  # open a borrow position
            market_deltas, agent_deltas = self.open_borrow(
                agent_wallet=agent_action.wallet,
                collateral=agent_action.collateral,  # in BASE or PT, the collateral being offered
            )
        elif agent_action.action_type == MarketActionType.CLOSE_BORROW:  # close a borrow position
            market_deltas, agent_deltas = self.close_borrow(
                agent_wallet=agent_action.wallet,
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

    def calc_open_borrow(
        self,
        wallet_address: int,
        collateral: types.QuantityFP,  # in amount of collateral type (BASE or PT)
        spot_price: Optional[FixedPoint] = None,
    ) -> tuple[MarketDeltasFP, wallet.WalletFP]:
        """
        execute a borrow as requested by the agent, return the market and agent deltas
        agents decides what COLLATERAL to put IN then we calculate how much BASE OUT to give them
        """
        _, borrow_amount_in_base = self.pricing_model.value_collateral(
            loan_to_value_ratio=self.market_state.loan_to_value_ratio,
            collateral=collateral,
            spot_price=spot_price,
        )
        # market reserves are stored in shares, so we need to convert the amount to shares
        # borrow shares increase because they're being lent out
        # collateral increases because it's being deposited
        market_deltas = MarketDeltasFP(
            d_borrow_shares=borrow_amount_in_base / self.market_state.borrow_share_price,
            d_collateral=types.QuantityFP(
                unit=collateral.unit,
                amount=collateral.amount,
            ),
        )
        borrow_summary = wallet.BorrowFP(
            borrow_token=types.TokenType.BASE,
            borrow_amount=borrow_amount_in_base,
            borrow_shares=borrow_amount_in_base / self.market_state.borrow_share_price,
            collateral_token=collateral.unit,
            collateral_amount=collateral.amount,
            start_time=self.block_time.time,
        )
        # agent wallet is stored in token units (BASE or PT) so we pass back the deltas in those units
        agent_deltas = wallet.WalletFP(
            address=wallet_address,
            borrows={int(self.block_time.time): borrow_summary},
        )
        return market_deltas, agent_deltas

    def open_borrow(
        self,
        agent_wallet: wallet.WalletFP,
        collateral: types.QuantityFP,  # in amount of collateral type (BASE or PT)
        spot_price: FixedPoint | None = None,
    ) -> tuple[MarketDeltasFP, wallet.WalletFP]:
        """Execute a borrow as requested by the agent and return the market and agent deltas.
        Agents decides what COLLATERAL to put IN then we calculate how much BASE OUT to give them.
        """
        market_deltas, agent_deltas = self.calc_open_borrow(agent_wallet.address, collateral, spot_price)
        self.market_state.apply_delta(market_deltas)
        agent_wallet.update(agent_deltas)
        return market_deltas, agent_deltas

    def calc_close_borrow(
        self,
        wallet_address: int,
        collateral: types.QuantityFP,  # in amount of collateral type (BASE or PT)
        spot_price: FixedPoint | None = None,
    ) -> tuple[MarketDeltasFP, wallet.WalletFP]:
        """
        close a borrow as requested by the agent, return the market and agent deltas
        agent asks for COLLATERAL OUT and we tell them how much BASE to put IN (then check if they have it)
        """
        _, borrow_amount_in_base = self.pricing_model.value_collateral(
            loan_to_value_ratio=self.market_state.loan_to_value_ratio,
            collateral=collateral,
            spot_price=spot_price,
        )
        # market reserves are stored in shares, so we need to convert the amount to shares
        # borrow shares increases because it's being repaid
        # collateral decreases because it's being sent back to the agent
        # TODO: why don't we decrease collateral amount?
        market_deltas = MarketDeltasFP(
            d_borrow_shares=-borrow_amount_in_base / self.market_state.borrow_share_price, d_collateral=-collateral
        )
        borrow_summary = wallet.BorrowFP(
            borrow_token=types.TokenType.BASE,
            borrow_amount=-borrow_amount_in_base,
            borrow_shares=-borrow_amount_in_base / self.market_state.borrow_share_price,
            collateral_token=collateral.unit,
            collateral_amount=-collateral.amount,
            start_time=self.block_time.time,
        )
        # agent wallet is stored in token units (BASE or PT) so we pass back the deltas in those units
        agent_deltas = wallet.WalletFP(
            address=wallet_address,
            borrows={int(self.block_time.time): borrow_summary},
        )
        return market_deltas, agent_deltas

    def close_borrow(
        self,
        agent_wallet: wallet.WalletFP,
        collateral: types.QuantityFP,  # in amount of collateral type (BASE or PT)
        spot_price: FixedPoint | None = None,
    ) -> tuple[MarketDeltasFP, wallet.WalletFP]:
        """Close a borrow as requested by the agent and return the market and agent deltas.
        Agent asks for COLLATERAL OUT and we tell them how much BASE to put IN (then check if they have it).
        """
        market_deltas, agent_deltas = self.calc_close_borrow(agent_wallet.address, collateral, spot_price)
        self.market_state.apply_delta(market_deltas)
        agent_wallet.update(agent_deltas)
        return market_deltas, agent_deltas

    def update_share_prices(self, compound_vault_apr=True) -> None:
        """Increment share price to account for accrued interest based on the current borrow rate"""
        if compound_vault_apr:  # Apply return to latest price (full compounding)
            price_multiplier = self.market_state.borrow_share_price
        else:  # Apply return to starting price (no compounding)
            price_multiplier = self.market_state.init_borrow_share_price
        delta = MarketDeltasFP(
            d_borrow_share_price=(
                self.borrow_rate
                / FixedPoint("365.0")
                * price_multiplier  # current day's apy  # convert annual yield to daily
            )
        )
        self.update_market(delta)  # save the delta of borrow share price into the market

    def log_market_step_string(self) -> None:
        """Logs the current market step"""
        logging.debug(
            ("t = %g\nborrow_asset = %g\ndeposit_assets = %g\nborrow_rate = %g"),
            self.block_time.time,
            self.market_state.borrow_amount,
            self.market_state.deposit_amount,
            self.borrow_rate,
        )

"""Market simulators store state information when interfacing AMM pricing models with users."""
from __future__ import annotations
import logging
from dataclasses import dataclass
from enum import Enum

import elfpy.agents.wallet as wallet
from elfpy.markets.borrow.borrow_pricing_model import BorrowPricingModel
from elfpy.markets.borrow.borrow_market_state import BorrowMarketState
from elfpy.markets.borrow.borrow_market_deltas import BorrowMarketDeltas
import elfpy.types as types

from elfpy.markets.base.base_market import BaseMarket, BaseMarketAction
from elfpy.math import FixedPoint


class MarketActionType(Enum):
    r"""Enumerate actions available in this market"""

    OPEN_BORROW = "open_borrow"
    CLOSE_BORROW = "close_borrow"


@types.freezable(frozen=False, no_new_attribs=True)
@dataclass
class BorrowMarketAction(BaseMarketAction):
    r"""Market action specification"""

    # these two variables are required to be set by the strategy
    action_type: MarketActionType
    # amount to supply for the action
    collateral: types.Quantity
    spot_price: FixedPoint | None = None


class Market(BaseMarket[BorrowMarketState, BorrowMarketDeltas, BorrowPricingModel]):
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
    ) -> tuple[BorrowMarketDeltas, wallet.Wallet]:
        """Construct a borrow market."""
        market_deltas = BorrowMarketDeltas()
        borrow_summary = wallet.Borrow(
            borrow_token=types.TokenType.BASE,
            borrow_amount=FixedPoint(0),
            borrow_shares=FixedPoint(0),
            collateral_token=types.TokenType.BASE,
            collateral_amount=FixedPoint(0),
            start_time=FixedPoint(0),
        )
        agent_deltas = wallet.Wallet(address=wallet_address, borrows={FixedPoint(0): borrow_summary})
        return market_deltas, agent_deltas

    def check_action(self, agent_action: BorrowMarketAction) -> None:
        r"""Ensure that the agent action is an allowed action for this market

        Arguments
        ----------
        agent_action : MarketAction
            Checks if the agent_action.action_type is in the list of all available actions for this market

        Returns
        -------
        None
        """
        if agent_action.action_type not in self.available_actions:
            raise ValueError(f"ERROR: agent_action.action_type must be in {self.available_actions=}")

    def perform_action(
        self, action_details: tuple[int, BorrowMarketAction]
    ) -> tuple[int, wallet.Wallet, BorrowMarketDeltas]:
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
        market_deltas = BorrowMarketDeltas()
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
        spot_price: FixedPoint | None = None,
    ) -> tuple[BorrowMarketDeltas, wallet.Wallet]:
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
        market_deltas = BorrowMarketDeltas(
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
        spot_price: FixedPoint | None = None,
    ) -> tuple[BorrowMarketDeltas, wallet.Wallet]:
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
        spot_price: FixedPoint | None = None,
    ) -> tuple[BorrowMarketDeltas, wallet.Wallet]:
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
        market_deltas = BorrowMarketDeltas(
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
        spot_price: FixedPoint | None = None,
    ) -> tuple[BorrowMarketDeltas, wallet.Wallet]:
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
        delta = BorrowMarketDeltas(
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

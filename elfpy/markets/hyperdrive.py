"""Market simulators store state information when interfacing AMM pricing models with users."""
from __future__ import annotations  # types will be strings by default in 3.11

import logging
from enum import Enum
from typing import TYPE_CHECKING, Optional, Generic
from dataclasses import dataclass

import numpy as np

from elfpy import PRECISION_THRESHOLD
import elfpy.utils.price as price_utils
import elfpy.utils.time as time_utils
import elfpy.agents.wallet as wallet
import elfpy.types as types
import elfpy.markets.base as base_market

if TYPE_CHECKING:
    from elfpy.pricing_models.base import PricingModel

# TODO: for now...
# pylint: disable=duplicate-code


class MarketActionType(Enum):
    r"""The descriptor of an action in a market"""

    OPEN_LONG = "open_long"
    OPEN_SHORT = "open_short"

    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"

    ADD_LIQUIDITY = "add_liquidity"
    REMOVE_LIQUIDITY = "remove_liquidity"


@types.freezable(frozen=True, no_new_attribs=True)
@dataclass
class MarketDeltas(base_market.MarketDeltas):
    r"""Specifies changes to values in the market"""
    d_base_asset: float = 0
    d_bond_asset: float = 0
    d_base_buffer: float = 0
    d_bond_buffer: float = 0
    d_lp_total_supply: float = 0
    d_share_price: float = 0

    def __str__(self):
        return (
            "MarketDeltas(\n"
            f"\t{self.d_base_asset=},\n"
            f"\t{self.d_bond_asset=},\n"
            f"\t{self.d_base_buffer=},\n"
            f"\t{self.d_bond_buffer=},\n"
            f"\t{self.d_lp_total_supply=},\n"
            f"\t{self.d_share_price=},\n"
            ")"
        )


@types.freezable(frozen=True, no_new_attribs=True)
@dataclass
class MarketTradeResult(base_market.MarketTradeResult):
    r"""The result to a market of performing a trade"""

    d_base: float
    d_bonds: float


@types.freezable(frozen=False, no_new_attribs=False)
@dataclass
class MarketState(base_market.BaseMarketState):
    r"""The state of an AMM

    Attributes
    ----------
    lp_total_supply: float
        Amount of lp tokens
    share_reserves: float
        Quantity of shares stored in the market
    bond_reserves: float
        Quantity of bonds stored in the market
    base_buffer: float
        Base amount set aside to account for open longs
    bond_buffer: float
        Bond amount set aside to account for open shorts
    variable_apr: float
        apr of underlying yield-bearing source
    share_price: float
        ratio of value of base & shares that are stored in the underlying vault,
        i.e. share_price = base_value / share_value
    init_share_price: float
        share price at pool initialization
    trade_fee_percent : float
        The percentage of the difference between the amount paid without
        slippage and the amount received that will be added to the input
        as a fee.
    redemption_fee_percent : float
        A flat fee applied to the output.  Not used in this equation for Yieldspace.
    """

    # lp reserves
    lp_total_supply: float = 0.0

    # dataclasses can have many attributes
    # pylint: disable=too-many-instance-attributes

    # trading reserves
    share_reserves: float = 0.0
    bond_reserves: float = 0.0

    # trading buffers
    base_buffer: float = 0.0
    bond_buffer: float = 0.0

    # share price
    variable_apr: float = 0.0
    share_price: float = 1.0
    init_share_price: float = 1.0

    # fee percents
    trade_fee_percent: float = 0.0
    redemption_fee_percent: float = 0.0

    def apply_delta(self, delta: MarketDeltas) -> None:
        r"""Applies a delta to the market state."""
        self.share_reserves += delta.d_base_asset / self.share_price
        self.bond_reserves += delta.d_bond_asset
        self.base_buffer += delta.d_base_buffer
        self.bond_buffer += delta.d_bond_buffer
        self.lp_total_supply += delta.d_lp_total_supply
        self.share_price += delta.d_share_price

        # TODO: issue #146
        # this is an imperfect solution to rounding errors, but it works for now
        for key, value in self.__dict__.items():
            if 0 > value > -PRECISION_THRESHOLD:
                logging.debug(
                    ("%s=%s is negative within PRECISION_THRESHOLD=%f, setting it to 0"),
                    key,
                    value,
                    PRECISION_THRESHOLD,
                )
                setattr(self, key, 0)
            else:
                assert (
                    value > -PRECISION_THRESHOLD
                ), f"MarketState values must be > {-PRECISION_THRESHOLD}. Error on {key} = {value}"

    def copy(self) -> MarketState:
        """Returns a new copy of self"""
        return MarketState(
            share_reserves=self.share_reserves,
            bond_reserves=self.bond_reserves,
            base_buffer=self.bond_buffer,
            lp_total_supply=self.lp_total_supply,
            variable_apr=self.variable_apr,
            share_price=self.share_price,
            init_share_price=self.init_share_price,
            trade_fee_percent=self.trade_fee_percent,
            redemption_fee_percent=self.redemption_fee_percent,
        )

    def __str__(self):
        return (
            "MarketState(\n"
            "\ttrading_reserves(\n"
            f"\t\t{self.share_reserves=},\n"
            f"\t\t{self.bond_reserves=},\n"
            "\t),\n"
            "\ttrading_buffers(\n"
            f"\t\t{self.base_buffer=},\n"
            f"\t\t{self.bond_buffer=},\n"
            "\t),\n"
            "\tlp_total_supply(\n"
            f"\t\t{self.lp_total_supply=},\n"
            "\t),\n"
            "\tunderlying_vault((\n"
            f"\t\t{self.variable_apr=},\n"
            f"\t\t{self.share_price=},\n"
            f"\t\t{self.init_share_price=},\n"
            "\t)\n"
            ")"
        )


@types.freezable(frozen=False, no_new_attribs=True)
@dataclass
class MarketAction(Generic[base_market.Action]):
    r"""Market action specification"""

    # these two variables are required to be set by the strategy
    action_type: MarketActionType
    # amount to supply for the action
    trade_amount: float  # TODO: should this be a Quantity, not a float? Make sure, then delete fixme
    # the agent's wallet
    wallet: wallet.Wallet
    # min amount to receive for the action
    min_amount_out: float = 0
    # mint time is set only for trades that act on existing positions (close long or close short)
    mint_time: Optional[float] = None

    def __str__(self):
        r"""Return a description of the Action"""
        output_string = (
            "MarketAction(\n"
            f"\tagent={self.wallet.address},\n"
            f"\t{self.action_type=},\n"
            f"\t{self.trade_amount=},\n"
            f"\t{self.min_amount_out=},\n"
            f"\t{self.mint_time=},\n"
            f"\t{self.wallet=},\n"
            ")"
        )
        return output_string


class Market(base_market.Market[MarketState, MarketDeltas]):
    r"""Market state simulator

    Holds state variables for market simulation and executes trades.
    The Market class executes trades by updating market variables according to the given pricing model.
    It also has some helper variables for assessing pricing model values given market conditions.
    """

    def __init__(
        self,
        pricing_model: PricingModel,
        market_state: MarketState,
        position_duration: time_utils.StretchedTime,
    ):
        # market state variables
        assert (
            position_duration.days == position_duration.normalizing_constant
        ), "position_duration argument term length (days) should normalize to 1"
        self.position_duration = time_utils.StretchedTime(
            position_duration.days, position_duration.time_stretch, position_duration.normalizing_constant
        )
        # NOTE: lint error false positives: This message may report object members that are created dynamically,
        # but exist at the time they are accessed.
        self.position_duration.freeze()  # pylint: disable=no-member # type: ignore
        super().__init__(pricing_model=pricing_model, market_state=market_state)

    @property
    def annualized_position_duration(self) -> float:
        r"""Returns the position duration in years"""
        return self.position_duration.days / 365

    def check_action(self, agent_action: MarketAction) -> None:
        r"""Ensure that the agent action is an allowed action for this market

        Parameters
        ----------
        action_type : MarketActionType
            See MarketActionType for all acceptable actions that can be performed on this market

        Returns
        -------
        None
        """
        if (
            agent_action.action_type
            in [
                MarketActionType.CLOSE_LONG,
                MarketActionType.CLOSE_SHORT,
            ]
            and agent_action.mint_time is None
        ):
            raise ValueError("ERROR: agent_action.mint_time must be provided when closing a short or long")

    def perform_action(self, action_details: tuple[int, MarketAction]) -> tuple[int, wallet.Wallet, MarketDeltas]:
        r"""Execute a trade in the simulated market

        check which of 6 action types are being executed, and handles each case:

        open_long

        close_long

        open_short

        close_short

        add_liquidity
            pricing model computes new market deltas
            market updates its "liquidity pool" wallet, which stores each trade's mint time and user address
            LP tokens are also stored in user wallet as fungible amounts, for ease of use

        remove_liquidity
            market figures out how much the user has contributed (calcualtes their fee weighting)
            market resolves fees, adds this to the agent_action (optional function, to check AMM logic)
            pricing model computes new market deltas
            market updates its "liquidity pool" wallet, which stores each trade's mint time and user address
            LP tokens are also stored in user wallet as fungible amounts, for ease of use

        .. todo: change agent deltas from Wallet type to its own type
        """
        agent_id, agent_action = action_details
        # TODO: add use of the Quantity type to enforce units while making it clear what units are being used
        # issue 216
        self.check_action(agent_action)
        # for each position, specify how to forumulate trade and then execute
        if agent_action.action_type == MarketActionType.OPEN_LONG:  # buy to open long
            market_deltas, agent_deltas = self.open_long(
                wallet_address=agent_action.wallet.address,
                trade_amount=agent_action.trade_amount,  # in base: that's the thing in your wallet you want to sell
            )
        elif agent_action.action_type == MarketActionType.CLOSE_LONG:  # sell to close long
            # TODO: python 3.10 includes TypeGuard which properly avoids issues when using Optional type
            mint_time = float(agent_action.mint_time or 0)
            market_deltas, agent_deltas = self.close_long(
                wallet_address=agent_action.wallet.address,
                trade_amount=agent_action.trade_amount,  # in bonds: that's the thing in your wallet you want to sell
                mint_time=mint_time,
            )
        elif agent_action.action_type == MarketActionType.OPEN_SHORT:  # sell PT to open short
            market_deltas, agent_deltas = self.open_short(
                wallet_address=agent_action.wallet.address,
                trade_amount=agent_action.trade_amount,  # in bonds: that's the thing you want to short
            )
        elif agent_action.action_type == MarketActionType.CLOSE_SHORT:  # buy PT to close short
            # TODO: python 3.10 includes TypeGuard which properly avoids issues when using Optional type
            mint_time = float(agent_action.mint_time or 0)
            open_share_price = agent_action.wallet.shorts[mint_time].open_share_price
            market_deltas, agent_deltas = self.close_short(
                wallet_address=agent_action.wallet.address,
                trade_amount=agent_action.trade_amount,  # in bonds: that's the thing you owe, and need to buy back
                mint_time=mint_time,
                open_share_price=open_share_price,
            )
        elif agent_action.action_type == MarketActionType.ADD_LIQUIDITY:
            market_deltas, agent_deltas = self.add_liquidity(
                wallet_address=agent_action.wallet.address,
                trade_amount=agent_action.trade_amount,
            )
        elif agent_action.action_type == MarketActionType.REMOVE_LIQUIDITY:
            market_deltas, agent_deltas = self.remove_liquidity(
                wallet_address=agent_action.wallet.address,
                trade_amount=agent_action.trade_amount,
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
        return (agent_id, agent_deltas, market_deltas)

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

    @property
    def fixed_apr(self) -> float:
        """Returns the current market apr"""
        # calc_apr_from_spot_price will throw an error if share_reserves <= zero
        # TODO: Negative values should never happen, but do because of rounding errors.
        #       Write checks to remedy this in the market.
        # issue #146

        if self.market_state.share_reserves <= 0:  # market is empty; negative value likely due to rounding error
            return np.nan
        return price_utils.calc_apr_from_spot_price(price=self.spot_price, time_remaining=self.position_duration)

    @property
    def spot_price(self) -> float:
        """Returns the current market price of the share reserves"""
        # calc_spot_price_from_reserves will throw an error if share_reserves is zero
        if self.market_state.share_reserves == 0:  # market is empty
            return np.nan
        return self.pricing_model.calc_spot_price_from_reserves(
            market_state=self.market_state,
            time_remaining=self.position_duration,
        )

    def get_market_state_string(self) -> str:
        """Returns a formatted string containing all of the Market class member variables"""
        strings = [f"{attribute} = {value}" for attribute, value in self.__dict__.items()]
        state_string = "\n".join(strings)
        return state_string

    def tick(self, delta_time: float) -> None:
        """Increments the time member variable"""
        self.time += delta_time

    def open_short(
        self,
        wallet_address: int,
        trade_amount: float,
    ) -> tuple[MarketDeltas, wallet.Wallet]:
        """
        shorts need their margin account to cover the worst case scenario (p=1)
        margin comes from 2 sources:
        - the proceeds from your short sale (p)
        - the max value you cover with base deposted from your wallet (1-p)
        these two components are both priced in base, yet happily add up to 1.0 units of bonds
        so we have the following identity:
        total margin (base, from proceeds + deposited) = face value of bonds shorted (# of bonds)

        this guarantees that bonds in the system are always fully backed by an equal amount of base
        """
        # Perform the trade.
        trade_quantity = types.Quantity(amount=trade_amount, unit=types.TokenType.PT)
        self.pricing_model.check_input_assertions(
            quantity=trade_quantity,
            market_state=self.market_state,
            time_remaining=self.position_duration,
        )
        trade_result = self.pricing_model.calc_out_given_in(
            in_=trade_quantity,
            market_state=self.market_state,
            time_remaining=self.position_duration,
        )
        self.pricing_model.check_output_assertions(trade_result=trade_result)
        # Return the market and wallet deltas.
        market_deltas = MarketDeltas(
            d_base_asset=trade_result.market_result.d_base,
            d_bond_asset=trade_result.market_result.d_bonds,
            d_bond_buffer=trade_amount,
        )
        # amount to cover the worst case scenario where p=1. this amount is 1-p. see logic above.
        max_loss = trade_amount - trade_result.user_result.d_base
        agent_deltas = wallet.Wallet(
            address=wallet_address,
            balance=-types.Quantity(amount=max_loss, unit=types.TokenType.BASE),
            shorts={self.time: wallet.Short(balance=trade_amount, open_share_price=self.market_state.share_price)},
            fees_paid=trade_result.breakdown.fee,
        )
        return market_deltas, agent_deltas

    def close_short(
        self,
        wallet_address: int,
        open_share_price: float,
        trade_amount: float,
        mint_time: float,
    ) -> tuple[MarketDeltas, wallet.Wallet]:
        """
        when closing a short, the number of bonds being closed out, at face value, give us the total margin returned
        the worst case scenario of the short is reduced by that amount, so they no longer need margin for it
        at the same time, margin in their account is drained to pay for the bonds being bought back
        so the amount returned to their wallet is trade_amount minus the cost of buying back the bonds
        that is, d_base = trade_amount (# of bonds) + trade_result.user_result.d_base (a negative amount, in base))
        for more on short accounting, see the open short method
        """

        # Clamp the trade amount to the bond reserves.
        if trade_amount > self.market_state.bond_reserves:
            logging.warning(
                (
                    "markets._close_short: WARNING: trade amount = %g"
                    "is greater than bond reserves = %g. "
                    "Adjusting to allowable amount."
                ),
                trade_amount,
                self.market_state.bond_reserves,
            )
            trade_amount = self.market_state.bond_reserves

        # Compute the time remaining given the mint time.
        years_remaining = time_utils.get_years_remaining(
            market_time=self.time, mint_time=mint_time, position_duration_years=self.position_duration.days / 365
        )  # all args in units of years
        time_remaining = time_utils.StretchedTime(
            days=years_remaining * 365,  # converting years to days
            time_stretch=self.position_duration.time_stretch,
            normalizing_constant=self.position_duration.normalizing_constant,
        )

        # Perform the trade.
        trade_quantity = types.Quantity(amount=trade_amount, unit=types.TokenType.PT)
        self.pricing_model.check_input_assertions(
            quantity=trade_quantity,
            market_state=self.market_state,
            time_remaining=time_remaining,
        )
        trade_result = self.pricing_model.calc_in_given_out(
            out=trade_quantity,
            market_state=self.market_state,
            time_remaining=time_remaining,
        )
        self.pricing_model.check_output_assertions(trade_result=trade_result)
        # Return the market and wallet deltas.
        market_deltas = MarketDeltas(
            d_base_asset=trade_result.market_result.d_base,
            d_bond_asset=trade_result.market_result.d_bonds,
            d_bond_buffer=-trade_amount,
        )
        agent_deltas = wallet.Wallet(
            address=wallet_address,
            balance=types.Quantity(
                amount=(self.market_state.share_price / open_share_price) * trade_amount
                + trade_result.user_result.d_base,
                unit=types.TokenType.BASE,
            ),  # see CLOSING SHORT LOGIC above
            shorts={
                mint_time: wallet.Short(
                    balance=-trade_amount,
                    open_share_price=0,
                )
            },
            fees_paid=trade_result.breakdown.fee,
        )
        return market_deltas, agent_deltas

    def open_long(
        self,
        wallet_address: int,
        trade_amount: float,  # in base
    ) -> tuple[MarketDeltas, wallet.Wallet]:
        """
        take trade spec & turn it into trade details
        compute wallet update spec with specific details
        will be conditional on the pricing model
        """
        # TODO: Why are we clamping elsewhere but we don't apply the trade at all here?
        # issue #146
        if trade_amount <= self.market_state.bond_reserves:
            # Perform the trade.
            trade_quantity = types.Quantity(amount=trade_amount, unit=types.TokenType.BASE)
            self.pricing_model.check_input_assertions(
                quantity=trade_quantity,
                market_state=self.market_state,
                time_remaining=self.position_duration,
            )
            trade_result = self.pricing_model.calc_out_given_in(
                in_=trade_quantity,
                market_state=self.market_state,
                time_remaining=self.position_duration,
            )
            self.pricing_model.check_output_assertions(trade_result=trade_result)
            # Get the market and wallet deltas to return.
            market_deltas = MarketDeltas(
                d_base_asset=trade_result.market_result.d_base,
                d_bond_asset=trade_result.market_result.d_bonds,
                d_base_buffer=trade_result.user_result.d_bonds,
            )
            agent_deltas = wallet.Wallet(
                address=wallet_address,
                balance=types.Quantity(amount=trade_result.user_result.d_base, unit=types.TokenType.BASE),
                longs={self.time: wallet.Long(trade_result.user_result.d_bonds)},
                fees_paid=trade_result.breakdown.fee,
            )
        else:
            market_deltas = MarketDeltas()
            agent_deltas = wallet.Wallet(
                address=wallet_address, balance=types.Quantity(amount=0, unit=types.TokenType.BASE)
            )
        return market_deltas, agent_deltas

    def close_long(
        self,
        wallet_address: int,
        trade_amount: float,  # in bonds
        mint_time: float,
    ) -> tuple[MarketDeltas, wallet.Wallet]:
        """
        take trade spec & turn it into trade details
        compute wallet update spec with specific details
        will be conditional on the pricing model
        """

        # Compute the time remaining given the mint time.
        years_remaining = time_utils.get_years_remaining(
            market_time=self.time, mint_time=mint_time, position_duration_years=self.position_duration.days / 365
        )  # all args in units of years
        time_remaining = time_utils.StretchedTime(
            days=years_remaining * 365,  # converting years to days
            time_stretch=self.position_duration.time_stretch,
            normalizing_constant=self.position_duration.normalizing_constant,
        )

        # Perform the trade.
        trade_quantity = types.Quantity(amount=trade_amount, unit=types.TokenType.PT)
        self.pricing_model.check_input_assertions(
            quantity=trade_quantity,
            market_state=self.market_state,
            time_remaining=time_remaining,
        )
        trade_result = self.pricing_model.calc_out_given_in(
            in_=trade_quantity,
            market_state=self.market_state,
            time_remaining=time_remaining,
        )
        self.pricing_model.check_output_assertions(trade_result=trade_result)
        # Return the market and wallet deltas.
        market_deltas = MarketDeltas(
            d_base_asset=trade_result.market_result.d_base,
            d_bond_asset=trade_result.market_result.d_bonds,
            d_base_buffer=-trade_amount,
        )
        agent_deltas = wallet.Wallet(
            address=wallet_address,
            balance=types.Quantity(amount=trade_result.user_result.d_base, unit=types.TokenType.BASE),
            longs={mint_time: wallet.Long(trade_result.user_result.d_bonds)},
            fees_paid=trade_result.breakdown.fee,
        )
        return market_deltas, agent_deltas

    def initialize_market(
        self,
        wallet_address: int,
        contribution: float,
        target_apr: float,
    ) -> tuple[MarketDeltas, wallet.Wallet]:
        """Allows an LP to initialize the market"""
        share_reserves = contribution / self.market_state.share_price
        bond_reserves = self.pricing_model.calc_bond_reserves(
            target_apr=target_apr,
            time_remaining=self.position_duration,
            market_state=MarketState(
                share_reserves=share_reserves,
                init_share_price=self.market_state.init_share_price,
                share_price=self.market_state.share_price,
            ),
        )
        market_deltas = MarketDeltas(
            d_base_asset=contribution,
            d_bond_asset=bond_reserves,
        )
        agent_deltas = wallet.Wallet(
            address=wallet_address,
            balance=-types.Quantity(amount=contribution, unit=types.TokenType.BASE),
            lp_tokens=2 * bond_reserves + contribution,  # 2y + cz
        )
        return (market_deltas, agent_deltas)

    def add_liquidity(
        self,
        wallet_address: int,
        trade_amount: float,
    ) -> tuple[MarketDeltas, wallet.Wallet]:
        """Computes new deltas for bond & share reserves after liquidity is added"""
        # get_rate assumes that there is some amount of reserves, and will throw an error if share_reserves is zero
        if (
            self.market_state.share_reserves == 0 and self.market_state.bond_reserves == 0
        ):  # pool has not been initialized
            rate = 0
        else:
            rate = self.fixed_apr
        # sanity check inputs
        self.pricing_model.check_input_assertions(
            quantity=types.Quantity(
                amount=trade_amount, unit=types.TokenType.PT
            ),  # temporary Quantity object just for this check
            market_state=self.market_state,
            time_remaining=self.position_duration,
        )
        # perform the trade
        lp_out, d_base_reserves, d_bond_reserves = self.pricing_model.calc_lp_out_given_tokens_in(
            d_base=trade_amount,
            rate=rate,
            market_state=self.market_state,
            time_remaining=self.position_duration,
        )
        market_deltas = MarketDeltas(
            d_base_asset=d_base_reserves,
            d_bond_asset=d_bond_reserves,
            d_lp_total_supply=lp_out,
        )
        agent_deltas = wallet.Wallet(
            address=wallet_address,
            balance=-types.Quantity(amount=d_base_reserves, unit=types.TokenType.BASE),
            lp_tokens=lp_out,
        )
        return market_deltas, agent_deltas

    def remove_liquidity(
        self,
        wallet_address: int,
        trade_amount: float,
    ) -> tuple[MarketDeltas, wallet.Wallet]:
        """Computes new deltas for bond & share reserves after liquidity is removed"""
        # sanity check inputs
        self.pricing_model.check_input_assertions(
            quantity=types.Quantity(
                amount=trade_amount, unit=types.TokenType.PT
            ),  # temporary Quantity object just for this check
            market_state=self.market_state,
            time_remaining=self.position_duration,
        )
        # perform the trade
        lp_in, d_base_reserves, d_bond_reserves = self.pricing_model.calc_tokens_out_given_lp_in(
            lp_in=trade_amount,
            rate=self.fixed_apr,
            market_state=self.market_state,
            time_remaining=self.position_duration,
        )
        market_deltas = MarketDeltas(
            d_base_asset=-d_base_reserves,
            d_bond_asset=-d_bond_reserves,
            d_lp_total_supply=-lp_in,
        )
        agent_deltas = wallet.Wallet(
            address=wallet_address,
            balance=types.Quantity(amount=d_base_reserves, unit=types.TokenType.BASE),
            lp_tokens=-lp_in,
        )
        return market_deltas, agent_deltas

    def log_market_step_string(self) -> None:
        """Logs the current market step"""
        # TODO: This is a HACK to prevent test_sim from failing on market shutdown
        # when the market closes, the share_reserves are 0 (or negative & close to 0) and several logging steps break
        if self.market_state.share_reserves <= 0:
            spot_price = str(np.nan)
            rate = str(np.nan)
        else:
            spot_price = self.spot_price
            rate = self.fixed_apr
        logging.debug(
            (
                "t = %g"
                "\nx = %g"
                "\ny = %g"
                "\nlp = %g"
                "\nz = %g"
                "\nx_b = %g"
                "\ny_b = %g"
                "\np = %s"
                "\npool apr = %s"
            ),
            self.time,
            self.market_state.share_reserves * self.market_state.share_price,
            self.market_state.bond_reserves,
            self.market_state.lp_total_supply,
            self.market_state.share_reserves,
            self.market_state.base_buffer,
            self.market_state.bond_buffer,
            str(spot_price),
            str(rate),
        )

"""
Market simulators store state information when interfacing AMM pricing models with users
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, TypeAlias
import logging

import numpy as np

from elfpy.pricing_models import ElementPricingModel, HyperdrivePricingModel, TradeResult
from elfpy.token import TokenType
import elfpy.utils.time as time_utils
import elfpy.utils.price as price_utils
from elfpy.utils.outputs import float_to_string
from elfpy.wallet import Wallet


TradeDirection = Literal["out", "in"]
MarketActionType: TypeAlias = Literal[
    "close_short", "close_long", "open_short", "open_long", "add_liquidity", "remove_liquidity"
]


@dataclass
class MarketAction:
    """market action specification"""

    # these two variables are required to be set by the strategy
    action_type: MarketActionType
    trade_amount: float
    # wallet_address is always set automatically by the basic agent class
    wallet_address: int
    # mint time is set only for trades that act on existing positions (close long or close short)
    mint_time: float = 0

    def __str__(self):
        """Return a description of the Action"""
        output_string = f"{self.wallet_address}"
        for key, value in self.__dict__.items():
            if key == "action_type":
                output_string += f" execute {value}()"
            elif key in ["trade_amount", "mint_time"]:
                output_string += f" {key}: {float_to_string(value)}"
            elif key not in ["wallet_address", "agent"]:
                output_string += f" {key}: {float_to_string(value)}"
        return output_string


@dataclass(frozen=False)
class MarketDeltas:
    """Specifies changes to values in the market"""

    # TODO: Create our own dataclass decorator that is always mutable and includes dict set/get syntax
    # pylint: disable=duplicate-code
    # pylint: disable=too-many-instance-attributes

    d_base_asset: float = 0
    d_token_asset: float = 0
    d_share_buffer: float = 0
    d_bond_buffer: float = 0
    d_lp_reserves: float = 0

    def __getitem__(self, key):
        getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __str__(self):
        output_string = ""
        for key, value in vars(self).items():
            if value:  #  check if object exists
                if value != 0:
                    output_string += f" {key}: "
                    if isinstance(value, float):
                        output_string += f"{float_to_string(value)}"
                    elif isinstance(value, list):
                        output_string += "[" + ", ".join([float_to_string(x) for x in value]) + "]"
                    elif isinstance(value, dict):
                        output_string += "{" + ", ".join([f"{k}: {float_to_string(v)}" for k, v in value.items()]) + "}"
                    else:
                        output_string += f"{value}"
        return output_string


class Market:
    """
    Holds state variables for market simulation and executes trades.

    The Market class executes trades by updating market variables according to the given pricing model.
    It also has some helper variables for assessing pricing model values given market conditions.
    """

    # TODO: set up member object that owns attributes instead of so many individual instance attributes
    # pylint: disable=too-many-instance-attributes
    # Currently many functions use >5 arguments.
    # These should be packaged up into shared variables, e.g.
    #     reserves = (in_reserves, out_reserves)
    #     share_prices = (init_share_price, share_price)
    # pylint: disable=too-many-arguments

    def __init__(
        self,
        fee_percent: float = 0,
        token_duration: float = 1,
        # TODO: remove this, pass to methods instead
        pricing_model: ElementPricingModel | HyperdrivePricingModel | None = None,
        share_reserves: float = 0,
        bond_reserves: float = 0,
        lp_reserves: float = 0,
        time_stretch_constant: float = 1,
        init_share_price: float = 1,
        share_price: float = 1,
    ):
        # market state variables
        self.time: float = 0  # t: timefrac unit is time normalized to 1 year, i.e. 0.5 = 1/2 year
        self.share_reserves: float = share_reserves  # z
        self.bond_reserves: float = bond_reserves  # y
        self.fee_percent: float = fee_percent  # g
        self.init_share_price: float = init_share_price  # u normalizing constant
        self.share_price: float = share_price  # c
        self.token_duration: float = token_duration  # how long does a token last before expiry
        self.share_buffer: float = 0
        self.bond_buffer: float = 0
        self.lp_reserves: float = lp_reserves
        self.time_stretch_constant: float = time_stretch_constant
        # TODO: It would be good to remove the tight coupling between pricing models and markets.
        #       For now, it makes sense to restrict the behavior at the market level since
        #       previous versions of Element didn't allow for shorting (despite the fact that
        #       their pricing models can support shorting).
        self.pricing_model: ElementPricingModel | HyperdrivePricingModel = pricing_model

    def check_action_type(self, action_type: MarketActionType) -> None:
        """Ensure that the agent action is an allowed action for this market
        Arguments
        ---------
        action_type: see MarketActionType for all acceptable actions that can be performed on this market
        """
        pricing_model_name = self.pricing_model.model_name()
        if pricing_model_name.lower() == "element":
            allowed_actions = ["open_long", "close_long", "add_liquidity", "remove_liquidity"]
        elif pricing_model_name.lower() == "hyperdrive":
            allowed_actions = [
                "open_long",
                "close_long",
                "open_short",
                "close_short",
                "add_liquidity",
                "remove_liquidity",
            ]
        else:
            raise ValueError(
                "market.check_action_type: ERROR: pricing model name should "
                f'be in ["element", "hyperdrive"], not {pricing_model_name}'
            )
        if action_type not in allowed_actions:
            raise AssertionError(
                "markets.check_action_type: ERROR: agent_action.action_type should be an allowed action for the"
                f" model={self.pricing_model.model_name()}, not {action_type}!"
            )

    def trade_and_update(self, agent_action: MarketAction) -> Wallet:
        """
        Execute a trade in the simulated market.

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
        """
        self.check_action_type(agent_action.action_type)

        # TODO: check the desired amount is feasible, otherwise return descriptive error
        # update market variables which may have changed since the user action was created
        time_remaining = time_utils.get_yearfrac_remaining(self.time, agent_action.mint_time, self.token_duration)
        stretched_time_remaining = time_utils.stretch_time(time_remaining, self.time_stretch_constant)
        logging.debug(agent_action)
        # for each position, specify how to forumulate trade and then execute
        if agent_action.action_type == "open_long":  # buy to open long
            market_deltas, agent_deltas = self._open_long(agent_action, "pt", stretched_time_remaining)
        elif agent_action.action_type == "close_long":  # sell to close long
            market_deltas, agent_deltas = self._close_long(agent_action, "base", stretched_time_remaining)
        elif agent_action.action_type == "open_short":  # sell PT to open short
            market_deltas, agent_deltas = self._open_short(agent_action, "pt", stretched_time_remaining)
        elif agent_action.action_type == "close_short":  # buy PT to close short
            market_deltas, agent_deltas = self._close_short(agent_action, "pt", stretched_time_remaining)
        elif agent_action.action_type == "add_liquidity":
            market_deltas, agent_deltas = self._add_liquidity(agent_action, time_remaining, stretched_time_remaining)
        elif agent_action.action_type == "remove_liquidity":
            market_deltas, agent_deltas = self._remove_liquidity(agent_action, time_remaining, stretched_time_remaining)
        else:
            raise ValueError(f'ERROR: Unknown trade type "{agent_action.action_type}".')
        # update market state
        self.update_market(market_deltas)
        logging.debug("market deltas = %s", market_deltas)
        return agent_deltas

    def update_market(self, market_deltas: MarketDeltas) -> None:
        """
        Increments member variables to reflect current market conditions
        """
        for key, value in market_deltas.__dict__.items():
            if value:  # check that it's instantiated and non-empty
                assert np.isfinite(value), f"markets.update_market: ERROR: market delta key {key} is not finite."
        self.share_reserves += market_deltas.d_base_asset / self.share_price
        self.bond_reserves += market_deltas.d_token_asset
        self.share_buffer += market_deltas.d_share_buffer
        self.bond_buffer += market_deltas.d_bond_buffer
        self.lp_reserves += market_deltas.d_lp_reserves

    def get_rate(self):
        """Returns the current market apr"""
        # calc_apr_from_spot_price will throw an error if share_reserves is zero
        if self.share_reserves <= 0:  # market is empty
            rate = np.nan
        else:
            rate = price_utils.calc_apr_from_spot_price(self.get_spot_price(), self.token_duration)
        return rate

    def get_spot_price(self):
        """Returns the current market price of the share reserves"""
        # calc_spot_price_from_reserves will throw an error if share_reserves is zero
        if self.share_reserves <= 0:  # market is empty
            spot_price = np.nan
        else:
            spot_price = self.pricing_model.calc_spot_price_from_reserves(
                share_reserves=self.share_reserves,
                bond_reserves=self.bond_reserves,
                init_share_price=self.init_share_price,
                share_price=self.share_price,
                time_remaining=time_utils.stretch_time(self.token_duration, self.time_stretch_constant),
            )
        return spot_price

    def get_market_state_string(self) -> str:
        """Returns a formatted string containing all of the Market class member variables"""
        strings = [f"{attribute} = {value}" for attribute, value in self.__dict__.items()]
        state_string = "\n".join(strings)
        return state_string

    def get_target_reserves(self, token_in: TokenType, trade_direction: TradeDirection) -> float:
        """
        Determine which asset is the target based on token_in and trade_direction
        """
        if trade_direction == "in":
            if token_in == "base":
                target_reserves = self.share_reserves
            elif token_in == "pt":
                target_reserves = self.bond_reserves
            else:
                raise AssertionError(
                    f'markets.get_target_reserves: ERROR: token_in should be "base" or "pt", not {token_in}!'
                )
        elif trade_direction == "out":
            if token_in == "base":
                target_reserves = self.share_reserves
            elif token_in == "pt":
                target_reserves = self.bond_reserves
            else:
                raise AssertionError(
                    f'markets.get_target_reserves: ERROR: token_in should be "base" or "pt", not {token_in}!'
                )
        else:
            raise AssertionError(
                f'markets.get_target_reserves: ERROR: trade_direction should be "in" or "out", not {trade_direction}!'
            )
        return target_reserves

    def check_fees(
        self,
        amount: float,
        tokens: tuple[TokenType, TokenType],
        reserves: tuple[float, float],
        trade_results: TradeResult,
    ) -> None:
        """Checks fee values for out of bounds"""
        (token_in, token_out) = tokens
        (in_reserves, out_reserves) = reserves
        (
            without_fee_or_slippage,
            output_with_fee,
            output_without_fee,
            fee,
        ) = trade_results
        if (
            any(
                [
                    isinstance(output_with_fee, complex),
                    isinstance(output_without_fee, complex),
                    isinstance(fee, complex),
                ]
            )
            or fee < 0
        ):
            state_string = self.get_market_state_string()
            assert False, (
                f"Market.check_fees: Error: fee={fee} should not be < 0 and the type should not be complex."
                f"\ntoken_in = {token_in}"
                f"\ntoken_out = {token_out}"
                f"\nin_reserves = {in_reserves}"
                f"\nout_reserves = {out_reserves}"
                f"\ntrade_amount = {amount}"
                f"\nwithout_fee_or_slippage = {without_fee_or_slippage}"
                f"\noutput_with_fee = {output_with_fee}"
                f"\noutput_without_fee = {output_without_fee}\n"
                f"{state_string}"
            )

    def tick(self, delta_time: float) -> None:
        """Increments the time member variable"""
        self.time += delta_time

    # TODO: lets rename all these internal functions that take a stretch_time_remaining to
    # time_remaining and explain what's expected of the parameter.  basically, the calc functions
    # shouldn't care what kind of time var is passed in.  It should be up to the consumer to pass in
    # properly formatted time.
    def _open_short(
        self, agent_action: MarketAction, token_out: TokenType, stretch_time_remaining: float
    ) -> tuple[MarketDeltas, Wallet]:
        """
        take trade spec & turn it into trade details
        compute wallet update spec with specific details
        will be conditional on the pricing model
        """
        trade_results = self.pricing_model.calc_out_given_in(
            in_=agent_action.trade_amount,
            share_reserves=self.share_reserves,
            bond_reserves=self.bond_reserves,
            token_out=token_out,
            fee_percent=self.fee_percent,
            time_remaining=stretch_time_remaining,
            init_share_price=self.init_share_price,
            share_price=self.share_price,
        )
        (
            without_fee_or_slippage,
            output_with_fee,
            output_without_fee,
            fee,
        ) = trade_results
        logging.debug(
            "opening short: without_fee_or_slippage = %g, output_with_fee = %g, output_without_fee = %g, fee = %g",
            without_fee_or_slippage,
            output_with_fee,
            output_without_fee,
            fee,
        )
        market_deltas = MarketDeltas(
            d_base_asset=-output_with_fee,
            d_token_asset=+agent_action.trade_amount,
            d_bond_buffer=+agent_action.trade_amount,
        )
        # TODO: _in_protocol values should be managed by pricing_model and referenced by user
        max_loss = agent_action.trade_amount - output_with_fee
        wallet_deltas = Wallet(
            address=0,
            base_in_wallet=-max_loss,
            base_in_protocol={agent_action.mint_time: +max_loss},
            token_in_protocol={agent_action.mint_time: -agent_action.trade_amount},
            fees_paid=+fee,
        )
        return market_deltas, wallet_deltas

    def _close_short(
        self, agent_action: MarketAction, token_in: TokenType, stretched_time_remaining: float
    ) -> tuple[MarketDeltas, Wallet]:
        """
        take trade spec & turn it into trade details
        compute wallet update spec with specific details
            will be conditional on the pricing model
        """
        if agent_action.trade_amount > self.bond_reserves:
            logging.warning(
                (
                    "markets._close_short: WARNING: trade amount = %g"
                    "is greater than bond reserves = %g."
                    "Adjusting to allowable amount."
                ),
                agent_action.trade_amount,
                self.bond_reserves,
            )
            agent_action.trade_amount = self.bond_reserves
        trade_results = self.pricing_model.calc_in_given_out(
            agent_action.trade_amount,
            self.share_reserves,
            self.bond_reserves,
            token_in,
            self.fee_percent,
            stretched_time_remaining,
            self.init_share_price,
            self.share_price,
        )
        (
            without_fee_or_slippage,
            output_with_fee,
            output_without_fee,
            fee,
        ) = trade_results
        logging.debug(
            "closing short: without_fee_or_slippage = %g, output_with_fee = %g, output_without_fee = %g, fee = %g",
            without_fee_or_slippage,
            output_with_fee,
            output_without_fee,
            fee,
        )
        market_deltas = MarketDeltas(
            d_base_asset=+output_with_fee,
            d_token_asset=-agent_action.trade_amount,
            d_bond_buffer=-agent_action.trade_amount,
        )
        # TODO: Add logic:
        # If the user is not closing a full short (i.e. the mint_time balance is not zeroed out)
        # then the user does not get any money into their wallet
        # Right now the user has to close the full short
        agent_deltas = Wallet(
            address=0,
            base_in_wallet=+output_with_fee,
            base_in_protocol={agent_action.mint_time: -output_with_fee},
            token_in_protocol={agent_action.mint_time: +agent_action.trade_amount},
            fees_paid=+fee,
        )
        return market_deltas, agent_deltas

    def _open_long(
        self, agent_action: MarketAction, token_out: TokenType, stretched_time_remaining: float
    ) -> tuple[MarketDeltas, Wallet]:
        """
        take trade spec & turn it into trade details
        compute wallet update spec with specific details
            will be conditional on the pricing model
        """
        if agent_action.trade_amount <= self.bond_reserves:
            trade_results = self.pricing_model.calc_out_given_in(
                agent_action.trade_amount,
                self.share_reserves,
                self.bond_reserves,
                token_out,
                self.fee_percent,
                stretched_time_remaining,
                self.init_share_price,
                self.share_price,
            )
            (
                without_fee_or_slippage,
                output_with_fee,
                output_without_fee,
                fee,
            ) = trade_results
            logging.debug(
                "opening long: without_fee_or_slippage = %g, output_with_fee = %g, output_without_fee = %g, fee = %g",
                without_fee_or_slippage,
                output_with_fee,
                output_without_fee,
                fee,
            )
            market_deltas = MarketDeltas(
                d_base_asset=+agent_action.trade_amount,
                d_token_asset=-output_with_fee,
                d_share_buffer=+output_with_fee / self.share_price,
            )
            agent_deltas = Wallet(
                address=0,
                base_in_wallet=-agent_action.trade_amount,
                token_in_protocol={agent_action.mint_time: +output_with_fee},
                fees_paid=+fee,
            )
        else:
            market_deltas = MarketDeltas()
            agent_deltas = Wallet(address=0, base_in_wallet=0)
        return market_deltas, agent_deltas

    def _close_long(
        self, agent_action: MarketAction, token_out: TokenType, stretched_time_remaining: float
    ) -> tuple[MarketDeltas, Wallet]:
        """
        take trade spec & turn it into trade details
        compute wallet update spec with specific details
            will be conditional on the pricing model
        """
        trade_results = self.pricing_model.calc_out_given_in(
            agent_action.trade_amount,
            self.share_reserves,
            self.bond_reserves,
            token_out,
            self.fee_percent,
            stretched_time_remaining,
            self.init_share_price,
            self.share_price,
        )
        (
            without_fee_or_slippage,
            output_with_fee,
            output_without_fee,
            fee,
        ) = trade_results
        logging.debug(
            "closing long: without_fee_or_slippage = %g, output_with_fee = %g, output_without_fee = %g, fee = %g",
            without_fee_or_slippage,
            output_with_fee,
            output_without_fee,
            fee,
        )
        market_deltas = MarketDeltas(
            d_base_asset=-output_with_fee,
            d_token_asset=+agent_action.trade_amount,
            d_share_buffer=-agent_action.trade_amount / self.share_price,
        )
        agent_deltas = Wallet(
            address=0,
            base_in_wallet=+output_with_fee,
            token_in_wallet={agent_action.mint_time: -agent_action.trade_amount},
            fees_paid=+fee,
        )
        return market_deltas, agent_deltas

    def _add_liquidity(
        self, agent_action: MarketAction, time_remaining: float, stretched_time_remaining: float
    ) -> tuple[MarketDeltas, Wallet]:
        """
        Computes new deltas for bond & share reserves after liquidity is added
        """
        # get_rate assumes that there is some amount of reserves, and will throw an error if share_reserves is zero
        if self.share_reserves == 0 and self.bond_reserves == 0:  # pool has not been initialized
            rate = 0
        else:
            rate = self.get_rate()
        lp_out, d_base_reserves, d_token_reserves = self.pricing_model.calc_lp_out_given_tokens_in(
            d_base=agent_action.trade_amount,
            share_reserves=self.share_reserves,
            bond_reserves=self.bond_reserves,
            share_buffer=self.share_buffer,
            init_share_price=self.init_share_price,
            share_price=self.share_price,
            lp_reserves=self.lp_reserves,
            rate=rate,
            time_remaining=time_remaining,
            stretched_time_remaining=stretched_time_remaining,
        )
        market_deltas = MarketDeltas(
            d_base_asset=+d_base_reserves,
            d_token_asset=+d_token_reserves,
            d_lp_reserves=+lp_out,
        )
        agent_deltas = Wallet(
            address=0,
            base_in_wallet=-d_base_reserves,
            lp_in_wallet=+lp_out,
        )
        return market_deltas, agent_deltas

    def _remove_liquidity(
        self, agent_action: MarketAction, time_remaining: float, stretched_time_remaining: float
    ) -> tuple[MarketDeltas, Wallet]:
        """
        Computes new deltas for bond & share reserves after liquidity is removed
        """
        lp_in, d_base_reserves, d_token_reserves = self.pricing_model.calc_tokens_out_given_lp_in(
            lp_in=agent_action.trade_amount,
            share_reserves=self.share_reserves,
            bond_reserves=self.bond_reserves,
            share_buffer=self.share_buffer,
            init_share_price=self.init_share_price,
            share_price=self.share_price,
            lp_reserves=self.lp_reserves,
            rate=self.get_rate(),
            time_remaining=time_remaining,
            stretched_time_remaining=stretched_time_remaining,
        )
        market_deltas = MarketDeltas(
            d_base_asset=-d_base_reserves,
            d_token_asset=-d_token_reserves,
            d_lp_reserves=-lp_in,
        )
        agent_deltas = Wallet(
            address=0,
            base_in_wallet=+d_base_reserves,
            lp_in_wallet=-lp_in,
        )
        return market_deltas, agent_deltas

    def log_market_step_string(self) -> str:
        """Returns a string that describes the current market step"""
        # TODO: This is a HACK to prevent test_sim from failing on market shutdown
        # when the market closes, the share_reserves are 0 (or negative & close to 0) and several logging steps break
        if self.share_reserves <= 0:
            spot_price = str(np.nan)
            rate = str(np.nan)
        else:
            spot_price = self.get_spot_price()
            rate = self.get_rate()
        logging.debug(
            (
                "\nt = %g"
                "\nx = %g"
                "\ny = %g"
                "\nlp = %g"
                "\nz = %g"
                "\nz_b = %g"
                "\ny_b = %g"
                "\np = %g"
                "\nrate = %g"
            ),
            self.time,
            self.share_reserves * self.share_price,
            self.bond_reserves,
            self.lp_reserves,
            self.share_reserves,
            self.share_buffer,
            self.bond_buffer,
            spot_price,
            rate,
        )

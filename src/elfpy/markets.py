"""
Market simulators store state information when interfacing AMM pricing models with users
"""

from __future__ import annotations
import logging

import numpy as np

from elfpy.pricing_models.base import PricingModel
from elfpy.types import (
    MarketAction,
    MarketActionType,
    MarketDeltas,
    MarketState,
    Quantity,
    StretchedTime,
    TokenType,
)
import elfpy.utils.time as time_utils
import elfpy.utils.price as price_utils
from elfpy.wallet import Wallet


class Market:
    """
    Holds state variables for market simulation and executes trades.

    The Market class executes trades by updating market variables according to the given pricing model.
    It also has some helper variables for assessing pricing model values given market conditions.
    """

    def __init__(
        self,
        fee_percent: float = 0,
        market_state: MarketState = MarketState(
            share_reserves=0,
            bond_reserves=0,
            base_buffer=0,
            bond_buffer=0,
            lp_reserves=0,
            share_price=1,
            init_share_price=1,
        ),
        position_duration: StretchedTime = StretchedTime(365, 1),
    ):
        # market state variables
        self.time: float = 0  # t: timefrac unit is time normalized to 1 year, i.e. 0.5 = 1/2 year
        self.market_state: MarketState = market_state
        self.fee_percent: float = fee_percent  # g
        self.position_duration: StretchedTime = position_duration  # how long do positions take to mature

    def check_action_type(self, action_type: MarketActionType, pricing_model_name: str) -> None:
        """Ensure that the agent action is an allowed action for this market

        Arguments
        ---------
        action_type : MarketActionType
            See MarketActionType for all acceptable actions that can be performed on this market
        pricing_model_name : str
            The name of the pricing model, must be "hyperdrive" or "yieldspace"
        """
        if pricing_model_name.lower() == "hyperdrive" or pricing_model_name.lower() == "yieldspace":
            allowed_actions = [
                MarketActionType.OPEN_LONG,
                MarketActionType.CLOSE_LONG,
                MarketActionType.OPEN_SHORT,
                MarketActionType.CLOSE_SHORT,
                MarketActionType.ADD_LIQUIDITY,
                MarketActionType.REMOVE_LIQUIDITY,
            ]
        else:
            raise ValueError(
                "market.check_action_type: ERROR: pricing model name should "
                f'be in ["hyperdrive", "yieldspace"], not {pricing_model_name}'
            )
        if action_type not in allowed_actions:
            raise AssertionError(
                "markets.check_action_type: ERROR: agent_action.action_type should be an allowed action for the"
                f" model={pricing_model_name}, not {action_type}!"
            )

    def trade_and_update(self, agent_action: MarketAction, pricing_model: PricingModel) -> Wallet:
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
        self.check_action_type(agent_action.action_type, pricing_model.model_name())
        # TODO: check the desired amount is feasible, otherwise return descriptive error
        # update market variables which may have changed since the user action was created
        time_remaining = StretchedTime(
            # TODO: We should improve the StretchedTime API so that it accepts yearfracs in
            # the place of days remaining.
            days=time_utils.get_yearfrac_remaining(
                self.time, agent_action.mint_time, self.position_duration.normalized_time
            )
            * 365,
            time_stretch=self.position_duration.time_stretch,
        )
        # for each position, specify how to forumulate trade and then execute
        if agent_action.action_type == MarketActionType.OPEN_LONG:  # buy to open long
            market_deltas, agent_deltas = self._open_long(
                pricing_model=pricing_model,
                agent_action=agent_action,
                time_remaining=time_remaining,
            )
        elif agent_action.action_type == MarketActionType.CLOSE_LONG:  # sell to close long
            market_deltas, agent_deltas = self._close_long(
                pricing_model=pricing_model,
                agent_action=agent_action,
                time_remaining=time_remaining,
            )
        elif agent_action.action_type == MarketActionType.OPEN_SHORT:  # sell PT to open short
            market_deltas, agent_deltas = self._open_short(
                pricing_model=pricing_model,
                agent_action=agent_action,
                time_remaining=time_remaining,
            )
        elif agent_action.action_type == MarketActionType.CLOSE_SHORT:  # buy PT to close short
            market_deltas, agent_deltas = self._close_short(
                pricing_model=pricing_model,
                agent_action=agent_action,
                time_remaining=time_remaining,
            )
        elif agent_action.action_type == MarketActionType.ADD_LIQUIDITY:
            market_deltas, agent_deltas = self._add_liquidity(
                pricing_model=pricing_model,
                agent_action=agent_action,
                time_remaining=time_remaining.normalized_time,
                stretched_time_remaining=time_remaining.stretched_time,
            )
        elif agent_action.action_type == MarketActionType.REMOVE_LIQUIDITY:
            market_deltas, agent_deltas = self._remove_liquidity(
                pricing_model=pricing_model,
                agent_action=agent_action,
                time_remaining=time_remaining.normalized_time,
                stretched_time_remaining=time_remaining.stretched_time,
            )
        else:
            raise ValueError(f'ERROR: Unknown trade type "{agent_action.action_type}".')
        # update market state
        self.update_market(market_deltas)
        logging.info(agent_action)
        logging.debug("market deltas = %s", market_deltas)
        return agent_deltas

    def update_market(self, market_deltas: MarketDeltas) -> None:
        """
        Increments member variables to reflect current market conditions
        """
        for key, value in market_deltas.__dict__.items():
            if value:  # check that it's instantiated and non-empty
                assert np.isfinite(value), f"markets.update_market: ERROR: market delta key {key} is not finite."
        self.market_state.apply_delta(market_deltas)

    def get_rate(self, pricing_model):
        """Returns the current market apr"""
        # calc_apr_from_spot_price will throw an error if share_reserves <= zero
        # TODO: Negative values should never happen, but do because of rounding errors.
        #       Write checks to remedy this in the market.
        if self.market_state.share_reserves <= 0:  # market is empty; negative value likely due to rounding error
            rate = np.nan
        else:
            rate = price_utils.calc_apr_from_spot_price(self.get_spot_price(pricing_model), self.position_duration)
        return rate

    def get_spot_price(self, pricing_model: PricingModel):
        """Returns the current market price of the share reserves"""
        # calc_spot_price_from_reserves will throw an error if share_reserves is zero
        if self.market_state.share_reserves == 0:  # market is empty
            spot_price = np.nan
        else:
            spot_price = pricing_model.calc_spot_price_from_reserves(
                market_state=self.market_state,
                time_remaining=self.position_duration,
            )
        return spot_price

    def get_market_state_string(self) -> str:
        """Returns a formatted string containing all of the Market class member variables"""
        strings = [f"{attribute} = {value}" for attribute, value in self.__dict__.items()]
        state_string = "\n".join(strings)
        return state_string

    def tick(self, delta_time: float) -> None:
        """Increments the time member variable"""
        self.time += delta_time

    def _open_short(
        self,
        pricing_model: PricingModel,
        agent_action: MarketAction,
        time_remaining: StretchedTime,
    ) -> tuple[MarketDeltas, Wallet]:
        """
        take trade spec & turn it into trade details
        compute wallet update spec with specific details
        will be conditional on the pricing model
        """
        # Perform the trade.
        trade_quantity = Quantity(amount=agent_action.trade_amount, unit=TokenType.PT)
        pricing_model.check_input_assertions(
            quantity=trade_quantity,
            market_state=self.market_state,
            fee_percent=self.fee_percent,
            time_remaining=time_remaining,
        )
        trade_result = pricing_model.calc_out_given_in(
            in_=trade_quantity,
            market_state=self.market_state,
            fee_percent=self.fee_percent,
            time_remaining=time_remaining,
        )
        pricing_model.check_output_assertions(trade_result=trade_result)

        # Log the trade result.
        logging.debug("opening short: trade_result = %s", trade_result)

        # Return the market and wallet deltas.
        market_deltas = MarketDeltas(
            d_base_asset=trade_result.market_result.d_base,
            d_token_asset=trade_result.market_result.d_bonds,
            d_bond_buffer=+agent_action.trade_amount,
        )
        # TODO: _in_protocol values should be managed by pricing_model and referenced by user
        max_loss = agent_action.trade_amount - trade_result.user_result.d_base
        wallet_deltas = Wallet(
            address=agent_action.wallet_address,
            base=-max_loss,
            # TODO: This implementation is opinionated in a way that may not be
            #       correct. The question of whether or not shorts should be
            #       fully backed is still up for debate.
            margin={agent_action.mint_time: +trade_result.user_result.d_base + max_loss},
            shorts={agent_action.mint_time: trade_result.user_result.d_bonds},
            fees_paid=+trade_result.breakdown.fee,
        )
        return market_deltas, wallet_deltas

    def _close_short(
        self,
        pricing_model: PricingModel,
        agent_action: MarketAction,
        time_remaining: StretchedTime,
    ) -> tuple[MarketDeltas, Wallet]:
        """
        take trade spec & turn it into trade details
        compute wallet update spec with specific details
            will be conditional on the pricing model
        """

        # Clamp the trade amount to the bond reserves.
        if agent_action.trade_amount > self.market_state.bond_reserves:
            logging.warning(
                (
                    "markets._close_short: WARNING: trade amount = %g"
                    "is greater than bond reserves = %g."
                    "Adjusting to allowable amount."
                ),
                agent_action.trade_amount,
                self.market_state.bond_reserves,
            )
            agent_action.trade_amount = self.market_state.bond_reserves

        # Perform the trade.
        trade_quantity = Quantity(amount=agent_action.trade_amount, unit=TokenType.PT)
        pricing_model.check_input_assertions(
            quantity=trade_quantity,
            market_state=self.market_state,
            fee_percent=self.fee_percent,
            time_remaining=time_remaining,
        )
        trade_result = pricing_model.calc_in_given_out(
            out=trade_quantity,
            market_state=self.market_state,
            fee_percent=self.fee_percent,
            time_remaining=time_remaining,
        )
        pricing_model.check_output_assertions(trade_result=trade_result)

        # Log the trade result.
        logging.debug(
            "closing short: trade_result = %s",
            trade_result,
        )

        # Return the market and wallet deltas.
        market_deltas = MarketDeltas(
            d_base_asset=trade_result.market_result.d_base,
            d_token_asset=trade_result.market_result.d_bonds,
            d_bond_buffer=-agent_action.trade_amount,
        )
        # TODO: This accounting doesn't look right. The profit from the
        #       short should be calculated using the difference between
        #       the open short price and the sale price plus the max loss
        #       buffer.
        agent_deltas = Wallet(
            address=agent_action.wallet_address,
            base=trade_result.user_result.d_base,
            margin={agent_action.mint_time: agent_action.trade_amount - trade_result.user_result.d_base},
            shorts={agent_action.mint_time: trade_result.user_result.d_bonds},
            fees_paid=trade_result.breakdown.fee,
        )
        return market_deltas, agent_deltas

    def _open_long(
        self,
        pricing_model: PricingModel,
        agent_action: MarketAction,
        time_remaining: StretchedTime,
    ) -> tuple[MarketDeltas, Wallet]:
        """
        take trade spec & turn it into trade details
        compute wallet update spec with specific details
            will be conditional on the pricing model
        """
        # TODO: Why are we clamping elsewhere but we don't apply the trade at
        # all here?
        if agent_action.trade_amount <= self.market_state.bond_reserves:
            # Perform the trade.
            trade_quantity = Quantity(amount=agent_action.trade_amount, unit=TokenType.BASE)
            pricing_model.check_input_assertions(
                quantity=trade_quantity,
                market_state=self.market_state,
                fee_percent=self.fee_percent,
                time_remaining=time_remaining,
            )
            trade_result = pricing_model.calc_out_given_in(
                in_=trade_quantity,
                market_state=self.market_state,
                fee_percent=self.fee_percent,
                time_remaining=time_remaining,
            )
            pricing_model.check_output_assertions(trade_result=trade_result)

            # Log the trade result.
            logging.debug(
                "opening long: trade_result %s",
                trade_result,
            )

            # Get the market and wallet deltas to return.
            market_deltas = MarketDeltas(
                d_base_asset=trade_result.market_result.d_base,
                d_token_asset=trade_result.market_result.d_bonds,
                d_base_buffer=trade_result.user_result.d_bonds,
            )
            agent_deltas = Wallet(
                address=agent_action.wallet_address,
                base=trade_result.user_result.d_base,
                shorts={agent_action.mint_time: trade_result.user_result.d_bonds},
                fees_paid=trade_result.breakdown.fee,
            )
        else:
            market_deltas = MarketDeltas()
            agent_deltas = Wallet(address=agent_action.wallet_address, base=0)
        return market_deltas, agent_deltas

    def _close_long(
        self,
        pricing_model: PricingModel,
        agent_action: MarketAction,
        time_remaining: StretchedTime,
    ) -> tuple[MarketDeltas, Wallet]:
        """
        take trade spec & turn it into trade details
        compute wallet update spec with specific details
            will be conditional on the pricing model
        """

        # Perform the trade.
        quantity = Quantity(amount=agent_action.trade_amount, unit=TokenType.PT)
        pricing_model.check_input_assertions(
            quantity=quantity,
            market_state=self.market_state,
            fee_percent=self.fee_percent,
            time_remaining=time_remaining,
        )
        trade_result = pricing_model.calc_out_given_in(
            in_=quantity,
            market_state=self.market_state,
            fee_percent=self.fee_percent,
            time_remaining=time_remaining,
        )
        pricing_model.check_output_assertions(trade_result)

        # Log the trade result.
        logging.debug("closing long: trade_result = %s", trade_result)

        # Return the market and wallet deltas.
        market_deltas = MarketDeltas(
            d_base_asset=trade_result.market_result.d_base,
            d_token_asset=trade_result.market_result.d_bonds,
            d_base_buffer=-agent_action.trade_amount,
        )
        agent_deltas = Wallet(
            address=agent_action.wallet_address,
            base=trade_result.user_result.d_base,
            longs={agent_action.mint_time: trade_result.user_result.d_bonds},
            fees_paid=trade_result.breakdown.fee,
        )
        return market_deltas, agent_deltas

    def _add_liquidity(
        self,
        pricing_model: PricingModel,
        agent_action: MarketAction,
        time_remaining: float,
        stretched_time_remaining: float,
    ) -> tuple[MarketDeltas, Wallet]:
        """
        Computes new deltas for bond & share reserves after liquidity is added
        """
        # get_rate assumes that there is some amount of reserves, and will throw an error if share_reserves is zero
        if (
            self.market_state.share_reserves == 0 and self.market_state.bond_reserves == 0
        ):  # pool has not been initialized
            rate = 0
        else:
            rate = self.get_rate(pricing_model)
        lp_out, d_base_reserves, d_token_reserves = pricing_model.calc_lp_out_given_tokens_in(
            d_base=agent_action.trade_amount,
            share_reserves=self.market_state.share_reserves,
            bond_reserves=self.market_state.bond_reserves,
            base_buffer=self.market_state.base_buffer,
            init_share_price=self.market_state.init_share_price,
            share_price=self.market_state.share_price,
            lp_reserves=self.market_state.lp_reserves,
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
            address=agent_action.wallet_address,
            base=-d_base_reserves,
            lp_tokens=+lp_out,
        )
        return market_deltas, agent_deltas

    def _remove_liquidity(
        self,
        pricing_model: PricingModel,
        agent_action: MarketAction,
        time_remaining: float,
        stretched_time_remaining: float,
    ) -> tuple[MarketDeltas, Wallet]:
        """
        Computes new deltas for bond & share reserves after liquidity is removed
        """
        lp_in, d_base_reserves, d_token_reserves = pricing_model.calc_tokens_out_given_lp_in(
            lp_in=agent_action.trade_amount,
            share_reserves=self.market_state.share_reserves,
            bond_reserves=self.market_state.bond_reserves,
            base_buffer=self.market_state.base_buffer,
            init_share_price=self.market_state.init_share_price,
            share_price=self.market_state.share_price,
            lp_reserves=self.market_state.lp_reserves,
            rate=self.get_rate(pricing_model),
            time_remaining=time_remaining,
            stretched_time_remaining=stretched_time_remaining,
        )
        market_deltas = MarketDeltas(
            d_base_asset=-d_base_reserves,
            d_token_asset=-d_token_reserves,
            d_lp_reserves=-lp_in,
        )
        agent_deltas = Wallet(
            address=agent_action.wallet_address,
            base=+d_base_reserves,
            lp_tokens=-lp_in,
        )
        return market_deltas, agent_deltas

    def log_market_step_string(self, pricing_model: PricingModel) -> None:
        """Logs the current market step"""
        # TODO: This is a HACK to prevent test_sim from failing on market shutdown
        # when the market closes, the share_reserves are 0 (or negative & close to 0) and several logging steps break
        if self.market_state.share_reserves <= 0:
            spot_price = str(np.nan)
            rate = str(np.nan)
        else:
            spot_price = self.get_spot_price(pricing_model)
            rate = self.get_rate(pricing_model)
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
            self.market_state.lp_reserves,
            self.market_state.share_reserves,
            self.market_state.base_buffer,
            self.market_state.bond_buffer,
            str(spot_price),
            str(rate),
        )

"""
Market simulators store state information when interfacing AMM pricing models with users
"""

from dataclasses import dataclass, field

import numpy as np
from elfpy.pricing_models import ElementPricingModel, HyperdrivePricingModel, TradeResult
from elfpy.token import TokenType

import elfpy.utils.time as time_utils
from elfpy.agent import Agent, AgentActionType, TradeDirection
import elfpy.utils.price as price_utils
from elfpy.utils.bcolors import Bcolors as bcolors
from elfpy.utils.outputs import float_to_string
from elfpy.wallet import Wallet

# Currently many functions use >5 arguments.
# These should be packaged up into shared variables, e.g.
#     reserves = (in_reserves, out_reserves)
#     share_prices = (init_share_price, share_price)
# pylint: disable=too-many-arguments


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
    d_lp_reserves_history: list[float] = field(default_factory=list)
    d_base_asset_slippage: float = 0
    d_token_asset_slippage: float = 0
    d_share_fee: float = 0
    d_share_fee_history: dict[float, float] = field(default_factory=dict)
    d_token_fee: float = 0
    d_token_fee_history: dict[float, float] = field(default_factory=dict)
    d_base_asset_orders: int = 0
    d_token_asset_orders: int = 0
    d_base_asset_volume: float = 0
    d_token_asset_volume: float = 0

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

    def __init__(
        self,
        fee_percent: float,
        token_duration: float,
        # TODO: remove this, pass to methods instead
        pricing_model: ElementPricingModel | HyperdrivePricingModel,
        share_reserves: float,
        bond_reserves: float,
        lp_reserves: float,
        time_stretch_constant: float = 1,
        init_share_price: float = 1,
        share_price: float = 1,
        verbose: bool = False,
    ):
        self.time: float = 0  # time normalized to 1 year, i.e. 0.5 = 1/2 year
        self.share_reserves: float = share_reserves  # z
        self.bond_reserves: float = bond_reserves  # y
        self.share_buffer: float = 0
        self.bond_buffer: float = 0
        self.lp_reserves: float = lp_reserves
        # TODO: why is this a list when other histories are a dict?  we should make this one match the
        # others. honestly we should make history dict type if this is a common pattern
        self.lp_reserves_history: list[
            float
        ] = []  # list trades by user and time, initialize as empty list to allow appending
        self.fee_percent: float = fee_percent  # g
        self.time_stretch_constant: float = time_stretch_constant
        self.init_share_price: float = init_share_price  # u normalizing constant
        self.share_price: float = share_price  # c
        self.token_duration: float = token_duration  # how long does a token last before expiry

        # TODO: It would be good to remove the tight coupling between pricing models and markets.
        #       For now, it makes sense to restrict the behavior at the market level since
        #       previous versions of Element didn't allow for shorting (despite the fact that
        #       their pricing models can support shorting).
        self.pricing_model: ElementPricingModel | HyperdrivePricingModel = pricing_model

        self.base_asset_orders: int = 0
        self.token_asset_orders: int = 0
        self.base_asset_volume: float = 0
        self.token_asset_volume: float = 0
        self.cum_token_asset_slippage: float = 0
        self.cum_base_asset_slippage: float = 0
        self.share_fees: float = 0
        self.share_fee_history: dict[float, float] = {}
        self.token_fees: float = 0
        self.token_fee_history: dict[float, float] = {}
        self.spot_price: float = 0
        self.rate: float = 0
        # TODO: fix this? is this true? total_supply is usually the num of lp shares, which is not equal to this sum
        self.total_supply: float = self.share_reserves + self.bond_reserves
        self.verbose: bool = verbose

    def check_action_type(self, action_type: AgentActionType) -> None:
        """Ensure that the agent action is an allowed action for this market
        Arguments
        ---------
        action_type :
            must be either "element" or "hyperdrive"
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

    def trade_and_update(self, agent_action: Agent.AgentAction) -> Wallet:
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
        # if self.verbose:
        agent_action.print_description_string()
        # for each position, specify how to forumulate trade and then execute
        # TODO: we shouldn't set values on the object passed in, add parameters to
        # open/close_long/short functions so that this isn't necessary
        update_price_and_rate = True
        if agent_action.action_type == "open_long":  # buy to open long
            market_deltas, agent_deltas = self._open_long(agent_action, "pt")
        elif agent_action.action_type == "close_long":  # sell to close long
            market_deltas, agent_deltas = self._close_long(agent_action, "base")
        elif agent_action.action_type == "open_short":  # sell PT to open short
            market_deltas, agent_deltas = self._open_short(agent_action, "pt")
        elif agent_action.action_type == "close_short":  # buy PT to close short
            market_deltas, agent_deltas = self._close_short(agent_action, "pt")
        elif agent_action.action_type == "add_liquidity":
            market_deltas, agent_deltas = self._add_liquidity(agent_action)
        elif agent_action.action_type == "remove_liquidity":
            market_deltas, agent_deltas = self._remove_liquidity(agent_action)
            update_price_and_rate = False
        else:
            raise ValueError(f'ERROR: Unknown trade type "{agent_action.action_type}".')
        # update market state
        self.update_market(market_deltas, update_price_and_rate)
        if self.verbose:
            print(f"market Δs ={market_deltas}")
        return agent_deltas

    def update_market(self, market_deltas: MarketDeltas, update_price_and_rate=True) -> None:
        """
        Increments member variables to reflect current market conditions
        """
        # TODO: The nested branching inside for-loops is cumbersome and can slow down the execution
        # pylint: disable=too-many-branches
        for key, value in market_deltas.__dict__.items():
            if value:  # check that it's instantiated and non-empty
                if key == "d_lp_reserves_history":
                    assert isinstance(
                        value, list
                    ), f"markets.update_market: Error: {key} has value={value} should be a dict"
                elif key in ["d_share_fee_history", "d_token_fee_history"]:
                    assert isinstance(
                        value, dict
                    ), f"markets.update_market: Error: {key} has value={value} should be a dict"
                else:
                    assert np.isfinite(value), f"markets.update_market: ERROR: market delta key {key} is not finite."
        self.share_reserves += market_deltas.d_base_asset / self.share_price
        self.bond_reserves += market_deltas.d_token_asset
        self.share_buffer += market_deltas.d_share_buffer
        self.bond_buffer += market_deltas.d_bond_buffer
        self.lp_reserves += market_deltas.d_lp_reserves
        if market_deltas.d_lp_reserves_history:  # not empty
            self.lp_reserves_history.extend(market_deltas.d_lp_reserves_history)
        self.share_fees += market_deltas.d_share_fee
        if market_deltas.d_share_fee_history:  # not empty
            for key, value in market_deltas.d_share_fee_history.items():
                if key not in self.share_fee_history:
                    self.share_fee_history.update(market_deltas.d_share_fee_history)
                else:
                    self.share_fee_history[key] += value
        self.token_fees += market_deltas.d_token_fee
        if market_deltas.d_token_fee_history:  # not empty
            for key, value in market_deltas.d_token_fee_history.items():
                if key not in self.token_fee_history:
                    self.token_fee_history.update(market_deltas.d_token_fee_history)
                else:
                    self.token_fee_history[key] += value
        self.cum_base_asset_slippage += market_deltas.d_base_asset_slippage
        self.cum_token_asset_slippage += market_deltas.d_token_asset_slippage
        self.base_asset_orders += market_deltas.d_base_asset_orders
        self.token_asset_orders += market_deltas.d_token_asset_orders
        self.base_asset_volume += market_deltas.d_base_asset_volume
        self.token_asset_volume += market_deltas.d_token_asset_volume
        if update_price_and_rate:
            self.spot_price = self.pricing_model.calc_spot_price_from_reserves(
                share_reserves=self.share_reserves,
                bond_reserves=self.bond_reserves,
                init_share_price=self.init_share_price,
                share_price=self.share_price,
                time_remaining=time_utils.stretch_time(self.token_duration, self.time_stretch_constant),
            )
            self.rate = price_utils.calc_apr_from_spot_price(self.spot_price, self.token_duration)

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
        """Checks fee values for out of bounds and prints verbose outputs"""
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
                + f"\ntoken_in = {token_in}"
                + f"\ntoken_out = {token_out}"
                + f"\nin_reserves = {in_reserves}"
                + f"\nout_reserves = {out_reserves}"
                + f"\ntrade_amount = {amount}"
                + f"\nwithout_fee_or_slippage = {without_fee_or_slippage}"
                + f"\noutput_with_fee = {output_with_fee}"
                + f"\noutput_without_fee = {output_without_fee}\n"
                + state_string
            )

    def tick(self, delta_time: float) -> None:
        """Increments the time member variable"""
        self.time += delta_time

    def _open_short(
        self, agent_action: Agent.AgentAction, token_out: TokenType, time_remaining: float
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
            time_remaining=time_remaining,
            init_share_price=self.init_share_price,
            share_price=self.share_price,
        )
        (
            without_fee_or_slippage,
            output_with_fee,
            output_without_fee,
            fee,
        ) = trade_results
        if self.verbose:
            print(f"opening short: {without_fee_or_slippage, output_with_fee, output_without_fee, fee}")
        market_deltas = MarketDeltas(
            d_base_asset=-output_with_fee,
            d_token_asset=+agent_action.trade_amount,
            d_bond_buffer=+agent_action.trade_amount,
            d_share_fee=+fee / self.share_price,
            d_share_fee_history={agent_action.mint_time: fee / self.share_price},
            d_base_asset_slippage=+abs(without_fee_or_slippage - output_without_fee),
            d_base_asset_orders=+1,
            d_base_asset_volume=+output_with_fee,
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
        self, agent_action: Agent.AgentAction, token_in: TokenType, stretched_time_remaining: float
    ) -> tuple[MarketDeltas, Wallet]:
        """
        take trade spec & turn it into trade details
        compute wallet update spec with specific details
            will be conditional on the pricing model
        """
        if agent_action.trade_amount > self.bond_reserves:
            print(
                f"markets._close_short: WARNING: trade amount = {agent_action.trade_amount} "
                f"is greater than bond reserves = {self.bond_reserves}."
                f"Adjusting to allowable amount."
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
        market_deltas = MarketDeltas(
            d_base_asset=+output_with_fee,
            d_token_asset=-agent_action.trade_amount,
            d_bond_buffer=-agent_action.trade_amount,
            d_share_fee=+fee / self.share_price,
            d_share_fee_history={agent_action.mint_time: fee / self.share_price},
            d_base_asset_slippage=+abs(without_fee_or_slippage - output_without_fee),
            d_base_asset_orders=+1,
            d_base_asset_volume=+output_with_fee,
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
        self, agent_action: Agent.AgentAction, token_out: TokenType, stretched_time_remaining: float
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
            market_deltas = MarketDeltas(
                d_base_asset=+agent_action.trade_amount,
                d_token_asset=-output_with_fee,
                d_share_buffer=+output_with_fee / self.share_price,
                d_token_fee=+fee,
                d_token_fee_history={agent_action.mint_time: fee},
                d_token_asset_slippage=+abs(without_fee_or_slippage - output_without_fee),
                d_token_asset_orders=+1,
                d_token_asset_volume=+output_with_fee,
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
        self, agent_action: Agent.AgentAction, token_out: TokenType, stretched_time_remaining: float
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
        market_deltas = MarketDeltas(
            d_base_asset=-output_with_fee,
            d_token_asset=+agent_action.trade_amount,
            d_share_buffer=-agent_action.trade_amount / self.share_price,
            d_share_fee=+fee / self.share_price,
            d_share_fee_history={agent_action.mint_time: fee / self.share_price},
            d_base_asset_slippage=+abs(without_fee_or_slippage - output_without_fee),
            d_base_asset_orders=+1,
            d_base_asset_volume=+output_with_fee,
        )
        agent_deltas = Wallet(
            address=0,
            base_in_wallet=+output_with_fee,
            token_in_wallet={agent_action.mint_time: -agent_action.trade_amount},
            fees_paid=+fee,
        )
        return market_deltas, agent_deltas

    def _add_liquidity(
        self, agent_action: Agent.AgentAction, time_remaining: float, stretched_time_remaining: float
    ) -> tuple[MarketDeltas, Wallet]:
        """
        Computes new deltas for bond & share reserves after liquidity is added
        """
        lp_out, d_base_reserves, d_token_reserves = self.pricing_model.calc_lp_out_given_tokens_in(
            d_base=agent_action.trade_amount,
            share_reserves=self.share_reserves,
            bond_reserves=self.bond_reserves,
            share_buffer=self.share_buffer,
            init_share_price=self.init_share_price,
            share_price=self.share_price,
            lp_reserves=self.lp_reserves,
            rate=self.rate,
            time_remaining=time_remaining,
            stretched_time_remaining=stretched_time_remaining,
        )
        market_deltas = MarketDeltas(
            d_base_asset=+d_base_reserves,
            d_token_asset=+d_token_reserves,
            d_lp_reserves=+lp_out,
            d_lp_reserves_history=[
                agent_action.mint_time,
                agent_action.wallet_address,
                +agent_action.trade_amount,
            ],
        )
        agent_deltas = Wallet(
            address=0,
            base_in_wallet=-d_base_reserves,
            lp_in_wallet=+lp_out,
        )
        return market_deltas, agent_deltas

    def _remove_liquidity(
        self, agent_action: Agent.AgentAction, time_remaining: float, stretched_time_remaining: float
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
            rate=self.rate,
            time_remaining=time_remaining,
            stretched_time_remaining=stretched_time_remaining,
        )
        market_deltas = MarketDeltas(
            d_base_asset=-d_base_reserves,
            d_token_asset=-d_token_reserves,
            d_lp_reserves=-lp_in,
            d_lp_reserves_history=[
                agent_action.mint_time,
                agent_action.wallet_address,
                -agent_action.trade_amount,
            ],
        )
        agent_deltas = Wallet(
            address=0,
            base_in_wallet=+d_base_reserves,
            lp_in_wallet=-lp_in,
        )
        return market_deltas, agent_deltas

    # TODO: This function is throwing linting errors (too many local variables)
    # It also appears to be useless, besides for printing verbose statements.
    # Need to clean it up and find a use for it OR delete it
    # def calc_fees_owed(self, return_agent=None):
    #    """
    #    Returns the fees owed to the agent
    #    """
    #    # TODO: This function has too many local variables (21/15), and is tough to parse.
    #    #       There might be an easy fix when setting up logging.
    #    # pylint: disable=too-many-locals
    #    cum_liq, prev_time, prev_share_fees, prev_token_fees = 0, 0, 0, 0
    #    cum_liq_by_agent, contribution, token_owed, share_owed = {}, {}, {}, {}
    #    for [current_time, acting_agent, new_liq] in self.lp_reserves_history:
    #        # calculate what happened since the last update, we use marginal values for everything
    #        share_fees_till_now = sum((v for k, v in self.share_fee_history.items() if k <= current_time))
    #        token_fees_till_now = sum((v for k, v in self.token_fee_history.items() if k <= current_time))
    #        delta_share_fees = share_fees_till_now - prev_share_fees
    #        delta_token_fees = token_fees_till_now - prev_token_fees
    #        delta_time = current_time - prev_time
    #        # initialize agent if this is the first time we see them
    #        if acting_agent not in cum_liq_by_agent:
    #            (
    #                contribution[acting_agent],
    #                token_owed[acting_agent],
    #                share_owed[acting_agent],
    #                cum_liq_by_agent[acting_agent],
    #            ) = (0, 0, 0, 0)
    #        if current_time != 0:  # only do a marginal update after first timestep where deltas are zero
    #            for update_agent_key, update_agent_value in cum_liq_by_agent.items():  # for each agent
    #                # update their marginal share of cumulative liquidity, give them credit for it (contribution)
    #                contribution[update_agent_key] += update_agent_value / cum_liq
    #                # update their owed fees
    #                share_owed[update_agent_key] = (
    #                    share_owed[update_agent_key] * prev_time
    #                    + contribution[update_agent_key] * delta_share_fees * delta_time
    #                ) / current_time
    #                token_owed[update_agent_key] = (
    #                    token_owed[update_agent_key] * prev_time
    #                    + contribution[update_agent_key] * delta_token_fees * delta_time
    #                ) / current_time
    #        # update values used for next iteration
    #        cum_liq += new_liq
    #        cum_liq_by_agent[acting_agent] += new_liq
    #        prev_time = current_time
    #        prev_share_fees, prev_token_fees = share_fees_till_now, token_fees_till_now
    #    # TODO: Clean up these prints
    #    if self.verbose:
    #        print(f"cum_liq_by_agent = {cum_liq_by_agent}")
    #        print(
    #            f"      share_owed = {share_owed} calculated sum = {sum(share_owed.values())}"
    #            f"\n           vs. direct = {self.share_fees} it's a "
    #            "match "
    #            if sum(share_owed.values()) == self.share_fees
    #            else "mismatch "
    #        )
    #        print(
    #            f"      token_owed = {token_owed} calculated sum = {sum(token_owed.values())}"
    #            f"\n           vs. direct = {self.token_fees} it's a "
    #            "match "
    #            if sum(token_owed.values()) == self.token_fees
    #            else "mismatch "
    #        )
    #    if return_agent is not None:
    #        return share_owed[return_agent], token_owed[return_agent]
    #    else:
    #        return None

    def get_market_step_string(self) -> str:
        """Returns a string that describes the current market step"""
        output_string = f"t={bcolors.HEADER}{self.time}{bcolors.ENDC}"
        output_string += (
            " reserves=["
            + f"x:{bcolors.OKBLUE}{self.share_reserves*self.share_price}{bcolors.ENDC}"
            + f",y:{bcolors.OKBLUE}{self.bond_reserves}{bcolors.ENDC}"
            + f",lp:{bcolors.OKBLUE}{self.lp_reserves}{bcolors.ENDC}"
            + f",z:{bcolors.OKBLUE}{self.share_reserves}{bcolors.ENDC}"
            + f",z_b:{bcolors.OKBLUE}{self.share_buffer}{bcolors.ENDC}"
            + f",y_b:{bcolors.OKBLUE}{self.bond_buffer}{bcolors.ENDC}"
        )
        if self.verbose:
            output_string += (
                f",fee_x:{bcolors.OKBLUE}{self.share_fees}{bcolors.ENDC}"
                f",fee_y:{bcolors.OKBLUE}{self.token_fees}{bcolors.ENDC}"
            )
        output_string += "]"
        output_string += f" p={bcolors.FAIL}{self.spot_price}{bcolors.ENDC}"
        output_string += f" rate={bcolors.FAIL}{self.rate}{bcolors.ENDC}"
        return output_string

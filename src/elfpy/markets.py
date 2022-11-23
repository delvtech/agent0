"""
Market simulators store state information when interfacing AMM pricing models with users

TODO: rewrite all functions to have typed inputs
"""

from elfpy.utils.fmt import *   # float→str formatter, also imports numpy as np
import elfpy.utils.time as time_utils
from elfpy.user import AgentWallet
from elfpy.utils.bcolors import bcolors
from elfpy.utils.basic_dataclass import *
import elfpy.utils.price as price_utils

# Currently many functions use >5 arguments.
# These should be packaged up into shared variables, e.g.
#     reserves = (in_reserves, out_reserves)
#     share_prices = (init_share_price, share_price)
# pylint: disable=too-many-arguments


@dataclass
class MarketDeltas(BasicDataclass):
    """specifies changes to values in the market"""
    d_base_asset: float = 0
    d_token_asset: float = 0
    d_share_buffer: float = 0
    d_bond_buffer: float = 0
    d_liquidity_pool: float = 0
    d_liquidity_pool_history: list = field(default_factory=list)
    d_base_asset_slippage: float = 0
    d_token_asset_slippage: float = 0
    d_base_asset_fee: float = 0
    d_token_asset_fee: float = 0
    d_base_asset_orders: int = 0
    d_token_asset_orders: int = 0
    d_base_asset_volume: float = 0
    d_token_asset_volume: float = 0


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
        fee_percent,
        token_duration,
        pricing_model,
        share_reserves = 0,
        bond_reserves = 0,
        liquidity_pool = 0,
        time_stretch_constant=1,
        init_share_price=1,
        share_price=1,
        verbose=False,
    ):
        self.time = 0  # time in year fractions
        self.share_reserves = share_reserves  # z
        self.bond_reserves = bond_reserves  # y
        self.share_buffer = 0
        self.bond_buffer = 0
        self.liquidity_pool = liquidity_pool
        self.liquidity_pool_history = []  # list trades by user and time, initialize as empty list to allow appending
        self.fee_percent = fee_percent  # g
        self.time_stretch_constant = time_stretch_constant
        self.init_share_price = init_share_price  # u normalizing constant
        self.share_price = share_price  # c
        self.token_duration = token_duration  # how long does a token last before expiry
        self.pricing_model = pricing_model
        # TODO: It would be good to remove the tight coupling between pricing models and markets.
        #       For now, it makes sense to restrict the behavior at the market level since
        #       previous versions of Element didn't allow for shorting (despite the fact that
        #       their pricing models can support shorting).
        pricing_model_name = self.pricing_model.model_name()
        if pricing_model_name == "Element":
            self.allowed_actions = ["open_long", "close_long"]
        elif pricing_model_name == "Hyperdrive":
            self.allowed_actions = ["open_long", "close_long", "open_short", "close_short", "add_liquidity", "remove_liquidity"]
        else:
            raise AssertionError(
                f'markets.__init__: ERROR: self.pricing.model_name() should be "Element" or "Hyperdrive", not {pricing_model_name}!'
            )
        self.base_asset_orders = 0
        self.token_asset_orders = 0
        self.base_asset_volume = 0
        self.token_asset_volume = 0
        self.cum_token_asset_slippage = 0
        self.cum_base_asset_slippage = 0
        self.cum_token_asset_fees = 0
        self.cum_base_asset_fees = 0
        self.spot_price = None
        self.total_supply = self.share_reserves + self.bond_reserves
        self.verbose = verbose
        self.rate = 0
        self.update_spot_price_and_rate() if self.share_reserves > 0 else None


    def trade_and_update(self, agent_action):
        """
        Execute a trade in the simulated market.
        """
        # ensure that the user action is an allowed action for this market
        if not agent_action.action_type in self.allowed_actions:
            raise AssertionError(
                f'markets.swap: ERROR: agent_action.action_type should be an allowed action for the model={self.pricing_model.model_name()}, not {agent_action.action_type}!'
            )
        # TODO: check the desired amount is feasible, otherwise return descriptive error
        # update market variables which may have changed since the user action was created
        agent_action.update_market_variables(market=self)
        agent_action.print_description_string()

        # for each position, specify how to forumulate trade and then execute
        if agent_action.action_type == "open_long":  # buy to open long
            agent_action.direction = "out"  # calcOutGivenIn
            agent_action.token_out = "pt"  # sell known base for unknown PT 
            market_deltas, agent_deltas = self._open_long(agent_action)
        elif agent_action.action_type == "close_long":  # sell to close long
            agent_action.direction = "out"  # calcOutGivenIn
            agent_action.token_out = "base"  # sell known PT for unknown base
            market_deltas, agent_deltas = self._close_long(agent_action)
        elif agent_action.action_type == "open_short":  # sell PT to open short
            agent_action.direction = "in"  # calcOutGivenIn
            agent_action.token_out = "pt"  # sell known PT for unknown base
            market_deltas, agent_deltas = self._open_short(agent_action)
        elif agent_action.action_type == "close_short":  # buy PT to close short
            agent_action.direction = "in"  # calcOutGivenIn
            agent_action.token_in = "pt"  # buy known PT for unknown base
            market_deltas, agent_deltas = self._close_short(agent_action)
        elif agent_action.action_type == "add_liquidity":
            # pricing model computes new market deltas
            # market updates its "liquidity pool" wallet, which stores each trade's mint time and user address
            # LP tokens are also storeds in user wallet as fungible amounts, for ease of user
            market_deltas, agent_deltas = self._add_liquidity(agent_action)
            pass
        elif agent_action.action_type == "remove_liquidity":
            # market figures out how much the user has contributed (calcualtes their fee weighting)
            # market resolves fees, adds this to the agent_action
            # pricing model computes new market deltas
            # market updates its "liquidity pool" wallet, which stores each trade's mint time and user address
            # LP tokens are also storeds in user wallet as fungible amounts, for ease of user
            # TODO: implement fee attribution and withdrawal
            market_deltas, agent_deltas = self._remove_liquidity(agent_action)
            pass
        else:
            raise ValueError(f'ERROR: Unknown trade type "{agent_action["action_type"]}".')
        # update market state
        self.update_market(market_deltas)
        self.update_spot_price_and_rate()
        print(f"{self.get_market_step_string()}")
        # TODO: self.update_LP_pool(agent_deltas["fees"])
        agent_action.agent.update_wallet(agent_deltas)  # update user state since market doesn't know about users
        if self.verbose:
            print(f" agent  Δs ={agent_deltas.display()}\n market Δs ={market_deltas.display()}")
            print(f" post-trade {agent_action.agent.status_report()}") if self.verbose else None
    
    def update_market(self, market_deltas):
        """
        Increments member variables to reflect current market conditions
        """
        for field in market_deltas.__dataclass_fields__:
            value = getattr(market_deltas, field)
            if field == "d_liquidity_pool_history":
                assert isinstance(value, list), f"markets.update_market: Error:"\
                + f" d_liquidity_pool_history has value={value} should be a list"
            else:
                assert np.isfinite(value), f"markets.update_market: ERROR: market delta key {field} is not finite."
        self.share_reserves += market_deltas.d_base_asset/self.share_price
        self.bond_reserves += market_deltas.d_token_asset
        self.share_buffer += market_deltas.d_share_buffer
        self.bond_buffer += market_deltas.d_bond_buffer
        self.liquidity_pool += market_deltas.d_liquidity_pool
        self.liquidity_pool_history.append(market_deltas.d_liquidity_pool_history)
        self.cum_base_asset_slippage += market_deltas.d_base_asset_slippage
        self.cum_token_asset_slippage += market_deltas.d_token_asset_slippage
        self.cum_base_asset_fees += market_deltas.d_base_asset_fee
        self.cum_token_asset_fees += market_deltas.d_token_asset_fee
        self.base_asset_orders += market_deltas.d_base_asset_orders
        self.token_asset_orders += market_deltas.d_token_asset_orders
        self.base_asset_volume += market_deltas.d_base_asset_volume
        self.token_asset_volume += market_deltas.d_token_asset_volume

    def get_market_state_string(self):
        """Returns a formatted string containing all of the Market class member variables"""
        strings = [f"{attribute} = {value}" for attribute, value in self.__dict__.items()]
        state_string = "\n".join(strings)
        return state_string

    def get_target_reserves(self, token_in, trade_direction):
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
        amount,
        tokens,
        reserves,
        trade_results,
    ):
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

    def tick(self, delta_time):
        """Increments the time member variable"""
        self.time += delta_time

    def update_spot_price_and_rate(self):
        """Update the spot price"""
        self.spot_price = self.pricing_model.calc_spot_price_from_reserves(
            share_reserves=self.share_reserves,
            bond_reserves=self.bond_reserves,
            init_share_price=self.init_share_price,
            share_price=self.share_price,
            time_remaining=time_utils.stretch_time(self.token_duration, self.time_stretch_constant),
        )
        self.rate = price_utils.calc_apr_from_spot_price(self.spot_price, self.token_duration)

    def swap(self, trade_details):
        if trade_details.direction == "in":
            trade_results = self.pricing_model.calc_out_given_in(
                in_                 = trade_details.trade_amount,
                share_reserves      = trade_details.share_reserves,
                bond_reserves       = trade_details.bond_reserves,
                token_out           = trade_details.token_out,
                fee_percent         = trade_details.fee_percent,
                time_remaining      = trade_details.stretched_time_remaining,
                init_share_price    = trade_details.init_share_price,
                share_price         = trade_details.share_price,
            )
            (
                without_fee_or_slippage,
                output_with_fee,
                output_without_fee,
                fee,
            ) = trade_results
        else:
            trade_results = self.pricing_model.calc_in_given_out(
                out                 = trade_details.trade_amount,
                share_reserves      = trade_details.share_reserves,
                bond_reserves       = trade_details.bond_reserves,
                token_in            = trade_details.token_in,
                fee_percent         = trade_details.fee_percent,
                time_remaining      = trade_details.stretched_time_remaining,
                init_share_price    = trade_details.init_share_price,
                share_price         = trade_details.share_price,
            )
            (
                without_fee_or_slippage,
                output_with_fee,
                output_without_fee,
                fee,
            ) = trade_results
        return without_fee_or_slippage, output_with_fee, output_without_fee, fee,

    def _open_short(self, trade_details):
        """
        take trade spec & turn it into trade details
        compute wallet update spec with specific details
            will be conditional on the pricing model
        """
        without_fee_or_slippage, output_with_fee, output_without_fee, fee = self.swap(trade_details)
        
        market_deltas = MarketDeltas( # write out explicit signs, so it's clear what's happening
            d_base_asset            = - output_with_fee,
            d_token_asset           = + trade_details.trade_amount,
            d_bond_buffer           = + trade_details.trade_amount,
            d_base_asset_slippage   = + abs(without_fee_or_slippage - output_without_fee),
            d_base_asset_fee        = + fee,
            d_base_asset_orders     = + 1,
            d_base_asset_volume     = + output_with_fee,
        )
        # TODO: _in_protocol values should be managed by pricing_model and referenced by user
        max_loss = trade_details.trade_amount - output_with_fee
        wallet_deltas = AgentWallet( # write out explicit signs, so it's clear what's happening
            base_in_wallet              = - max_loss,
            base_in_protocol            = {trade_details.mint_time: + max_loss},
            token_in_protocol           = {trade_details.mint_time: - trade_details.trade_amount},
            fees_paid                   = + fee
        )
        return market_deltas, wallet_deltas

    def _close_short(self, trade_details):
        """
        take trade spec & turn it into trade details
        compute wallet update spec with specific details
            will be conditional on the pricing model
        """
        trade_results = self.pricing_model.calc_in_given_out(
            trade_details.trade_amount,
            trade_details.share_reserves,
            trade_details.bond_reserves,
            trade_details.token_in,
            trade_details.fee_percent,
            trade_details.stretched_time_remaining,
            trade_details.init_share_price,
            trade_details.share_price,
        )
        (
            without_fee_or_slippage,
            output_with_fee,
            output_without_fee,
            fee,
        ) = trade_results
        
        market_deltas = MarketDeltas( # write out explicit signs, so it's clear what's happening
            d_base_asset            = + output_with_fee,
            d_token_asset           = - trade_details.trade_amount,
            d_bond_buffer           = - trade_details.trade_amount,
            d_base_asset_slippage   = + abs(without_fee_or_slippage - output_without_fee),
            d_base_asset_fee        = + fee,
            d_base_asset_orders     = + 1,
            d_base_asset_volume     = + output_with_fee,
        )
        # TODO: Add logic:
        # If the user is not closing a full short (i.e. the mint_time balance is not zeroed out)
        # then the user does not get any money into their wallet
        # Right now the user has to close the full short
        agent_deltas = AgentWallet( # write out explicit signs, so it's clear what's happening
            base_in_wallet              = + output_with_fee,
            base_in_protocol            = {trade_details.mint_time: - output_with_fee},
            token_in_protocol           = {trade_details.mint_time: + trade_details.trade_amount},
            fees_paid                   = + fee
        )
        return market_deltas, agent_deltas

    def _open_long(self, trade_details):
        """
        take trade spec & turn it into trade details
        compute wallet update spec with specific details
            will be conditional on the pricing model
        """
        # test trade spec = {'trade_amount': 100, 'direction': 'out', 'token_in': 'base', 'mint_time': -1}
        # logic: use calcOutGivenIn because we want to buy unknown PT with known base
        #        use current mint time because this is a fresh
        trade_results = self.pricing_model.calc_out_given_in(
            trade_details.trade_amount,
            trade_details.share_reserves,
            trade_details.bond_reserves,
            trade_details.token_out,
            trade_details.fee_percent,
            trade_details.stretched_time_remaining,
            trade_details.init_share_price,
            trade_details.share_price,
        )
        (
            without_fee_or_slippage,
            output_with_fee,
            output_without_fee,
            fee,
        ) = trade_results

        market_deltas = MarketDeltas( # write out explicit signs, so it's clear what's happening
            d_base_asset                = + trade_details.trade_amount,
            d_token_asset               = - output_with_fee,
            d_share_buffer              = + output_with_fee / trade_details.share_price,
            d_token_asset_slippage      = + abs(without_fee_or_slippage - output_without_fee),
            d_token_asset_fee           = + fee,
            d_token_asset_orders        = + 1,
            d_token_asset_volume        = + output_with_fee,
        )
        agent_deltas = AgentWallet( # write out explicit signs, so it's clear what's happening
            base_in_wallet              = - trade_details.trade_amount,
            token_in_protocol           = {trade_details.mint_time: + output_with_fee},
            fees_paid                   = + fee
        )
        return market_deltas, agent_deltas

    def _close_long(self, trade_details):
        """
        take trade spec & turn it into trade details
        compute wallet update spec with specific details
            will be conditional on the pricing model
        """
        trade_results = self.pricing_model.calc_out_given_in(
            trade_details.trade_amount,
            trade_details.share_reserves,
            trade_details.bond_reserves,
            trade_details.token_out,
            trade_details.fee_percent,
            trade_details.stretched_time_remaining,
            trade_details.init_share_price,
            trade_details.share_price,
        )
        (
            without_fee_or_slippage,
            output_with_fee,
            output_without_fee,
            fee,
        ) = trade_results
        market_deltas = MarketDeltas( # write out explicit signs, so it's clear what's happening
            d_base_asset                = - output_with_fee,
            d_token_asset               = + trade_details.trade_amount,
            d_share_buffer              = - trade_details.trade_amount / trade_details.share_price,
            d_base_asset_slippage       = + abs(without_fee_or_slippage - output_without_fee),
            d_base_asset_fee            = + fee,
            d_base_asset_orders         = + 1,
            d_base_asset_volume         = + output_with_fee,
        )
        agent_deltas = AgentWallet( # write out explicit signs, so it's clear what's happening
            base_in_wallet              = + output_with_fee,
            token_in_wallet             = {trade_details.mint_time: - trade_details.trade_amount},
            fees_paid                   = + fee
        )
        return market_deltas, agent_deltas

    def _add_liquidity(self, trade_details):
        """
        Computes new deltas for bond & share reserves after liquidity is added
        """
        lp_out, d_base_reserves, d_token_reserves = self.pricing_model.calc_lp_out_given_tokens_in(
            base_asset_in = trade_details.trade_amount,
            share_reserves = trade_details.share_reserves,
            bond_reserves = trade_details.bond_reserves,
            share_buffer = trade_details.share_buffer,
            init_share_price = trade_details.init_share_price,
            share_price = trade_details.share_price,
            liquidity_pool = trade_details.liquidity_pool,
            rate = trade_details.rate,
            time_remaining = trade_details.time_remaining,
            stretched_time_remaining = trade_details.stretched_time_remaining
        )
        market_deltas = MarketDeltas( # write out explicit signs, so it's clear what's happening
            d_base_asset                = + d_base_reserves,
            d_token_asset               = + d_token_reserves,
            d_liquidity_pool            = + lp_out,
            d_liquidity_pool_history    = [trade_details.mint_time, trade_details.trade_amount]
        )
        agent_deltas = AgentWallet( # write out explicit signs, so it's clear what's happening
            base_in_wallet              = - d_base_reserves,
            lp_in_wallet                = + lp_out,
        )
        return market_deltas, agent_deltas

    def _remove_liquidity(self, trade_details):
        """
        Computes new deltas for bond & share reserves after liquidity is removed
        """
        lp_in, d_base_reserves, d_token_reserves = self.pricing_model.calc_tokens_out_given_lp_in(
            lp_in = trade_details.trade_amount,
            share_reserves = trade_details.share_reserves,
            bond_reserves = trade_details.bond_reserves,
            share_buffer = trade_details.share_buffer,
            init_share_price = trade_details.init_share_price,
            share_price = trade_details.share_price,
            liquidity_pool = trade_details.liquidity_pool,
            rate = trade_details.rate,
            time_remaining = trade_details.time_remaining,
            stretched_time_remaining = trade_details.stretched_time_remaining
        )

        market_deltas = MarketDeltas(
            d_base_asset=-d_base_reserves,
            d_token_asset=-d_token_reserves,
            d_liquidity_pool=-lp_in,
            d_liquidity_pool_history=[trade_details.mint_time, trade_details.trade_amount]
        )
        agent_deltas = AgentWallet(
            # write out explicit signs, so it's clear what's happening
            base_in_wallet              = + d_base_reserves,
            lp_in_wallet                = - lp_in,
        )
        return market_deltas, agent_deltas

    def get_market_step_string(self):
        """Returns a string that describes the current market step"""
        return f"t={bcolors.HEADER}{self.time}{bcolors.ENDC}"\
            + f" reserves=["\
                + f"x:{bcolors.OKBLUE}{self.share_reserves*self.share_price}{bcolors.ENDC}"\
                + f",y:{bcolors.OKBLUE}{self.bond_reserves}{bcolors.ENDC}"\
                + f",z:{bcolors.OKBLUE}{self.share_reserves}{bcolors.ENDC}"\
                + f",z_b:{bcolors.OKBLUE}{self.share_buffer}{bcolors.ENDC}"\
                + f",y_b:{bcolors.OKBLUE}{self.bond_buffer}{bcolors.ENDC}"\
            + f"]"\
            + f" p={bcolors.FAIL}{self.spot_price}{bcolors.ENDC}"\
            + f" rate={bcolors.FAIL}{self.rate}{bcolors.ENDC}"
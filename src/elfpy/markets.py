"""
Market simulators store state information when interfacing AMM pricing models with users

TODO: rewrite all functions to have typed inputs
"""

# Currently many functions use >5 arguments.
# These should be packaged up into shared variables, e.g.
#     reserves = (in_reserves, out_reserves)
#     share_prices = (init_share_price, share_price)
# pylint: disable=too-many-arguments


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
        base_asset,
        token_asset,
        fee_percent,
        pricing_model,
        init_share_price=1,
        share_price=1,
        verbose=False,
    ):
        # TODO: In order for the AMM to work as expected we should store
        # a share reserve instead of a base reserve.
        self.base_asset = base_asset  # x
        self.token_asset = token_asset  # y
        self.fee_percent = fee_percent  # g
        self.share_price = share_price  # c
        self.init_share_price = init_share_price  # u normalizing constant
        self.pricing_model = pricing_model
        self.base_asset_orders = 0
        self.token_asset_orders = 0
        self.base_asset_volume = 0
        self.token_asset_volume = 0
        self.cum_token_asset_slippage = 0
        self.cum_base_asset_slippage = 0
        self.cum_token_asset_fees = 0
        self.cum_base_asset_fees = 0
        self.total_supply = self.base_asset + self.token_asset
        self.verbose = verbose

    def get_target_reserves(self, token_in, trade_direction):
        """
        Determine which asset is the target based on token_in and trade_direction
        """
        if trade_direction == "in":
            if token_in == "fyt":
                target_reserves = self.token_asset
            else:
                target_reserves = self.base_asset
        elif trade_direction == "out":
            if token_in == "fyt":
                target_reserves = self.base_asset
            else:
                target_reserves = self.token_asset
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

    def update_market(self, d_asset, d_slippage, d_fees, d_orders, d_volume):
        """
        Increments member variables to reflect current market conditions

        All arguments are tuples containing the (base, token) adjustments for each metric
        """
        self.base_asset += d_asset[0]
        self.token_asset += d_asset[1]
        self.cum_base_asset_slippage += d_slippage[0]
        self.cum_token_asset_slippage += d_slippage[1]
        self.cum_base_asset_fees += d_fees[0]
        self.cum_token_asset_fees += d_fees[1]
        self.base_asset_orders += d_orders[0]
        self.token_asset_orders += d_orders[1]
        self.base_asset_volume += d_volume[0]
        self.token_asset_volume += d_volume[1]

    def swap(self, amount, token_in, time_remaining):
        """
        Execute a trade in the simulated market.

        Arguments:
        amount [float] volume to be traded, in units of the target asset
        token_in [str] either "pt" or "base" -- the output token will be the opposite

        Fees are computed, as well as the adjustments in asset volume.
        All internal market variables are updated from the trade.
        """
        # TODO: Break this function up to use private class functions
        # pylint: disable=too-many-locals
        # pylint: disable=too-many-statements
        if token_in == "pt":
            in_reserves = self.token_asset + self.total_supply
            out_reserves = self.base_asset
            token_out = "base"
            trade_results = self.pricing_model.calc_out_given_in(
                amount,
                in_reserves,
                out_reserves,
                token_out,
                self.fee_percent,
                time_remaining,
                self.init_share_price,
                self.share_price,
            )
            (
                without_fee_or_slippage,
                output_with_fee,
                output_without_fee,
                fee,
            ) = trade_results
            d_base_asset = -output_with_fee
            d_token_asset = amount
            d_base_asset_slippage = abs(without_fee_or_slippage - output_without_fee)
            d_token_asset_slippage = 0
            d_base_asset_fee = fee
            d_token_asset_fee = 0
            d_base_asset_orders = 1
            d_token_asset_orders = 0
            d_base_asset_volume = output_with_fee
            d_token_asset_volume = 0
        elif token_in == "base":
            in_reserves = self.base_asset
            out_reserves = self.token_asset + self.total_supply
            token_out = "pt"
            trade_results = self.pricing_model.calc_out_given_in(
                amount,
                in_reserves,
                out_reserves,
                token_out,
                self.fee_percent,
                time_remaining,
                self.init_share_price,
                self.share_price,
            )
            (
                without_fee_or_slippage,
                output_with_fee,
                output_without_fee,
                fee,
            ) = trade_results
            d_base_asset = amount
            d_token_asset = -output_with_fee
            d_base_asset_slippage = 0
            d_token_asset_slippage = abs(without_fee_or_slippage - output_without_fee)
            d_base_asset_fee = 0
            d_token_asset_fee = fee
            d_base_asset_orders = 0
            d_token_asset_orders = 1
            d_base_asset_volume = 0
            d_token_asset_volume = output_with_fee
        self.check_fees(
            amount,
            (token_in, token_out),
            (in_reserves, out_reserves),
            trade_results,
        )
        self.update_market(
            (d_base_asset, d_token_asset),
            (d_base_asset_slippage, d_token_asset_slippage),
            (d_base_asset_fee, d_token_asset_fee),
            (d_base_asset_orders, d_token_asset_orders),
            (d_base_asset_volume, d_token_asset_volume),
        )
        return (without_fee_or_slippage, output_with_fee, output_without_fee, fee)

    def get_market_state_string(self):
        """Returns a formatted string containing all of the Market class member variables"""
        strings = [f"{attribute} = {value}" for attribute, value in self.__dict__.items()]
        state_string = "\n".join(strings)
        return state_string

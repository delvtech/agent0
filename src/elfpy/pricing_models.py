"""
Pricing models implement automated market makers (AMMs)

TODO: rewrite all functions to have typed inputs
"""

import elfpy.utils.time as time_utils

# Currently many functions use >5 arguments.
# These should be packaged up into shared variables, e.g.
#     reserves = (in_reserves, out_reserves)
#     share_prices = (init_share_price, share_price)
# pylint: disable=too-many-arguments


class PricingModel:
    """
    Contains functions for calculating AMM variables

    Base class should not be instantiated on its own; it is assumed that a user will instantiate a child class
    """

    # TODO: Change argument defaults to be None & set inside of def to avoid accidental overwrite
    # TODO: set up member object that owns attributes instead of so many individual instance attributes
    # pylint: disable=too-many-instance-attributes

    def __init__(self, verbose=None):
        """
        Arguments
        ---------
        verbose : bool
            if True, print verbose outputs
        """
        self.verbose = False if verbose is None else verbose

    def calc_in_given_out(
        self,
        out,
        in_reserves,
        out_reserves,
        token_in,
        fee_percent,
        time_remaining,
        init_share_price,
        share_price,
    ):
        """Calculate fees and asset quantity adjustments"""
        raise NotImplementedError

    def calc_out_given_in(
        self,
        in_,
        in_reserves,
        out_reserves,
        token_out,
        fee_percent,
        time_remaining,
        init_share_price,
        share_price,
    ):
        """Calculate fees and asset quantity adjustments"""
        raise NotImplementedError

    def model_name(self):
        """Unique name given to the model, can be based on member variable states"""
        raise NotImplementedError

    @staticmethod
    def calc_time_stretch(apy):
        """Returns fixed time-stretch value based on current apy (as a decimal)"""
        apy_percent = apy * 100
        return 3.09396 / (0.02789 * apy_percent)

    @staticmethod
    def calc_tokens_in_given_lp_out(lp_out, base_asset_reserves, token_asset_reserves, total_supply):
        """Returns how much supply is needed if liquidity is removed"""
        # Check if the pool is initialized
        if total_supply == 0:
            base_asset_needed = lp_out
            token_asset_needed = 0
        else:
            # solve for y_needed: lp_out = ((x_reserves / y_reserves) * y_needed * total_supply) / x_reserves
            token_asset_needed = (lp_out * base_asset_reserves) / (
                (base_asset_reserves / token_asset_reserves) * total_supply
            )
            # solve for x_needed: x_reserves / y_reserves = x_needed / y_needed
            base_asset_needed = (base_asset_reserves / token_asset_reserves) * token_asset_needed
        return (base_asset_needed, token_asset_needed)

    @staticmethod
    def calc_lp_out_given_tokens_in(
        base_asset_in,
        token_asset_in,
        base_asset_reserves,
        token_asset_reserves,
        total_supply,
    ):
        """Returns how much liquidity can be removed given newly minted assets"""
        # Check if the pool is initialized
        if total_supply == 0:
            # When uninitialized we mint exactly the underlying input in LP tokens
            lp_out = base_asset_in
            base_asset_needed = base_asset_in
            token_asset_needed = 0
        else:
            # Calc the number of base_asset needed for the y_in provided
            base_asset_needed = (base_asset_reserves / token_asset_reserves) * token_asset_in
            # If there isn't enough x_in provided
            if base_asset_needed > base_asset_in:
                lp_out = (base_asset_in * total_supply) / base_asset_reserves
                base_asset_needed = base_asset_in  # use all the x_in
                # Solve for: x_reserves / y_reserves = x_needed / y_needed
                token_asset_needed = base_asset_needed / (base_asset_reserves / token_asset_reserves)
            else:
                # We calculate the percent increase in the reserves from contributing all of the bond
                lp_out = (base_asset_needed * total_supply) / base_asset_reserves
                token_asset_needed = token_asset_in
        return (base_asset_needed, token_asset_needed, lp_out)

    @staticmethod
    def calc_lp_in_given_tokens_out(
        min_base_asset_out,
        min_token_asset_out,
        base_asset_reserves,
        token_asset_reserves,
        total_supply,
    ):
        """Returns how much liquidity is needed given a removal of asset quantities"""
        # Calc the number of base_asset needed for the y_out provided
        base_asset_needed = (base_asset_reserves / token_asset_reserves) * min_token_asset_out
        # If there isn't enough x_out provided
        if min_base_asset_out > base_asset_needed:
            lp_in = (min_base_asset_out * total_supply) / base_asset_reserves
            base_asset_needed = min_base_asset_out  # use all the x_out
            # Solve for: x_reserves/y_reserves = x_needed/y_needed
            token_asset_needed = base_asset_needed / (base_asset_reserves / token_asset_reserves)
        else:
            token_asset_needed = min_token_asset_out
            lp_in = (token_asset_needed * total_supply) / token_asset_reserves
        return (base_asset_needed, token_asset_needed, lp_in)

    @staticmethod
    def calc_tokens_out_for_lp_in(lp_in, base_asset_reserves, token_asset_reserves, total_supply):
        """Returns allowable asset reduction for an increase in liquidity"""
        # Solve for y_needed: lp_out = ((x_reserves / y_reserves) * y_needed * total_supply)/x_reserves
        token_asset_needed = (lp_in * base_asset_reserves) / (
            (base_asset_reserves / token_asset_reserves) * total_supply
        )
        # Solve for x_needed: x_reserves/y_reserves = x_needed/y_needed
        base_asset_needed = (base_asset_reserves / token_asset_reserves) * token_asset_needed
        return (base_asset_needed, token_asset_needed)

    # TODO: This has been re-parameterized. More updates will be required.
    @staticmethod
    def _calc_k_const(share_reserves, bond_reserves, share_price, init_share_price, time_elapsed):
        """Returns the 'k' constant variable for trade mathematics"""
        scale = share_price / init_share_price
        total_reserves = bond_reserves + share_price * share_reserves
        return scale * (init_share_price * share_reserves) ** (time_elapsed) + (bond_reserves + total_reserves) ** (
            time_elapsed
        )

    @staticmethod
    def _calc_total_liquidity_from_reserves_and_price(base_asset_reserves, token_asset_reserves, spot_price):
        """
        We are using spot_price when calculating total_liquidity to convert the two tokens into the same units.
        Otherwise we're comparing apples(base_asset_reserves in ETH) and oranges (token_asset_reserves in ptETH)
            ptEth = 1.0 ETH at maturity ONLY
            ptEth = 0.95 ETH ahead of time
        Discount factor from the time value of money
            Present Value = Future Value / (1 + r)^n
            Future Value = Present Value * (1 + r)^n
        The equation converts from future value to present value at the appropriate discount rate,
        which measures the opportunity cost of getting a dollar tomorrow instead of today.
        discount rate = (1 + r)^n
        spot price APR = 1 / (1 + r)^n
        """
        return base_asset_reserves + token_asset_reserves * spot_price

    def days_to_time_remaining(self, days_remaining, time_stretch=1, normalizing_constant=365):
        """Converts remaining pool length in days to normalized and stretched time"""
        normed_days_remaining = time_utils.norm_days(days_remaining, normalizing_constant)
        time_remaining = time_utils.stretch_time(normed_days_remaining, time_stretch)
        return time_remaining

    def time_to_days_remaining(self, time_remaining, time_stretch=1, normalizing_constant=365):
        """Converts normalized and stretched time remaining in pool to days"""
        normed_days_remaining = time_utils.unstretch_time(time_remaining, time_stretch)
        days_remaining = time_utils.unnorm_days(normed_days_remaining, normalizing_constant)
        return days_remaining

    def calc_max_trade(self, in_reserves, out_reserves, time_remaining):
        """
        Returns the maximum allowable trade amount given the current asset reserves

        TODO: write a test to verify that this is correct
        """
        time_elapsed = 1 - time_remaining
        # TODO: fix calc_k_const args
        k = 1  # self._calc_k_const(in_reserves, out_reserves, time_elapsed)  # in_reserves^(1 - t) + out_reserves^(1 - t)
        return k ** (1 / time_elapsed) - in_reserves

    def calc_apy_from_spot_price(self, price, normalized_days_remaining):
        """Returns the APY (decimal) given the current (positive) base asset price and the remaining pool duration"""
        assert (
            price > 0
        ), f"pricing_models.calc_apy_from_spot_price: ERROR: calc_apy_from_spot_price: Price argument should be greater than zero, not {price}"
        assert (
            normalized_days_remaining > 0
        ), f"normalized_days_remaining argument should be greater than zero, not {normalized_days_remaining}"
        return (1 - price) / price / normalized_days_remaining  # price = 1 / (1 + r * t)

    def calc_spot_price_from_apy(self, apy_decimal, normalized_days_remaining):
        """Returns the current spot price based on the current APY (decimal) and the remaining pool duration"""
        return 1 / (1 + apy_decimal * normalized_days_remaining)  # price = 1 / (1 + r * t)

    def calc_apy_from_reserves(
        self,
        base_asset_reserves,
        token_asset_reserves,
        total_supply,
        time_remaining,
        time_stretch,
        init_share_price=1,
        share_price=1,
    ):
        """
        Returns the apy given reserve amounts
        """
        spot_price = self.calc_spot_price_from_reserves(
            base_asset_reserves,
            token_asset_reserves,
            total_supply,
            time_remaining,
            init_share_price,
            share_price,
        )
        days_remaining = self.time_to_days_remaining(time_remaining, time_stretch)
        apy = self.calc_apy_from_spot_price(spot_price, time_utils.norm_days(days_remaining))
        return apy

    def calc_spot_price_from_reserves(
        self,
        base_asset_reserves,
        token_asset_reserves,
        total_supply,
        time_remaining,
        init_share_price=1,
        share_price=1,
    ):
        """Returns the spot price given the current supply and temporal position along the yield curve"""
        log_inv_price = share_price * (token_asset_reserves + total_supply) / (init_share_price * base_asset_reserves)
        spot_price = 1 / log_inv_price**time_remaining
        return spot_price

    def calc_base_asset_reserves(
        self,
        apy_decimal,
        token_asset_reserves,
        days_remaining,
        time_stretch,
        init_share_price,
        share_price,
    ):
        """Returns the assumed base_asset reserve amounts given the token_asset reserves and APY"""
        normalized_days_remaining = time_utils.norm_days(days_remaining)
        time_stretch_exp = 1 / time_utils.stretch_time(normalized_days_remaining, time_stretch)
        numerator = 2 * share_price * token_asset_reserves  # 2*c*y
        scaled_apy_decimal = apy_decimal * normalized_days_remaining + 1  # assuming price_apr = 1/(1+r*t)
        denominator = init_share_price * scaled_apy_decimal**time_stretch_exp - share_price
        result = numerator / denominator  # 2*c*y/(u*(r*t + 1)**(1/T) - c)
        if self.verbose:
            print(f"PricingModel.calc_base_asset_reserves:\nbase_asset_reserves: {result}")
        return result

    def calc_liquidity(
        self,
        target_liquidity_usd,
        market_price,
        apy,
        days_remaining,
        time_stretch,
        init_share_price=1,
        share_price=1,
    ):
        """
        Returns the reserve volumes and total supply

        The scaling factor ensures token_asset_reserves and base_asset_reserves add
        up to target_liquidity, while keeping their ratio constant (preserves apy).

        total_liquidity = in USD terms, used to target liquidity as passed in (in USD terms)
        total_reserves  = in arbitrary units (AU), used for yieldspace math
        """
        # estimate reserve values with the information we have
        spot_price = self.calc_spot_price_from_apy(apy, time_utils.norm_days(days_remaining))
        token_asset_reserves = target_liquidity_usd / market_price / 2 / spot_price  # guesstimate
        base_asset_reserves = self.calc_base_asset_reserves(
            apy,
            token_asset_reserves,
            days_remaining,
            time_stretch,
            init_share_price,
            share_price,
        )  # ensures an accurate ratio of prices
        total_liquidity = self._calc_total_liquidity_from_reserves_and_price(
            base_asset_reserves, token_asset_reserves, spot_price
        )
        # compute scaling factor to adjust reserves so that they match the target liquidity
        scaling_factor = (target_liquidity_usd / market_price) / total_liquidity  # both in token terms
        # update variables by rescaling the original estimates
        token_asset_reserves = token_asset_reserves * scaling_factor
        base_asset_reserves = base_asset_reserves * scaling_factor
        total_liquidity = self._calc_total_liquidity_from_reserves_and_price(
            base_asset_reserves, token_asset_reserves, spot_price
        )
        if self.verbose:
            actual_apy = self.calc_apy_from_reserves(
                base_asset_reserves,
                token_asset_reserves,
                base_asset_reserves + token_asset_reserves,
                self.days_to_time_remaining(days_remaining, time_stretch),
                time_stretch,
                init_share_price,
                share_price,
            )
            print(
                "PricingModel.calc_liquidity: \n"
                + f"base_asset_reserves={base_asset_reserves}, "
                + f"token_asset_reserves={token_asset_reserves}, "
                + f"scaling_factor={scaling_factor}, "
                + f"spot_price_from_apy={spot_price}, "
                + f"total_supply={total_liquidity:,.0f}({total_liquidity*market_price:,.0f} USD), "
                + f"apy={actual_apy}"
            )
        return (base_asset_reserves, token_asset_reserves, total_liquidity)


class ElementPricingModel(PricingModel):
    """
    Element v1 pricing model

    Does not use the Yield Bearing Vault `init_share_price` (u) and `share_price` (c) variables.
    """

    def model_name(self):
        return "Element"

    def calc_in_given_out(
        self,
        out,
        in_reserves,
        out_reserves,
        token_in,
        fee_percent,
        time_remaining,
        init_share_price=1,
        share_price=1,
    ):
        time_elapsed = 1 - time_remaining
        # TODO: Fix k calculation for element v1
        k = 1  # self._calc_k_const(in_reserves, out_reserves, time_elapsed)  # in_reserves**(1 - t) + out_reserves**(1 - t)
        without_fee = (k - (out_reserves - out) ** time_elapsed) ** (1 / time_elapsed) - in_reserves
        if token_in == "base":
            fee = fee_percent * (out - without_fee)
        elif token_in == "fyt":
            fee = fee_percent * (without_fee - out)
        with_fee = without_fee + fee
        without_fee_or_slippage = out * (in_reserves / out_reserves) ** time_remaining
        return (without_fee_or_slippage, with_fee, without_fee, fee)

    def calc_out_given_in(
        self,
        in_,
        in_reserves,
        out_reserves,
        token_out,
        fee_percent,
        time_remaining,
        init_share_price=1,
        share_price=1,
    ):
        time_elapsed = 1 - time_remaining
        # TODO: Fix k calculation for element v1
        k = 1  # self._calc_k_const(in_reserves, out_reserves, time_elapsed)  # in_reserves**(1 - t) + out_reserves**(1 - t)
        without_fee = out_reserves - pow(k - pow(in_reserves + in_, time_elapsed), 1 / time_elapsed)
        if token_out == "base":
            fee = fee_percent * (in_ - without_fee)
        elif token_out == "fyt":
            fee = fee_percent * (without_fee - in_)
        with_fee = without_fee - fee
        without_fee_or_slippage = in_ / (in_reserves / out_reserves) ** time_remaining
        return (without_fee_or_slippage, with_fee, without_fee, fee)

    def calc_base_asset_reserves(
        self,
        apy_decimal,
        token_asset_reserves,
        days_remaining,
        time_stretch,
        init_share_price=1,
        share_price=1,
    ):
        return super().calc_base_asset_reserves(apy_decimal, token_asset_reserves, days_remaining, time_stretch, 1, 1)

    def calc_spot_price_from_reserves(
        self,
        base_asset_reserves,
        token_asset_reserves,
        total_supply,
        time_remaining,
        init_share_price=1,
        share_price=1,
    ):
        return super().calc_spot_price_from_reserves(
            base_asset_reserves,
            token_asset_reserves,
            total_supply,
            time_remaining,
            1,
            1,
        )

    def calc_apy_from_reserves(
        self,
        base_asset_reserves,
        token_asset_reserves,
        total_supply,
        time_remaining,
        time_stretch,
        init_share_price=1,
        share_price=1,
    ):
        return super().calc_apy_from_reserves(
            base_asset_reserves,
            token_asset_reserves,
            total_supply,
            time_remaining,
            time_stretch,
            1,
            1,
        )

    def calc_liquidity(
        self,
        target_liquidity_usd,
        market_price,
        apy,
        days_remaining,
        time_stretch,
        init_share_price=1,
        share_price=1,
    ):
        return super().calc_liquidity(target_liquidity_usd, market_price, apy, days_remaining, time_stretch, 1, 1)


class HyperdrivePricingModel(PricingModel):
    """
    Hyperdrive Pricing Model

    This pricing model uses the YieldSpace invariant with modifications to
    enable the base reserves to be deposited into yield bearing vaults
    """

    def model_name(self):
        return "Hyperdrive"

    def open_short(self, trade_details):
        """
        take trade spec & turn it into trade details
        compute wallet update spec with specific details
            will be conditional on the pricing model
        """
        trade_results = self.calc_out_given_in(
            trade_details["trade_amount"],
            trade_details["share_reserves"],
            trade_details["bond_reserves"],
            trade_details["token_out"],
            trade_details["fee_percent"],
            trade_details["stretched_time_remaining"],
            trade_details["init_share_price"],
            trade_details["share_price"],
        )
        (
            without_fee_or_slippage,
            output_with_fee,
            output_without_fee,
            fee,
        ) = trade_results
        market_deltas = {
            "d_base_asset": -output_with_fee,
            "d_token_asset": trade_details["trade_amount"],
            "d_base_asset_slippage": abs(without_fee_or_slippage - output_without_fee),
            "d_token_asset_slippage": 0,
            "d_base_asset_fee": fee,
            "d_token_asset_fee": 0,
            "d_base_asset_orders": 1,
            "d_token_asset_orders": 0,
            "d_base_asset_volume": output_with_fee,
            "d_token_asset_volume": 0,
        }
        # TODO: _in_protocol values should be managed by pricing_model and referenced by user
        max_loss = trade_details["trade_amount"] - output_with_fee
        wallet_deltas = {
            "base_in_wallet": -1 * max_loss,
            "base_in_protocol": [trade_details["mint_time"], max_loss],
            "token_in_wallet": None,
            "token_in_protocol": [trade_details["mint_time"], trade_details["trade_amount"]],
            "fee": [trade_details["mint_time"], fee],
        }
        return market_deltas, wallet_deltas

    def close_short(self, trade_details):
        """
        take trade spec & turn it into trade details
        compute wallet update spec with specific details
            will be conditional on the pricing model
        """
        trade_results = self.calc_in_given_out(
            trade_details["trade_amount"],  # tokens
            trade_details["share_reserves"],
            trade_details["bond_reserves"],
            trade_details["token_in"],  # to be calculated, in base units
            trade_details["fee_percent"],
            trade_details["stretched_time_remaining"],
            trade_details["init_share_price"],
            trade_details["share_price"],
        )
        (
            without_fee_or_slippage,
            output_with_fee,
            output_without_fee,
            fee,
        ) = trade_results
        market_deltas = {
            "d_base_asset": output_with_fee,
            "d_token_asset": -trade_details["trade_amount"],
            "d_base_asset_slippage": abs(without_fee_or_slippage - output_without_fee),
            "d_token_asset_slippage": 0,
            "d_base_asset_fee": fee,
            "d_token_asset_fee": 0,
            "d_base_asset_orders": 1,
            "d_token_asset_orders": 0,
            "d_base_asset_volume": output_with_fee,
            "d_token_asset_volume": 0,
        }
        # TODO: Add logic:
        # If the user is not closing a full short (i.e. the mint_time balance is not zeroed out)
        # then the user does not get any money into their wallet
        # Right now the user has to close the full short
        wallet_deltas = {
            "base_in_wallet": trade_details["token_in_protocol"] - output_with_fee,
            "base_in_protocol": [trade_details["mint_time"], -trade_details["base_in_protocol"]],
            "token_in_wallet": [trade_details["mint_time"], 0],
            "token_in_protocol": [trade_details["mint_time"], -trade_details["trade_amount"]],
            "fee": [trade_details["mint_time"], fee],
        }
        return (market_deltas, wallet_deltas)

    def open_long(self, trade_details):
        """
        take trade spec & turn it into trade details
        compute wallet update spec with specific details
            will be conditional on the pricing model
        """
        # test trade spec = {'trade_amount': 100, 'direction': 'out', 'token_in': 'base', 'mint_time': -1}
        # logic: use calcOutGivenIn because we want to buy unknown PT with known base
        #        use current mint time because this is a fresh
        trade_results = self.calc_out_given_in(
            trade_details["trade_amount"],
            trade_details["share_reserves"],
            trade_details["bond_reserves"],
            trade_details["token_out"],
            trade_details["fee_percent"],
            trade_details["stretched_time_remaining"],
            trade_details["init_share_price"],
            trade_details["share_price"],
        )
        (
            without_fee_or_slippage,
            output_with_fee,
            output_without_fee,
            fee,
        ) = trade_results
        market_deltas = {
            "d_base_asset": trade_details["trade_amount"],
            "d_token_asset": -output_with_fee,
            "d_base_asset_slippage": 0,
            "d_token_asset_slippage": abs(without_fee_or_slippage - output_without_fee),
            "d_base_asset_fee": 0,
            "d_token_asset_fee": fee,
            "d_base_asset_orders": 0,
            "d_token_asset_orders": 1,
            "d_base_asset_volume": 0,
            "d_token_asset_volume": output_with_fee,
        }
        wallet_deltas = {
            "base_in_wallet": -trade_details["trade_amount"],
            "base_in_protocol": [trade_details["mint_time"], 0],
            "token_in_wallet": [trade_details["mint_time"], output_with_fee],
            "token_in_protocol": [trade_details["mint_time"], 0],
            "fee": [trade_details["mint_time"], fee],
        }
        return market_deltas, wallet_deltas

    def close_long(self, trade_details):
        """
        take trade spec & turn it into trade details
        compute wallet update spec with specific details
            will be conditional on the pricing model
        """
        trade_results = self.calc_out_given_in(
            trade_details["trade_amount"],
            trade_details["share_reserves"],
            trade_details["bond_reserves"],
            trade_details["token_out"],
            trade_details["fee_percent"],
            trade_details["stretched_time_remaining"],
            trade_details["init_share_price"],
            trade_details["share_price"],
        )
        (
            without_fee_or_slippage,
            output_with_fee,
            output_without_fee,
            fee,
        ) = trade_results
        market_deltas = {
            "d_base_asset": -output_with_fee,
            "d_token_asset": trade_details["trade_amount"],
            "d_base_asset_slippage": abs(without_fee_or_slippage - output_without_fee),
            "d_token_asset_slippage": 0,
            "d_base_asset_fee": fee,
            "d_token_asset_fee": 0,
            "d_base_asset_orders": 1,
            "d_token_asset_orders": 0,
            "d_base_asset_volume": output_with_fee,
            "d_token_asset_volume": 0,
        }
        wallet_deltas = {
            "base_in_wallet": output_with_fee,
            "base_in_protocol": [trade_details["mint_time"], 0],
            "token_in_wallet": [trade_details["mint_time"], -1 * trade_details["trade_amount"]],
            "token_in_protocol": [trade_details["mint_time"], 0],
            "fee": [trade_details["mint_time"], fee],
        }
        return market_deltas, wallet_deltas

    def calc_in_given_out(
        self,
        out,
        # TODO: This should be share_reserves when we update the market class
        share_reserves,
        bond_reserves,
        token_in,
        fee_percent,
        time_remaining,
        init_share_price,
        share_price,
    ):
        assert out > 0, f"pricing_models.calc_in_given_out: ERROR: expected out > 0, not {out}!"
        assert (
            share_reserves > 0
        ), f"pricing_models.calc_in_given_out: ERROR: expected share_reserves > 0, not {share_reserves}!"
        assert (
            bond_reserves > 0
        ), f"pricing_models.calc_in_given_out: ERROR: expected bond_reserves > 0, not {bond_reserves}!"
        assert (
            1 >= fee_percent >= 0
        ), f"pricing_models.calc_in_given_out: ERROR: expected 1 >= fee_percent >= 0, not {fee_percent}!"
        assert (
            1 > time_remaining >= 0
        ), f"pricing_models.calc_in_given_out: ERROR: expected 1 > time_remaining >= 0, not {time_remaining}!"
        assert (
            share_price >= init_share_price >= 1
        ), f"pricing_models.calc_in_given_out: ERROR: expected share_price >= init_share_price >= 1, not share_price={share_price} and init_share_price={init_share_price}!"
        r"""
        Calculates the amount of an asset that must be provided to receive a
        specified amount of the other asset given the current AMM reserves.

        The input is calculated as:

        .. math::
            in' =
            \begin{cases}
            c (\frac{1}{\mu} (\frac{k - (2y + cz - \Delta y)^{1-t}}{\frac{c}{\mu}})^{\frac{1}{1-t}} - z), &\text{ if } token\_in = \text{"base"} \\
            (k - \frac{c}{\mu} (\mu * (z - \Delta z))^{1 - t})^{\frac{1}{1 - t}} - (2y + cz), &\text{ if } token\_in = \text{"pt"}
            \end{cases} \\
            f = 
            \begin{cases}
            (1 - \frac{1}{(\frac{2y + cz}{\mu z})^t}) \phi \Delta y, &\text{ if } token\_in = \text{"base"} \\
            (\frac{2y + cz}{\mu z})^t - 1) \phi (c \Delta z), &\text{ if } token\_in = \text{"pt"}
            \end{cases} \\
            in = in' + f

        Arguments
        ---------
        out : float
            The amount of tokens that the user wants to receive. When the user
            wants to pay in bonds, this value should be an amount of base tokens
            rather than an amount of shares.
        share_reserves : float
            The reserves of shares in the pool.
        bond_reserves : float
            The reserves of bonds in the pool.
        token_in : str
            The token that the user pays. The only valid values are "base" and
            "pt".
        fee_percent : float
            The percentage of the difference between the amount paid without
            slippage and the amount received that will be added to the input
            as a fee.
        time_remaining : float
            The time remaining for the asset (incorporates time stretch).
        init_share_price : float
            The share price when the pool was initialized.
        share_price : float
            The current share price.

        Returns
        -------
        float
            The amount the user pays without fees or slippage. The units
            are always in terms of bonds or base.
        float
            The amount the user pays with fees and slippage. The units are
            always in terms of bonds or base.
        float
            The amount the user pays with slippage and no fees. The units are
            always in terms of bonds or base.
        float
            The fee the user pays. The units are always in terms of bonds or
            base.
        """

        # TODO: Break this function up to use private class functions
        # pylint: disable=too-many-locals
        time_elapsed = 1 - time_remaining
        scale = share_price / init_share_price
        total_reserves = share_price * share_reserves + bond_reserves
        spot_price = self._calc_spot_price(share_reserves, bond_reserves, init_share_price, share_price, time_remaining)
        # We precompute the YieldSpace constant k using the current reserves and
        # share price:
        #
        # k = (c / mu) * (mu * z)**(1 - t) + (2y + cz)**(1 - t)
        k = self._calc_k_const(share_reserves, bond_reserves, share_price, init_share_price, time_elapsed)
        if token_in == "base":  # calc shares in for pt out
            in_reserves = share_reserves
            out_reserves = bond_reserves + total_reserves
            d_bonds = out
            # The amount the user would pay without fees or slippage is simply
            # the amount of bonds the user would receive times the spot price of
            # base in terms of bonds (this is the inverse of the usual spot
            # price). If we let p be the conventional spot price, then we can
            # write this as:
            #
            # (1 / p) * d_y
            without_fee_or_slippage = d_bonds * (1 / spot_price)
            # Solve the YieldSpace invariant for the base required to purchase
            # the requested amount of bonds.
            #
            # We set up the invariant where the user pays d_z shares and
            # receives d_y bonds:
            #
            # (c / mu) * (mu * (z + d_z))**(1 - t) + (2y + cz - d_y)**(1 - t) = k
            #
            # Solving for d_z gives us the amount of shares the user must pay
            # without including fees:
            #
            # d_z = (1 / mu) * ((k - (2y + cz - d_y)**(1 - t)) / (c / mu))**(1 / (1 - t)) - z
            #
            # We really want to know the value of d_x, the amount of base the
            # user pays. This is simply c * d_x
            without_fee = (
                (1 / init_share_price)
                * pow(
                    (k - pow(out_reserves - d_bonds, time_elapsed)) / scale,
                    1 / time_elapsed,
                )
                - in_reserves
            ) * share_price
            # The fees are calculated as the difference between the bonds
            # received and the base paid without slippage times the fee
            # percentage. This can also be expressed as:
            #
            # (1 - (1 / p)) * phi * d_y
            fee = (1 - (1 / spot_price)) * fee_percent * d_bonds
        elif token_in == "pt":
            in_reserves = bond_reserves + total_reserves
            out_reserves = share_reserves
            d_shares = out / share_price
            # The amount the user would pay without fees or slippage is simply
            # the amount of base the user would receive times the spot price of
            # bonds in terms of base (this is the conventional spot price).
            # The amount of base the user receives is given by c * d_z where
            # d_z is the number of shares the pool will need to unwrap to give
            # the user their base. If we let p be the conventional spot price,
            # then we can write this as:
            #
            # p * c * d_z
            without_fee_or_slippage = spot_price * share_price * d_shares
            # Solve the YieldSpace invariant for the bonds required to purchase
            # the requested amount of base.
            #
            # We set up the invariant where the user pays d_y bonds and
            # receives d_z shares:
            #
            # (c / mu) * (mu * (z - d_z))**(1 - t) + (2y + cz + d_y)**(1 - t) = k
            #
            # Solving for d_y gives us the amount of bonds the user must pay
            # without including fees:
            #
            # d_y = (k - (c / mu) * (mu * (z - d_z))**(1 - t))**(1 / (1 - t)) - (2y + cz)
            without_fee = (
                pow(
                    k - scale * pow((init_share_price * (out_reserves - d_shares)), time_elapsed),
                    1 / time_elapsed,
                )
                - in_reserves
            )
            # The fees are calculated as the difference between the bonds paid
            # without slippage and the base received times the fee percentage.
            # This can also be expressed as:
            #
            # (p - 1) * phi * c * d_z
            fee = (spot_price - 1) * fee_percent * share_price * d_shares
        else:
            raise AssertionError(
                f'pricing_models.calc_in_given_out: ERROR: expected token_in == "base" or token_in == "pt", not {token_in}!'
            )
        # To get the amount paid with fees, add the fee to the calculation that
        # excluded fees. Adding the fees results in more tokens paid, which
        # indicates that the fees are working correctly.
        with_fee = without_fee + fee
        assert fee >= 0, (
            f"pricing_models.calc_in_given_out: ERROR: Fee should not be negative!"
            f"\n\tout={out}\n\tshare_reserves={share_reserves}\n\tbond_reserves={bond_reserves}"
            f"\n\ttotal_reserves={total_reserves}\n\tinit_share_price={init_share_price}"
            f"\n\tshare_price={share_price}\n\tscale={scale}\n\tfee_percent={fee_percent}"
            f"\n\ttime_remaining={time_remaining}\n\ttime_elapsed={time_elapsed}"
            f"\n\tin_reserves={in_reserves}\n\tout_reserves={out_reserves}\n\ttoken_in={token_in}"
            f"\n\tspot_price={spot_price}\n\tk={k}\n\twithout_fee_or_slippage={without_fee_or_slippage}"
            f"\n\twithout_fee={without_fee}\n\tfee={fee}"
        )

        # TODO(jalextowle): With some analysis, it seems possible to show that
        # we skip straight from non-negative reals to the complex plane without
        # hitting negative reals.
        #
        # Ensure that the outputs are all non-negative floats. We only need to
        # check with_fee since without_fee_or_slippage will always be a positive
        # float due to the constraints on the inputs, without_fee = with_fee + fee
        # so it is a positive float if with_fee and fee are positive floats, and
        # fee is a positive float due to the constraints on the inputs.
        assert isinstance(
            with_fee, float
        ), f"pricing_models.calc_in_given_out: ERROR: with_fee should be a float, not {type(with_fee)}!"
        assert (
            with_fee >= 0
        ), f"pricing_models.calc_in_given_out: ERROR: with_fee should be non-negative, not {with_fee}!"

        return (without_fee_or_slippage, with_fee, without_fee, fee)

    def calc_out_given_in(
        self,
        in_,
        # TODO: This should be share_reserves when we update the market class
        share_reserves,
        bond_reserves,
        token_out,
        fee_percent,
        # TODO: The high slippage tests in tests/test_pricing_model.py should
        # arguably have much higher slippage. This is something we should
        # consider more when thinking about the use of a time stretch parameter.
        time_remaining,
        init_share_price,
        share_price,
    ):
        r"""
        Calculates the amount of an asset that must be provided to receive a
        specified amount of the other asset given the current AMM reserves.

        The output is calculated as:

        .. math::
            out' =
            \begin{cases}
            c (z - \frac{1}{\mu} (\frac{k - (2y + cz + \Delta y)^{1 - t}}{\frac{c}{\mu}})^{\frac{1}{1 - t}}), &\text{ if } token\_out = \text{"base"} \\
            2y + cz - (k - \frac{c}{\mu} (\mu (z + \Delta z))^{1 - t})^{\frac{1}{1 - t}}, &\text{ if } token\_out = \text{"pt"}
            \end{cases} \\
            f = 
            \begin{cases}
            (1 - \frac{1}{(\frac{2y + cz}{\mu z})^t}) \phi \Delta y, &\text{ if } token\_out = \text{"base"} \\
            (\frac{2y + cz}{\mu z})^t - 1) \phi (c \Delta z), &\text{ if } token\_out = \text{"pt"}
            \end{cases} \\
            out = out' + f

        Arguments
        ---------
        in_ : float
            The amount of tokens that the user pays. When users receive bonds,
            this value reflects the base paid.
        share_reserves : float
            The reserves of shares in the pool.
        bond_reserves : float
            The reserves of bonds (PT) in the pool.
        token_out : str
            The token that the user receives. The only valid values are "base"
            and "pt".
        fee_percent : float
            The percentage of the difference between the amount paid and the
            amount received without slippage that will be debited from the
            output as a fee.
        time_remaining : float
            The time remaining for the asset (incorporates time stretch).
        init_share_price : float
            The share price when the pool was initialized.
        share_price : float
            The current share price.

        Returns
        -------
        float
            The amount the user receives without fees or slippage. The units
            are always in terms of bonds or base.
        float
            The amount the user receives with fees and slippage. The units are
            always in terms of bonds or base.
        float
            The amount the user receives with slippage and no fees. The units are
            always in terms of bonds or base.
        float
            The fee the user pays. The units are always in terms of bonds or
            base.
        """
        assert in_ > 0, f"pricing_models.calc_out_given_in: ERROR: expected in_ > 0, not {in_}!"
        assert (
            share_reserves > 0
        ), f"pricing_models.calc_out_given_in: ERROR: expected share_reserves > 0, not {share_reserves}!"
        assert (
            bond_reserves > 0
        ), f"pricing_models.calc_out_given_in: ERROR: expected bond_reserves > 0, not {bond_reserves}!"
        assert (
            1 >= fee_percent >= 0
        ), f"pricing_models.calc_out_given_in: ERROR: expected 1 >= fee_percent >= 0, not {fee_percent}!"
        assert (
            1 > time_remaining >= 0
        ), f"pricing_models.calc_out_given_in: ERROR: expected 1 > time_remaining >= 0, not {time_remaining}!"
        assert (
            share_price >= init_share_price >= 1
        ), f"pricing_models.calc_out_given_in: ERROR: expected share_price >= init_share_price >= 1, not share_price={share_price} and init_share_price={init_share_price}!"

        # TODO: Break this function up to use private class functions
        # pylint: disable=too-many-locals
        scale = share_price / init_share_price
        time_elapsed = 1 - time_remaining
        total_reserves = share_price * share_reserves + bond_reserves
        spot_price = self._calc_spot_price(share_reserves, bond_reserves, init_share_price, share_price, time_remaining)
        # We precompute the YieldSpace constant k using the current reserves and
        # share price:
        #
        # k = (c / mu) * (mu * z)**(1 - t) + (2y + cz)**(1 - t)
        k = self._calc_k_const(share_reserves, bond_reserves, share_price, init_share_price, time_elapsed)
        if token_out == "base":
            d_bonds = in_
            in_reserves = bond_reserves + total_reserves
            out_reserves = share_reserves
            # The amount the user would receive without fees or slippage is
            # the amount of bonds the user pays times the spot price of
            # base in terms of bonds (this is the inverse of the conventional
            # spot price). If we let p be the conventional spot price, then we
            # can write this as:
            #
            # (1 / p) * d_y
            without_fee_or_slippage = (1 / spot_price) * d_bonds
            # Solve the YieldSpace invariant for the base received from selling
            # the specified amount of bonds.
            #
            # We set up the invariant where the user pays d_y bonds and
            # receives d_z shares:
            #
            # (c / mu) * (mu * (z - d_z))**(1 - t) + (2y + cz + d_y)**(1 - t) = k
            #
            # Solving for d_z gives us the amount of shares the user receives
            # without including fees:
            #
            # d_z = z - (1 / mu) * ((k - (2y + cz + d_y)**(1 - t)) / (c / mu))**(1 / (1 - t))
            #
            # We really want to know the value of d_x, the amount of base the
            # user receives. This is simply c * d_x
            without_fee = (
                share_reserves
                - (1 / init_share_price) * ((k - (in_reserves + d_bonds) ** time_elapsed) / scale) ** (1 / time_elapsed)
            ) * share_price
            # The fees are calculated as the difference between the bonds paid
            # and the base received without slippage times the fee percentage.
            # This can also be expressed as:
            #
            # (1 - (1 / p) * phi * d_y
            fee = (1 - (1 / spot_price)) * fee_percent * d_bonds
            with_fee = without_fee - fee
        elif token_out == "pt":
            d_shares = in_ / share_price  # convert from base_asset to z (x=cz)
            in_reserves = share_reserves
            out_reserves = bond_reserves + total_reserves
            # The amount the user would receive without fees or slippage is
            # the amount of base the user pays times the spot price of
            # base in terms of bonds (this is the conventional spot price). If
            # we let p be the conventional spot price, then we can write this
            # as:
            #
            # p * c * d_z
            without_fee_or_slippage = spot_price * share_price * d_shares
            # Solve the YieldSpace invariant for the base received from selling
            # the specified amount of bonds.
            #
            # We set up the invariant where the user pays d_y bonds and
            # receives d_z shares:
            #
            # (c / mu) * (mu * (z + d_z))**(1 - t) + (2y + cz - d_y)**(1 - t) = k
            #
            # Solving for d_y gives us the amount of bonds the user receives
            # without including fees:
            #
            # d_y = 2y + cz - (k - (c / mu) * (mu * (z + d_z))**(1 - t))**(1 / (1 - t))
            without_fee = out_reserves - pow(
                k - scale * pow(init_share_price * (in_reserves + d_shares), time_elapsed), 1 / time_elapsed
            )
            # The fees are calculated as the difference between the bonds
            # received without slippage and the base paid times the fee
            # percentage. This can also be expressed as:
            #
            # (p - 1) * phi * c * d_z
            fee = (spot_price - 1) * fee_percent * share_price * d_shares
        else:
            raise AssertionError(
                f'pricing_models.calc_out_given_in: ERROR: expected token_out == "base" or token_out == "pt", not {token_out}!'
            )
        # To get the amount paid with fees, subtract the fee from the
        # calculation that excluded fees. Subtracting the fees results in less
        # tokens received, which indicates that the fees are working correctly.
        with_fee = without_fee - fee
        if self.verbose:
            print(
                f"pricing_models.calc_out_given_in:"
                f"\n\tin_ = {in_}\n\tshare_reserves = {share_reserves}\n\tbond_reserves = {bond_reserves}"
                f"\n\ttotal_reserves = {total_reserves}\n\tinit_share_price = {init_share_price}"
                f"\n\tshare_price = {share_price}\n\tscale = {scale}\n\tfee_percent = {fee_percent}"
                f"\n\ttime_remaining = {time_remaining}\n\ttime_elapsed = {time_elapsed}"
                f"\n\tin_reserves = {in_reserves}\n\tout_reserves = {out_reserves}\n\ttoken_out = {token_out}"
                f"\n\tspot_price = {spot_price}\n\tk = {k}\n\twithout_fee_or_slippage = {without_fee_or_slippage}"
                f"\n\twithout_fee = {without_fee}\n\twith_fee = {with_fee}\n\tfee = {fee}"
            )

        # TODO(jalextowle): With some analysis, it seems possible to show that
        # we skip straight from non-negative reals to the complex plane without
        # hitting negative reals.
        #
        # Ensure that the outputs are all non-negative floats. We only need to
        # check with_fee since without_fee_or_slippage will always be a positive
        # float due to the constraints on the inputs, without_fee = with_fee + fee
        # so it is a positive float if with_fee and fee are positive floats, and
        # fee is a positive float due to the constraints on the inputs.
        assert isinstance(
            with_fee, float
        ), f"pricing_models.calc_out_given_in: ERROR: with_fee should be a float, not {type(with_fee)}!"
        assert (
            with_fee >= 0
        ), f"pricing_models.calc_out_given_in: ERROR: with_fee should be non-negative, not {with_fee}!"

        return (without_fee_or_slippage, with_fee, without_fee, fee)

    def _calc_spot_price(self, share_reserves, bond_reserves, init_share_price, share_price, time_remaining):
        r"""
        Calculates the spot price of a principal token in terms of the base asset.

        The spot price is defined as:

        .. math::
            \begin{align}
            p = (\frac{2y + cz}{\mu z})^{t}
            \end{align}

        Arguments
        ---------
        share_reserves : float
            The reserves of shares in the pool.
        bond_reserves : float
            The reserves of bonds in the pool.
        init_share_price : float
            The share price when the pool was initialized.
        share_price : float
            The current share price.
        time_remaining : float
            The time remaining for the asset (incorporates time stretch).

        Returns
        -------
        float
            The spot price of principal tokens.
        """
        total_reserves = share_price * share_reserves + bond_reserves
        bond_reserves_ = bond_reserves + total_reserves
        return pow((bond_reserves_) / (init_share_price * share_reserves), time_remaining)

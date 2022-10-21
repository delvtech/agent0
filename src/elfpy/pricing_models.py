"""
Pricing models implement automated market makers (AMMs)
"""

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
    def norm_days(days, normalizing_constant=365):
        """Returns days normalized between 0 and 1, with a default assumption of a year-long scale"""
        return days / normalizing_constant

    @staticmethod
    def _stretch_time(time, time_stretch=1):
        """Returns stretched time values"""
        return time / time_stretch

    @staticmethod
    def _unnorm_days(normed_days, normalizing_constant=365):
        """Returns days from a value between 0 and 1"""
        return normed_days * normalizing_constant

    @staticmethod
    def _unstretch_time(stretched_time, time_stretch=1):
        """Returns unstretched time value, which should be between 0 and 1"""
        return stretched_time * time_stretch

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

    @staticmethod
    def _calc_k_const(in_reserves, out_reserves, time_elapsed, scale=1):
        """Returns the 'k' constant variable for trade mathematics"""
        return scale * in_reserves ** (time_elapsed) + out_reserves ** (time_elapsed)

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
        normed_days_remaining = self.norm_days(days_remaining, normalizing_constant)
        time_remaining = self._stretch_time(normed_days_remaining, time_stretch)
        return time_remaining

    def time_to_days_remaining(self, time_remaining, time_stretch=1, normalizing_constant=365):
        """Converts normalized and stretched time remaining in pool to days"""
        normed_days_remaining = self._unstretch_time(time_remaining, time_stretch)
        days_remaining = self._unnorm_days(normed_days_remaining, normalizing_constant)
        return days_remaining

    def calc_max_trade(self, in_reserves, out_reserves, time_remaining):
        """
        Returns the maximum allowable trade amount given the current asset reserves

        TODO: write a test to verify that this is correct
        """
        time_elapsed = 1 - time_remaining
        k = self._calc_k_const(in_reserves, out_reserves, time_elapsed)  # in_reserves^(1 - t) + out_reserves^(1 - t)
        return k ** (1 / time_elapsed) - in_reserves

    def calc_apy_from_spot_price(self, price, normalized_days_remaining):
        """Returns the APY (decimal) given the current (positive) base asset price and the remaining pool duration"""
        assert price > 0, f"ERROR: calc_apy_from_spot_price: Price argument should be greater than zero, not {price}"
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
        apy = self.calc_apy_from_spot_price(spot_price, self.norm_days(days_remaining))
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
        normalized_days_remaining = self.norm_days(days_remaining)
        time_stretch_exp = 1 / self._stretch_time(normalized_days_remaining, time_stretch)
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
        spot_price = self.calc_spot_price_from_apy(apy, self.norm_days(days_remaining))
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
        k = self._calc_k_const(in_reserves, out_reserves, time_elapsed)  # in_reserves**(1 - t) + out_reserves**(1 - t)
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
        k = self._calc_k_const(in_reserves, out_reserves, time_elapsed)  # in_reserves**(1 - t) + out_reserves**(1 - t)
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


class YieldSpacev2PricingModel(PricingModel):
    """
    V2 pricing model that uses Yield Bearing Vault equations
    """

    def __init__(self, verbose=False, floor_fee=0):
        super().__init__(verbose)
        self.floor_fee = floor_fee

    def model_name(self):
        if self.floor_fee > 0:
            return "YieldSpacev2MinFee"
        return "YieldSpacev2"

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
        # TODO: Break this function up to use private class functions
        # pylint: disable=too-many-locals
        scale = share_price / init_share_price
        time_elapsed = 1 - time_remaining
        if token_in == "base":  # calc shares in for fyt out
            d_token_asset = out
            share_reserves = in_reserves / share_price  # convert from base_asset to z (x=cz)
            token_asset = out_reserves
            # AMM math
            # k = scale * (u * z)**(1 - t) + y**(1 - t)
            k = self._calc_k_const(init_share_price * share_reserves, token_asset, time_elapsed, scale)
            inv_init_share_price = 1 / init_share_price
            new_token_asset = token_asset - d_token_asset
            without_fee = (
                inv_init_share_price * ((k - new_token_asset**time_elapsed) / scale) ** (1 / time_elapsed)
                - share_reserves
            ) * share_price
            # Fee math
            fee = (out - without_fee) * fee_percent
            with_fee = without_fee + fee
            without_fee_or_slippage = (
                out * (in_reserves / (share_price / init_share_price * out_reserves)) ** time_remaining
            )
        elif token_in == "fyt":  # calc fyt in for shares out
            d_share_reserves = out / share_price
            share_reserves = out_reserves / share_price  # convert from base_asset to z (x=cz)
            token_asset = in_reserves
            # AMM math
            # k = scale * (u * z)**(1 - t) + y**(1 - t)
            k = self._calc_k_const(init_share_price * share_reserves, token_asset, time_elapsed, scale)
            without_fee = (
                k - scale * (init_share_price * share_reserves - init_share_price * d_share_reserves) ** time_elapsed
            ) ** (1 / time_elapsed) - token_asset
            # Fee math
            fee = (without_fee - out) * fee_percent
            with_fee = without_fee + fee
            without_fee_or_slippage = (
                out * ((share_price / init_share_price * in_reserves) / out_reserves) ** time_remaining
            )
        return (without_fee_or_slippage, with_fee, without_fee, fee)

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
        # TODO: Break this function up to use private class functions
        # pylint: disable=too-many-locals
        scale = share_price / init_share_price  # normalized function of vault yields
        time_elapsed = 1 - time_remaining
        if token_out == "base":  # calc shares out for fyt in
            d_token_asset = in_
            share_reserves = out_reserves / share_price  # convert from x to z (x=cz)
            token_asset = in_reserves
            # AMM math
            # k = scale * (u * z)**(1 - t) + y**(1 - t)
            k = self._calc_k_const(init_share_price * share_reserves, token_asset, time_elapsed, scale)
            inv_init_share_price = 1 / init_share_price
            without_fee = (
                share_reserves
                - inv_init_share_price
                * ((k - (token_asset + d_token_asset) ** time_elapsed) / scale) ** (1 / time_elapsed)
            ) * share_price
            # Fee math
            fee = (in_ - without_fee) * fee_percent
            assert fee >= 0, (
                f"ERROR: Fee should not be negative fee={fee}"
                f" in_={in_} without_fee={without_fee} fee_percent={fee_percent} token_out={token_out}"
            )
            if fee / in_ < self.floor_fee / 100 / 100:
                fee = in_ * self.floor_fee / 100 / 100
            with_fee = without_fee - fee
            without_fee_or_slippage = (
                1 / ((share_price / init_share_price * in_reserves) / out_reserves) ** time_remaining * in_
            )
        elif token_out == "fyt":  # calc fyt out for shares in
            d_share_reserves = in_ / share_price  # convert from base_asset to z (x=cz)
            share_reserves = in_reserves / share_price  # convert from base_asset to z (x=cz)
            token_asset = out_reserves
            # AMM math
            # k = scale * (u * z)**(1 - t) + y**(1 - t)
            k = self._calc_k_const(init_share_price * share_reserves, token_asset, time_elapsed, scale)
            without_fee = token_asset - (
                k - scale * (init_share_price * share_reserves + init_share_price * d_share_reserves) ** time_elapsed
            ) ** (1 / time_elapsed)
            # Fee math
            fee = (without_fee - in_) * fee_percent
            assert fee >= 0, (
                f"ERROR: Fee should not be negative fee={fee}"
                f" in_={in_} without_fee={without_fee} fee_percent={fee_percent} token_out={token_out}"
            )
            if fee / in_ < self.floor_fee / 100 / 100:
                fee = in_ * self.floor_fee / 100 / 100
            with_fee = without_fee - fee
            without_fee_or_slippage = (
                in_ / (in_reserves / (share_price / init_share_price * out_reserves)) ** time_remaining
            )
        return (without_fee_or_slippage, with_fee, without_fee, fee)

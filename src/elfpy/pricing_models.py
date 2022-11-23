"""
Pricing models implement automated market makers (AMMs)

TODO: rewrite all functions to have typed inputs
"""


import elfpy.utils.price as price_utils
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

    def __init__(self, verbose=False):
        """
        Arguments
        ---------
        verbose : bool
            if True, print verbose outputs
        """
        self.verbose = verbose

    def calc_in_given_out(
        self,
        out,
        share_reserves,
        bond_reserves,
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
        share_reserves,
        bond_reserves,
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

    def calc_spot_price_from_reserves(
        self, share_reserves, bond_reserves, init_share_price, share_price, time_remaining
    ):
        r"""
        Calculates the spot price of base in terms of bonds.

        The spot price is defined as:

        .. math::
            \begin{align}
            p = (\frac{2y + cz}{\mu z})^{-\tau}
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
        # if share_reserves == 0:
        #     return np.inf
        # else:
        return 1 / (((bond_reserves_) / (init_share_price * share_reserves)) ** time_remaining)

    def calc_apr_from_reserves(
        self,
        share_reserves,
        bond_reserves,
        time_remaining,
        time_stretch,
        init_share_price=1,
        share_price=1,
    ):
        # TODO: Update this comment so that it matches the style of the other comments.
        """
        Returns the apr given reserve amounts
        """
        spot_price = self.calc_spot_price_from_reserves(
            share_reserves,
            bond_reserves,
            init_share_price,
            share_price,
            time_remaining,
        )
        days_remaining = time_utils.time_to_days_remaining(time_remaining, time_stretch)
        apr = price_utils.calc_apr_from_spot_price(spot_price, time_utils.norm_days(days_remaining))
        return apr

    def calc_time_stretch(self, apr):
        """Returns fixed time-stretch value based on current apr (as a decimal)"""
        apr_percent = apr * 100
        return 3.09396 / (0.02789 * apr_percent)


class ElementPricingModel(PricingModel):
    """
    Element v1 pricing model
    Does not use the Yield Bearing Vault `init_share_price` (μ) and `share_price` (c) variables.
    """

    def model_name(self):
        return "Element"

    def calc_in_given_out(
        self,
        out,
        share_reserves,
        bond_reserves,
        token_in,
        fee_percent,
        time_remaining,
        init_share_price=1,
        share_price=1,
    ):
        r"""
        Calculates the amount of an asset that must be provided to receive a
        specified amount of the other asset given the current AMM reserves.

        The input is calculated as:

        .. math::
            in' =
            \begin{cases}
            (\frac{k - (2y + x - \Delta y)^{1 - \tau}})^{\frac{1}{1 - \tau}} - x, &\text{ if } token\_in = \text{"base"} \\
            (k - (x - \Delta x)^{1 - \tau})^{\frac{1}{1 - \tau}} - (2y + x), &\text{ if } token\_in = \text{"pt"}
            \end{cases} \\
            f = 
            \begin{cases}
            (\Delta y - in') \cdot \phi, &\text{ if } token\_in = \text{"base"} \\
            (in' - \Delta x) \cdot \phi, &\text{ if } token\_in = \text{"pt"}
            \end{cases} \\
            in = in' + f

        Arguments
        ---------
        out : float
            The amount of tokens that the user wants to receive. When the user
            wants to pay in bonds, this value should be an amount of base tokens
            rather than an amount of shares.
        share_reserves : float
            The reserves of shares in the pool. NOTE: Element V1 didn't have a
            concept of shares and instead used base.
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
            The share price when the pool was initialized. NOTE: For this 
            pricing model, the initial share price must always be one.
        share_price : float
            The current share price. NOTE: For this pricing model, the share 
            price must always be one.

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
            share_price == init_share_price == 1
        ), f"pricing_models.calc_in_given_out: ERROR: expected share_price == init_share_price == 1, not share_price={share_price} and init_share_price={init_share_price}!"

        time_elapsed = 1 - time_remaining
        bond_reserves_ = 2 * bond_reserves + share_reserves
        spot_price = self.calc_spot_price_from_reserves(share_reserves, bond_reserves, 1, 1, time_remaining)
        # We precompute the YieldSpace constant k using the current reserves and
        # share price:
        #
        # k = x**(1 - τ) + (2y + x)**(1 - τ)
        # k = (c / μ) * (μ * z)**(1 - τ) + (2y + cz)**(1 - τ)
        k = price_utils.calc_k_const(share_reserves, bond_reserves, share_price, init_share_price, time_elapsed)
        # Solve for the amount that must be paid to receive the specified amount
        # of the output.
        if token_in == "base":
            d_bonds = out
            # The amount the user pays without fees or slippage is the amount of
            # bonds the user receives times the spot price of base in terms
            # of bonds. If we let p be the conventional spot price, then we can
            # write this as:
            #
            # without_fee_or_slippage = p * d_y
            without_fee_or_slippage = spot_price * d_bonds
            # We solve the YieldSpace invariant for the base required to
            # purchase the requested amount of bonds. We set up the invariant
            # where the user pays d_x' base and receives d_y bonds:
            #
            # (x + d_x')**(1 - t) + (2y + x - d_y)**(1 - t) = k
            #
            # Solving for d_x' gives us the amount of base the user must pay
            # without including fees:
            #
            # d_x' = (k - (2y + x - d_y)**(1 - t))**(1 / (1 - t)) - x
            #
            # without_fee = d_x'
            without_fee = (k - (bond_reserves_ - d_bonds) ** time_elapsed) ** (1 / time_elapsed) - share_reserves
            # The fees are calculated as the difference between the bonds
            # received and the base paid without fees times the fee percentage.
            # This can also be expressed as:
            #
            # fee = phi * (d_y - d_x')
            fee = fee_percent * (d_bonds - without_fee)
        elif token_in == "pt":
            d_base = out
            # The amount the user pays without fees or slippage is the amount of
            # bonds the user receives times the inverse of the spot price
            # of base in terms of bonds. If we let p be the conventional spot
            # price, then we can write this as:
            #
            # without_fee_or_slippage = (1 / p) * d_x
            without_fee_or_slippage = (1 / spot_price) * out
            # We solve the YieldSpace invariant for the bonds required to
            # purchase the requested amount of base. We set up the invariant
            # where the user pays d_y bonds and receives d_x base:
            #
            # (x - d_x)**(1 - t) + (2y + x + d_y')**(1 - t) = k
            #
            # Solving for d_y' gives us the amount of bonds the user must pay
            # without including fees:
            #
            # d_y' = (k - (x - d_x)**(1 - t))**(1 / (1 - t)) - (2y + x)
            #
            # without_fee = d_y'
            without_fee = (k - (share_reserves - d_base) ** time_elapsed) ** (1 / time_elapsed) - bond_reserves_
            # The fees are calculated as the difference between the bonds
            # paid without fees and the base received times the fee percentage.
            # This can also be expressed as:
            #
            # fee = phi * (d_y' - d_x)
            fee = fee_percent * (without_fee - d_base)
        else:
            raise AssertionError(
                f'pricing_models.calc_in_given_out: ERROR: expected token_in to be "base" or "pt", not {token_in}!'
            )
        # To get the amount paid with fees, add the fee to the calculation that
        # excluded fees. Adding the fees results in more tokens paid, which
        # indicates that the fees are working correctly.
        with_fee = without_fee + fee
        if self.verbose:
            print(
                f"pricing_models.calc_in_given_out:"
                f"\n\tout = {out}\n\tshare_reserves = {share_reserves}\n\tbond_reserves = {bond_reserves}"
                f"\n\ttotal_reserves = {share_reserves + bond_reserves}\n\tinit_share_price = {init_share_price}"
                f"\n\tshare_price = {share_price}\n\tfee_percent = {fee_percent}"
                f"\n\ttime_remaining = {time_remaining}\n\ttime_elapsed = {time_elapsed}"
                f"\n\ttoken_in = {token_in}\n\tspot_price = {spot_price}"
                f"\n\tk = {k}\n\twithout_fee_or_slippage = {without_fee_or_slippage}"
                f"\n\twithout_fee = {without_fee}\n\twith_fee = {with_fee}\n\tfee = {fee}"
            )

        # TODO(jalextowle): With some analysis, it seems possible to show that
        # we skip straight from non-negative reals to the complex plane without
        # hitting negative reals.
        #
        # Ensure that the outputs are all non-negative floats. We only need to
        # check without_fee since without_fee_or_slippage will always be a positive
        # float due to the constraints on the inputs, with_fee = without_fee + fee
        # so it is a positive float if without_fee and fee are positive floats, and
        # fee is a positive float due to the constraints on the inputs.
        assert isinstance(
            without_fee, float
        ), f"pricing_models.calc_in_given_out: ERROR: without_fee should be a float, not {type(without_fee)}!"
        assert (
            without_fee >= 0
        ), f"pricing_models.calc_in_given_out: ERROR: without_fee should be non-negative, not {without_fee}!"

        return (without_fee_or_slippage, with_fee, without_fee, fee)

    def calc_out_given_in(
        self,
        in_,
        share_reserves,
        bond_reserves,
        token_out,
        fee_percent,
        time_remaining,
        init_share_price=1,
        share_price=1,
    ):
        r"""
        Calculates the amount of an asset that must be provided to receive a
        specified amount of the other asset given the current AMM reserves.

        The output is calculated as:

        .. math::
            out' =
            \begin{cases}
            (x - (k - (2y + x + \Delta y)^{1 - \tau})^{\frac{1}{1 - \tau}}), &\text{ if } token\_out = \text{"base"} \\
            2y + x - (k - (x + \Delta x)^{1 - \tau})^{\frac{1}{1 - \tau}}, &\text{ if } token\_out = \text{"pt"}
            \end{cases} \\
            f = 
            \begin{cases}
            (\Delta y - out') \cdot \phi, &\text{ if } token\_out = \text{"base"} \\
            (out' - \Delta x) \cdot \phi, &\text{ if } token\_out = \text{"pt"}
            \end{cases} \\
            out = out' + f
        Arguments
        ---------
        in_ : float
            The amount of tokens that the user pays. When users receive bonds,
            this value reflects the base paid.
        share_reserves : float
            The reserves of base in the pool.
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
            The share price when the pool was initialized. NOTE: For this 
            pricing model, the initial share price must always be one.
        share_price : float
            The current share price. NOTE: For this pricing model, the share 
            price must always be one.

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
            share_price == init_share_price == 1
        ), f"pricing_models.calc_out_given_in: ERROR: expected share_price == init_share_price == 1, not share_price={share_price} and init_share_price={init_share_price}!"

        time_elapsed = 1 - time_remaining
        bond_reserves_ = 2 * bond_reserves + share_reserves
        spot_price = self.calc_spot_price_from_reserves(share_reserves, bond_reserves, 1, 1, time_remaining)
        # We precompute the YieldSpace constant k using the current reserves and
        # share price:
        #
        # k = x**(1 - τ) + (2y + x)**(1 - τ)
        k = price_utils.calc_k_const(share_reserves, bond_reserves, share_price, init_share_price, time_elapsed)
        # Solve for the amount that received if the specified amount is paid.
        if token_out == "base":
            d_bonds = in_
            # The amount the user pays without fees or slippage is the amount of
            # bonds the user pays times the spot price of base in terms of bonds.
            # If we let p be the conventional spot price, then we can write this
            # as:
            #
            # without_fee_or_slippage = p * d_y
            without_fee_or_slippage = spot_price * d_bonds
            # We solve the YieldSpace invariant for the base received from
            # paying the specified amount of bonds. We set up the invariant
            # where the user pays d_y bonds and receives d_x' base:
            #
            # (x - d_x')**(1 - t) + (2y + x + d_y)**(1 - t) = k
            #
            # Solving for d_x' gives us the amount of base the user must pay
            # without including fees:
            #
            # d_x' = x - (k - (2y + x + d_y)**(1 - t))**(1 / (1 - t))
            #
            # without_fee = d_x'
            without_fee = share_reserves - (k - (bond_reserves_ + d_bonds) ** time_elapsed) ** (1 / time_elapsed)
            # The fees are calculated as the difference between the bonds paid
            # and the base received without fees times the fee percentage. This
            # can also be expressed as:
            #
            # fee = phi * (d_y - d_x')
            fee = fee_percent * (d_bonds - without_fee)
        elif token_out == "pt":
            d_base = in_
            # The amount the user pays without fees or slippage is the amount of
            # base the user pays times the inverse of the spot price of base in
            # terms of bonds. If we let p be the conventional spot price, then
            # we can write this as:
            #
            # without_fee_or_slippage = (1 / p) * d_x
            without_fee_or_slippage = (1 / spot_price) * d_base
            # We solve the YieldSpace invariant for the bonds received from
            # paying the specified amount of base. We set up the invariant
            # where the user pays d_x base and receives d_y' bonds:
            #
            # (x + d_x)**(1 - t) + (2y + x - d_y')**(1 - t) = k
            #
            # Solving for d_x' gives us the amount of base the user must pay
            # without including fees:
            #
            # d_y' = 2y + x - (k - (x + d_x)**(1 - t))**(1 / (1 - t))
            #
            # without_fee = d_x'
            without_fee = bond_reserves_ - (k - (share_reserves + d_base) ** time_elapsed) ** (1 / time_elapsed)
            # The fees are calculated as the difference between the bonds paid
            # and the base received without fees times the fee percentage. This
            # can also be expressed as:
            #
            # fee = phi * (d_y' - d_x)
            fee = fee_percent * (without_fee - d_base)
        else:
            raise AssertionError(
                f'pricing_models.calc_out_given_in: ERROR: expected token_out to be "base" or "pt", not {token_out}!'
            )
        # To get the amount paid with fees, subtract the fee from the
        # calculation that excluded fees. Subtracting the fees results in less
        # tokens received, which indicates that the fees are working correctly.
        with_fee = without_fee - fee
        if self.verbose:
            print(
                f"pricing_models.calc_out_given_in:"
                f"\n\tin_ = {in_}\n\tshare_reserves = {share_reserves}\n\tbond_reserves = {bond_reserves}"
                f"\n\ttotal_reserves = {share_reserves + bond_reserves}\n\tinit_share_price = {init_share_price}"
                f"\n\tshare_price = {share_price}\n\tfee_percent = {fee_percent}"
                f"\n\ttime_remaining = {time_remaining}\n\ttime_elapsed = {time_elapsed}"
                f"\n\ttoken_out = {token_out}\n\tspot_price = {spot_price}"
                f"\n\tk = {k}\n\twithout_fee_or_slippage = {without_fee_or_slippage}"
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



class HyperdrivePricingModel(PricingModel):
    """
    Hyperdrive Pricing Model

    This pricing model uses the YieldSpace invariant with modifications to
    enable the base reserves to be deposited into yield bearing vaults
    """

    def model_name(self):
        return "Hyperdrive"

    def calc_lp_out_given_tokens_in(
        self,
        base_asset_in,
        share_reserves,
        bond_reserves,
        share_buffer,
        init_share_price,
        share_price,
        liquidity_pool,
        rate,
        time_remaining,
        stretched_time_remaining,
    ):
        assert (
            base_asset_in > 0
        ), f"pricing_models.calc_lp_out_given_tokens_in: ERROR: expected base_asset_in > 0, not {base_asset_in}!"
        assert (
            share_reserves >= 0
        ), f"pricing_models.calc_lp_out_given_tokens_in: ERROR: expected share_reserves >= 0, not {share_reserves}!"
        assert (
            bond_reserves >= 0
        ), f"pricing_models.calc_lp_out_given_tokens_in: ERROR: expected bond_reserves >= 0, not {bond_reserves}!"
        assert (
            share_buffer >= 0
        ), f"pricing_models.calc_lp_out_given_tokens_in: ERROR: expected share_buffer >= 0, not {share_buffer}!"
        assert (
            liquidity_pool >= 0
        ), f"pricing_models.calc_lp_out_given_tokens_in: ERROR: expected liquidity_pool >= 0, not {liquidity_pool}!"
        assert (
            rate >= 0
        ), f"pricing_models.calc_lp_out_given_tokens_in: ERROR: expected rate >= 0, not {rate}!"
        assert (
            1 > time_remaining >= 0
        ), f"pricing_models.calc_lp_out_given_tokens_in: ERROR: expected 1 > time_remaining >= 0, not {time_remaining}!"
        assert (
            stretched_time_remaining >= 0
        ), f"pricing_models.calc_lp_out_given_tokens_in: ERROR: expected stretched_time_remaining >= 0, not {stretched_time_remaining}!"
        assert share_price >= init_share_price >= 1, (
            "pricing_models.calc_lp_out_given_tokens_in: ERROR: expected share_price >= init_share_price >= 1, not"
            f" share_price={share_price} and init_share_price={init_share_price}!"
        )
        r"""
        Computes the amount of LP tokens to be minted for a given amount of base asset

        .. math::

        y = \frac{(z - \Delta z)(\mu \cdot (\frac{1}{1 + r \cdot t(d)})^{\frac{1}{\tau(d_b)}} - c)}{2}

        """
        if self.verbose:
            print(f"  inputs: base_asset_in={base_asset_in}, share_reserves={share_reserves}, bond_reserves={bond_reserves}, share_buffer={share_buffer}, init_share_price={init_share_price}, share_price={share_price}, liquidity_pool={liquidity_pool}, rate={rate}, time_remaining={time_remaining}, stretched_time_remaining={stretched_time_remaining}")
        d_share_reserves = base_asset_in / share_price
        if self.verbose:
            print(f"  d_share_reserves={d_share_reserves} (base_asset_in / share_price = {base_asset_in} / {share_price})")
        if share_reserves > 0:  # normal case where we have some share reserves
            lp_out = d_share_reserves * liquidity_pool / (share_reserves - share_buffer)
        else:  # initial case where we have 0 share reserves
            lp_out = d_share_reserves
        d_token_reserves = (share_reserves + d_share_reserves) / 2 * (
            init_share_price * (1 + rate * time_remaining) ** (1 / stretched_time_remaining) - share_price
        ) - bond_reserves
        if self.verbose:
            print(f"  lp_out={lp_out} (d_share_reserves * liquidity_pool / (share_reserves - share_buffer) = {d_share_reserves} * {liquidity_pool} / ({share_reserves} - {share_buffer}))")
            print(f"  d_token_reserves={d_token_reserves} ((share_reserves + d_share_reserves) / 2 * (init_share_price * (1 + rate * time_remaining) ** (1 / stretched_time_remaining) - share_price) - bond_reserves = ({share_reserves} + {d_share_reserves}) / 2 * ({init_share_price} * (1 + {rate} * {time_remaining}) ** (1 / {stretched_time_remaining}) - {share_price}) - {bond_reserves})")
        return lp_out, base_asset_in, d_token_reserves

    def calc_lp_in_given_tokens_out(
        self,
        base_asset_out,
        share_reserves,
        bond_reserves,
        share_buffer,
        init_share_price,
        share_price,
        liquidity_pool,
        rate,
        time_remaining,
        stretched_time_remaining,
    ):
        assert (
            base_asset_out > 0
        ), f"pricing_models.calc_lp_in_given_tokens_out: ERROR: expected base_asset_out > 0, not {base_asset_out}!"
        assert (
            share_reserves > 0
        ), f"pricing_models.calc_lp_in_given_tokens_out: ERROR: expected share_reserves > 0, not {share_reserves}!"
        assert (
            bond_reserves >= 0
        ), f"pricing_models.calc_lp_in_given_tokens_out: ERROR: expected bond_reserves >= 0, not {bond_reserves}!"
        assert (
            share_buffer >= 0
        ), f"pricing_models.calc_lp_in_given_tokens_out: ERROR: expected share_buffer >= 0, not {share_buffer}!"
        assert (
            liquidity_pool >= 0
        ), f"pricing_models.calc_lp_in_given_tokens_out: ERROR: expected liquidity_pool >= 0, not {liquidity_pool}!"
        assert (
            rate >= 0
        ), f"pricing_models.calc_lp_in_given_tokens_out: ERROR: expected rate >= 0, not {rate}!"
        assert (
            1 > time_remaining >= 0
        ), f"pricing_models.calc_lp_in_given_tokens_out: ERROR: expected 1 > time_remaining >= 0, not {time_remaining}!"
        assert (
            stretched_time_remaining >= 0
        ), f"pricing_models.calc_lp_in_given_tokens_out: ERROR: expected stretched_time_remaining >= 0, not {stretched_time_remaining}!"
        assert share_price >= init_share_price >= 1, (
            "pricing_models.calc_lp_in_given_tokens_out: ERROR: expected share_price >= init_share_price >= 1, not"
        )
        r"""
        Computes the amount of LP tokens to be minted for a given amount of base asset
        
        .. math::

        y = \frac{(z - \Delta z)(\mu \cdot (\frac{1}{1 + r \cdot t(d)})^{\frac{1}{\tau(d_b)}} - c)}{2}

        """
        d_share_reserves = base_asset_out / share_price
        lp_in = d_share_reserves * liquidity_pool / (share_reserves - share_buffer)
        d_token_reserves = (share_reserves + d_share_reserves) / 2 * (
            init_share_price * (1 + rate * time_remaining) ** (1 / stretched_time_remaining) - share_price
        ) - bond_reserves
        return lp_in, base_asset_out, d_token_reserves

    def calc_tokens_out_given_lp_in(
        self,
        lp_in,
        share_reserves,
        bond_reserves,
        share_buffer,
        init_share_price,
        share_price,
        liquidity_pool,
        rate,
        time_remaining,
        stretched_time_remaining,
    ):
        assert (
            lp_in > 0
        ), f"pricing_models.calc_lp_out_given_tokens_in: ERROR: expected lp_in > 0, not {lp_in}!"
        assert (
            share_reserves > 0
        ), f"pricing_models.calc_lp_out_given_tokens_in: ERROR: expected share_reserves > 0, not {share_reserves}!"
        assert (
            bond_reserves >= 0
        ), f"pricing_models.calc_lp_out_given_tokens_in: ERROR: expected bond_reserves >= 0, not {bond_reserves}!"
        assert (
            share_buffer >= 0
        ), f"pricing_models.calc_lp_out_given_tokens_in: ERROR: expected share_buffer >= 0, not {share_buffer}!"
        assert (
            liquidity_pool >= 0
        ), f"pricing_models.calc_lp_out_given_tokens_in: ERROR: expected liquidity_pool >= 0, not {liquidity_pool}!"
        assert (
            rate >= 0
        ), f"pricing_models.calc_lp_out_given_tokens_in: ERROR: expected rate >= 0, not {rate}!"
        assert (
            1 > time_remaining >= 0
        ), f"pricing_models.calc_lp_out_given_tokens_in: ERROR: expected 1 > time_remaining >= 0, not {time_remaining}!"
        assert (
            stretched_time_remaining >= 0
        ), f"pricing_models.calc_lp_out_given_tokens_in: ERROR: expected stretched_time_remaining >= 0, not {stretched_time_remaining}!"
        assert share_price >= init_share_price >= 1, (
            "pricing_models.calc_lp_out_given_tokens_in: ERROR: expected share_price >= init_share_price >= 1, not"
        )
        if self.verbose:
            print(f"  inputs: lp_in={lp_in}, share_reserves={share_reserves}, bond_reserves={bond_reserves}, share_buffer={share_buffer}, init_share_price={init_share_price}, share_price={share_price}, liquidity_pool={liquidity_pool}, rate={rate}, time_remaining={time_remaining}, stretched_time_remaining={stretched_time_remaining}")
        d_base_reserves = share_price * (share_reserves - share_buffer) * lp_in / liquidity_pool
        d_share_reserves = d_base_reserves / share_price
        if self.verbose:
            print(f"  d_share_reserves={d_share_reserves} (d_base_reserves / share_price = {d_base_reserves} / {share_price})")
        d_token_reserves = (share_reserves + d_share_reserves) / 2 * (
            init_share_price * (1 + rate * time_remaining) ** (1 / stretched_time_remaining) - share_price
        ) - bond_reserves
        if self.verbose:
            print(f"  d_token_reserves={d_token_reserves} ((share_reserves + d_share_reserves) / 2 * (init_share_price * (1 + rate * time_remaining) ** (1 / stretched_time_remaining) - share_price) - bond_reserves = ({share_reserves} + {d_share_reserves}) / 2 * ({init_share_price} * (1 + {rate} * {time_remaining}) ** (1 / {stretched_time_remaining}) - {share_price}) - {bond_reserves})")
        return lp_in, d_base_reserves, d_token_reserves

    def calc_in_given_out(
        self,
        out,
        share_reserves,
        bond_reserves,
        token_in,
        fee_percent,
        time_remaining,
        init_share_price,
        share_price,
    ):
        r"""
        Calculates the amount of an asset that must be provided to receive a
        specified amount of the other asset given the current AMM reserves.

        The input is calculated as:

        .. math::
            in' =
            \begin{cases}
            c (\frac{1}{\mu} (\frac{k - (2y + cz - \Delta y)^{1-t}}{\frac{c}{\mu}})^{\frac{1}{1-t}} - z),
            &\text{ if } token\_in = \text{"base"} \\
            (k - \frac{c}{\mu} (\mu * (z - \Delta z))^{1 - t})^{\frac{1}{1 - t}} - (2y + cz),
            &\text{ if } token\_in = \text{"pt"}
            \end{cases} \\
            f =
            \begin{cases}
            (1 - \frac{1}{(\frac{2y + cz}{\mu z})^{\tau}}) \phi \Delta y, &\text{ if } token\_in = \text{"base"} \\
            (\frac{2y + cz}{\mu z})^{\tau} - 1) \phi (c \Delta z), &\text{ if } token\_in = \text{"pt"}
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
        assert share_price >= init_share_price >= 1, (
            f"pricing_models.calc_in_given_out: ERROR:"
            f" expected share_price >= init_share_price >= 1, not share_price={share_price}"
            f" and init_share_price={init_share_price}!"
        )
        # TODO: Break this function up to use private class functions
        # pylint: disable=too-many-locals
        time_elapsed = 1 - time_remaining
        scale = share_price / init_share_price
        total_reserves = share_price * share_reserves + bond_reserves
        spot_price = self.calc_spot_price_from_reserves(
            share_reserves=share_reserves,
            bond_reserves=bond_reserves,
            init_share_price=init_share_price,
            share_price=share_price,
            time_remaining=time_remaining,
        )
        # We precompute the YieldSpace constant k using the current reserves and
        # share price:
        #
        # k = (c / μ) * (μ * z)**(1 - τ) + (2y + cz)**(1 - τ)
        k = price_utils.calc_k_const(share_reserves, bond_reserves, share_price, init_share_price, time_elapsed)
        if token_in == "base":
            in_reserves = share_reserves
            out_reserves = bond_reserves + total_reserves
            d_bonds = out
            # The amount the user pays without fees or slippage is simply
            # the amount of bonds the user would receive times the spot price of
            # base in terms of bonds. If we let p be the conventional spot price,
            # then we can write this as:
            #
            # without_fee_or_slippage = p * d_y
            without_fee_or_slippage = spot_price * d_bonds
            # We solve the YieldSpace invariant for the base paid for the
            # requested amount of bonds. We set up the invariant where the user
            # pays d_z' shares and receives d_y bonds:
            #
            # (c / μ) * (μ * (z + d_z'))**(1 - t) + (2y + cz - d_y)**(1 - t) = k
            #
            # Solving for d_z' gives us the amount of shares the user pays
            # without including fees:
            #
            # d_z' = (1 / μ) * ((k - (2y + cz - d_y)**(1 - t)) / (c / μ))**(1 / (1 - t)) - z
            #
            # We really want to know the value of d_x', the amount of base the
            # user pays. This is given by d_x' = c * d_z'.
            #
            # without_fee = d_x'
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
            # fee = (1 - p) * φ * d_y
            fee = (1 - spot_price) * fee_percent * d_bonds
        elif token_in == "pt":
            in_reserves = bond_reserves + total_reserves
            out_reserves = share_reserves
            d_shares = out / share_price
            # The amount the user pays without fees or slippage is simply the
            # amount of base the user would receive times the inverse of the
            # spot price of base in terms of bonds. The amount of base the user
            # receives is given by c * d_z where d_z is the number of shares the
            # pool will need to unwrap to give the user their base. If we let p
            # be the conventional spot price, then we can write this as:
            #
            # without_fee_or_slippage = (1 / p) * c * d_z
            without_fee_or_slippage = (1 / spot_price) * share_price * d_shares
            # We solve the YieldSpace invariant for the bonds paid to receive
            # the requested amount of base. We set up the invariant where the
            # user pays d_y' bonds and receives d_z shares:
            #
            # (c / μ) * (μ * (z - d_z))**(1 - τ) + (2y + cz + d_y')**(1 - τ) = k
            #
            # Solving for d_y' gives us the amount of bonds the user must pay
            # without including fees:
            #
            # d_y' = (k - (c / μ) * (μ * (z - d_z))**(1 - τ))**(1 / (1 - τ)) - (2y + cz)
            #
            # without_fee = d_y'
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
            # fee = ((1 / p) - 1) * φ * c * d_z
            print(f"fee = ((1 / spot_price) - 1) * fee_percent * share_price * d_shares = "
                +f"((1 / {spot_price}) - 1) * {fee_percent} * {share_price} * {d_shares}"
                +f"{((1 / spot_price) - 1) * fee_percent * share_price * d_shares}"
            )
            fee = ((1 / spot_price) - 1) * fee_percent * share_price * d_shares
        else:
            raise AssertionError(
                f"pricing_models.calc_in_given_out: ERROR: "
                f'expected token_in to be "base" or "pt", not {token_in}!'
            )
        # To get the amount paid with fees, add the fee to the calculation that
        # excluded fees. Adding the fees results in more tokens paid, which
        # indicates that the fees are working correctly.
        with_fee = without_fee + fee
        assert fee >= 0, (
            "pricing_models.calc_in_given_out: ERROR: Fee should not be negative!"
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
        # check without_fee since without_fee_or_slippage will always be a positive
        # float due to the constraints on the inputs, with_fee = without_fee + fee
        # so it is a positive float if without_fee and fee are positive floats, and
        # fee is a positive float due to the constraints on the inputs.
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
        assert isinstance(without_fee, float), (
            f"pricing_models.calc_in_given_out: ERROR: without_fee should be a float, not {type(without_fee)}!"
            f"\n\tout={out}\n\tshare_reserves={share_reserves}\n\tbond_reserves={bond_reserves}"
            f"\n\ttotal_reserves={total_reserves}\n\tinit_share_price={init_share_price}"
            f"\n\tshare_price={share_price}\n\tscale={scale}\n\tfee_percent={fee_percent}"
            f"\n\ttime_remaining={time_remaining}\n\ttime_elapsed={time_elapsed}"
            f"\n\tin_reserves={in_reserves}\n\tout_reserves={out_reserves}\n\ttoken_in={token_in}"
            f"\n\tspot_price={spot_price}\n\tk={k}\n\twithout_fee_or_slippage={without_fee_or_slippage}"
            f"\n\twithout_fee={without_fee}\n\tfee={fee}"
        )
        assert without_fee >= 0, (
            f"pricing_models.calc_in_given_out: ERROR: without_fee should be non-negative, not {without_fee}!"
            f"\n\tout={out}\n\tshare_reserves={share_reserves}\n\tbond_reserves={bond_reserves}"
            f"\n\ttotal_reserves={total_reserves}\n\tinit_share_price={init_share_price}"
            f"\n\tshare_price={share_price}\n\tscale={scale}\n\tfee_percent={fee_percent}"
            f"\n\ttime_remaining={time_remaining}\n\ttime_elapsed={time_elapsed}"
            f"\n\tin_reserves={in_reserves}\n\tout_reserves={out_reserves}\n\ttoken_in={token_in}"
            f"\n\tspot_price={spot_price}\n\tk={k}\n\twithout_fee_or_slippage={without_fee_or_slippage}"
            f"\n\twithout_fee={without_fee}\n\tfee={fee}"
        )

        return (without_fee_or_slippage, with_fee, without_fee, fee)

    # TODO: The high slippage tests in tests/test_pricing_model.py should
    # arguably have much higher slippage. This is something we should
    # consider more when thinking about the use of a time stretch parameter.
    def calc_out_given_in(
        self,
        in_,
        share_reserves,
        bond_reserves,
        token_out,
        fee_percent,
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
            c (z - \frac{1}{\mu} (\frac{k - (2y + cz + \Delta y)^{1 - t}}{\frac{c}{\mu}})^{\frac{1}{1 - t}}),
            &\text{ if } token\_out = \text{"base"} \\
            2y + cz - (k - \frac{c}{\mu} (\mu (z + \Delta z))^{1 - t})^{\frac{1}{1 - t}},
            &\text{ if } token\_out = \text{"pt"}
            \end{cases} \\
            f = 
            \begin{cases}
            (1 - \frac{1}{(\frac{2y + cz}{\mu z})^{\tau}}) \phi \Delta y, &\text{ if } token\_out = \text{"base"} \\
            (\frac{2y + cz}{\mu z})^{\tau} - 1) \phi (c \Delta z), &\text{ if } token\_out = \text{"pt"}
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
            share_reserves >= 0
        ), f"pricing_models.calc_out_given_in: ERROR: expected share_reserves >= 0, not {share_reserves}!"
        assert (
            bond_reserves >= 0
        ), f"pricing_models.calc_out_given_in: ERROR: expected bond_reserves >= 0, not {bond_reserves}!"
        assert (
            1 >= fee_percent >= 0
        ), f"pricing_models.calc_out_given_in: ERROR: expected 1 >= fee_percent >= 0, not {fee_percent}!"
        assert (
            1 > time_remaining >= 0
        ), f"pricing_models.calc_out_given_in: ERROR: expected 1 > time_remaining >= 0, not {time_remaining}!"
        assert share_price >= init_share_price >= 1, (
            "pricing_models.calc_out_given_in: ERROR: expected share_price >= init_share_price >= 1, not"
            f" share_price={share_price} and init_share_price={init_share_price}!"
        )

        # TODO: Break this function up to use private class functions
        # pylint: disable=too-many-locals
        scale = share_price / init_share_price
        time_elapsed = 1 - time_remaining
        total_reserves = share_price * share_reserves + bond_reserves
        spot_price = self.calc_spot_price_from_reserves(
            share_reserves=share_reserves,
            bond_reserves=bond_reserves,
            init_share_price=init_share_price,
            share_price=share_price,
            time_remaining=time_remaining
        )
        # We precompute the YieldSpace constant k using the current reserves and
        # share price:
        #
        k = price_utils.calc_k_const(share_reserves, bond_reserves, share_price, init_share_price, time_elapsed)
        if token_out == "base":
            d_bonds = in_  # PTs passed in
            in_reserves = bond_reserves + total_reserves  # add virtual liquidity
            out_reserves = share_reserves
            # The amount the user would receive without fees or slippage is the
            # amount of bonds the user pays times the spot price of base in
            # terms of bonds. If we let p be the conventional spot price, then
            # we can write this as:
            #
            # p * d_y
            without_fee_or_slippage = spot_price * d_bonds
            # We solve the YieldSpace invariant for the base received from
            # selling the specified amount of bonds. We set up the invariant
            # where the user pays d_y bonds and receives d_z' shares:
            #
            # (c / μ) * (μ * (z - d_z'))**(1 - τ) + (2y + cz + d_y)**(1 - τ) = k
            #
            # Solving for d_z' gives us the amount of shares the user receives
            # without fees:
            #
            # d_z' = z - (1 / μ) * ((k - (2y + cz + d_y)**(1 - τ)) / (c / μ))**(1 / (1 - τ))
            #
            # We really want to know the value of d_x', the amount of base the
            # user receives without fees. This is given by d_x' = c * d_z'.
            #
            # without_fee = d_x'
            without_fee = (
                share_reserves
                - (1 / init_share_price) * ((k - (in_reserves + d_bonds) ** time_elapsed) / scale) ** (1 / time_elapsed)
            ) * share_price
            # The fees are calculated as the difference between the bonds paid
            # and the base received without slippage times the fee percentage.
            # This can also be expressed as:
            #
            # fee = (1 - p) * φ * d_y
            fee = (1 - spot_price) * fee_percent * d_bonds
            with_fee = without_fee - fee
        elif token_out == "pt":
            d_shares = in_ / share_price  # convert from base_asset to z (x=cz)
            in_reserves = share_reserves
            out_reserves = bond_reserves + total_reserves
            # The amount the user would receive without fees or slippage is
            # the amount of base the user pays times inverse of the spot price
            # of base in terms of bonds. If we let p be the conventional spot
            # price, then we can write this as:
            #
            # (1 / p) * c * d_z
            without_fee_or_slippage = (1 / spot_price) * share_price * d_shares
            # We solve the YieldSpace invariant for the bonds received from
            # paying the specified amount of base. We set up the invariant where
            # the user pays d_z shares and receives d_y' bonds:
            #
            # (c / μ) * (μ * (z + d_z))**(1 - τ) + (2y + cz - d_y')**(1 - τ) = k
            #
            # Solving for d_y' gives us the amount of bonds the user receives
            # without including fees:
            #
            # d_y' = 2y + cz - (k - (c / μ) * (μ * (z + d_z))**(1 - τ))**(1 / (1 - τ))
            without_fee = out_reserves - pow(
                k - scale * pow(init_share_price * (in_reserves + d_shares), time_elapsed), 1 / time_elapsed
            )
            # The fees are calculated as the difference between the bonds
            # received without slippage and the base paid times the fee
            # percentage. This can also be expressed as:
            #
            # ((1 / p) - 1) * φ * c * d_z
            fee = ((1 / spot_price) - 1) * fee_percent * share_price * d_shares
        else:
            raise AssertionError(
                f'pricing_models.calc_out_given_in: ERROR: expected token_out to be "base" or "pt", not {token_out}!'
            )
        # To get the amount paid with fees, subtract the fee from the
        # calculation that excluded fees. Subtracting the fees results in less
        # tokens received, which indicates that the fees are working correctly.
        with_fee = without_fee - fee

        # TODO(jalextowle): With some analysis, it seems possible to show that
        # we skip straight from non-negative reals to the complex plane without
        # hitting negative reals.
        #
        # Ensure that the outputs are all non-negative floats. We only need to
        # check with_fee since without_fee_or_slippage will always be a positive
        # float due to the constraints on the inputs, without_fee = with_fee + fee
        # so it is a positive float if with_fee and fee are positive floats, and
        # fee is a positive float due to the constraints on the inputs.
        assert fee >= 0, (
            f"pricing_models.calc_out_given_in: ERROR: Fee should not be negative!"
            f"\n\tin_={in_}\n\tshare_reserves={share_reserves}\n\tbond_reserves={bond_reserves}"
            f"\n\ttotal_reserves={total_reserves}\n\tinit_share_price={init_share_price}"
            f"\n\tshare_price={share_price}\n\tscale={scale}\n\tfee_percent={fee_percent}"
            f"\n\ttime_remaining={time_remaining}\n\ttime_elapsed={time_elapsed}"
            f"\n\tin_reserves={in_reserves}\n\tout_reserves={out_reserves}\n\ttoken_out={token_out}"
            f"\n\tspot_price={spot_price}\n\tk={k}\n\twithout_fee_or_slippage={without_fee_or_slippage}"
            f"\n\twithout_fee={without_fee}\n\tfee={fee}"
        )
        assert isinstance(with_fee, float), (
            f"pricing_models.calc_out_given_in: ERROR: with_fee should be a float, not {type(with_fee)}!"
            f"\n\tin_={in_}\n\tshare_reserves={share_reserves}\n\tbond_reserves={bond_reserves}"
            f"\n\ttotal_reserves={total_reserves}\n\tinit_share_price={init_share_price}"
            f"\n\tshare_price={share_price}\n\tscale={scale}\n\tfee_percent={fee_percent}"
            f"\n\ttime_remaining={time_remaining}\n\ttime_elapsed={time_elapsed}"
            f"\n\tin_reserves={in_reserves}\n\tout_reserves={out_reserves}\n\ttoken_out={token_out}"
            f"\n\tspot_price={spot_price}\n\tk={k}\n\twithout_fee_or_slippage={without_fee_or_slippage}"
            f"\n\twithout_fee={without_fee}\n\tfee={fee}"
        )
        assert with_fee >= 0, (
            f"pricing_models.calc_out_given_in: ERROR: with_fee should be non-negative, not {with_fee}!"
            f"\n\tin_={in_}\n\tshare_reserves={share_reserves}\n\tbond_reserves={bond_reserves}"
            f"\n\ttotal_reserves={total_reserves}\n\tinit_share_price={init_share_price}"
            f"\n\tshare_price={share_price}\n\tscale={scale}\n\tfee_percent={fee_percent}"
            f"\n\ttime_remaining={time_remaining}\n\ttime_elapsed={time_elapsed}"
            f"\n\tin_reserves={in_reserves}\n\tout_reserves={out_reserves}\n\ttoken_out={token_out}"
            f"\n\tspot_price={spot_price}\n\tk={k}\n\twithout_fee_or_slippage={without_fee_or_slippage}"
            f"\n\twithout_fee={without_fee}\n\tfee={fee}"
        )

        return (without_fee_or_slippage, with_fee, without_fee, fee)

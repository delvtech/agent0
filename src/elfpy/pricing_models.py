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


# TODO: Update the docstring comments
#
# FIXME: Consider giving these error messages a special signature so they aren't
#        identical to the error messages for the other pricing models.
class ElementPricingModel(PricingModel):
    """
    Element v1 pricing model

    Does not use the Yield Bearing Vault `init_share_price` (mu) and `share_price` (c) variables.
    """

    # FIXME: This should have v1 in the name
    def model_name(self):
        return "Element"

    # FIXME: Add assertions on the inputs and outputs
    #
    # FIXME: Improve the documentation of this function.
    #
    # FIXME: Do we need to add virtual reserve accounting to this function?
    def calc_in_given_out(
        self,
        out,
        base_reserves,
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
            (\frac{k - (2y + x - \Delta y)^{1-t}})^{\frac{1}{1-t}} - x, &\text{ if } token\_in = \text{"base"} \\
            (k - (x - \Delta x)^{1 - t})^{\frac{1}{1 - t}} - (2y + x), &\text{ if } token\_in = \text{"pt"}
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
        base_reserves : float
            The reserves of base in the pool.
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
            base_reserves > 0
        ), f"pricing_models.calc_in_given_out: ERROR: expected base_reserves > 0, not {base_reserves}!"
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
        bond_reserves_ = 2 * bond_reserves + base_reserves
        spot_price = price_utils.calc_spot_price_from_reserves(base_reserves, bond_reserves, time_remaining)
        # We precompute the YieldSpace constant k using the current reserves and
        # share price:
        #
        # k = x**(1 - t) + (2y + x)**(1 - t)
        k = price_utils.calc_k_const(base_reserves, bond_reserves, share_price, init_share_price, time_elapsed)
        # Solve for the amount of token that must be paid to receive the
        # specified amount of the output token.
        if token_in == "base":
            d_bonds = out
            # The amount the user pays without fees or slippage is the amount of
            # bonds the user would receive times the spot price of base in terms
            # of bonds. If we let p be the conventional spot price, then we can
            # write this as:
            #
            # without_fee_or_slippage = p * d_y
            without_fee_or_slippage = spot_price * d_bonds
            # We solve the YieldSpace invariant for the base required to
            # purchase the requested amount of bonds. We set up the invariant
            # where the user pays d_x base and receives d_y bonds:
            #
            # (x + d_x')**(1 - t) + (2y + x - d_y)**(1 - t) = k
            #
            # Solving for d_x' gives us the amount of base the user must pay
            # without including fees:
            #
            # d_x' = (k - (2y + x - d_y)**(1 - t))**(1 / (1 - t)) - x
            #
            # without_fee = d_x'
            without_fee = (k - (bond_reserves_ - d_bonds) ** time_elapsed) ** (1 / time_elapsed) - base_reserves
            # The fees are calculated as the difference between the bonds
            # received and the base paid without fees times the fee percentage.
            # This can also be expressed as:
            #
            # fee = phi * (d_y - d_x')
            fee = fee_percent * (d_bonds - without_fee)
        elif token_in == "pt":
            # The amount the user pays without fees or slippage is the amount of
            # bonds the user would receive times the inverse of the spot price
            # of base in terms of bonds. If we let p be the conventional spot
            # price, then we can write this as:
            #
            # without_fee_or_slippage = (1 / p) * d_x
            without_fee_or_slippage = (1 / spot_price) * out
            # We solve the YieldSpace invariant for the bonds required to
            # purchase the requested amount of bbase. We set up the invariant
            # where the user pays d_x base and receives d_y bonds:
            #
            # (x - d_x)**(1 - t) + (2y + x + d_y')**(1 - t) = k
            #
            # Solving for d_y' gives us the amount of base the user must pay
            # without including fees:
            #
            # d_y' = (k - (x - d_x)**(1 - t))**(1 / (1 - t)) - (2y + x)
            #
            # without_fee = d_y'
            without_fee = (k - (base_reserves - out) ** time_elapsed) ** (1 / time_elapsed) - bond_reserves_
            # The fees are calculated as the difference between the bonds
            # paid without fees and the base received times the fee percentage.
            # This can also be expressed as:
            #
            # fee = phi * (d_y' - d_x)
            fee = fee_percent * (without_fee - out)
        else:
            raise AssertionError(
                f'pricing_models.calc_in_given_out: ERROR: expected token_in == "base" or token_in == "pt", not {token_in}!'
            )
        # To get the amount paid with fees, add the fee to the calculation that
        # excluded fees. Adding the fees results in more tokens paid, which
        # indicates that the fees are working correctly.
        with_fee = without_fee + fee
        return (without_fee_or_slippage, with_fee, without_fee, fee)

    # FIXME: Add assertions on the inputs and outputs
    #
    # FIXME: Improve the documentation of this function.
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
        k = price_utils.calc_k_const(share_reserves, bond_reserves, share_price, init_share_price, time_elapsed)
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
        # TODO: add back in with proper logging
        # print(
        #     f"pricing_models.calc_out_given_in:"
        #     f"\n\tin_ = {in_}\n\tshare_reserves = {share_reserves}\n\tbond_reserves = {bond_reserves}"
        #     f"\n\ttotal_reserves = {total_reserves}\n\tinit_share_price = {init_share_price}"
        #     f"\n\tshare_price = {share_price}\n\tscale = {scale}\n\tfee_percent = {fee_percent}"
        #     f"\n\ttime_remaining = {time_remaining}\n\ttime_elapsed = {time_elapsed}"
        #     f"\n\tin_reserves = {in_reserves}\n\tout_reserves = {out_reserves}\n\ttoken_out = {token_out}"
        #     f"\n\tspot_price = {spot_price}\n\tk = {k}\n\twithout_fee_or_slippage = {without_fee_or_slippage}"
        #     f"\n\twithout_fee = {without_fee}\n\twith_fee = {with_fee}\n\tfee = {fee}"
        # )

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

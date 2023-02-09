"""The base pricing model"""
from __future__ import annotations  # types will be strings by default in 3.11

from abc import ABC
import copy
import decimal
from decimal import Decimal

from elfpy.types import (
    MAX_RESERVES_DIFFERENCE,
    WEI,
    MarketDeltas,
    Quantity,
    MarketState,
    StretchedTime,
    TokenType,
    TradeResult,
)
import elfpy.utils.price as price_utils

# Set the Decimal precision to be higher than the default of 28. This ensures
# that the pricing models can safely a lowest possible input of 1e-18 with an
# reserves difference of up to 20 billion.
decimal.getcontext().prec = 30


class PricingModel(ABC):
    """Contains functions for calculating AMM variables

    Base class should not be instantiated on its own; it is assumed that a user will instantiate a child class
    """

    def calc_in_given_out(
        self,
        out: Quantity,
        market_state: MarketState,
        time_remaining: StretchedTime,
    ) -> TradeResult:
        """Calculate fees and asset quantity adjustments"""
        raise NotImplementedError

    def calc_out_given_in(
        self,
        in_: Quantity,
        market_state: MarketState,
        time_remaining: StretchedTime,
    ) -> TradeResult:
        """Calculate fees and asset quantity adjustments"""
        raise NotImplementedError

    def calc_lp_out_given_tokens_in(
        self,
        d_base: float,
        rate: float,
        market_state: MarketState,
        time_remaining: StretchedTime,
    ) -> tuple[float, float, float]:
        """Computes the amount of LP tokens to be minted for a given amount of base asset"""
        raise NotImplementedError

    def calc_lp_in_given_tokens_out(
        self,
        d_base: float,
        rate: float,
        market_state: MarketState,
        time_remaining: StretchedTime,
    ) -> tuple[float, float, float]:
        """Computes the amount of LP tokens to be minted for a given amount of base asset"""
        raise NotImplementedError

    def calc_tokens_out_given_lp_in(
        self,
        lp_in: float,
        rate: float,
        market_state: MarketState,
        time_remaining: StretchedTime,
    ) -> tuple[float, float, float]:
        """Calculate how many tokens should be returned for a given lp addition"""
        raise NotImplementedError

    def model_name(self) -> str:
        """Unique name given to the model, can be based on member variable states"""
        raise NotImplementedError

    def model_type(self) -> str:
        """Unique identifier given to the model, should be lower snake_cased name"""
        raise NotImplementedError

    def _calc_k_const(self, market_state: MarketState, time_remaining: StretchedTime) -> Decimal:
        """Returns the 'k' constant variable for trade mathematics"""
        raise NotImplementedError

    def calc_bond_reserves(
        self,
        target_apr: float,
        time_remaining: StretchedTime,
        market_state: MarketState,
    ):
        """Returns the assumed bond (i.e. token asset) reserve amounts given
        the share (i.e. base asset) reserves and APR

        Parameters
        ----------
        target_apr : float
            Target fixed APR in decimal units (for example, 5% APR would be 0.05)
        time_remaining : StretchedTime
            Amount of time left until bond maturity
        market_state : MarketState
            MarketState object; the following attributes are used:
                share_reserves : float
                    Base asset reserves in the pool
                init_share_price : float
                    Original share price when the pool started
                share_price : float
                    Current share price

        Returns
        -------
        float
            The expected amount of bonds (token asset) in the pool, given the inputs

        .. todo:: TODO: Write a test for this function
        """
        bond_reserves = (market_state.share_reserves / 2) * (
            market_state.init_share_price
            * (1 + target_apr * time_remaining.normalized_time) ** (1 / time_remaining.stretched_time)
            - market_state.share_price
        )  # y = z/2 * (mu * (1 + rt)**(1/tau) - c)
        return bond_reserves

    def calc_share_reserves(
        self,
        target_apr: float,
        bond_reserves: float,
        time_remaining: StretchedTime,
        init_share_price: float = 1,
    ):
        """Returns the assumed share (i.e. base asset) reserve amounts given
        the bond (i.e. token asset) reserves and APR

        Parameters
        ----------
        target_apr : float
            Target fixed APR in decimal units (for example, 5% APR would be 0.05)
        bond_reserves : float
            Token asset (pt) reserves in the pool
        days_remaining : float
            Amount of days left until bond maturity
        time_stretch : float
            Time stretch parameter, in years
        init_share_price : float
            Original share price when the pool started
        share_price : float
            Current share price

        Returns
        -------
        float
            The expected amount of base asset in the pool, calculated from the provided parameters

        """
        # TODO: Write a test for this function
        share_reserves = bond_reserves / (
            init_share_price * (1 - target_apr * time_remaining.normalized_time) ** (1 / time_remaining.stretched_time)
        )  # z = y / (mu * (1 - rt)**(1/tau))
        return share_reserves

    def calc_liquidity(
        self,
        market_state: MarketState,
        target_liquidity: float,
        target_apr: float,
        # TODO: Fields like position_duration and fee_percent could arguably be
        # wrapped up into a "MarketContext" value that includes the state as
        # one of its fields.
        position_duration: StretchedTime,
    ) -> tuple[float, float]:
        """Returns the reserve volumes and total supply

        The scaling factor ensures bond_reserves and share_reserves add
        up to target_liquidity, while keeping their ratio constant (preserves apr).

        total_liquidity = in base terms, used to target liquidity as passed in
        total_reserves  = in arbitrary units (AU), used for yieldspace math

        Parameters
        ----------
        market_state : MarketState
            The state of the market
        target_liquidity_usd : float
            Amount of liquidity that the simulation is trying to achieve in a given market
        target_apr : float
            Desired APR for the seeded market
        position_duration : StretchedTime
            The duration of bond positions in this market

        Returns
        -------
        (float, float)
            Tuple that contains (share_reserves, bond_reserves)
            calculated from the provided parameters
        """
        share_reserves = target_liquidity / market_state.share_price
        # guarantees only that it hits target_apr
        bond_reserves = self.calc_bond_reserves(
            target_apr=target_apr,
            time_remaining=position_duration,
            market_state=MarketState(
                share_reserves=share_reserves,
                init_share_price=market_state.init_share_price,
                share_price=market_state.share_price,
            ),
        )
        total_liquidity = self.calc_total_liquidity_from_reserves_and_price(
            MarketState(
                share_reserves=share_reserves,
                bond_reserves=bond_reserves,
                base_buffer=market_state.base_buffer,
                bond_buffer=market_state.bond_buffer,
                lp_reserves=market_state.lp_reserves,
                share_price=market_state.share_price,
                init_share_price=market_state.init_share_price,
            ),
            market_state.share_price,
        )
        # compute scaling factor to adjust reserves so that they match the target liquidity
        scaling_factor = target_liquidity / total_liquidity  # both in token units
        # update variables by rescaling the original estimates
        bond_reserves = bond_reserves * scaling_factor
        share_reserves = share_reserves * scaling_factor
        return share_reserves, bond_reserves

    def calc_total_liquidity_from_reserves_and_price(self, market_state: MarketState, share_price: float) -> float:
        """Returns the total liquidity in the pool in terms of base

        Parameters
        ----------
        MarketState : MarketState
            The following member variables are used:
                share_reserves : float
                    Base asset reserves in the pool
                bond_reserves : float
                    Token asset (pt) reserves in the pool
        share_price : float
            Variable (underlying) yield source price

        Returns
        -------
        float
            Total liquidity in the pool in terms of base, calculated from the provided parameters

        .. todo:: TODO: Write a test for this function
        """
        return market_state.share_reserves * share_price

    def calc_spot_price_from_reserves(
        self,
        market_state: MarketState,
        time_remaining: StretchedTime,
    ) -> float:
        r"""
        Calculates the spot price of base in terms of bonds.

        The spot price is defined as:

        .. math::
            \begin{align}
            p = (\frac{2y + cz}{\mu z})^{-\tau}
            \end{align}

        Parameters
        ----------
        market_state: MarketState
            The reserves and share prices of the pool.
        time_remaining : StretchedTime
            The time remaining for the asset (uses time stretch).

        Returns
        -------
        float
            The spot price of principal tokens.
        """
        return float(
            self._calc_spot_price_from_reserves_high_precision(market_state=market_state, time_remaining=time_remaining)
        )

    def _calc_spot_price_from_reserves_high_precision(
        self,
        market_state: MarketState,
        time_remaining: StretchedTime,
    ) -> Decimal:
        r"""
        Calculates the current market spot price of base in terms of bonds.
        This variant returns the result in a high precision format.

        The spot price is defined as:

        .. math::
            \begin{align}
            p = (\frac{2y + cz}{\mu z})^{-\tau}
            \end{align}

        Parameters
        ----------
        market_state: MarketState
            The reserves and share prices of the pool.
        time_remaining : StretchedTime
            The time remaining for the asset (incorporates time stretch).

        Returns
        -------
        Decimal
            The spot price of principal tokens.
        """
        # TODO: in general s != y + c*z, we'll want to update this to have s = lp_reserves
        # s = y + c*z
        total_reserves = Decimal(market_state.bond_reserves) + Decimal(market_state.share_price) * Decimal(
            market_state.share_reserves
        )
        # p = ((y + s)/(mu*z))^(-tau) = ((2y + cz)/(mu*z))^(-tau)
        spot_price = (
            (Decimal(market_state.bond_reserves) + total_reserves)
            / (Decimal(market_state.init_share_price) * Decimal(market_state.share_reserves))
        ) ** Decimal(-time_remaining.stretched_time)
        return spot_price

    def calc_apr_from_reserves(
        self,
        market_state: MarketState,
        time_remaining: StretchedTime,
    ) -> float:
        r"""Returns the apr given reserve amounts

        Parameters
        ----------
        market_state : MarketState
            The reserves and share prices of the pool
        time_remaining : StretchedTime
            The expiry time for the asset
        """
        spot_price = self.calc_spot_price_from_reserves(
            market_state,
            time_remaining,
        )
        apr = price_utils.calc_apr_from_spot_price(spot_price, time_remaining)
        return apr

    def get_max_long(
        self,
        market_state: MarketState,
        time_remaining: StretchedTime,
    ) -> tuple[float, float]:
        r"""
        Calculates the maximum long the market can support using the bisection
        method.

        Parameters
        ----------
        market_state : MarketState
            The reserves and share prices of the pool
        fee_percent : float
            The fee percent charged by the market
        time_remaining : StretchedTime
            The time remaining for the asset (incorporates time stretch)

        Returns
        -------
        float
            The maximum amount of base that can be used to purchase bonds

        .. todo:: This needs to be tested more rigorously.
            Some of these conditionals seem unnecessary.
            If they aren't document why they aren't.
            Otherwise, remove them.
        """
        available_bonds = market_state.bond_reserves - market_state.bond_buffer
        if available_bonds <= 0:
            return 0, 0
        last_maybe_max_long = 0, 0
        bond_percent = 1
        num_iters = 25
        for step_size in [1 / (2 ** (x + 1)) for x in range(num_iters)]:
            # Compute the amount of base needed to purchase the specified amount
            # of bonds.
            trade_result = self.calc_in_given_out(
                out=Quantity(amount=available_bonds * bond_percent, unit=TokenType.PT),
                market_state=market_state,
                time_remaining=time_remaining,
            )
            maybe_max_long = trade_result.breakdown.with_fee

            # If the max long is less than or equal to zero, we need to reduce
            # the amount of bonds that we are attempting to purchase. Otherwise,
            # go through the other checks for the bisection.
            if maybe_max_long <= 0:
                bond_percent -= step_size
            else:
                # TODO: Do we actually need to do this? Run some tests and see
                # if the result that only uses calc_in_given_out is always
                # slightly lower. If so, then just take that.
                #
                # Compute the amount of bonds that will be purchased with the
                # amount of base. We feed the result of calc_in_given_out back
                # into the pricing model as this computation is more accurate.
                trade_result = self.calc_out_given_in(
                    in_=Quantity(amount=maybe_max_long, unit=TokenType.BASE),
                    market_state=market_state,
                    time_remaining=time_remaining,
                )
                d_bonds = trade_result.breakdown.with_fee

                # Apply the trade to the market state.
                market_state_post_trade = copy.copy(market_state)
                market_state_post_trade.apply_delta(
                    delta=MarketDeltas(
                        d_base_asset=trade_result.market_result.d_base,
                        d_token_asset=trade_result.market_result.d_bonds,
                        d_base_buffer=d_bonds,
                    )
                )

                # Verify that none of the reserve invariants were broken. If
                # the invariants were broken, reduce the bond size. Otherwise,
                # we've found a new max long amount, so we store that value and
                # proceed with bisection with larger bond purchases.
                if (
                    market_state.bond_reserves < d_bonds
                    or self.calc_apr_from_reserves(market_state=market_state_post_trade, time_remaining=time_remaining)
                    < 0
                    or market_state_post_trade.share_price * market_state_post_trade.share_reserves
                    < market_state_post_trade.base_buffer
                    or market_state_post_trade.bond_reserves < market_state_post_trade.bond_buffer
                ):
                    bond_percent -= step_size
                else:
                    last_maybe_max_long = (maybe_max_long, d_bonds)
                    if bond_percent == 1:
                        return last_maybe_max_long
                    bond_percent += step_size

        return last_maybe_max_long

    def get_max_short(
        self,
        market_state: MarketState,
        time_remaining: StretchedTime,
    ) -> tuple[float, float]:
        r"""
        Calculates the maximum short the market can support using the bisection
        method.

        Parameters
        ----------
        market_state : MarketState
            The reserves and share prices of the pool.
        fee_percent : float
            The fee percent charged by the market.
        time_remaining : StretchedTime
            The time remaining for the asset (incorporates time stretch).

        Returns
        -------
        float
            The maximum amount of base that can be used to short bonds.
        float
            The maximum amount of bonds that can be shorted.
        """
        available_bonds = market_state.bond_reserves - market_state.bond_buffer
        if available_bonds <= 0:
            return 0, 0

        last_maybe_max_short = 0, 0
        bond_percent = 1
        num_iters = 25
        for step_size in [1 / (2 ** (x + 1)) for x in range(num_iters)]:
            try:
                # Compute the amount of base returned by selling the specified
                # amount of bonds.
                maybe_max_short_bonds = available_bonds * bond_percent
                trade_result = self.calc_out_given_in(
                    in_=Quantity(amount=maybe_max_short_bonds, unit=TokenType.PT),
                    market_state=market_state,
                    time_remaining=time_remaining,
                )
                maybe_max_short_base = maybe_max_short_bonds - trade_result.breakdown.with_fee
            except decimal.InvalidOperation:
                bond_percent -= step_size
                continue

            # If the max short base is less than or equal to zero, we need to
            # reduce the amount of bonds that we are attempting to short.
            # Otherwise, go through the other checks for the bisection.
            if maybe_max_short_base <= 0:
                bond_percent -= step_size
            else:
                # Apply the trade to the market state.
                market_state_post_trade = copy.copy(market_state)
                market_state_post_trade.apply_delta(
                    delta=MarketDeltas(
                        d_base_asset=trade_result.market_result.d_base,
                        d_token_asset=trade_result.market_result.d_bonds,
                        d_bond_buffer=maybe_max_short_bonds,
                    )
                )

                # TODO: Some of these checks are certainly unnecessary. When
                # writing rigorous tests these should be removed.
                #
                # Verify that none of the reserve invariants were broken. If
                # the invariants were broken, reduce the bond size. Otherwise,
                # we've found a new max short amount, so we store that value and
                # proceed with bisection with larger bond purchases.
                if (
                    self.calc_apr_from_reserves(market_state=market_state_post_trade, time_remaining=time_remaining) < 0
                    or market_state_post_trade.share_price * market_state_post_trade.share_reserves
                    < market_state_post_trade.base_buffer
                    or market_state_post_trade.bond_reserves < market_state_post_trade.bond_buffer
                ):
                    bond_percent -= step_size
                else:
                    last_maybe_max_short = (maybe_max_short_base, maybe_max_short_bonds)
                    if bond_percent == 1:
                        return last_maybe_max_short
                    bond_percent += step_size

        return last_maybe_max_short

    def calc_time_stretch(self, apr) -> float:
        """Returns fixed time-stretch value based on current apr (as a decimal)"""
        apr_percent = apr * 100  # bounded between 0 and 100
        return 3.09396 / (0.02789 * apr_percent)  # bounded between ~1.109 (apr=1) and inf (apr=0)

    def check_input_assertions(
        self,
        quantity: Quantity,
        market_state: MarketState,
        time_remaining: StretchedTime,
    ):
        """Applies a set of assertions to the input of a trading function."""

        assert quantity.amount >= WEI, (
            "pricing_models.check_input_assertions: ERROR: "
            f"expected quantity.amount >= {WEI}, not {quantity.amount}!"
        )
        assert market_state.share_reserves >= WEI, (
            "pricing_models.check_input_assertions: ERROR: "
            f"expected share_reserves >= {WEI}, not {market_state.share_reserves}!"
        )
        assert market_state.bond_reserves >= WEI or market_state.bond_reserves == 0, (
            "pricing_models.check_input_assertions: ERROR: "
            f"expected bond_reserves >= {WEI} or bond_reserves == 0, not {market_state.bond_reserves}!"
        )
        assert market_state.share_price >= market_state.init_share_price >= 1, (
            f"pricing_models.check_input_assertions: ERROR: "
            f"expected share_price >= init_share_price >= 1, not share_price={market_state.share_price} "
            f"and init_share_price={market_state.init_share_price}!"
        )
        reserves_difference = abs(market_state.share_reserves * market_state.share_price - market_state.bond_reserves)
        assert reserves_difference < MAX_RESERVES_DIFFERENCE, (
            "pricing_models.check_input_assertions: ERROR: "
            f"expected reserves_difference < {MAX_RESERVES_DIFFERENCE}, not {reserves_difference}!"
        )
        assert 1 >= market_state.trade_fee_percent >= 0, (
            "pricing_models.calc_in_given_out: ERROR: "
            f"expected 1 >= trade_fee_percent >= 0, not {market_state.trade_fee_percent}!"
        )
        assert 1 >= market_state.redemption_fee_percent >= 0, (
            "pricing_models.calc_in_given_out: ERROR: "
            f"expected 1 >= redemption_fee_percent >= 0, not {market_state.redemption_fee_percent}!"
        )
        # TODO: convert this to a check for 1>=time and fix tests as necessary
        assert 1 > time_remaining.stretched_time >= 0, (
            "pricing_models.calc_in_given_out: ERROR: "
            f"expected 1 > time_remaining.stretched_time >= 0, not {time_remaining.stretched_time}!"
        )

    # TODO: Add checks for TradeResult's other outputs.
    def check_output_assertions(
        self,
        trade_result: TradeResult,
    ):
        """Applies a set of assertions to a trade result."""

        assert isinstance(trade_result.breakdown.fee, float), (
            "pricing_models.check_output_assertions: ERROR: "
            f"fee should be a float, not {type(trade_result.breakdown.fee)}!"
        )
        assert trade_result.breakdown.fee >= 0, (
            "pricing_models.check_output_assertions: ERROR: "
            f"Fee should not be negative, but is {trade_result.breakdown.fee}!"
        )
        assert isinstance(trade_result.breakdown.without_fee, float), (
            "pricing_models.check_output_assertions: ERROR: "
            f"without_fee should be a float, not {type(trade_result.breakdown.without_fee)}!"
        )
        assert trade_result.breakdown.without_fee >= 0, (
            "pricing_models.check_output_assertions: ERROR: "
            f"without_fee should be non-negative, not {trade_result.breakdown.without_fee}!"
        )

"""The base pricing model."""

from abc import ABC, abstractmethod

from elfpy.types import Quantity, MarketState, StretchedTime, TradeResult
import elfpy.utils.price as price_utils


class PricingModel(ABC):
    """Contains functions for calculating AMM variables

    Base class should not be instantiated on its own; it is assumed that a user will instantiate a child class
    """

    @abstractmethod
    def calc_in_given_out(
        self,
        out: Quantity,
        market_state: MarketState,
        fee_percent: float,
        time_remaining: StretchedTime,
    ) -> TradeResult:
        """Calculate fees and asset quantity adjustments"""
        raise NotImplementedError

    @abstractmethod
    def calc_out_given_in(
        self,
        in_: Quantity,
        market_state: MarketState,
        fee_percent: float,
        time_remaining: StretchedTime,
    ) -> TradeResult:
        """Calculate fees and asset quantity adjustments"""
        raise NotImplementedError

    @abstractmethod
    def calc_lp_out_given_tokens_in(
        self,
        d_base: float,
        rate: float,
        market_state: MarketState,
        time_remaining: StretchedTime,
    ) -> tuple[float, float, float]:
        """Computes the amount of LP tokens to be minted for a given amount of base asset"""
        raise NotImplementedError

    @abstractmethod
    def calc_lp_in_given_tokens_out(
        self,
        d_base: float,
        rate: float,
        market_state: MarketState,
        time_remaining: StretchedTime,
    ) -> tuple[float, float, float]:
        """Computes the amount of LP tokens to be minted for a given amount of base asset"""
        raise NotImplementedError

    @abstractmethod
    def calc_tokens_out_given_lp_in(
        self,
        lp_in: float,
        rate: float,
        market_state: MarketState,
        time_remaining: StretchedTime,
    ) -> tuple[float, float, float]:
        """Calculate how many tokens should be returned for a given lp addition"""
        raise NotImplementedError

    @abstractmethod
    def model_name(self) -> str:
        """Unique name given to the model, can be based on member variable states"""
        raise NotImplementedError

    def calc_bond_reserves(
        self,
        target_apr: float,
        share_reserves: float,
        time_remaining: StretchedTime,
        init_share_price: float = 1,
        share_price: float = 1,
    ):
        """Returns the assumed bond (i.e. token asset) reserve amounts given
        the share (i.e. base asset) reserves and APR

        Arguments
        ---------
        target_apr : float
            Target fixed APR in decimal units (for example, 5% APR would be 0.05)
        share_reserves : float
            base asset reserves in the pool
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
            The expected amount of bonds (token asset) in the pool, given the inputs
        """
        # TODO: Package up some of these arguments into market_state
        # pylint: disable=too-many-arguments
        bond_reserves = (share_reserves / 2) * (
            init_share_price * (1 + target_apr * time_remaining.normalized_time) ** (1 / time_remaining.stretched_time)
            - share_price
        )  # y = x/2 * (u * (1 + rt)**(1/T) - c)
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

        Arguments
        ---------
        target_apr : float
            Target fixed APR in decimal units (for example, 5% APR would be 0.05)
        bond_reserves : float
            token asset (pt) reserves in the pool
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
        share_reserves = bond_reserves / (
            init_share_price * (1 - target_apr * time_remaining.normalized_time) ** (1 / time_remaining.stretched_time)
        )  # z = y / (u * (1 - rt)**(1/T))
        return share_reserves

    def calc_total_liquidity_from_reserves_and_price(self, market_state: MarketState, share_price: float) -> float:
        """Returns the total liquidity in the pool in terms of base

        Arguments
        ---------
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

        TODO: Write a test for this function
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
            p = (\frac{y + cz}{\mu z})^{-\tau}
            \end{align}

        Arguments
        ---------
        market_state: MarketState
            The reserves and share prices of the pool.
        time_remaining : StretchedTime
            The time remaining for the asset (incorporates time stretch).

        Returns
        -------
        float
            The spot price of principal tokens.
        """
        assert market_state.share_reserves > 0, (
            "pricing_models.calc_spot_price_from_reserves: ERROR: "
            f"expected share_reserves > 0, not {market_state.share_reserves}!",
        )
        total_reserves = market_state.bond_reserves + market_state.share_price * market_state.share_reserves
        spot_price = (
            (market_state.bond_reserves + total_reserves)
            / (market_state.init_share_price * market_state.share_reserves)
        ) ** -time_remaining.stretched_time
        return spot_price

    def calc_apr_from_reserves(
        self,
        market_state: MarketState,
        time_remaining: StretchedTime,
    ) -> float:
        # TODO: Update this comment so that it matches the style of the other comments.
        """
        Returns the apr given reserve amounts
        """
        spot_price = self.calc_spot_price_from_reserves(
            market_state,
            time_remaining,
        )
        apr = price_utils.calc_apr_from_spot_price(spot_price, time_remaining)
        return apr

    def calc_time_stretch(self, apr):
        """Returns fixed time-stretch value based on current apr (as a decimal)"""
        apr_percent = apr * 100
        return 3.09396 / (0.02789 * apr_percent)

    def check_input_assertions(
        self,
        quantity: Quantity,
        market_state: MarketState,
        fee_percent: float,
        time_remaining: StretchedTime,
    ):
        """Applies a set of assertions to the input of a trading function."""

        assert quantity.amount > 0, (
            "pricing_models.check_input_assertions: ERROR: " f"expected quantity.amount > 0, not {quantity.amount}!"
        )
        assert market_state.share_reserves >= 0, (
            "pricing_models.check_input_assertions: ERROR: "
            f"expected share_reserves >= 0, not {market_state.share_reserves}!"
        )
        assert market_state.bond_reserves >= 0, (
            "pricing_models.check_input_assertions: ERROR: "
            f"expected bond_reserves >= 0, not {market_state.bond_reserves}!"
        )
        assert market_state.share_price >= market_state.init_share_price >= 1, (
            f"pricing_models.check_input_assertions: ERROR: "
            f"expected share_price >= init_share_price >= 1, not share_price={market_state.share_price} "
            f"and init_share_price={market_state.init_share_price}!"
        )
        assert 1 >= fee_percent >= 0, (
            "pricing_models.calc_in_given_out: ERROR: " f"expected 1 >= fee_percent >= 0, not {fee_percent}!"
        )
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

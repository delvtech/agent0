"""The base pricing model."""

from abc import ABC, abstractmethod

from elfpy.types import Quantity, MarketState, StretchedTime, TradeResult
import elfpy.utils.price as price_utils

# TODO: Currently many functions use >5 arguments.
# These should be packaged up into shared variables, e.g.
#     reserves = (in_reserves, out_reserves)
#     share_prices = (init_share_price, share_price)
# pylint: disable=too-many-arguments

# TODO: This module is too big, we should break it up into pricing_models/{base.py, element.py, hyperdrive.py}
# pylint: disable=too-many-lines

# TODO: some functions have too many local variables (15 is recommended max),
#     we should consider how to break them up or delete this TODO if it's not possible
# pylint: disable=too-many-locals


class PricingModel(ABC):
    """
    Contains functions for calculating AMM variables

    Base class should not be instantiated on its own; it is assumed that a user will instantiate a child class
    """

    # TODO: set up member object that owns attributes instead of so many individual instance attributes
    # pylint: disable=too-many-instance-attributes
    # pylint: disable=line-too-long

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

    # TODO: Use the MarketState class.
    @abstractmethod
    def calc_lp_out_given_tokens_in(
        self,
        d_base: float,
        share_reserves: float,
        bond_reserves: float,
        share_buffer: float,
        init_share_price: float,
        share_price: float,
        lp_reserves: float,
        rate: float,
        time_remaining: float,
        stretched_time_remaining: float,
    ) -> tuple[float, float, float]:
        """
        Computes the amount of LP tokens to be minted for a given amount of base asset"""
        raise NotImplementedError

    # TODO: Use the MarketState class.
    @abstractmethod
    def calc_lp_in_given_tokens_out(
        self,
        d_base: float,
        share_reserves: float,
        bond_reserves: float,
        share_buffer: float,
        init_share_price: float,
        share_price: float,
        lp_reserves: float,
        rate: float,
        time_remaining: float,
        stretched_time_remaining: float,
    ) -> tuple[float, float, float]:
        """
        Computes the amount of LP tokens to be minted for a given amount of base asset"""
        raise NotImplementedError

    # TODO: Use the MarketState class.
    @abstractmethod
    def calc_tokens_out_given_lp_in(
        self,
        lp_in: float,
        share_reserves: float,
        bond_reserves: float,
        share_buffer: float,
        init_share_price: float,
        share_price: float,
        lp_reserves: float,
        rate: float,
        time_remaining: float,
        stretched_time_remaining: float,
    ) -> tuple[float, float, float]:
        """Calculate how many tokens should be returned for a given lp addition"""
        raise NotImplementedError

    @abstractmethod
    def model_name(self) -> str:
        """Unique name given to the model, can be based on member variable states"""
        raise NotImplementedError

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
            f"pricing_models.calc_spot_price_from_reserves: ERROR: expected share_reserves > 0, not {market_state.share_reserves}!",
        )
        total_reserves = market_state.share_price * market_state.share_reserves + market_state.bond_reserves
        bond_reserves_ = market_state.bond_reserves + total_reserves
        spot_price = 1 / (
            ((bond_reserves_) / (market_state.init_share_price * market_state.share_reserves))
            ** time_remaining.stretched_time
        )
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

        assert (
            quantity.amount > 0
        ), f"pricing_models.check_input_assertions: ERROR: expected quantity.amount > 0, not {quantity.amount}!"
        assert (
            market_state.share_reserves >= 0
        ), f"pricing_models.check_input_assertions: ERROR: expected share_reserves >= 0, not {market_state.share_reserves}!"
        assert (
            market_state.bond_reserves >= 0
        ), f"pricing_models.check_input_assertions: ERROR: expected bond_reserves >= 0, not {market_state.bond_reserves}!"
        assert market_state.share_price >= market_state.init_share_price >= 1, (
            f"pricing_models.check_input_assertions: ERROR:"
            f" expected share_price >= init_share_price >= 1, not share_price={market_state.share_price}"
            f" and init_share_price={market_state.init_share_price}!"
        )
        assert (
            1 >= fee_percent >= 0
        ), f"pricing_models.calc_in_given_out: ERROR: expected 1 >= fee_percent >= 0, not {fee_percent}!"
        assert (
            1 > time_remaining.stretched_time >= 0
        ), f"pricing_models.calc_in_given_out: ERROR: expected 1 > time_remaining.stretched_time >= 0, not {time_remaining.stretched_time}!"

    # TODO: Add checks for TradeResult's other outputs.
    def check_output_assertions(
        self,
        trade_result: TradeResult,
    ):
        """Applies a set of assertions to a trade result."""

        assert isinstance(
            trade_result.breakdown.fee, float
        ), f"pricing_models.check_output_assertions: ERROR: fee should be a float, not {type(trade_result.breakdown.fee)}!"
        assert (
            trade_result.breakdown.fee >= 0
        ), "pricing_models.check_output_assertions: ERROR: Fee should not be negative!"
        assert isinstance(
            trade_result.breakdown.without_fee, float
        ), f"pricing_models.check_output_assertions: ERROR: without_fee should be a float, not {type(trade_result.breakdown.without_fee)}!"
        assert (
            trade_result.breakdown.without_fee >= 0
        ), f"pricing_models.check_output_assertions: ERROR: without_fee should be non-negative, not {trade_result.breakdown.without_fee}!"

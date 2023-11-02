"""Agent policy for LP trading that also arbitrage on the fixed rate."""
from __future__ import annotations

import logging
import time
from copy import copy
from dataclasses import dataclass
from statistics import mean
from typing import TYPE_CHECKING

from agent0.hyperdrive.state import HyperdriveActionType, HyperdriveMarketAction
from elfpy.types import MarketType, Trade
from fixedpointmath import FixedPoint

from .hyperdrive_policy import HyperdrivePolicy

if TYPE_CHECKING:
    from agent0.hyperdrive.state import HyperdriveWallet
    from ethpy.hyperdrive import PoolConfig, PoolInfo
    from ethpy.hyperdrive.api import HyperdriveInterface
    from numpy.random._generator import Generator as NumpyGenerator

# pylint: disable=too-many-arguments, too-many-locals

# constants
TOLERANCE = 1e-16
MAX_ITER = 50


# functions
# TODO: switch over to using function in the SDK
def calc_bond_reserves(
    share_reserves: FixedPoint,
    share_adjustment: FixedPoint,
    initial_share_price: FixedPoint,
    target_rate: FixedPoint,
    position_duration: int,
    inverted_time_stretch: FixedPoint,
):
    r"""Calculate the amount of bonds that hit the target rate for the given shares.

    The calculation is based on the formula: .. math::
            mu * (z - zeta) * (1 + apr * t) ** (1 / time_stretch)


    Arguments
    ---------
    share_reserves : FixedPoint
        The amount of share reserves in the Hyperdrive pool.
    share_adjustment : FixedPoint
        The zeta adjustment to share reserves, which gives us effective share reserves (z - zeta).
    initial_share_price : FixedPoint
        The initial price of a share in the yield source, from the original pool configurartion.
    target_rate : FixedPoint
        The target rate the pool will have after the calculated change in bonds and shares.
    position_duration : int
        The term of the pool in seconds.
    inverted_time_stretch : FixedPoint
        The inverse of the time stretch factor, from the original pool configurartion.

    Returns
    -------
    FixedPoint
        The amount of bonds that hit the target rate.
    """
    return (
        initial_share_price
        * (share_reserves - share_adjustment)
        * (
            (FixedPoint(1) + target_rate * FixedPoint(position_duration) / FixedPoint(365 * 24 * 60 * 60))
            ** inverted_time_stretch
        )
    )


# TODO: switch over to using function in the SDK
def calc_spot_price_local(
    initial_share_price: FixedPoint,
    share_reserves: FixedPoint,
    share_adjustment: FixedPoint,
    bond_reserves: FixedPoint,
    time_stretch: FixedPoint,
) -> FixedPoint:
    """Calculate spot price.

    Arguments
    ---------
    initial_share_price : FixedPoint
        The initial price of a share in the yield source.
    share_reserves : FixedPoint
        The amount of share reserves in the Hyperdrive pool.
    share_adjustment : FixedPoint
        The zeta adjustment to share reserves, which gives us effective share reserves (z - zeta).
    bond_reserves : FixedPoint
        The amount of bond reserves in the Hyperdrive pool.
    time_stretch : FixedPoint
        The time stretch factor, from the original pool configurartion.

    Returns
    -------
    FixedPoint
        The spot price.
    """
    effective_share_reserves = share_reserves - share_adjustment
    return (initial_share_price * effective_share_reserves / bond_reserves) ** time_stretch


def calc_apr_local_dict(pool_config: PoolConfig, pool_info: PoolInfo):
    """Calculate APR by passing in the pool config and pool info as dicts."""
    return calc_apr_local(
        pool_info.share_reserves,
        pool_info.share_adjustment,
        pool_info.bond_reserves,
        pool_config.initial_share_price,
        pool_config.position_duration,
        pool_config.time_stretch,
    )


# TODO: switch over to using function in the SDK
def calc_apr_local(
    share_reserves: FixedPoint,
    share_adjustment: FixedPoint,
    bond_reserves: FixedPoint,
    initial_share_price: FixedPoint,
    position_duration_seconds: int,
    time_stretch: FixedPoint,
) -> FixedPoint:
    """Calculate APR.

    Arguments
    ---------
    share_reserves : FixedPoint
        The amount of share reserves in the Hyperdrive pool.
    share_adjustment : FixedPoint
        The zeta adjustment to share reserves, which gives us effective share reserves (z - zeta).
    bond_reserves : FixedPoint
        The amount of bond reserves in the Hyperdrive pool.
    initial_share_price : FixedPoint
        The initial price of a share in the yield source, from the original pool configurartion.
    position_duration_seconds : int
        The duration of the position, in seconds.
    time_stretch : FixedPoint
        The time stretch factor, from the original pool configurartion.

    Returns
    -------
    FixedPoint
        The APR.
    """
    annualized_time = FixedPoint(position_duration_seconds) / FixedPoint(365 * 24 * 60 * 60)
    spot_price = calc_spot_price_local(
        initial_share_price,
        share_reserves,
        share_adjustment,
        bond_reserves,
        time_stretch,
    )
    return (FixedPoint(1) - spot_price) / (spot_price * annualized_time)


# TODO: switch over to using function in the SDK
def calc_k_local(
    share_price: FixedPoint,
    initial_share_price: FixedPoint,
    share_reserves: FixedPoint,
    bond_reserves: FixedPoint,
    time_stretch: FixedPoint,
) -> FixedPoint:
    """Calculate the AMM invariant.

    Uses the following equation:
        k_t = (c / mu) * (mu * z) ** (1 - t) + y ** (1 - t)

    Arguments
    ---------
    share_price : FixedPoint
        The price of a share in the yield source.
    initial_share_price : FixedPoint
        The initial price of a share in the yield source, from the original pool configurartion.
    share_reserves : FixedPoint
        The amount of share reserves in the Hyperdrive pool.
    bond_reserves : FixedPoint
        The amount of bond reserves in the Hyperdrive pool.
    time_stretch : FixedPoint
        The time stretch factor, from the original pool configurartion.

    Returns
    -------
    FixedPoint
        The AMM invariant.
    """
    return (share_price / initial_share_price) * (initial_share_price * share_reserves) ** (
        FixedPoint(1) - time_stretch
    ) + bond_reserves ** (FixedPoint(1) - time_stretch)


# TODO: switch over to using function in the SDK
def get_shares_in_for_bonds_out(
    bond_reserves: FixedPoint,
    share_price: FixedPoint,
    initial_share_price: FixedPoint,
    share_reserves: FixedPoint,
    bonds_out: FixedPoint,
    time_stretch: FixedPoint,
    curve_fee: FixedPoint,
    gov_fee: FixedPoint,
) -> tuple[FixedPoint, FixedPoint, FixedPoint]:
    """Calculate the amount of shares a user will receive from the pool by providing a specified amount of bonds.

    Implements the formula:
        y_term = (y - out) ** (1 - t)
        z_val = (k_t - y_term) / (c / mu)
        z_val = z_val ** (1 / (1 - t))
        z_val /= mu
        return z_val - z

    Arguments
    ---------
    bond_reserves : FixedPoint
        The amount of bond reserves in the Hyperdrive pool.
    share_price : FixedPoint
        The price of a share in the yield source.
    initial_share_price : FixedPoint
        The initial price of a share in the yield source, from the original pool configurartion.
    share_reserves : FixedPoint
        The amount of share reserves in the Hyperdrive pool.
    bonds_out : FixedPoint
        The amount of bonds exiting the pool.
    time_stretch : FixedPoint
        The time stretch factor, from the original pool configurartion.
    curve_fee : FixedPoint
        The curve fee, as a percentage of the price discount, from pool config.
    gov_fee : FixedPoint
        The governance fee, as a percentage of the flat+curve fee, from pool config.
    """
    # pylint: disable=too-many-arguments
    k_t = calc_k_local(
        share_price,
        initial_share_price,
        share_reserves,
        bond_reserves,
        time_stretch,
    )
    y_term = (bond_reserves - bonds_out) ** (FixedPoint(1) - time_stretch)
    z_val = (k_t - y_term) / (share_price / initial_share_price)
    z_val = z_val ** (FixedPoint(1) / (FixedPoint(1) - time_stretch))
    z_val /= initial_share_price
    spot_price = calc_spot_price_local(initial_share_price, share_reserves, FixedPoint(0), bond_reserves, time_stretch)
    amount_in_shares = z_val - share_reserves
    price_discount = FixedPoint(1) - spot_price
    curve_fee_rate = price_discount * curve_fee
    curve_fee_amount_in_shares = amount_in_shares * curve_fee_rate
    gov_fee_amount_in_shares = curve_fee_amount_in_shares * gov_fee
    # applying fees means you pay MORE shares in for the same amount of bonds OUT
    amount_from_user_in_shares = amount_in_shares + curve_fee_amount_in_shares
    return (
        amount_from_user_in_shares,
        curve_fee_amount_in_shares,
        gov_fee_amount_in_shares,
    )


# TODO: switch over to using function in the SDK
def get_shares_out_for_bonds_in(
    bond_reserves: FixedPoint,
    share_price: FixedPoint,
    initial_share_price: FixedPoint,
    share_reserves: FixedPoint,
    bonds_in: FixedPoint,
    time_stretch: FixedPoint,
    curve_fee: FixedPoint,
    gov_fee: FixedPoint,
):
    """Calculate the amount of shares a user will receive from the pool by providing a specified amount of bonds.

    Implements the formula:
        y_term = (y + in_) ** (1 - t)
        z_val = (k_t - y_term) / (c / mu)
        z_val = z_val ** (1 / (1 - t))
        z_val /= mu
        return z - z_val if z > z_val else 0.0

    Arguments
    ---------
    bond_reserves : FixedPoint
        The amount of bond reserves in the Hyperdrive pool.
    share_price : FixedPoint
        The price of a share in the yield source.
    initial_share_price : FixedPoint
        The initial price of a share in the yield source, from the original pool configurartion.
    share_reserves : FixedPoint
        The amount of share reserves in the Hyperdrive pool.
    bonds_in : FixedPoint
        The amount of bonds entering the pool.
    time_stretch : FixedPoint
        The time stretch factor, from the original pool configurartion.
    curve_fee : FixedPoint
        The curve fee, as a percentage of the price discount, from pool config.
    gov_fee : FixedPoint
        The governance fee, as a percentage of the flat+curve fee, from pool config.
    """
    # pylint: disable=too-many-arguments
    k_t = calc_k_local(
        share_price,
        initial_share_price,
        share_reserves,
        bond_reserves,
        time_stretch,
    )
    y_term = (bond_reserves + bonds_in) ** (FixedPoint(1) - time_stretch)
    z_val = (k_t - y_term) / (share_price / initial_share_price)
    z_val = z_val ** (FixedPoint(1) / (FixedPoint(1) - time_stretch))
    z_val /= initial_share_price
    spot_price = calc_spot_price_local(initial_share_price, share_reserves, FixedPoint(0), bond_reserves, time_stretch)
    price_discount = FixedPoint(1) - spot_price
    amount_in_shares = max(FixedPoint(0), share_reserves - z_val)
    curve_fee_rate = price_discount * curve_fee
    curve_fee_amount_in_shares = amount_in_shares * curve_fee_rate
    gov_fee_amount_in_shares = curve_fee_amount_in_shares * gov_fee
    # applying fee means you get LESS shares out for the same amount of bonds IN
    amount_to_user_in_shares = amount_in_shares - curve_fee_amount_in_shares
    return (
        amount_to_user_in_shares,
        curve_fee_amount_in_shares,
        gov_fee_amount_in_shares,
    )


def calc_shares_needed_for_bonds(
    bonds_needed: FixedPoint, pool_info: PoolInfo, pool_config: PoolConfig
) -> tuple[FixedPoint, FixedPoint]:
    """Calculate the shares needed to trade a certain amount of bonds, and the associate governance fee.

    Arguments
    ---------
    bonds_needed : FixedPoint
        The given amount of bonds that is going to be traded.
    pool_info : PoolInfo
        The hyperdrive pool info.
    pool_config : PoolConfig
        The hyperdrive pool config.


    Returns
    -------
    tuple[FixedPoint, FixedPoint] containing:
        shares_needed : FixedPoint
            The amount of shares needed to trade the given amount of bonds.
        gov_fee : FixedPoint
            The associated governance fee.
    """
    if bonds_needed > 0:  # handle the short case
        shares_needed, _, gov_fee = get_shares_out_for_bonds_in(
            pool_info.bond_reserves,
            pool_info.share_price,
            pool_config.initial_share_price,
            pool_info.share_reserves - pool_info.share_adjustment,
            bonds_needed,
            pool_config.time_stretch,
            pool_config.fees.curve,
            pool_config.fees.governance,
        )
    else:  # handle the long case
        shares_needed, _, gov_fee = get_shares_in_for_bonds_out(
            pool_info.bond_reserves,
            pool_info.share_price,
            pool_config.initial_share_price,
            pool_info.share_reserves - pool_info.share_adjustment,
            -bonds_needed,
            pool_config.time_stretch,
            pool_config.fees.curve,
            pool_config.fees.governance,
        )
    return shares_needed, gov_fee


# TODO: switch over to using function in the SDK
def calc_reserves_to_hit_target_rate(
    target_rate: FixedPoint, hyperdrive: HyperdriveInterface
) -> tuple[FixedPoint, FixedPoint, int, float]:
    """Calculate the bonds and shares needed to hit the target fixed rate.

    Arguments
    ---------
    target_rate : FixedPoint
        The target rate the pool will have after the calculated change in bonds and shares.
    hyperdrive : HyperdriveInterface
        The Hyperdrive API interface object.

    Returns
    -------
    tuple[FixedPoint, FixedPoint] containing:
        total_shares_needed : FixedPoint
            Total amount of shares needed to be added into the pool to hit the target rate.
        total_bonds_needed : FixedPoint
            Total amount of bonds needed to be added into the pool to hit the target rate.
        convergence_iterations : int
            The number of iterations it took to converge.
        convergence_speed : float
            The amount of time it took to converge, in seconds.
    """
    # variables
    predicted_rate = FixedPoint(0)
    pool_config = copy(hyperdrive.current_pool_state.pool_config)
    pool_info = copy(hyperdrive.current_pool_state.pool_info)

    iteration = 0
    start_time = time.time()
    total_shares_needed = FixedPoint(0)
    total_bonds_needed = FixedPoint(0)
    # pylint: disable=logging-fstring-interpolation
    logging.debug(f"Targeting {float(target_rate):.2%} from {float(hyperdrive.calc_fixed_rate()):.2%}")
    while float(abs(predicted_rate - target_rate)) > TOLERANCE:
        iteration += 1
        latest_fixed_rate = calc_apr_local_dict(pool_config, pool_info)
        target_bonds = calc_bond_reserves(
            pool_info.share_reserves,
            pool_info.share_adjustment,
            pool_config.initial_share_price,
            target_rate,
            pool_config.position_duration,
            FixedPoint(1) / pool_config.time_stretch,
        )
        # bonds_needed tells us the number of bonds to hit the desired reserves ratio, keeping shares constant.
        # however trades modify both bonds and shares in amounts of equal value.
        # we modify bonds by only half of bonds_needed, knowing that an amount of equal
        # value will move shares in the other direction, toward our desired ratio.
        # this guess is very bad when slippage is high, so we check how bad, then scale accordingly.
        bonds_needed = (target_bonds - pool_info.bond_reserves) / FixedPoint(2)
        shares_needed, gov_fee = calc_shares_needed_for_bonds(bonds_needed, pool_info, pool_config)
        # save my bad first guess to a temporary variable
        temp_pool_info = apply_step(copy(pool_info), bonds_needed, shares_needed, gov_fee)
        predicted_rate = calc_apr_local_dict(pool_config, temp_pool_info)
        # improve my guess by scaling up or down based on how much I overshot or undershot and try again
        overshoot_or_undershoot = (predicted_rate - latest_fixed_rate) / (target_rate - latest_fixed_rate)
        # if we overshot by 2x, we adjust our guess to be 2x less, etc.
        bonds_needed /= overshoot_or_undershoot
        shares_needed, gov_fee = calc_shares_needed_for_bonds(bonds_needed, pool_info, pool_config)
        # save my step for real
        pool_info = apply_step(pool_info, bonds_needed, shares_needed, gov_fee)
        predicted_rate = calc_apr_local_dict(pool_config, pool_info)
        total_shares_needed = pool_info.share_reserves - hyperdrive.current_pool_state.pool_info.share_reserves
        total_bonds_needed = pool_info.bond_reserves - hyperdrive.current_pool_state.pool_info.bond_reserves
        # log info about my step
        formatted_str = (
            f"iteration {iteration:3}: {float(predicted_rate):22.18%}"
            + f" d_bonds={float(total_bonds_needed):27,.18f} d_shares={float(total_shares_needed):27,.18f}"
        )
        logging.debug(formatted_str)
        if iteration >= MAX_ITER:
            break
    convergence_speed = time.time() - start_time
    formatted_str = f"predicted precision: {float(abs(predicted_rate-target_rate))}, time taken: {convergence_speed}s"
    logging.debug(formatted_str)
    return total_shares_needed, total_bonds_needed, iteration, convergence_speed


def apply_step(
    pool_info: PoolInfo,
    bonds_needed: FixedPoint,
    shares_needed: FixedPoint,
    gov_fee: FixedPoint,
) -> PoolInfo:
    """Save a single convergence step into the pool info.

    Arguments
    ---------
    pool_info : PoolInfo
        The current pool info.
    bonds_needed : FixedPoint
        The amount of bonds that is going to be traded.
    shares_needed : FixedPoint
        The amount of shares that is going to be traded.
    gov_fee : FixedPoint
        The associated governance fee.


    Returns
    -------
    pool_info : PoolInfo
        The updated pool info.
    """
    if bonds_needed > 0:  # short case
        # shares_needed is what the user takes OUT: curve_fee less due to fees.
        # gov_fee of that doesn't stay in the pool, going OUT to governance (same direction as user flow).
        pool_info.share_reserves += -shares_needed - gov_fee
    else:  # long case
        # shares_needed is what the user pays IN: curve_fee more due to fees.
        # gov_fee of that doesn't go to the pool, going OUT to governance (opposite direction of user flow).
        pool_info.share_reserves += shares_needed - gov_fee
    pool_info.bond_reserves += bonds_needed
    return pool_info


# TODO this should maybe subclass from arbitrage policy, but perhaps making it swappable
class LPandArb(HyperdrivePolicy):
    """LP and Arbitrage in a fixed proportion."""

    @classmethod
    def description(cls) -> str:
        """Describe the policy in a user friendly manner that allows newcomers to decide whether to use it.

        Returns
        -------
        str
            The description of the policy, as described above.
        """
        raw_description = """
        LP and arbitrage in a fixed proportion.
        If no arb opportunity, that portion is LPed. In the future this could go into the yield source.
        Try to redeem withdrawal shares right away.
        Arbitrage logic is as follows:
        - Calculate number of bonds or shares needed to hit the target rate.
        - If the fixed rate is higher than the variable rate by `high_fixed_rate_thresh`:
            - Reduce shorts and open a new long, if required.
        - If the fixed rate is lower than the variable rate by `low_fixed_rate_thresh`:
            - Reduce longs and open a new short, if required.
        """
        return super().describe(raw_description)

    @dataclass
    class Config(HyperdrivePolicy.Config):
        """Custom config arguments for this policy.

        Attributes
        ----------
        high_fixed_rate_thresh: FixedPoint
            Amount over variable rate to arbitrage.
        low_fixed_rate_thresh: FixedPoint
            Amount below variable rate to arbitrage
        lp_portion: FixedPoint
            The portion of capital assigned to LP
        """

        lp_portion: FixedPoint = FixedPoint("0.5")
        high_fixed_rate_thresh: FixedPoint = FixedPoint("0.01")
        low_fixed_rate_thresh: FixedPoint = FixedPoint("0.01")
        rate_slippage: FixedPoint = FixedPoint("0.01")

        @property
        def arb_portion(self) -> FixedPoint:
            """The portion of capital assigned to arbitrage."""
            return FixedPoint(1) - self.lp_portion

    def __init__(
        self,
        budget: FixedPoint,
        rng: NumpyGenerator | None = None,
        slippage_tolerance: FixedPoint | None = None,
        policy_config: Config | None = None,
    ):
        """Initialize the bot.

        Arguments
        ---------
        budget: FixedPoint
            The budget of this policy
        rng: NumpyGenerator | None
            Random number generator
        slippage_tolerance: FixedPoint | None
            Slippage tolerance of trades
        policy_config: Config | None
            The custom arguments for this policy
        """
        # Defaults
        if policy_config is None:
            policy_config = self.Config()
        self.policy_config = policy_config
        self.arb_amount = self.policy_config.arb_portion * budget
        self.lp_amount = self.policy_config.lp_portion * budget
        self.minimum_trade_amount = FixedPoint(10)
        self.convergence_iters = []
        self.convergence_speed = []

        super().__init__(budget, rng, slippage_tolerance)

    # We want to rename the argument from "interface" to "hyperdrive" to be more explicit
    # pylint: disable=arguments-renamed
    # pylint: disable=too-many-branches
    def action(
        self, hyperdrive: HyperdriveInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """Specify actions.

        Arguments
        ---------
        hyperdrive : HyperdriveInterface
            Interface for the market on which this agent will be executing trades (MarketActions)
        wallet : HyperdriveWallet
            agent's wallet

        Returns
        -------
        tuple[list[MarketAction], bool]
            A tuple where the first element is a list of actions,
            and the second element defines if the agent is done trading
        """
        action_list = []

        # Initial conditions, open LP position
        if wallet.lp_tokens == FixedPoint(0):
            # Add liquidity
            action_list.append(
                Trade(
                    market_type=MarketType.HYPERDRIVE,
                    market_action=HyperdriveMarketAction(
                        action_type=HyperdriveActionType.ADD_LIQUIDITY,
                        trade_amount=self.lp_amount,
                        wallet=wallet,
                        min_apr=hyperdrive.calc_fixed_rate() - self.policy_config.rate_slippage,
                        max_apr=hyperdrive.calc_fixed_rate() + self.policy_config.rate_slippage,
                    ),
                )
            )

        # arbitrage from here on out
        high_fixed_rate_detected = (
            hyperdrive.calc_fixed_rate()
            >= hyperdrive.current_pool_state.variable_rate + self.policy_config.high_fixed_rate_thresh
        )
        low_fixed_rate_detected = (
            hyperdrive.calc_fixed_rate()
            <= hyperdrive.current_pool_state.variable_rate - self.policy_config.low_fixed_rate_thresh
        )
        we_have_money = wallet.balance.amount >= self.minimum_trade_amount

        # Close longs if matured
        for maturity_time, long in wallet.longs.items():
            # If matured
            if maturity_time < hyperdrive.current_pool_state.block_time:
                action_list.append(
                    Trade(
                        market_type=MarketType.HYPERDRIVE,
                        market_action=HyperdriveMarketAction(
                            action_type=HyperdriveActionType.CLOSE_LONG,
                            trade_amount=long.balance,
                            slippage_tolerance=self.slippage_tolerance,
                            wallet=wallet,
                            maturity_time=maturity_time,
                        ),
                    )
                )
        # Close shorts if matured
        for maturity_time, short in wallet.shorts.items():
            # If matured
            if maturity_time < hyperdrive.current_pool_state.block_time:
                action_list.append(
                    Trade(
                        market_type=MarketType.HYPERDRIVE,
                        market_action=HyperdriveMarketAction(
                            action_type=HyperdriveActionType.CLOSE_SHORT,
                            trade_amount=short.balance,
                            slippage_tolerance=self.slippage_tolerance,
                            wallet=wallet,
                            maturity_time=maturity_time,
                        ),
                    )
                )

        # calculate bonds and shares needed if we're arbitraging in either direction
        bonds_needed, shares_needed = FixedPoint(0), FixedPoint(0)
        if high_fixed_rate_detected or low_fixed_rate_detected:
            (
                shares_needed,
                bonds_needed,
                iters,
                speed,
            ) = calc_reserves_to_hit_target_rate(
                target_rate=hyperdrive.current_pool_state.variable_rate,
                hyperdrive=hyperdrive,
            )
            self.convergence_iters.append(iters)
            self.convergence_speed.append(speed)
            logging.debug(
                "  ==> iters: %s, speed: %s, n: %s",
                mean(self.convergence_iters),
                mean(self.convergence_speed),
                len(self.convergence_iters),
            )

        if high_fixed_rate_detected:
            bonds_needed = -bonds_needed  # we trade positive numbers around here
            # Reduce shorts first, if we have them
            if len(wallet.shorts) > 0:
                for maturity_time, short in wallet.shorts.items():
                    max_long_bonds = hyperdrive.calc_max_long(wallet.balance.amount)
                    reduce_short_amount = min(short.balance, bonds_needed, max_long_bonds)
                    bonds_needed -= reduce_short_amount
                    logging.debug("reducing short by %s", reduce_short_amount)
                    action_list.append(
                        Trade(
                            market_type=MarketType.HYPERDRIVE,
                            market_action=HyperdriveMarketAction(
                                action_type=HyperdriveActionType.CLOSE_SHORT,
                                trade_amount=reduce_short_amount,
                                slippage_tolerance=self.slippage_tolerance,
                                wallet=wallet,
                                maturity_time=maturity_time,
                            ),
                        )
                    )
            # Open a new long, if there's still a need, and we have money
            if we_have_money and bonds_needed > hyperdrive.current_pool_state.pool_config.minimum_transaction_amount:
                max_long_bonds = hyperdrive.calc_max_long(wallet.balance.amount)
                max_long_shares, _, _ = get_shares_in_for_bonds_out(
                    hyperdrive.current_pool_state.pool_info.bond_reserves,
                    hyperdrive.current_pool_state.pool_info.share_price,
                    hyperdrive.current_pool_state.pool_config.initial_share_price,
                    hyperdrive.current_pool_state.pool_info.share_reserves
                    - hyperdrive.current_pool_state.pool_info.share_reserves,
                    max_long_bonds,
                    hyperdrive.current_pool_state.pool_config.time_stretch,
                    hyperdrive.current_pool_state.pool_config.fees.curve,
                    hyperdrive.current_pool_state.pool_config.fees.governance,
                )
                amount = min(shares_needed, max_long_shares) * hyperdrive.current_pool_state.pool_info.share_price
                action_list.append(
                    Trade(
                        market_type=MarketType.HYPERDRIVE,
                        market_action=HyperdriveMarketAction(
                            action_type=HyperdriveActionType.OPEN_LONG,
                            trade_amount=amount,
                            slippage_tolerance=self.slippage_tolerance,
                            wallet=wallet,
                        ),
                    )
                )

        if low_fixed_rate_detected:
            # Reduce longs first, if we have them
            if len(wallet.longs) > 0:
                for maturity_time, long in wallet.longs.items():
                    max_short_bonds = hyperdrive.calc_max_short(wallet.balance.amount)
                    reduce_long_amount = min(long.balance, bonds_needed, max_short_bonds)
                    bonds_needed -= reduce_long_amount
                    logging.debug("reducing long by %s", reduce_long_amount)
                    action_list.append(
                        Trade(
                            market_type=MarketType.HYPERDRIVE,
                            market_action=HyperdriveMarketAction(
                                action_type=HyperdriveActionType.CLOSE_LONG,
                                trade_amount=reduce_long_amount,
                                slippage_tolerance=self.slippage_tolerance,
                                wallet=wallet,
                                maturity_time=maturity_time,
                            ),
                        )
                    )
            # Open a new short, if there's still a need, and we have money
            if we_have_money and bonds_needed > hyperdrive.current_pool_state.pool_config.minimum_transaction_amount:
                max_short_bonds = hyperdrive.calc_max_short(wallet.balance.amount)
                amount = min(bonds_needed, max_short_bonds)
                action_list.append(
                    Trade(
                        market_type=MarketType.HYPERDRIVE,
                        market_action=HyperdriveMarketAction(
                            action_type=HyperdriveActionType.OPEN_SHORT,
                            trade_amount=amount,
                            slippage_tolerance=self.slippage_tolerance,
                            wallet=wallet,
                        ),
                    )
                )

        return action_list, False

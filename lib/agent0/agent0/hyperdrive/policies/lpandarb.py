"""Agent policy for LP trading that also arbitrage on the fixed rate."""
from __future__ import annotations

import logging
import time
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from statistics import mean
from typing import TYPE_CHECKING

from ethpy.hyperdrive.state import PoolState
from fixedpointmath import FixedPoint

from agent0.base import Trade
from agent0.hyperdrive.policies.hyperdrive_policy import HyperdrivePolicy
from agent0.hyperdrive.state import HyperdriveMarketAction

if TYPE_CHECKING:
    from ethpy.hyperdrive.interface import HyperdriveReadInterface

    from agent0.hyperdrive.state import HyperdriveWallet

# pylint: disable=too-many-arguments, too-many-locals

# constants
TOLERANCE = 1e-18
MAX_ITER = 50


def calc_shares_needed_for_bonds(
    bonds_needed: FixedPoint, pool_state: PoolState, interface: HyperdriveReadInterface
) -> tuple[FixedPoint, FixedPoint]:
    """Calculate the shares needed to trade a certain amount of bonds, and the associate governance fee.

    Arguments
    ---------
    bonds_needed: FixedPoint
        The given amount of bonds that is going to be traded.
    pool_state: PoolState
        The hyperdrive pool state.
    interface: HyperdriveReadInterface
        The Hyperdrive API interface object.


    Returns
    -------
    tuple[FixedPoint, FixedPoint]
        _shares_to_pool: FixedPoint
            The change in shares in the pool for the given amount of bonds.
        _shares_to_gov: FixedPoint
            The associated shares going to governance.
    """
    _shares_to_pool = interface.calc_shares_out_given_bonds_in_down(abs(bonds_needed), pool_state)
    # _shares_to_pool = interface.calc_shares_in_given_bonds_out_down(abs(bonds_needed), pool_state)
    # _shares_to_pool = interface.calc_shares_in_given_bonds_out_up(abs(bonds_needed), pool_state)
    spot_price = interface.calc_spot_price(pool_state)
    price_discount = FixedPoint(1) - spot_price
    _shares_to_gov = (
        _shares_to_pool * price_discount * pool_state.pool_config.fees.curve * pool_state.pool_config.fees.governance_lp
    )
    _shares_to_pool -= _shares_to_gov
    return _shares_to_pool, _shares_to_gov


def calc_reserves_to_hit_target_rate(
    target_rate: FixedPoint, interface: HyperdriveReadInterface
) -> tuple[FixedPoint, FixedPoint, int, float]:
    """Calculate the bonds and shares needed to hit the target fixed rate.

    Arguments
    ---------
    target_rate: FixedPoint
        The target rate the pool will have after the calculated change in bonds and shares.
    interface: HyperdriveReadInterface
        The Hyperdrive API interface object.

    Returns
    -------
    tuple[FixedPoint, FixedPoint]
        total_shares_needed: FixedPoint
            Total amount of shares needed to be added into the pool to hit the target rate.
        total_bonds_needed: FixedPoint
            Total amount of bonds needed to be added into the pool to hit the target rate.
        convergence_iterations: int
            The number of iterations it took to converge.
        convergence_speed: float
            The amount of time it took to converge, in seconds.
    """
    predicted_rate = FixedPoint(0)
    pool_state = deepcopy(interface.current_pool_state)

    iteration = 0
    start_time = time.time()
    total_shares_needed = FixedPoint(0)
    total_bonds_needed = FixedPoint(0)
    # pylint: disable=logging-fstring-interpolation
    logging.warning(f"Targeting {float(target_rate):.2%} from {float(interface.calc_fixed_rate()):.2%}")
    while float(abs(predicted_rate - target_rate)) > TOLERANCE:
        iteration += 1
        latest_fixed_rate = interface.calc_fixed_rate(pool_state)
        target_bonds = interface.calc_bonds_given_shares_and_rate(
            target_rate, pool_state.pool_info.share_reserves, pool_state
        )
        # bonds_needed tells us the number of bonds to hit the desired reserves ratio, keeping shares constant.
        # however trades modify both bonds and shares in amounts of equal value.
        # we modify bonds by only half of bonds_needed, knowing that an amount of equal
        # value will move shares in the other direction, toward our desired ratio.
        # this guess is very bad when slippage is high, so we check how bad, then scale accordingly.
        # to avoid negative share reserves, we increase the divisor until they are no longer negative.
        divisor = FixedPoint(2)
        bonds_needed = FixedPoint(0)
        avoid_negative_share_reserves = False
        # We want to take as large of a step as possible while avoiding negative share reserves.
        # So we loop through, increasing the divisor until the share reserves are no longer negative.
        while avoid_negative_share_reserves is False:
            bonds_needed = (target_bonds - pool_state.pool_info.bond_reserves) / divisor
            shares_to_pool, shares_to_gov = calc_shares_needed_for_bonds(bonds_needed, pool_state, interface)
            # save bad first guess to a temporary variable
            temp_pool_state = apply_step(deepcopy(pool_state), bonds_needed, shares_to_pool, shares_to_gov)
            predicted_rate = interface.calc_fixed_rate(temp_pool_state)
            avoid_negative_share_reserves = temp_pool_state.pool_info.share_reserves >= 0
            divisor *= FixedPoint(2)
        # adjust guess up or down based on how much the first guess overshot or undershot
        if (target_rate - latest_fixed_rate) != FixedPoint(0):
            overshoot_or_undershoot = (predicted_rate - latest_fixed_rate) / (target_rate - latest_fixed_rate)
        else:
            overshoot_or_undershoot = FixedPoint(0)
        if overshoot_or_undershoot != FixedPoint(0):
            bonds_needed = bonds_needed / overshoot_or_undershoot
        shares_to_pool, shares_to_gov = calc_shares_needed_for_bonds(bonds_needed, pool_state, interface)
        # update pool state with second guess and continue from there
        pool_state = apply_step(pool_state, bonds_needed, shares_to_pool, shares_to_gov)
        predicted_rate = interface.calc_fixed_rate(pool_state)
        # update running totals
        total_shares_needed = (
            pool_state.pool_info.share_reserves - interface.current_pool_state.pool_info.share_reserves
        )
        total_bonds_needed = pool_state.pool_info.bond_reserves - interface.current_pool_state.pool_info.bond_reserves
        # log info about the completed step
        formatted_str = (
            f"iteration {iteration:3}: {float(predicted_rate):22.18%}"
            + f" d_bonds={float(total_bonds_needed):27,.18f} d_shares={float(total_shares_needed):27,.18f}"
        )
        logging.warning(formatted_str)
        if iteration >= MAX_ITER:
            break
    convergence_speed = time.time() - start_time
    formatted_str = f"predicted precision: {float(abs(predicted_rate-target_rate))}, time taken: {convergence_speed}s"
    logging.warning(formatted_str)
    return total_shares_needed, total_bonds_needed, iteration, convergence_speed


def apply_step(
    pool_state: PoolState,
    bonds_needed: FixedPoint,
    shares_needed: FixedPoint,
    gov_fee: FixedPoint,
) -> PoolState:
    """Save a single convergence step into the pool info.

    Arguments
    ---------
    pool_state: PoolState
        The current pool state.
    bonds_needed: FixedPoint
        The amount of bonds that is going to be traded.
    shares_needed: FixedPoint
        The amount of shares that is going to be traded.
    gov_fee: FixedPoint
        The associated governance fee.


    Returns
    -------
    PoolState
        The updated pool state.
    """
    if bonds_needed > 0:  # short case
        # shares_needed is what the user takes OUT: curve_fee less due to fees.
        # gov_fee of that doesn't stay in the pool, going OUT to governance (same direction as user flow).
        pool_state.pool_info.share_reserves += -shares_needed - gov_fee
    else:  # long case
        # shares_needed is what the user pays IN: curve_fee more due to fees.
        # gov_fee of that doesn't go to the pool, going OUT to governance (opposite direction of user flow).
        pool_state.pool_info.share_reserves += shares_needed - gov_fee
    pool_state.pool_info.bond_reserves += bonds_needed
    return pool_state


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

    @dataclass(kw_only=True)
    class Config(HyperdrivePolicy.Config):
        """Custom config arguments for this policy.

        Attributes
        ----------
        high_fixed_rate_thresh: FixedPoint
            Amount over variable rate to arbitrage.
        low_fixed_rate_thresh: FixedPoint
            Amount below variable rate to arbitrage. Defaults to 0.
        lp_portion: FixedPoint
            The portion of capital assigned to LP. Defaults to 0.
        done_on_empty: bool
            Whether to exit the bot if there are no trades.
        minimum_trade_amount: FixedPoint
            The minimum trade amount below which the agent won't submit a trade.
        """

        lp_portion: FixedPoint = FixedPoint("0.5")
        high_fixed_rate_thresh: FixedPoint = FixedPoint(0)
        low_fixed_rate_thresh: FixedPoint = FixedPoint(0)
        rate_slippage: FixedPoint = FixedPoint("0.01")
        done_on_empty: bool = False
        minimum_trade_amount: FixedPoint = FixedPoint(10)

        @property
        def arb_portion(self) -> FixedPoint:
            """The portion of capital assigned to arbitrage."""
            return FixedPoint(1) - self.lp_portion

    def __init__(
        self,
        policy_config: Config,
    ):
        """Initialize the bot.

        Arguments
        ---------
        policy_config: Config
            The custom arguments for this policy
        """
        self.policy_config = policy_config
        self.minimum_trade_amount = policy_config.minimum_trade_amount
        self.convergence_iters = []
        self.convergence_speed = []

        super().__init__(policy_config)

    # pylint: disable=too-many-branches
    def action(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """Specify actions.

        Arguments
        ---------
        interface: HyperdriveReadInterface
            Interface for the market on which this agent will be executing trades (MarketActions).
        wallet: HyperdriveWallet
            The agent's wallet.

        Returns
        -------
        tuple[list[MarketAction], bool]
            A tuple where the first element is a list of actions,
            and the second element defines if the agent is done trading.
        """
        action_list = []

        # Initial conditions, open LP position
        lp_amount = self.policy_config.lp_portion * wallet.balance.amount
        if wallet.lp_tokens == FixedPoint(0) and lp_amount > FixedPoint(0):
            # Add liquidity
            action_list.append(
                interface.add_liquidity_trade(
                    trade_amount=lp_amount,
                    min_apr=interface.calc_fixed_rate() - self.policy_config.rate_slippage,
                    max_apr=interface.calc_fixed_rate() + self.policy_config.rate_slippage,
                )
            )

        # arbitrage from here on out
        high_fixed_rate_detected = (
            interface.calc_fixed_rate()
            >= interface.current_pool_state.variable_rate + self.policy_config.high_fixed_rate_thresh
        )
        low_fixed_rate_detected = (
            interface.calc_fixed_rate()
            <= interface.current_pool_state.variable_rate - self.policy_config.low_fixed_rate_thresh
        )
        we_have_money = wallet.balance.amount >= self.minimum_trade_amount

        # Close longs if matured
        for maturity_time, long in wallet.longs.items():
            # If matured
            if maturity_time < interface.current_pool_state.block_time and long.balance > self.minimum_trade_amount:
                action_list.append(interface.close_long_trade(long.balance, maturity_time, self.slippage_tolerance))
        # Close shorts if matured
        for maturity_time, short in wallet.shorts.items():
            # If matured
            if maturity_time < interface.current_pool_state.block_time and short.balance > self.minimum_trade_amount:
                action_list.append(interface.close_short_trade(short.balance, maturity_time, self.slippage_tolerance))

        # calculate bonds and shares needed if we're arbitraging in either direction
        bonds_needed = FixedPoint(0)
        if high_fixed_rate_detected or low_fixed_rate_detected:
            _, bonds_needed, iters, speed = calc_reserves_to_hit_target_rate(
                target_rate=interface.current_pool_state.variable_rate, interface=interface
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
                    max_long_bonds = interface.calc_max_long(wallet.balance.amount)
                    current_block_time = interface.current_pool_state.block_time
                    next_block_time = current_block_time + 12
                    # logging.warning("current block time is %s (human-readable: %s)", current_block_time, datetime.fromtimestamp(current_block_time))
                    curve_portion = FixedPoint((maturity_time - next_block_time) / interface.pool_config.position_duration)
                    logging.warning("curve portion is %s", curve_portion)
                    logging.warning("bonds needed is %s", bonds_needed)
                    reduce_short_amount = min(short.balance, bonds_needed/curve_portion, max_long_bonds)
                    if reduce_short_amount > self.minimum_trade_amount:
                        bonds_needed -= reduce_short_amount*curve_portion
                        logging.warning("reducing short by %s", reduce_short_amount)
                        logging.warning("reduce_short_amount*curve_portion = %s", reduce_short_amount*curve_portion)
                        action_list.append(
                            interface.close_short_trade(reduce_short_amount, maturity_time, self.slippage_tolerance)
                        )
            # Open a new long, if there's still a need, and we have money
            if we_have_money and bonds_needed > self.minimum_trade_amount:
                max_long_bonds = interface.calc_max_long(wallet.balance.amount)
                max_long_shares = interface.calc_shares_in_given_bonds_out_down(max_long_bonds)
                amount = min(bonds_needed, max_long_shares) * interface.current_pool_state.pool_info.share_price
                action_list.append(interface.open_long_trade(amount, self.slippage_tolerance))

        if low_fixed_rate_detected:
            # Reduce longs first, if we have them
            if len(wallet.longs) > 0:
                for maturity_time, long in wallet.longs.items():
                    max_short_bonds = interface.calc_max_short(wallet.balance.amount)
                    current_block_time = interface.current_pool_state.block_time
                    next_block_time = current_block_time + 12
                    curve_portion = FixedPoint((maturity_time - next_block_time) / interface.pool_config.position_duration)
                    logging.warning("curve portion is %s", curve_portion)
                    logging.warning("bonds needed is %s", bonds_needed)
                    reduce_long_amount = min(long.balance, bonds_needed/curve_portion, max_short_bonds)
                    if reduce_long_amount > self.minimum_trade_amount:
                        bonds_needed -= reduce_long_amount*curve_portion
                        logging.debug("reducing long by %s", reduce_long_amount)
                        action_list.append(
                            interface.close_long_trade(reduce_long_amount, maturity_time, self.slippage_tolerance)
                        )
            # Open a new short, if there's still a need, and we have money
            if we_have_money and bonds_needed > self.minimum_trade_amount:
                max_short_bonds = interface.calc_max_short(wallet.balance.amount)
                amount = min(bonds_needed, max_short_bonds)
                action_list.append(interface.open_short_trade(amount, self.slippage_tolerance))

        if self.policy_config.done_on_empty and len(action_list) == 0:
            return [], True
        return action_list, False

"""Agent policy for LP trading that can also arbitrage on the fixed rate."""

from __future__ import annotations

import logging
import time
from copy import deepcopy
from dataclasses import dataclass
from statistics import mean
from typing import TYPE_CHECKING

from fixedpointmath import FixedPoint, maximum, minimum

from agent0.core.base import Trade
from agent0.core.hyperdrive import HyperdriveMarketAction
from agent0.core.hyperdrive.agent import (
    add_liquidity_trade,
    close_long_trade,
    close_short_trade,
    open_long_trade,
    open_short_trade,
)
from agent0.core.utilities.predict import predict_long, predict_short
from agent0.ethpy.hyperdrive.state import PoolState

from .hyperdrive_policy import HyperdriveBasePolicy

if TYPE_CHECKING:
    from agent0.core.hyperdrive import HyperdriveWallet
    from agent0.ethpy.hyperdrive import HyperdriveReadInterface

# constants
TOLERANCE = 1e-18
MAX_ITER = 50


def calc_shares_needed_for_bonds(
    interface: HyperdriveReadInterface,
    pool_state: PoolState,
    bonds_needed: FixedPoint,
    minimum_trade_amount: FixedPoint,
) -> FixedPoint:
    """Calculate the shares needed to trade a certain amount of bonds, and the associate governance fee.

    Arguments
    ---------
    interface: HyperdriveReadInterface
        The Hyperdrive API interface object.
    pool_state: PoolState
        The hyperdrive pool state.
    bonds_needed: FixedPoint
        The given amount of bonds that is going to be traded.
    minimum_trade_amount: FixedPoint
        The minimum amount of bonds needed to open a trade.

    Returns
    -------
    FixedPoint
        The change in shares in the pool for the given amount of bonds.
    """
    if bonds_needed > minimum_trade_amount:  # need more bonds in pool -> user sells bonds -> user opens short
        delta = predict_short(hyperdrive_interface=interface, bonds=bonds_needed, pool_state=pool_state, for_pool=True)
    elif bonds_needed < -minimum_trade_amount:  # need less bonds in pool -> user buys bonds -> user opens long
        delta = predict_long(hyperdrive_interface=interface, bonds=-bonds_needed, pool_state=pool_state, for_pool=True)
    else:
        return FixedPoint(0)
    return abs(delta.pool.shares)


def calc_delta_reserves_for_target_rate(
    interface: HyperdriveReadInterface,
    pool_state: PoolState,
    target_rate: FixedPoint,
    minimum_trade_amount: FixedPoint,
) -> tuple[FixedPoint, FixedPoint]:
    """Calculate the bonds needed to hit the desired reserves ratio, keeping shares constant.

    delta_bonds tells us the number of bonds to hit the desired reserves ratio, keeping shares constant.
    However trades modify both bonds and shares in amounts of equal value.
    We modify bonds by only half of delta_bonds, knowing that an amount of equal
    value will move shares in the other direction, toward our desired ratio.
    This guess is very bad when slippage is high, so we check how bad, then scale accordingly.
    To avoid negative share reserves, we increase the divisor until they are no longer negative.

    Arguments
    ---------
    interface: HyperdriveReadInterface
        Interface for the market on which this agent will be executing trades (MarketActions).
    pool_state: PoolState
        The current pool state.
    target_rate: FixedPoint
        The target rate the pool will have after the calculated change in bonds and shares.
    minimum_trade_amount: FixedPoint
        The minimum trade amount below which the agent won't submit a trade.

    Returns
    -------
    tuple[FixedPoint, FixedPoint]
        The delta (bonds, shares) needed to hit the desired fixed rate.
    """
    divisor = FixedPoint(2)
    delta_bonds = FixedPoint(0)
    target_bonds = interface.calc_bonds_given_shares_and_rate(
        target_rate=target_rate, target_shares=pool_state.pool_info.share_reserves, pool_state=pool_state
    )
    avoid_negative_share_reserves = False
    # We want to take as large of a step as possible while avoiding negative share reserves.
    # So we loop through, increasing the divisor until the share reserves are no longer negative.
    delta_shares = FixedPoint(0)
    while avoid_negative_share_reserves is False:
        delta_bonds = (target_bonds - pool_state.pool_info.bond_reserves) / divisor
        delta_shares = calc_shares_needed_for_bonds(interface, pool_state, delta_bonds, minimum_trade_amount)
        # simulate pool state update without a deep copy to save time
        new_share_reserves, _ = apply_step_to_reserves(
            pool_state.pool_info.share_reserves, delta_shares, pool_state.pool_info.bond_reserves, delta_bonds
        )
        avoid_negative_share_reserves = new_share_reserves >= 0
        divisor *= FixedPoint(2)
    return delta_bonds, delta_shares


def calc_reserves_to_hit_target_rate(
    interface: HyperdriveReadInterface, pool_state: PoolState, target_rate: FixedPoint, minimum_trade_amount: FixedPoint
) -> tuple[FixedPoint, FixedPoint]:
    """Calculate the bonds and shares needed to hit the target fixed rate.

    Arguments
    ---------
    interface: HyperdriveReadInterface
        The Hyperdrive API interface object.
    pool_state: PoolState
        The current pool state.
    target_rate: FixedPoint
        The target rate the pool will have after the calculated change in bonds and shares.
    minimum_trade_amount: FixedPoint
        The minimum amount of bonds needed to open a trade.

    Returns
    -------
    tuple[FixedPoint, FixedPoint, int]
        total_shares_needed: FixedPoint
            Total amount of shares needed to be added into the pool to hit the target rate.
        total_bonds_needed: FixedPoint
            Total amount of bonds needed to be added into the pool to hit the target rate.
    """
    predicted_rate = FixedPoint(0)
    temp_pool_state = deepcopy(pool_state)
    iteration = 0
    total_shares_needed = FixedPoint(0)
    total_bonds_needed = FixedPoint(0)
    logging.info("Targeting %.2f from %.2f", float(target_rate), float(interface.calc_fixed_rate(pool_state)))
    while float(abs(predicted_rate - target_rate)) > TOLERANCE and iteration < MAX_ITER:
        iteration += 1
        latest_fixed_rate = interface.calc_fixed_rate(temp_pool_state)
        # get the predicted reserve levels
        bonds_needed, shares_needed = calc_delta_reserves_for_target_rate(
            interface, temp_pool_state, target_rate, minimum_trade_amount
        )
        # get the fixed rate for an updated pool state, without storing the state variable
        # TODO: This deepcopy is slow. https://github.com/delvtech/agent0/issues/1355
        predicted_rate = interface.calc_fixed_rate(
            apply_step_to_pool_state(deepcopy(temp_pool_state), bonds_needed, shares_needed)
        )
        # adjust guess up or down based on how much the first guess overshot or undershot
        overshoot_or_undershoot = FixedPoint(0)
        if (target_rate - latest_fixed_rate) != FixedPoint(0):
            overshoot_or_undershoot = (predicted_rate - latest_fixed_rate) / (target_rate - latest_fixed_rate)
        if overshoot_or_undershoot != FixedPoint(0):
            bonds_needed = bonds_needed / overshoot_or_undershoot
        shares_to_pool = calc_shares_needed_for_bonds(interface, temp_pool_state, bonds_needed, minimum_trade_amount)
        # update pool state with second guess and continue from there
        temp_pool_state = apply_step_to_pool_state(temp_pool_state, bonds_needed, shares_to_pool)
        predicted_rate = interface.calc_fixed_rate(temp_pool_state)
        # log info about the completed step
        logging.info(
            "iteration %3d: %s%% d_bonds=%s d_shares=%s predicted_precision=%s",
            iteration,
            format(float(predicted_rate), "22,.18f"),
            format(float(total_bonds_needed), "27,.18f"),
            format(float(total_shares_needed), "27,.18f"),
            format(float(abs(predicted_rate - target_rate)), ".18f"),
        )
    # update running totals
    total_shares_needed = temp_pool_state.pool_info.share_reserves - pool_state.pool_info.share_reserves
    total_bonds_needed = temp_pool_state.pool_info.bond_reserves - pool_state.pool_info.bond_reserves
    return total_shares_needed, total_bonds_needed


def apply_step_to_reserves(
    share_reserves: FixedPoint, delta_shares: FixedPoint, bond_reserves: FixedPoint, delta_bonds: FixedPoint
) -> tuple[FixedPoint, FixedPoint]:
    """Apply a single convergence step to pool share and bond reserve levels.

    Arguments
    ---------
    share_reserves: FixedPoint
        The current Hyperdrive pool's share reserves.
    delta_shares: FixedPoint
        The amount of shares to add or remove from the reserves, depending on the delta bonds sign.
    bond_reserves: FixedPoint
        The current Hyperdrive pool's bond reserves.
    delta_bonds: FixedPoint
        The amount of bonds to add or remove from the reserves.

    Returns
    -------
    tuple[FixedPoint, FixedPoint]
        The resulting share reserves and bond reserves after the delta updates are applied.
    """
    if delta_bonds > 0:  # short case
        share_reserves -= delta_shares  # take shares out of pool
    else:  # long case
        share_reserves += delta_shares  # put shares in pool
    bond_reserves += delta_bonds
    return (share_reserves, bond_reserves)


def apply_step_to_pool_state(
    pool_state: PoolState,
    delta_bonds: FixedPoint,
    delta_shares: FixedPoint,
) -> PoolState:
    """Save a single convergence step into the pool info.

    .. todo::
        This function updates the pool_state argument _and_ returns it.
        This is a bad pattern because it obscures that the input argument is modified in-place.
        We should either always return a new instance (either via deepcopy or constructing from scratch)
        or always modify the provided variable in-place.

    Arguments
    ---------
    pool_state: PoolState
        The current pool state.
    delta_bonds: FixedPoint
        The amount of bonds that is going to be traded.
    delta_shares: FixedPoint
        The amount of shares that is going to be traded.

    Returns
    -------
    PoolState
        The updated pool state.
    """
    new_share_reserves, new_bond_reserves = apply_step_to_reserves(
        pool_state.pool_info.share_reserves, delta_shares, pool_state.pool_info.bond_reserves, delta_bonds
    )
    setattr(pool_state.pool_info, "share_reserves", new_share_reserves)
    setattr(pool_state.pool_info, "bond_reserves", new_bond_reserves)
    return pool_state


# TODO this should maybe subclass from arbitrage policy, but perhaps making it swappable
class LPandArb(HyperdriveBasePolicy):
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
    class Config(HyperdriveBasePolicy.Config):
        """Custom config arguments for this policy."""

        lp_portion: FixedPoint = FixedPoint("0.5")
        """The portion of capital assigned to LP. Defaults to 0."""
        high_fixed_rate_thresh: FixedPoint = FixedPoint(0)
        """Amount over variable rate to arbitrage."""
        low_fixed_rate_thresh: FixedPoint = FixedPoint(0)
        """Amount below variable rate to arbitrage. Defaults to 0."""
        auto_fixed_rate_thresh: bool = False
        """If set, override the high and low rate thresholds to compute profitable amounts based on fees."""
        rate_slippage: FixedPoint = FixedPoint("0.01")
        done_on_empty: bool = False
        """Whether to exit the bot if there are no trades."""
        minimum_trade_amount: FixedPoint = FixedPoint(10)
        """The minimum trade amount below which the agent won't submit a trade."""

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

    # TODO: Fix this function up
    # pylint: disable=too-many-locals
    # pylint: disable=too-many-branches
    # pylint: disable=too-many-statements
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
        current_pool_state = interface.current_pool_state  # compute this once to avoid race conditions
        current_fixed_rate = interface.calc_fixed_rate(current_pool_state)

        # close matured positions
        self.close_matured_positions(wallet, current_pool_state, self.minimum_trade_amount)

        # open LP position
        lp_amount = self.policy_config.lp_portion * wallet.balance.amount
        if wallet.lp_tokens == FixedPoint(0) and lp_amount > FixedPoint(0):
            # Add liquidity
            action_list.append(
                add_liquidity_trade(
                    trade_amount=lp_amount,
                    min_apr=current_fixed_rate - self.policy_config.rate_slippage,
                    max_apr=current_fixed_rate + self.policy_config.rate_slippage,
                )
            )

        # arbitrage from here on out
        high_fixed_rate_detected = (
            current_fixed_rate >= current_pool_state.variable_rate + self.policy_config.high_fixed_rate_thresh
        )
        low_fixed_rate_detected = (
            current_fixed_rate <= current_pool_state.variable_rate - self.policy_config.low_fixed_rate_thresh
        )
        we_have_money = wallet.balance.amount >= self.minimum_trade_amount

        # calculate bonds and shares needed if we're arbitraging in either direction
        bonds_needed = FixedPoint(0)
        if high_fixed_rate_detected or low_fixed_rate_detected:
            start_time = time.time()
            _, bonds_needed = calc_reserves_to_hit_target_rate(
                interface=interface,
                pool_state=current_pool_state,
                target_rate=current_pool_state.variable_rate,
                minimum_trade_amount=self.minimum_trade_amount,
            )
            speed = time.time() - start_time
            self.convergence_speed.append(speed)
            logging.debug("  ==> speed: %s", mean(self.convergence_speed))

        if high_fixed_rate_detected:
            bonds_needed = -bonds_needed  # we trade positive numbers around here
            # Reduce shorts first, if we have them
            if len(wallet.shorts) > 0:
                for maturity_time, short in wallet.shorts.items():
                    max_long_bonds = interface.calc_max_long(wallet.balance.amount)
                    current_block_time = current_pool_state.block_time
                    # TODO: Get time-between-blocks from the interface instead of hard-coding to 12
                    next_block_time = current_block_time + 12
                    curve_portion = maximum(
                        FixedPoint(0),
                        FixedPoint((maturity_time - next_block_time))
                        / FixedPoint(interface.pool_config.position_duration),
                    )
                    logging.info("curve portion is %s\nbonds needed is %s", curve_portion, bonds_needed)
                    reduce_short_amount = minimum(short.balance, bonds_needed / curve_portion, max_long_bonds)
                    if reduce_short_amount > self.minimum_trade_amount:
                        bonds_needed -= reduce_short_amount * curve_portion
                        logging.info(
                            "reducing short by %s\nreduce_short_amount*curve_portion = %s",
                            reduce_short_amount,
                            reduce_short_amount * curve_portion,
                        )
                        action_list.append(
                            close_short_trade(reduce_short_amount, maturity_time, self.slippage_tolerance)
                        )
            # Open a new long, if there's still a need, and we have money
            if we_have_money and bonds_needed > self.minimum_trade_amount:
                max_long_bonds = interface.calc_max_long(wallet.balance.amount)
                max_long_shares = interface.calc_shares_in_given_bonds_out_down(max_long_bonds)
                shares_needed = interface.calc_shares_in_given_bonds_out_down(bonds_needed)
                amount_base = minimum(shares_needed, max_long_shares) * current_pool_state.pool_info.vault_share_price
                action_list.append(open_long_trade(amount_base, self.slippage_tolerance))

        if low_fixed_rate_detected:
            # Reduce longs first, if we have them
            if len(wallet.longs) > 0:
                for maturity_time, long in wallet.longs.items():
                    max_short_bonds = interface.calc_max_short(wallet.balance.amount)
                    current_block_time = current_pool_state.block_time
                    # TODO: Get time-between-blocks from the interface instead of hard-coding to 12
                    next_block_time = current_block_time + 12
                    curve_portion = maximum(
                        FixedPoint(0),
                        FixedPoint(maturity_time - next_block_time)
                        / FixedPoint(interface.pool_config.position_duration),
                    )
                    logging.info("curve portion is %s", curve_portion)
                    logging.info("bonds needed is %s", bonds_needed)
                    reduce_long_amount = minimum(long.balance, bonds_needed / curve_portion, max_short_bonds)
                    if reduce_long_amount > self.minimum_trade_amount:
                        bonds_needed -= reduce_long_amount * curve_portion
                        logging.debug("reducing long by %s", reduce_long_amount)
                        action_list.append(close_long_trade(reduce_long_amount, maturity_time, self.slippage_tolerance))
            # Open a new short, if there's still a need, and we have money
            if we_have_money and bonds_needed > self.minimum_trade_amount:
                max_short_bonds = interface.calc_max_short(wallet.balance.amount)
                amount_bonds = minimum(bonds_needed, max_short_bonds)
                action_list.append(open_short_trade(amount_bonds, self.slippage_tolerance))

        if self.policy_config.done_on_empty and len(action_list) == 0:
            return [], True
        return action_list, False

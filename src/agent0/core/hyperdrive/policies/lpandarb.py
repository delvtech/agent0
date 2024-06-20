"""Agent policy for LP trading that can also arbitrage on the fixed rate."""

from __future__ import annotations

import logging
from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fixedpointmath import FixedPoint, maximum, minimum

from agent0.core.base import Trade
from agent0.core.hyperdrive.agent import (
    add_liquidity_trade,
    close_long_trade,
    close_short_trade,
    open_long_trade,
    open_short_trade,
)
from agent0.core.hyperdrive.utilities.predict import predict_long, predict_short
from agent0.ethpy.hyperdrive.state import PoolState

from .hyperdrive_policy import HyperdriveBasePolicy

if TYPE_CHECKING:
    from agent0.core.hyperdrive import HyperdriveMarketAction, HyperdriveWallet
    from agent0.ethpy.hyperdrive import HyperdriveReadInterface

# constants
TOLERANCE = 1e-18
MAX_ITER = 50

# TODO: we can either make these helper fns member functions of a parent class
# or we can make them static utils and pass the agent object itself. Either way,
# this will simplify the argument space down to a much smaller set.
# pylint: disable=too-many-arguments
# ruff: noqa: PLR0913
# pylint: disable=too-many-locals


def arb_fixed_rate_down(
    interface: HyperdriveReadInterface,
    pool_state: PoolState,
    wallet: HyperdriveWallet,
    max_trade_amount_base: FixedPoint,
    min_trade_amount_bonds: FixedPoint,
    slippage_tolerance: FixedPoint | None = None,
    base_fee_multiple: float | None = None,
    priority_fee_multiple: float | None = None,
) -> list[Trade[HyperdriveMarketAction]]:
    """Return an action list for arbitraging the fixed rate down to the variable rate.

    Arguments
    ---------
    interface: HyperdriveReadInterface
        The Hyperdrive API interface object.
    pool_state: PoolState
        The hyperdrive pool state.
    wallet: HyperdriveWallet
        The agent's wallet.
    max_trade_amount_base: FixedPoint
        The maximum amount of base allowed to trade.
    min_trade_amount_bonds: FixedPoint
        The minimum amount of bonds needed to open a trade.
    slippage_tolerance: FixedPoint | None, optional
        The slippage tolerance for trades. Defaults to None.
    base_fee_multiple: float | None, optional
        The base fee multiple for transactions. Defaults to None.
    priority_fee_multiple: float | None, optional
        The priority fee multiple for transactions. Defaults to None.

    Returns
    -------
    list[MarketAction]
        A list of actions for arbitration trades.
    """
    action_list = []

    variable_rate = pool_state.variable_rate
    # Variable rate can be None if underlying yield doesn't have a `getRate` function
    if variable_rate is None:
        variable_rate = interface.get_standardized_variable_rate()

    # calculate bonds needed using iterative refinement
    _, bonds_needed = calc_reserves_to_hit_target_rate(
        interface=interface,
        pool_state=pool_state,
        target_rate=variable_rate,
        min_trade_amount_bonds=min_trade_amount_bonds,
    )
    bonds_needed = -bonds_needed  # we trade positive numbers around here
    # Reduce shorts first, if we have them
    for maturity_time, short in wallet.shorts.items():
        # TODO: Get time_between_blocks from the interface instead of hard-coding to 12
        curve_portion = maximum(
            FixedPoint(0),
            FixedPoint((maturity_time - pool_state.block_time + 12))
            / FixedPoint(interface.pool_config.position_duration),
        )
        if curve_portion > FixedPoint(0):
            logging.info("curve portion is %s\nbonds needed is %s", curve_portion, bonds_needed)
            reduce_short_amount = minimum(
                short.balance, bonds_needed / curve_portion, interface.calc_max_long(max_trade_amount_base, pool_state)
            )
            if reduce_short_amount > min_trade_amount_bonds:
                action_list.append(
                    close_short_trade(
                        reduce_short_amount, maturity_time, slippage_tolerance, base_fee_multiple, priority_fee_multiple
                    )
                )
    # Open a new long, if there's still a need, and we have money
    if max_trade_amount_base >= min_trade_amount_bonds and bonds_needed > min_trade_amount_bonds:
        max_long_shares = interface.calc_shares_in_given_bonds_out_down(
            interface.calc_max_long(max_trade_amount_base, pool_state), pool_state
        )
        shares_needed = interface.calc_shares_in_given_bonds_out_down(bonds_needed, pool_state)
        amount_base = minimum(
            shares_needed * pool_state.pool_info.vault_share_price,
            max_long_shares * pool_state.pool_info.vault_share_price,
            max_trade_amount_base,
        )
        action_list.append(open_long_trade(amount_base, slippage_tolerance, base_fee_multiple, priority_fee_multiple))
    return action_list


def arb_fixed_rate_up(
    interface: HyperdriveReadInterface,
    pool_state: PoolState,
    wallet: HyperdriveWallet,
    max_trade_amount_base: FixedPoint,
    min_trade_amount_bonds: FixedPoint,
    slippage_tolerance: FixedPoint | None = None,
    base_fee_multiple: float | None = None,
    priority_fee_multiple: float | None = None,
) -> list[Trade[HyperdriveMarketAction]]:
    """Return an action list for arbitraging the fixed rate up to the variable rate.

    Arguments
    ---------
    interface: HyperdriveReadInterface
        The Hyperdrive API interface object.
    pool_state: PoolState
        The hyperdrive pool state.
    wallet: HyperdriveWallet
        The agent's wallet.
    max_trade_amount_base: FixedPoint
        The maximum amount of base allowed to trade.
    min_trade_amount_bonds: FixedPoint
        The minimum amount of bonds needed to open a trade.
    slippage_tolerance: FixedPoint | None, optional
        The slippage tolerance for trades. Defaults to None.
    base_fee_multiple: float | None, optional
        The base fee multiple for transactions. Defaults to None.
    priority_fee_multiple: float | None, optional
        The priority fee multiple for transactions. Defaults to None.

    Returns
    -------
    list[MarketAction]
        A list of actions for arbitration trades.
    """
    action_list = []

    variable_rate = pool_state.variable_rate
    # Variable rate can be None if underlying yield doesn't have a `getRate` function
    if variable_rate is None:
        variable_rate = interface.get_standardized_variable_rate()

    # calculate bonds needed using iterative refinement
    _, bonds_needed = calc_reserves_to_hit_target_rate(
        interface=interface,
        pool_state=pool_state,
        target_rate=variable_rate,
        min_trade_amount_bonds=min_trade_amount_bonds,
    )
    # Reduce longs first, if we have them
    for maturity_time, long in wallet.longs.items():
        # TODO: Get time_between_blocks from the interface instead of hard-coding to 12
        curve_portion = maximum(
            FixedPoint(0),
            FixedPoint(maturity_time - pool_state.block_time + 12)
            / FixedPoint(interface.pool_config.position_duration),
        )
        if curve_portion > FixedPoint(0):
            logging.info("curve portion is %s\nbonds needed is %s", curve_portion, bonds_needed)
            reduce_long_amount = minimum(
                long.balance, bonds_needed / curve_portion, interface.calc_max_short(max_trade_amount_base, pool_state)
            )
            if reduce_long_amount > min_trade_amount_bonds:
                bonds_needed -= reduce_long_amount * curve_portion
                logging.debug("reducing long by %s", reduce_long_amount)
                action_list.append(
                    close_long_trade(
                        reduce_long_amount, maturity_time, slippage_tolerance, base_fee_multiple, priority_fee_multiple
                    )
                )
    # Open a new short, if there's still a need, and we have money
    if max_trade_amount_base >= min_trade_amount_bonds and bonds_needed > min_trade_amount_bonds:
        max_short = interface.calc_max_short(max_trade_amount_base, pool_state)
        # TODO calc_max_short seems to be a bit off wrt the budget we have, likely
        # due to the underlying calc_open_short being off. We subtract a small amount
        # from the max short for a fix for now to fix test.
        # https://github.com/delvtech/hyperdrive/issues/969
        max_short -= FixedPoint("0.1")
        amount_bonds = minimum(bonds_needed, max_short)
        action_list.append(open_short_trade(amount_bonds, slippage_tolerance, base_fee_multiple, priority_fee_multiple))
    return action_list


def calc_shares_needed_for_bonds(
    interface: HyperdriveReadInterface,
    pool_state: PoolState,
    bonds_needed: FixedPoint,
    min_trade_amount_bonds: FixedPoint,
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
    min_trade_amount_bonds: FixedPoint
        The minimum amount of bonds needed to open a trade.

    Returns
    -------
    FixedPoint
        The change in shares in the pool for the given amount of bonds.
    """
    if bonds_needed > min_trade_amount_bonds:  # need more bonds in pool -> user sells bonds -> user opens short
        delta = predict_short(hyperdrive_interface=interface, bonds=bonds_needed, pool_state=pool_state, for_pool=True)
    elif bonds_needed < -min_trade_amount_bonds:  # need less bonds in pool -> user buys bonds -> user opens long
        delta = predict_long(hyperdrive_interface=interface, bonds=-bonds_needed, pool_state=pool_state, for_pool=True)
    else:
        return FixedPoint(0)
    return abs(delta.pool.shares)


def calc_delta_reserves_for_target_rate(
    interface: HyperdriveReadInterface,
    pool_state: PoolState,
    target_rate: FixedPoint,
    min_trade_amount_bonds: FixedPoint,
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
    min_trade_amount_bonds: FixedPoint
        The minimum amount of bonds needed to open a trade.

    Returns
    -------
    tuple[FixedPoint, FixedPoint]
        The delta (bonds, shares) needed to hit the desired fixed rate.
    """
    divisor = FixedPoint(2)
    trade_delta_bonds = FixedPoint(0)
    target_bonds = interface.calc_bonds_given_shares_and_rate(target_rate=target_rate, pool_state=pool_state)
    avoid_negative_share_reserves = False
    # We want to take as large of a step as possible while avoiding negative share reserves.
    # So we loop through, increasing the divisor until the share reserves are no longer negative.
    pool_delta_shares = FixedPoint(0)
    while avoid_negative_share_reserves is False:
        trade_delta_bonds = (target_bonds - pool_state.pool_info.bond_reserves) / divisor
        pool_delta_shares = calc_shares_needed_for_bonds(
            interface, pool_state, trade_delta_bonds, min_trade_amount_bonds
        )
        # simulate pool state update without a deep copy to save time
        new_share_reserves, _ = apply_step_to_reserves(
            pool_state.pool_info.share_reserves,
            pool_delta_shares,
            pool_state.pool_info.bond_reserves,
            trade_delta_bonds,
        )
        avoid_negative_share_reserves = new_share_reserves >= 0
        divisor *= FixedPoint(2)
    return trade_delta_bonds, pool_delta_shares


def calc_reserves_to_hit_target_rate(
    interface: HyperdriveReadInterface,
    pool_state: PoolState,
    target_rate: FixedPoint,
    min_trade_amount_bonds: FixedPoint,
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
    min_trade_amount_bonds: FixedPoint
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
    logging.info("Targeting %.2f from %.2f", float(target_rate), float(interface.calc_spot_rate(pool_state)))
    while float(abs(predicted_rate - target_rate)) > TOLERANCE and iteration < MAX_ITER:
        iteration += 1
        latest_fixed_rate = interface.calc_spot_rate(temp_pool_state)
        # get the predicted reserve levels
        bonds_needed, shares_needed = calc_delta_reserves_for_target_rate(
            interface, temp_pool_state, target_rate, min_trade_amount_bonds
        )
        # get the fixed rate for an updated pool state, without storing the state variable
        # TODO: This deepcopy is slow. https://github.com/delvtech/agent0/issues/1355
        predicted_rate = interface.calc_spot_rate(
            apply_step_to_pool_state(deepcopy(temp_pool_state), bonds_needed, shares_needed)
        )
        # adjust guess up or down based on how much the first guess overshot or undershot
        overshoot_or_undershoot = FixedPoint(0)
        if (target_rate - latest_fixed_rate) != FixedPoint(0):
            overshoot_or_undershoot = (predicted_rate - latest_fixed_rate) / (target_rate - latest_fixed_rate)
        if overshoot_or_undershoot != FixedPoint(0):
            bonds_needed = bonds_needed / overshoot_or_undershoot
        shares_to_pool = calc_shares_needed_for_bonds(interface, temp_pool_state, bonds_needed, min_trade_amount_bonds)
        # update pool state with second guess and continue from there
        temp_pool_state = apply_step_to_pool_state(temp_pool_state, bonds_needed, shares_to_pool)
        predicted_rate = interface.calc_spot_rate(temp_pool_state)
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
        min_trade_amount_bonds: FixedPoint = FixedPoint(10)
        """The minimum bond trade amount below which the agent won't submit a trade."""

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
        self.min_trade_amount_bonds = policy_config.min_trade_amount_bonds
        super().__init__(policy_config)

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

        # compute these once to avoid race conditions
        current_pool_state = interface.current_pool_state
        current_fixed_rate = interface.calc_spot_rate(current_pool_state)

        # close matured positions
        self.close_matured_positions(wallet, current_pool_state, self.min_trade_amount_bonds)

        # open LP position
        max_trade_amount_base = wallet.balance.amount
        lp_amount = self.config.lp_portion * wallet.balance.amount  # type: ignore
        if wallet.lp_tokens == FixedPoint(0) and lp_amount > FixedPoint(0):  # type: ignore
            # Add liquidity
            action_list.append(
                add_liquidity_trade(
                    trade_amount=lp_amount,
                    base_fee_multiple=self.config.base_fee_multiple,
                    priority_fee_multiple=self.config.priority_fee_multiple,
                    min_apr=current_fixed_rate - self.config.rate_slippage,  # type: ignore
                    max_apr=current_fixed_rate + self.config.rate_slippage,  # type: ignore
                )
            )
            max_trade_amount_base -= lp_amount

        variable_rate = current_pool_state.variable_rate
        # Variable rate can be None if underlying yield doesn't have a `getRate` function
        if variable_rate is None:
            variable_rate = interface.get_standardized_variable_rate()

        # arbitrage from here on out
        # check for a high fixed rate
        if current_fixed_rate >= variable_rate + self.config.high_fixed_rate_thresh:  # type: ignore
            action_list.extend(
                arb_fixed_rate_down(
                    interface,
                    current_pool_state,
                    wallet,
                    max_trade_amount_base,
                    self.min_trade_amount_bonds,
                    self.slippage_tolerance,
                    self.config.base_fee_multiple,
                    self.config.priority_fee_multiple,
                )
            )

        # check for a low fixed rate
        if current_fixed_rate <= variable_rate - self.config.low_fixed_rate_thresh:  # type: ignore
            action_list.extend(
                arb_fixed_rate_up(
                    interface,
                    current_pool_state,
                    wallet,
                    max_trade_amount_base,
                    self.min_trade_amount_bonds,
                    self.slippage_tolerance,
                    self.config.base_fee_multiple,
                    self.config.priority_fee_multiple,
                )
            )

        if self.config.done_on_empty and len(action_list) == 0:  # type: ignore
            return [], True
        return action_list, False

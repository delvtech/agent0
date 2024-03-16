"""Agent policy for LP trading that can also arbitrage on the fixed rate."""

from __future__ import annotations

import logging
import time
from copy import deepcopy
from dataclasses import dataclass
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
from agent0.core.hyperdrive.agent.hyperdrive_wallet import Long
from agent0.core.utilities.predict import predict_long, predict_short
from agent0.ethpy.hyperdrive.state import PoolState

from .hyperdrive_policy import HyperdriveBasePolicy

if TYPE_CHECKING:
    from agent0.core.hyperdrive import HyperdriveWallet
    from agent0.ethpy.hyperdrive import HyperdriveReadInterface

# constants
TOLERANCE = 1e-18
MAX_ITER = 50

# TODO: we can either make these helper fns member functions of a parent class
# or we can make them static utils and pass the agent object itself. Either way,
# this will simplify the argument space down to a much smaller set.
# pylint: disable=too-many-arguments


def _measure_value(
    wallet: HyperdriveWallet,
    interface: HyperdriveReadInterface,
    pool_state: PoolState | None = None,
    spot_price: FixedPoint | None = None,
    block_time: int | None = None,
) -> tuple[FixedPoint, FixedPoint]:
    # either provide interface or all of the other arguments
    pool_state = interface.current_pool_state if pool_state is None else pool_state
    spot_price = interface.calc_spot_price(pool_state) if spot_price is None else spot_price
    block_time = interface.get_block_timestamp(interface.get_current_block()) if block_time is None else block_time
    assert isinstance(pool_state, PoolState), "pool_state must be a PoolState"
    assert isinstance(spot_price, FixedPoint), "spot_price must be a FixedPoint"
    assert isinstance(block_time, int), "block_time must be an int"

    position_duration = pool_state.pool_config.position_duration
    value = wallet.balance.amount  # base in wallet
    old_lp_share_price = pool_state.pool_info.lp_share_price
    logging.info("old_lp_share_price is %s", old_lp_share_price)
    logging.info("=== predicted_pool_state ===")
    for k,v in pool_state.__dict__.items():
        if k not in ["block", "pool_info", "pool_config"]:
            logging.info("%s : %s", k, v)
    logging.info("=== predicted_pool_info ===")    
    for k,v in pool_state.pool_info.__dict__.items():
        logging.info("%s : %s", k, v)
    new_lp_share_price = interface.calc_present_value(pool_state=pool_state) / pool_state.pool_info.lp_total_supply * pool_state.pool_info.vault_share_price
    logging.info("new_lp_share_price is %s (%s%.2f%%)", new_lp_share_price, "+" if new_lp_share_price > old_lp_share_price else "",(new_lp_share_price / old_lp_share_price - 1)* 100)
    # LP position
    simple_lp_value = wallet.lp_tokens * new_lp_share_price
    closeout_lp_value = wallet.lp_tokens * new_lp_share_price
    value += closeout_lp_value
    for maturity, long in wallet.longs.items():
        normalized_time_remaining = max(maturity - block_time, 0) / FixedPoint(position_duration)
        value += interface.calc_close_long(long.balance, normalized_time_remaining, pool_state)
    for maturity, short in wallet.shorts.items():
        normalized_time_remaining = max(maturity - block_time, 0) / FixedPoint(position_duration)
        open_checkpoint_time = maturity - position_duration
        open_share_price = interface.get_checkpoint(open_checkpoint_time).vault_share_price
        if block_time >= maturity:
            close_share_price = interface.get_checkpoint(maturity).vault_share_price
        else:
            close_share_price = pool_state.pool_info.vault_share_price
        value += interface.calc_close_short(
            short.balance,
            open_vault_share_price=open_share_price,
            close_vault_share_price=close_share_price,
            normalized_time_remaining=normalized_time_remaining,
            pool_state=pool_state,
        )
    return value, new_lp_share_price


def arb_fixed_rate_down(
    interface: HyperdriveReadInterface,
    pool_state: PoolState,
    wallet: HyperdriveWallet,
    max_trade_amount_base: FixedPoint,
    min_trade_amount_bonds: FixedPoint,
    arb_portion: FixedPoint,
    slippage_tolerance: FixedPoint | None = None,
) -> list[Trade[HyperdriveMarketAction]]:
    """Returns an action list for arbitraging the fixed rate down to the variable rate.

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
    arb_portion: FixedPoint
        The portion of the pool to arbitrage.
    slippage_tolerance: FixedPoint | None, optional
        The slippage tolerance for trades. Defaults to None.

    Returns
    -------
    list[MarketAction]
        A list of actions for arbitration trades.
    """
    action_list = []
    # calculate bonds needed using iterative refinement
    _, bonds_needed = calc_reserves_to_hit_target_rate(
        interface=interface,
        pool_state=pool_state,
        target_rate=pool_state.variable_rate,
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
        logging.info("curve portion is %s\nbonds needed is %s", curve_portion, bonds_needed)
        reduce_short_amount = minimum(
            short.balance, bonds_needed / curve_portion, interface.calc_max_long(wallet.balance.amount, pool_state)
        )
        if reduce_short_amount > min_trade_amount_bonds:
            bonds_needed -= reduce_short_amount * curve_portion
            logging.debug(
                "reducing short by %s\nreduce_short_amount*curve_portion = %s",
                reduce_short_amount,
                reduce_short_amount * curve_portion,
            )
            action_list.append(close_short_trade(reduce_short_amount, maturity_time, slippage_tolerance))
    # Open a new long, if there's still a need, and we have money
    if wallet.balance.amount >= min_trade_amount_bonds and bonds_needed > min_trade_amount_bonds:
        max_long_shares = interface.calc_shares_in_given_bonds_out_down(
            interface.calc_max_long(wallet.balance.amount, pool_state), pool_state
        )
        shares_needed = interface.calc_shares_in_given_bonds_out_down(bonds_needed, pool_state)
        amount_base = minimum(
            shares_needed * pool_state.pool_info.vault_share_price,
            max_long_shares * pool_state.pool_info.vault_share_price,
            max_trade_amount_base,
        )

        original_total_value, new_lp_share_price = _measure_value(wallet, interface)
        orignal_lp_value = wallet.lp_tokens * interface.current_pool_state.pool_info.lp_share_price
        original_arb_value = original_total_value - orignal_lp_value
        original_arb_portion = original_arb_value / original_total_value
        new_arb_portion = FixedPoint(1)
        iteration = 0
        while new_arb_portion > arb_portion:
            iteration += 1
            logging.info("=== iteration %s ===", iteration)
            new_block_time = interface.current_pool_state.block_time + 12
            new_maturity_time = new_block_time + interface.pool_config.position_duration
            predicted_pool_state = deepcopy(interface.current_pool_state)
            trade_outcome = predict_long(
                hyperdrive_interface=interface,
                pool_state=predicted_pool_state,
                base=amount_base,
            )
            predicted_wallet = deepcopy(wallet)
            predicted_long = Long(maturity_time=new_maturity_time, balance=trade_outcome.user.bonds)
            predicted_wallet.longs.update({new_maturity_time: predicted_long})
            logging.info("predicted_pool_state.pool_info.bond_reserves is %s", predicted_pool_state.pool_info.bond_reserves)
            predicted_pool_state.pool_info.bond_reserves += trade_outcome.pool.bonds
            logging.info("predicted_pool_state.pool_info.bond_reserves is %s", predicted_pool_state.pool_info.bond_reserves)
            logging.info("trade_outcome.pool.bonds is %s", trade_outcome.pool.bonds)
            logging.info("predicted_pool_state.pool_info.share_reserves is %s", predicted_pool_state.pool_info.share_reserves)
            predicted_pool_state.pool_info.share_reserves += trade_outcome.pool.shares
            logging.info("predicted_pool_state.pool_info.share_reserves is %s", predicted_pool_state.pool_info.share_reserves)
            new_long_average_maturity_time = (
                predicted_pool_state.pool_info.longs_outstanding * predicted_pool_state.pool_info.long_average_maturity_time
                + trade_outcome.user.bonds * new_maturity_time
                ) / ( predicted_pool_state.pool_info.longs_outstanding + trade_outcome.user.bonds )
            logging.info("new_long_average_maturity_time is %s (%s)", new_long_average_maturity_time, type(new_long_average_maturity_time))
            logging.info("predicted_pool_state.pool_info.longs_outstanding is %s (%s)", predicted_pool_state.pool_info.longs_outstanding, type(predicted_pool_state.pool_info.longs_outstanding))
            predicted_pool_state.pool_info.longs_outstanding += trade_outcome.user.bonds
            # predicted_pool_state.pool_info.long_exposure += trade_outcome.user.bonds
            predicted_pool_state.exposure -= trade_outcome.user.bonds
            predicted_pool_state.exposure = FixedPoint(-129338.867334504463130003)
            logging.info("predicted_pool_state.pool_info.longs_outstanding is %s (%s)", predicted_pool_state.pool_info.longs_outstanding, type(predicted_pool_state.pool_info.longs_outstanding))
            logging.info("predicted_pool_state.pool_info.long_average_maturity_time is %s (%s)", predicted_pool_state.pool_info.long_average_maturity_time, type(predicted_pool_state.pool_info.long_average_maturity_time))
            predicted_pool_state.pool_info.long_average_maturity_time = new_long_average_maturity_time
            logging.info("predicted_pool_state.pool_info.long_average_maturity_time is %s (%s)", predicted_pool_state.pool_info.long_average_maturity_time, type(predicted_pool_state.pool_info.long_average_maturity_time))
            logging.info("trade_outcome.pool.shares is %s", trade_outcome.pool.shares)
            logging.info("predicted_pool_state.pool_info is %s", predicted_pool_state.pool_info)
            old_spot_price = interface.calc_spot_price()
            logging.info("old_spot_price is %s", old_spot_price)
            new_spot_price = interface.calc_spot_price(pool_state=predicted_pool_state)
            logging.info("new_spot_price is %s", new_spot_price)
            delta_spot_price = new_spot_price - old_spot_price
            logging.info("delta_spot_price is %s (%.2f%%)", delta_spot_price, delta_spot_price / old_spot_price * 100)
            # new_total_value, new_lp_share_price = _measure_value(
            #     interface=interface,
            #     wallet=predicted_wallet,
            #     pool_state=predicted_pool_state,
            #     spot_price=new_spot_price,
            #     block_time=new_block_time,
            # )
            # logging.info("new_total_value is %s", new_total_value)
            # new_lp_value = predicted_wallet.lp_tokens * new_lp_share_price
            # logging.info("new_lp_value is %s", new_lp_value)
            # new_arb_value = new_total_value - new_lp_value
            # logging.info("new_arb_value is %s", new_arb_value)
            # new_arb_portion = new_arb_value / new_total_value
            # logging.info("new_arb_portion is %s", new_arb_portion)
            # overshoot_or_undershoot = (new_arb_portion - original_arb_portion) / (arb_portion - original_arb_portion)
            # logging.info("overshoot_or_undershoot is %s", overshoot_or_undershoot)

            # # update trade size
            # logging.info("amount_base is %s", old_amount_base := amount_base)
            # amount_base /= overshoot_or_undershoot
            # logging.info("amount_base is %s (%.2f%%)", amount_base, (amount_base / old_amount_base - 1) * 100)

            # # update prediction
            # predicted_pool_state = deepcopy(interface.current_pool_state)
            # trade_outcome = predict_long(
            #     hyperdrive_interface=interface,
            #     pool_state=predicted_pool_state,
            #     base=amount_base,
            # )
            # predicted_wallet = deepcopy(wallet)
            # predicted_long = Long(maturity_time=new_maturity_time, balance=trade_outcome.user.bonds)
            # predicted_wallet.longs.update({new_maturity_time: predicted_long})
            # predicted_pool_state.pool_info.bond_reserves += trade_outcome.pool.bonds
            # logging.info("trade_outcome.pool.bonds is %s", trade_outcome.pool.bonds)
            # predicted_pool_state.pool_info.share_reserves += trade_outcome.pool.shares
            # new_long_average_maturity_time = (
            #     predicted_pool_state.pool_info.longs_outstanding * predicted_pool_state.pool_info.long_average_maturity_time
            #     + trade_outcome.user.bonds * new_maturity_time
            #     ) / ( predicted_pool_state.pool_info.longs_outstanding + trade_outcome.user.bonds )
            # predicted_pool_state.pool_info.longs_outstanding += trade_outcome.user.bonds
            # # predicted_pool_state.pool_info.long_exposure += trade_outcome.user.bonds
            # # predicted_pool_state.pool_info.long_average_maturity_time = new_long_average_maturity_time

            # # update new_arb_portion
            # new_spot_price = interface.calc_spot_price(pool_state=predicted_pool_state)
            # new_lp_share_price = predicted_pool_state.pool_info.lp_share_price
            # new_total_value, new_lp_share_price = _measure_value(
            #     interface=interface,
            #     wallet=predicted_wallet,
            #     pool_state=predicted_pool_state,
            #     spot_price=new_spot_price,
            #     block_time=new_block_time,
            # )
            # new_lp_value = predicted_wallet.lp_tokens * new_lp_share_price
            # new_arb_value = new_total_value - new_lp_value
            # new_arb_portion = new_arb_value / new_total_value
            new_arb_portion = FixedPoint(0)
            # logging.info("new_arb_portion is %s", new_arb_portion)
            # time.sleep(0.5)

        action_list.append(open_long_trade(amount_base, slippage_tolerance))
    return action_list


def arb_fixed_rate_up(
    interface: HyperdriveReadInterface,
    pool_state: PoolState,
    wallet: HyperdriveWallet,
    max_trade_amount_base: FixedPoint,
    min_trade_amount_bonds: FixedPoint,
    slippage_tolerance: FixedPoint | None = None,
) -> list[Trade[HyperdriveMarketAction]]:
    """Returns an action list for arbitraging the fixed rate up to the variable rate.

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

    Returns
    -------
    list[MarketAction]
        A list of actions for arbitration trades.
    """
    action_list = []
    # calculate bonds needed using iterative refinement
    _, bonds_needed = calc_reserves_to_hit_target_rate(
        interface=interface,
        pool_state=pool_state,
        target_rate=pool_state.variable_rate,
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
        logging.info("curve portion is %s\nbonds needed is %s", curve_portion, bonds_needed)
        reduce_long_amount = minimum(
            long.balance, bonds_needed / curve_portion, interface.calc_max_short(wallet.balance.amount, pool_state)
        )
        if reduce_long_amount > min_trade_amount_bonds:
            bonds_needed -= reduce_long_amount * curve_portion
            logging.debug("reducing long by %s", reduce_long_amount)
            action_list.append(close_long_trade(reduce_long_amount, maturity_time, slippage_tolerance))
    # Open a new short, if there's still a need, and we have money
    if wallet.balance.amount >= min_trade_amount_bonds and bonds_needed > min_trade_amount_bonds:
        amount_bonds = minimum(bonds_needed, interface.calc_max_short(max_trade_amount_base, pool_state))
        action_list.append(open_short_trade(amount_bonds, slippage_tolerance))
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
    target_bonds = interface.calc_bonds_given_shares_and_rate(
        target_rate=target_rate, target_shares=pool_state.pool_info.share_reserves, pool_state=pool_state
    )
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
    logging.info("Targeting %.2f from %.2f", float(target_rate), float(interface.calc_fixed_rate(pool_state)))
    while float(abs(predicted_rate - target_rate)) > TOLERANCE and iteration < MAX_ITER:
        iteration += 1
        latest_fixed_rate = interface.calc_fixed_rate(temp_pool_state)
        # get the predicted reserve levels
        bonds_needed, shares_needed = calc_delta_reserves_for_target_rate(
            interface, temp_pool_state, target_rate, min_trade_amount_bonds
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
        shares_to_pool = calc_shares_needed_for_bonds(interface, temp_pool_state, bonds_needed, min_trade_amount_bonds)
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
        self.policy_config = policy_config
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
        current_fixed_rate = interface.calc_fixed_rate(current_pool_state)

        # close matured positions
        self.close_matured_positions(wallet, current_pool_state, self.min_trade_amount_bonds)

        # open LP position
        max_trade_amount_base = wallet.balance.amount
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
            max_trade_amount_base -= lp_amount

        # arbitrage from here on out
        # check for a high fixed rate
        if current_fixed_rate >= current_pool_state.variable_rate + self.policy_config.high_fixed_rate_thresh:
            action_list.extend(
                arb_fixed_rate_down(
                    interface,
                    current_pool_state,
                    wallet,
                    max_trade_amount_base,
                    self.min_trade_amount_bonds,
                    self.policy_config.arb_portion,
                    self.slippage_tolerance,
                )
            )

        # check for a low fixed rate
        if current_fixed_rate <= current_pool_state.variable_rate - self.policy_config.low_fixed_rate_thresh:
            action_list.extend(
                arb_fixed_rate_up(
                    interface,
                    current_pool_state,
                    wallet,
                    max_trade_amount_base,
                    self.min_trade_amount_bonds,
                    self.slippage_tolerance,
                )
            )

        if self.policy_config.done_on_empty and len(action_list) == 0:
            return [], True
        return action_list, False

"""Agent policy for LP trading that can also arbitrage on the fixed rate."""

from __future__ import annotations

import logging
import time
from copy import deepcopy
from dataclasses import dataclass
from statistics import mean
from typing import TYPE_CHECKING

from agent0.hyperdrive.agent.hyperdrive_wallet import Long
from ethpy.hyperdrive.state import PoolState
from fixedpointmath import FixedPoint

from agent0.base import Trade
from agent0.hyperdrive import HyperdriveMarketAction
from agent0.hyperdrive.agent import (
    add_liquidity_trade,
    close_long_trade,
    close_short_trade,
    open_long_trade,
    open_short_trade,
)
from agent0.utilities.predict import predict_long, predict_short

from .hyperdrive_policy import HyperdriveBasePolicy

if TYPE_CHECKING:
    from ethpy.hyperdrive import HyperdriveReadInterface

    from agent0.hyperdrive import HyperdriveWallet

# pylint: disable=too-many-arguments, too-many-locals

# constants
TOLERANCE = 1e-18
MAX_ITER = 50


def calc_shares_needed_for_bonds(
    bonds_needed: FixedPoint,
    pool_state: PoolState,
    interface: HyperdriveReadInterface,
    minimum_trade_amount: FixedPoint,
) -> FixedPoint:
    """Calculate the shares needed to trade a certain amount of bonds, and the associate governance fee.

    Arguments
    ---------
    bonds_needed: FixedPoint
        The given amount of bonds that is going to be traded.
    pool_state: PoolState
        The hyperdrive pool state.
    interface: HyperdriveReadInterface
        The Hyperdrive API interface object.
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


def calc_reserves_to_hit_target_rate(
    target_rate: FixedPoint, interface: HyperdriveReadInterface, minimum_trade_amount: FixedPoint
) -> tuple[FixedPoint, FixedPoint, int, float]:
    """Calculate the bonds and shares needed to hit the target fixed rate.

    Arguments
    ---------
    target_rate: FixedPoint
        The target rate the pool will have after the calculated change in bonds and shares.
    interface: HyperdriveReadInterface
        The Hyperdrive API interface object.
    minimum_trade_amount: FixedPoint
        The minimum amount of bonds needed to open a trade.

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
    logging.info(f"Targeting {float(target_rate):.2%} from {float(interface.calc_fixed_rate()):.2%}")
    while float(abs(predicted_rate - target_rate)) > TOLERANCE and iteration < MAX_ITER:
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
            shares_to_pool = calc_shares_needed_for_bonds(bonds_needed, pool_state, interface, minimum_trade_amount)
            # save bad first guess to a temporary variable
            temp_pool_state = apply_step(deepcopy(pool_state), bonds_needed, shares_to_pool)
            predicted_rate = interface.calc_fixed_rate(temp_pool_state)
            avoid_negative_share_reserves = temp_pool_state.pool_info.share_reserves >= 0
            divisor *= FixedPoint(2)
        # adjust guess up or down based on how much the first guess overshot or undershot
        overshoot_or_undershoot = FixedPoint(0)
        if (target_rate - latest_fixed_rate) != FixedPoint(0):
            overshoot_or_undershoot = (predicted_rate - latest_fixed_rate) / (target_rate - latest_fixed_rate)
        if overshoot_or_undershoot != FixedPoint(0):
            bonds_needed = bonds_needed / overshoot_or_undershoot
        shares_to_pool = calc_shares_needed_for_bonds(bonds_needed, pool_state, interface, minimum_trade_amount)
        # update pool state with second guess and continue from there
        pool_state = apply_step(pool_state, bonds_needed, shares_to_pool)
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
        logging.info(formatted_str)
    convergence_speed = time.time() - start_time
    formatted_str = f"predicted precision: {float(abs(predicted_rate-target_rate))}, time taken: {convergence_speed}s"
    logging.info(formatted_str)
    return total_shares_needed, total_bonds_needed, iteration, convergence_speed


def apply_step(
    pool_state: PoolState,
    bonds_needed: FixedPoint,
    shares_to_pool: FixedPoint,
) -> PoolState:
    """Save a single convergence step into the pool info.

    Arguments
    ---------
    pool_state: PoolState
        The current pool state.
    bonds_needed: FixedPoint
        The amount of bonds that is going to be traded.
    shares_to_pool: FixedPoint
        The amount of shares that is going to be traded.

    Returns
    -------
    PoolState
        The updated pool state.
    """
    if bonds_needed > 0:  # short case
        pool_state.pool_info.share_reserves += -shares_to_pool  # take shares out of pool
    else:  # long case
        pool_state.pool_info.share_reserves += shares_to_pool  # put shares in pool
    pool_state.pool_info.bond_reserves += bonds_needed
    return pool_state


def _measure_value(
    wallet: HyperdriveWallet,
    interface: HyperdriveReadInterface | None = None,
    pool_state: PoolState | None = None,
    spot_price: FixedPoint | None = None,
    block_time: int | None = None,
) -> FixedPoint:
    # either provide interface or all of the other arguments
    if interface is not None:
        assert all(
            arg is None for arg in [pool_state, spot_price, block_time]
        ), "must provide interface or pool_state, spot_price, and block_time"
        pool_state = interface.current_pool_state
        spot_price = interface.calc_spot_price(pool_state)
        block_time = interface.get_block_timestamp(interface.get_current_block())
    # measure value
    assert isinstance(pool_state, PoolState), "pool_state must be a PoolState"
    assert isinstance(spot_price, FixedPoint), "spot_price must be a FixedPoint"
    assert isinstance(block_time, int), "block_time must be an int"
    lp_share_price = pool_state.pool_info.lp_share_price
    vault_share_price = pool_state.pool_info.vault_share_price
    term_length = pool_state.pool_config.position_duration
    value = wallet.lp_tokens * lp_share_price  # LP position
    value += wallet.balance.amount  # base
    for maturity, long in wallet.longs.items():
        time_remaining = FixedPoint((maturity - block_time) / term_length)
        logging.info("time remaining is %s", time_remaining)
        curve_price = time_remaining * spot_price
        logging.info("curve price is %s", curve_price)
        flat_price = 1 - time_remaining
        logging.info("flat price is %s", flat_price)
        pull_to_par = curve_price + flat_price
        logging.info("pull to par is %s", pull_to_par)
        long_value = long.balance * pull_to_par
        logging.info("long value is %s", long_value)
        value += long_value
    for maturity, short in wallet.shorts.items():
        time_remaining = FixedPoint((maturity - block_time) / term_length)
        # Short value = users_shorts * (vault_share_price / open_vault_share_price)
        #           - users_shorts * time_remaining * spot_price
        #           - users_shorts * (1 - time_remaining)
        print(f"{short.open_vault_share_price=}")
        variable_interest_received = vault_share_price / short.open_vault_share_price
        curve_price = time_remaining * spot_price
        flat_price = 1 - time_remaining
        # Short value = user_shorts * (variable_interest_received - curve_price - flat_price)
        pull_to_par = curve_price + flat_price
        # Short value = user_shorts * (variable_interest_received - pull_to_par)
        short_value = short.balance * (variable_interest_received - pull_to_par)
        value += short_value
    return value


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

    # pylint: disable=too-many-branches, too-many-statements
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
        if wallet.lp_tokens == FixedPoint(0) and lp_amount > FixedPoint(0) and lp_amount > self.minimum_trade_amount:
            # Add liquidity
            action_list.append(
                add_liquidity_trade(
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
                action_list.append(close_long_trade(long.balance, maturity_time, self.slippage_tolerance))
        # Close shorts if matured
        for maturity_time, short in wallet.shorts.items():
            # If matured
            if maturity_time < interface.current_pool_state.block_time and short.balance > self.minimum_trade_amount:
                action_list.append(close_short_trade(short.balance, maturity_time, self.slippage_tolerance))

        # calculate bonds and shares needed if we're arbitraging in either direction
        spot_price = FixedPoint(0)
        bonds_needed = FixedPoint(0)
        base_budget = FixedPoint(0)
        if high_fixed_rate_detected or low_fixed_rate_detected:
            spot_price = interface.calc_spot_price()
            _, bonds_needed, iters, speed = calc_reserves_to_hit_target_rate(
                target_rate=interface.current_pool_state.variable_rate,
                interface=interface,
                minimum_trade_amount=self.minimum_trade_amount,
            )
            total_value = _measure_value(wallet, interface)
            arb_budget = total_value * self.policy_config.arb_portion
            lp_budget = total_value * self.policy_config.lp_portion
            lp_value = wallet.lp_tokens * interface.current_pool_state.pool_info.lp_share_price
            base_budget = min(arb_budget, wallet.balance.amount)
            logging.info("arb_budget  is %s", arb_budget)
            logging.info("lp_budget   is %s", lp_budget)
            logging.info("  => usage  is %s (%.2f%%)", lp_value, lp_value / lp_budget * 100)
            logging.info("base_budget is %s", base_budget)
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
                    max_long_bonds = interface.calc_max_long(base_budget)
                    current_block_time = interface.current_pool_state.block_time
                    next_block_time = current_block_time + 12
                    curve_portion = FixedPoint(
                        max(0, (maturity_time - next_block_time) / interface.pool_config.position_duration)
                    )
                    logging.info("curve portion is %s", curve_portion)
                    logging.info("bonds needed is %s", bonds_needed)
                    reduce_short_amount = min(short.balance, bonds_needed / curve_portion, max_long_bonds)
                    if reduce_short_amount > self.minimum_trade_amount:
                        bonds_needed -= reduce_short_amount * curve_portion
                        logging.info("reducing short by %s", reduce_short_amount)
                        logging.info("reduce_short_amount*curve_portion = %s", reduce_short_amount * curve_portion)
                        action_list.append(
                            close_short_trade(reduce_short_amount, maturity_time, self.slippage_tolerance)
                        )
            # Open a new long, if there's still a need, and we have money
            if we_have_money and bonds_needed > self.minimum_trade_amount:
                max_long_base = interface.calc_max_long(budget=base_budget)
                logging.info("max long base is %s", max_long_base)
                shares_needed = interface.calc_shares_in_given_bonds_out_down(bonds_needed)
                logging.info("shares needed is %s", shares_needed)
                amount_base = min(
                    shares_needed * interface.current_pool_state.pool_info.vault_share_price, max_long_base
                )
                original_total_value = _measure_value(wallet, interface)
                orignal_lp_value = wallet.lp_tokens * interface.current_pool_state.pool_info.lp_share_price
                original_arb_value = original_total_value - orignal_lp_value
                original_arb_portion = original_arb_value / original_total_value
                new_arb_portion = FixedPoint(1)
                iteration = 0
                while new_arb_portion > self.policy_config.arb_portion:
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
                    predicted_pool_state.pool_info.bond_reserves += trade_outcome.pool.bonds
                    # predicted_pool_state.pool_info.bond_reserves = FixedPoint(1797791407.896132777930667096)
                    logging.info("trade_outcome.pool.bonds is %s", trade_outcome.pool.bonds)
                    predicted_pool_state.pool_info.share_reserves += trade_outcome.pool.shares
                    # predicted_pool_state.pool_info.share_reserves = FixedPoint(599964099.646531164548583477)
                    # predicted_pool_state.pool_info.lp_share_price = FixedPoint(1.000145669748435808)
                    # predicted_pool_state.pool_info.vault_share_price = FixedPoint(1.000000133181130312)
                    # predicted_pool_state.pool_info.longs_outstanding = FixedPoint(99870661.132665495726221672)
                    # predicted_pool_state.pool_info.long_average_maturity_time = FixedPoint(1742054400.0)
                    logging.info("trade_outcome.pool.shares is %s", trade_outcome.pool.shares)
                    logging.info("predicted_pool_state.pool_info is %s", predicted_pool_state.pool_info)
                    old_spot_price = interface.calc_spot_price()
                    logging.info("old_spot_price is %s", old_spot_price)
                    new_spot_price = interface.calc_spot_price(pool_state=predicted_pool_state)
                    logging.info("new_spot_price is %s", new_spot_price)
                    delta_spot_price = new_spot_price - old_spot_price
                    logging.info(
                        "delta_spot_price is %s (%.2f%%)", delta_spot_price, delta_spot_price / old_spot_price * 100
                    )
                    new_lp_share_price = predicted_pool_state.pool_info.lp_share_price
                    new_total_value = _measure_value(
                        predicted_wallet,
                        pool_state=predicted_pool_state,
                        spot_price=new_spot_price,
                        block_time=new_block_time,
                    )
                    logging.info("new_total_value is %s", new_total_value)
                    new_lp_value = predicted_wallet.lp_tokens * new_lp_share_price
                    logging.info("new_lp_value is %s", new_lp_value)
                    new_arb_value = new_total_value - new_lp_value
                    logging.info("new_arb_value is %s", new_arb_value)
                    new_arb_portion = new_arb_value / new_total_value
                    logging.info("new_arb_portion is %s", new_arb_portion)
                    overshoot_or_undershoot = (new_arb_portion - original_arb_portion) / (
                        self.policy_config.arb_portion - original_arb_portion
                    )
                    logging.info("overshoot_or_undershoot is %s", overshoot_or_undershoot)

                    # update trade size
                    logging.info("amount_base is %s", old_amount_base := amount_base)
                    amount_base /= overshoot_or_undershoot
                    logging.info("amount_base is %s (%.2f%%)", amount_base, (amount_base / old_amount_base - 1) * 100)

                    # update prediction
                    predicted_pool_state = deepcopy(interface.current_pool_state)
                    trade_outcome = predict_long(
                        hyperdrive_interface=interface,
                        pool_state=predicted_pool_state,
                        base=amount_base,
                    )
                    predicted_wallet = deepcopy(wallet)
                    predicted_long = Long(maturity_time=new_maturity_time, balance=trade_outcome.user.bonds)
                    predicted_wallet.longs.update({new_maturity_time: predicted_long})
                    predicted_pool_state.pool_info.bond_reserves += trade_outcome.pool.bonds
                    # predicted_pool_state.pool_info.bond_reserves = FixedPoint(1797791407.896132777930667096)
                    logging.info("trade_outcome.pool.bonds is %s", trade_outcome.pool.bonds)
                    predicted_pool_state.pool_info.share_reserves += trade_outcome.pool.shares

                    # update new_arb_portion
                    new_spot_price = interface.calc_spot_price(pool_state=predicted_pool_state)
                    new_lp_share_price = predicted_pool_state.pool_info.lp_share_price
                    new_total_value = _measure_value(
                        predicted_wallet,
                        pool_state=predicted_pool_state,
                        spot_price=new_spot_price,
                        block_time=new_block_time,
                    )
                    new_lp_value = predicted_wallet.lp_tokens * new_lp_share_price
                    new_arb_value = new_total_value - new_lp_value
                    new_arb_portion = new_arb_value / new_total_value
                    logging.info("new_arb_portion is %s", new_arb_portion)
                    time.sleep(0.5)
                action_list.append(open_long_trade(amount_base, self.slippage_tolerance))

        if low_fixed_rate_detected:
            # Reduce longs first, if we have them
            if len(wallet.longs) > 0:
                for maturity_time, long in wallet.longs.items():
                    max_short_bonds = interface.calc_max_short(base_budget)
                    current_block_time = interface.current_pool_state.block_time
                    next_block_time = current_block_time + 12
                    curve_portion = FixedPoint(
                        max(0, (maturity_time - next_block_time) / interface.pool_config.position_duration)
                    )
                    logging.info("curve portion is %s", curve_portion)
                    logging.info("bonds needed is %s", bonds_needed)
                    reduce_long_amount = min(long.balance, bonds_needed / curve_portion, max_short_bonds)
                    if reduce_long_amount > self.minimum_trade_amount:
                        bonds_needed -= reduce_long_amount * curve_portion
                        logging.debug("reducing long by %s", reduce_long_amount)
                        action_list.append(close_long_trade(reduce_long_amount, maturity_time, self.slippage_tolerance))
            # Open a new short, if there's still a need, and we have money
            if we_have_money and bonds_needed > self.minimum_trade_amount:
                max_short_base = interface.calc_max_short(base_budget)
                max_short_bonds = max_short_base / spot_price
                amount_bonds = min(bonds_needed, max_short_bonds)
                action_list.append(open_short_trade(amount_bonds, self.slippage_tolerance))

        if self.policy_config.done_on_empty and len(action_list) == 0:
            return [], True
        return action_list, False

"""Return a list of results from opening a random longs and shorts."""

from __future__ import annotations

from typing import Literal, overload

import numpy as np
from fixedpointmath import FixedPoint
from numpy.random import Generator

from agent0.core.hyperdrive import HyperdriveActionType
from agent0.core.hyperdrive.interactive import LocalChain, LocalHyperdrive
from agent0.core.hyperdrive.interactive.event_types import OpenLong, OpenShort
from agent0.core.hyperdrive.interactive.local_hyperdrive_agent import LocalHyperdriveAgent


def execute_random_trades(
    num_trades: int,
    chain: LocalChain,
    rng: Generator,
    interactive_hyperdrive: LocalHyperdrive,
    advance_time: bool = False,
) -> list[tuple[LocalHyperdriveAgent, OpenLong | OpenShort]]:
    """Conduct some trades specified by the trade list.
    If advance time is true, the sum of all time passed between all trades will be between 0 and the position duration.

    Arguments
    ---------
    num_trades: int
        The number of trades to execute.
    chain: LocalChain
        An instantiated LocalChain.
    rng: `Generator <https://numpy.org/doc/stable/reference/random/generator.html>`_
        The numpy Generator provides access to a wide range of distributions, and stores the random state.
    interactive_hyperdrive: InteractiveHyperdrive
        An instantiated InteractiveHyperdrive object.
    advance_time: bool, optional
        If True, advance time a random amount between 0 and the position duration after each trade.
        Defaults to False, which follows the anvil settings.
        Typically this advances one block and 12 seconds between each trade.

    Returns
    -------
    list[tuple[InteractiveHyperdriveAgent, OpenLong | OpenShort]]
        A list with an entry per trade, containing a tuple with:
            - the agent executing the trade
            - either the OpenLong or OpenShort trade event
    """
    time_diffs = None
    if advance_time:
        # Generate the total time elapsed for all trades
        max_advance_time = rng.integers(low=0, high=interactive_hyperdrive.interface.pool_config.position_duration)
        # Generate intermediate points between 0 and max_advance_time, sorted in ascending order
        # Generating number of trades + 1 since cumulative diff results in one less
        intermediate_points = np.sort(rng.integers(low=0, high=max_advance_time, size=num_trades + 1))
        # Find cumulative differences of intermediate points for how much time to wait between each trade
        time_diffs = np.diff(intermediate_points)

    # Generate a list of trades
    available_actions = np.array([HyperdriveActionType.OPEN_LONG, HyperdriveActionType.OPEN_SHORT])
    # Do the trades
    trade_events: list[tuple[LocalHyperdriveAgent, OpenLong | OpenShort]] = []
    for trade_index, trade_type in enumerate([rng.choice(available_actions, size=1)[0] for _ in range(num_trades)]):
        trade_amount = _get_open_trade_amount(trade_type, rng, interactive_hyperdrive)
        # the short trade amount is technically bonds, but we know that will be less than the required base
        agent = chain.init_agent(base=trade_amount, eth=FixedPoint(100), pool=interactive_hyperdrive)
        trade_event = _execute_trade(trade_type, trade_amount, agent)
        trade_events.append((agent, trade_event))
        if advance_time:
            # Advance a random amount of time between opening trades
            assert time_diffs is not None
            chain.advance_time(
                time_diffs[trade_index],
                create_checkpoints=True,
            )
    return trade_events


def _get_open_trade_amount(
    trade_type: HyperdriveActionType,
    rng: Generator,
    interactive_hyperdrive: LocalHyperdrive,
    max_budget: FixedPoint = FixedPoint("1e9"),
    percent_max: FixedPoint = FixedPoint("0.75"),
) -> FixedPoint:
    """Get a trade amount for a given trade and Hyperdrive pool.

    Arguments
    ---------
    trade_type: HyperdriveActionType
        A trade to be executed on the Hyperdrive pool.
    rng: `Generator <https://numpy.org/doc/stable/reference/random/generator.html>`_
        The numpy Generator provides access to a wide range of distributions, and stores the random state.
    interactive_hyperdrive: InteractiveHyperdrive
        An instantiated InteractiveHyperdrive object.
    max_budget: FixedPoint, optional
        An optional amount to set an upper bound for the trade, defaults to FixedPoint("1e9").
    percent_max: FixedPoint, optional
        A percentage of the max trade to use for the upper bound for the trade, defaults to FixedPoint("0.75").

    Returns
    -------
    FixedPoint
        The trade amount, bound by the min & max amount allowed.
    """
    min_trade = interactive_hyperdrive.interface.pool_config.minimum_transaction_amount
    match trade_type:
        case HyperdriveActionType.OPEN_LONG:
            max_trade = interactive_hyperdrive.interface.calc_max_long(
                max_budget, interactive_hyperdrive.interface.current_pool_state
            )
        case HyperdriveActionType.OPEN_SHORT:
            max_trade = interactive_hyperdrive.interface.calc_max_short(
                max_budget, interactive_hyperdrive.interface.current_pool_state
            )
        case _:
            raise ValueError(f"Invalid {trade_type=}\nOnly opening trades are allowed.")

    max_trade = max_trade * percent_max
    return FixedPoint(scaled_value=int(np.floor(rng.uniform(low=min_trade.scaled_value, high=max_trade.scaled_value))))


@overload
def _execute_trade(
    trade_type: Literal[HyperdriveActionType.OPEN_LONG], trade_amount: FixedPoint, agent: LocalHyperdriveAgent
) -> OpenLong: ...


@overload
def _execute_trade(
    trade_type: Literal[HyperdriveActionType.OPEN_SHORT], trade_amount: FixedPoint, agent: LocalHyperdriveAgent
) -> OpenShort: ...


def _execute_trade(
    trade_type: HyperdriveActionType, trade_amount: FixedPoint, agent: LocalHyperdriveAgent
) -> OpenLong | OpenShort:
    """Execute a trade given the type, amount, and agent.

    Arguments
    ---------
    trade_type: HyperdriveActionType
        A trade to be executed on the Hyperdrive pool.
        Must be open long or open short.
    trade_amount: FixedPoint
        A valid (between pool and agent wallet min & max) amount of base or bonds to be traded.
        The unit changes depending on the trade type, where long uses base and short uses bonds.
    agent: InteractiveHyperdriveAgent
        An agent to use for executing the trade.
        It must have enough base in its wallet.

    Returns
    -------
    OpenLong | OpenShort
        The receipt for the given trade.
    """
    match trade_type:
        case HyperdriveActionType.OPEN_LONG:
            trade_event = agent.open_long(base=trade_amount)
        case HyperdriveActionType.OPEN_SHORT:
            trade_event = agent.open_short(bonds=trade_amount)
        case _:
            raise ValueError(f"{trade_type=} is not supported.")
    return trade_event

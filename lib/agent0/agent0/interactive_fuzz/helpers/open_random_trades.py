"""Return a list of results from opening a random longs and shorts."""
from __future__ import annotations

from fixedpointmath import FixedPoint
from numpy.random._generator import Generator

from agent0.hyperdrive.interactive import InteractiveHyperdrive, LocalChain
from agent0.hyperdrive.interactive.event_types import OpenLong, OpenShort
from agent0.hyperdrive.interactive.interactive_hyperdrive_agent import InteractiveHyperdriveAgent
from agent0.hyperdrive.state.hyperdrive_actions import HyperdriveActionType


def open_random_trades(
    trade_list: list[tuple[InteractiveHyperdriveAgent, HyperdriveActionType, FixedPoint]],
    chain: LocalChain,
    rng: Generator,
    interactive_hyperdrive: InteractiveHyperdrive,
    advance_time: bool = False,
) -> list[tuple[InteractiveHyperdriveAgent, OpenLong | OpenShort]]:
    """Open some trades specified by the trade list.

    Arguments
    ---------
    trade_list: list[tuple[InteractiveHyperdriveAgent, HyperdriveActionType, FixedPoint]]
        Each element in the returned list is a tuple containing
            - an agent
            - a trade for that agent
            - the trade amount in base
    chain: LocalChain
        An instantiated LocalChain.
    rng: `Generator <https://numpy.org/doc/stable/reference/random/generator.html>`_
        The numpy Generator provides access to a wide range of distributions, and stores the random state.
    interactive_hyperdrive: InteractiveHyperdrive
        An instantiated InteractiveHyperdrive object.
    advance_time: bool, optional
        If True, advance time a random amount between 0 and the position duration after each trade.
        Defaults to False.

    Returns
    -------
    list[tuple[InteractiveHyperdriveAgent, OpenLong | OpenShort]]
        A list with an entry per trade, containing a tuple with:
            - the agent executing the trade
            - either the OpenLong or OpenShort trade event
    """
    trade_events: list[tuple[InteractiveHyperdriveAgent, OpenLong | OpenShort]] = []
    for trade in trade_list:
        agent, trade_type, trade_amount = trade
        if trade_type == HyperdriveActionType.OPEN_LONG:
            trade_event = agent.open_long(base=trade_amount)
        elif trade_type == HyperdriveActionType.OPEN_SHORT:
            trade_event = agent.open_short(bonds=trade_amount)
        else:
            raise AssertionError(f"{trade_type=} is not supported.")
        trade_events.append((agent, trade_event))
        if advance_time:
            # Advance a random amount of time between opening trades
            chain.advance_time(
                rng.integers(
                    low=0,
                    high=interactive_hyperdrive.hyperdrive_interface.pool_config.position_duration,
                )
            )
    return trade_events

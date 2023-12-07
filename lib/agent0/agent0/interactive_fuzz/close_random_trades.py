"""Close trades in a random order."""
from __future__ import annotations

from numpy.random._generator import Generator

from agent0.hyperdrive.interactive.event_types import OpenLong, OpenShort
from agent0.hyperdrive.interactive.interactive_hyperdrive_agent import InteractiveHyperdriveAgent


def close_random_trades(
    trade_events: list[tuple[InteractiveHyperdriveAgent, OpenLong | OpenShort]], rng: Generator
) -> None:
    """Close trades provided in a random order.

    Arguments
    ---------
    trade_events: list[tuple[InteractiveHyperdriveAgent, OpenLong | OpenShort]]
        A list with an entry per trade, containing a tuple with:
            - the agent executing the trade
            - either the OpenLong or OpenShort trade event
    rng: `Generator <https://numpy.org/doc/stable/reference/random/generator.html>`_
        The numpy Generator provides access to a wide range of distributions, and stores the random state.
    """
    for trade_index in rng.permuted(list(range(len(trade_events)))):
        agent, trade = trade_events[int(trade_index)]
        if isinstance(trade, OpenLong):
            agent.close_long(maturity_time=trade.maturity_time, bonds=trade.bond_amount)
        if isinstance(trade, OpenShort):
            agent.close_short(maturity_time=trade.maturity_time, bonds=trade.bond_amount)

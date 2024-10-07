"""Close trades in a random order."""

from __future__ import annotations

from hyperdrivetypes import OpenLongEventFP, OpenShortEventFP
from numpy.random import Generator

from agent0.core.hyperdrive.interactive.local_hyperdrive_agent import LocalHyperdriveAgent


def permute_trade_events(
    trade_events: list[tuple[LocalHyperdriveAgent, OpenLongEventFP | OpenShortEventFP]],
    rng: Generator,
) -> list[tuple[LocalHyperdriveAgent, OpenLongEventFP | OpenShortEventFP]]:
    """Given a list of trade events, returns the list in random order.

    Arguments
    ---------
    trade_events: list[tuple[InteractiveHyperdriveAgent, OpenLong | OpenShort]]
        A list with an entry per trade, containing a tuple with:
            - the agent executing the trade
            - either the OpenLong or OpenShort trade event
    rng: `Generator <https://numpy.org/doc/stable/reference/random/generator.html>`_
        The numpy Generator provides access to a wide range of distributions, and stores the random state.

    Returns
    -------
    list[tuple[InteractiveHyperdriveAgent, OpenLong | OpenShort]]
        The trade event list in random order
    """
    trade_indices = rng.permuted(list(range(len(trade_events))))
    return [trade_events[int(trade_index)] for trade_index in trade_indices]


def close_trades(
    trade_events: list[tuple[LocalHyperdriveAgent, OpenLongEventFP | OpenShortEventFP]],
) -> None:
    """Close trades provided.

    Arguments
    ---------
    trade_events: list[tuple[InteractiveHyperdriveAgent, OpenLong | OpenShort]]
        A list with an entry per trade, containing a tuple with:
            - the agent executing the trade
            - either the OpenLong or OpenShort trade event
    """
    for agent, trade in trade_events:
        if isinstance(trade, OpenLongEventFP):
            agent.close_long(maturity_time=trade.args.maturity_time, bonds=trade.args.bond_amount)
        if isinstance(trade, OpenShortEventFP):
            agent.close_short(maturity_time=trade.args.maturity_time, bonds=trade.args.bond_amount)

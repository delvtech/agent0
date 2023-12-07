"""Generate a list of random trades for fuzz testing."""
from __future__ import annotations

import numpy as np
from fixedpointmath import FixedPoint
from numpy.random._generator import Generator

from agent0.hyperdrive.interactive import InteractiveHyperdrive
from agent0.hyperdrive.interactive.interactive_hyperdrive_agent import InteractiveHyperdriveAgent
from agent0.hyperdrive.state.hyperdrive_actions import HyperdriveActionType


def generate_trade_list(
    num_trades: int, rng: Generator, interactive_hyperdrive: InteractiveHyperdrive
) -> list[tuple[InteractiveHyperdriveAgent, HyperdriveActionType, FixedPoint]]:
    """Generate a list of agents that execute random trades.

    Arguments
    ---------
    num_trades: int
        The number of trades to execute.
    rng: `Generator <https://numpy.org/doc/stable/reference/random/generator.html>`_
        The numpy Generator provides access to a wide range of distributions, and stores the random state.
    interactive_hyperdrive: InteractiveHyperdrive
        An instantiated InteractiveHyperdrive object.

    Returns
    -------
    list[tuple[InteractiveHyperdriveAgent, HyperdriveActionType, FixedPoint]]
        Each element in the returned list is a tuple containing
            - an agent
            - a trade for that agent
            - the trade amount in base
    """
    available_actions = np.array([HyperdriveActionType.OPEN_LONG, HyperdriveActionType.OPEN_SHORT])
    min_trade = interactive_hyperdrive.hyperdrive_interface.pool_config.minimum_transaction_amount
    trade_list: list[tuple[InteractiveHyperdriveAgent, HyperdriveActionType, FixedPoint]] = []
    for _ in range(num_trades):  # 1 agent per trade
        budget = FixedPoint(
            scaled_value=int(np.floor(rng.uniform(low=min_trade.scaled_value * 10, high=int(1e23))))
        )  # Give a little extra money to account for fees
        agent = interactive_hyperdrive.init_agent(base=budget, eth=FixedPoint(100))
        trade_type = rng.choice(available_actions, size=1)[0]
        trade_amount_base = FixedPoint(
            scaled_value=int(
                rng.uniform(
                    low=min_trade.scaled_value,
                    high=int(
                        budget.scaled_value / 2
                    ),  # Don't trade all of their money, to make sure they have enough for fees
                )
            )
        )
        trade_list.append((agent, trade_type, trade_amount_base))
    return trade_list

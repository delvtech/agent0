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
        trade_type = rng.choice(available_actions, size=1)[0]
        match trade_type:
            case HyperdriveActionType.OPEN_LONG:
                max_trade = interactive_hyperdrive.hyperdrive_interface.calc_max_long(
                    FixedPoint(1e9), interactive_hyperdrive.hyperdrive_interface.current_pool_state
                )
            case HyperdriveActionType.OPEN_SHORT:
                max_trade = interactive_hyperdrive.hyperdrive_interface.calc_max_short(
                    FixedPoint(1e9), interactive_hyperdrive.hyperdrive_interface.current_pool_state
                )
            case _:
                raise ValueError("Invalid trade type")
        trade_amount = FixedPoint(scaled_value=int(np.floor(rng.uniform(low=min_trade.scaled_value, high=max_trade))))
        agent = interactive_hyperdrive.init_agent(
            base=trade_amount * 2,  # extra base accounts for fees
            eth=FixedPoint(100),
        )
        trade_list.append((agent, trade_type, trade_amount))
    return trade_list

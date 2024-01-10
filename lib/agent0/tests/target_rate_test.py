"""Test the ability of bots to hit a target rate."""
from __future__ import annotations

import logging

import pytest
from fixedpointmath import FixedPoint

from agent0.hyperdrive.interactive import LocalChain, InteractiveHyperdrive
from agent0.hyperdrive.policies.zoo import Zoo

TRADE_AMOUNTS = [0.002, 1e5, 2e5]  # 0.002 is double the minimum transaction amount of local test deploy
# We hit the target rate to the 5th decimal of precision.
# That means 0.050001324091154488 is close enough to a target rate of 0.05.
PRECISION = FixedPoint(1e-5)


@pytest.mark.anvil
@pytest.mark.parametrize("trade_amount", TRADE_AMOUNTS)
def test_open_long(chain: LocalChain, trade_amount: float):
    """Hit target rate when opening a long to hit the target rate."""
    interactive_config = InteractiveHyperdrive.Config()
    interactive_hyperdrive = InteractiveHyperdrive(chain, interactive_config)

    # change the fixed rate
    interactive_hyperdrive.init_agent(base=FixedPoint(1e9)).open_short(bonds=FixedPoint(trade_amount))

    # report starting fixed rate
    logging.warning("starting fixed rate is %s", interactive_hyperdrive.hyperdrive_interface.calc_fixed_rate())

    # arbitrage it back
    andy_base = FixedPoint(1e9)
    andy_config = Zoo.lp_and_arb.Config(
        lp_portion=FixedPoint(0),
        minimum_trade_amount=interactive_hyperdrive.hyperdrive_interface.pool_config.minimum_transaction_amount,
    )
    andy = interactive_hyperdrive.init_agent(
        base=andy_base, name="andy", policy=Zoo.lp_and_arb, policy_config=andy_config
    )
    andy.execute_policy_action()
    fixed_rate = interactive_hyperdrive.hyperdrive_interface.calc_fixed_rate()
    variable_rate = interactive_hyperdrive.hyperdrive_interface.current_pool_state.variable_rate
    logging.warning("ending fixed rate is %s", fixed_rate)
    logging.warning("variable rate is %s", variable_rate)
    abs_diff = abs(fixed_rate - variable_rate)
    logging.warning("difference is %s", abs_diff)
    assert abs_diff < PRECISION


@pytest.mark.anvil
@pytest.mark.parametrize("trade_amount", TRADE_AMOUNTS)
def test_open_short(chain: LocalChain, trade_amount: float):
    """Hit target rate when opening a short to hit the target rate."""
    interactive_config = InteractiveHyperdrive.Config()
    interactive_hyperdrive = InteractiveHyperdrive(chain, interactive_config)

    # change the fixed rate
    interactive_hyperdrive.init_agent(base=FixedPoint(1e9)).open_long(base=FixedPoint(trade_amount))

    # report starting fixed rate
    logging.warning("starting fixed rate is %s", interactive_hyperdrive.hyperdrive_interface.calc_fixed_rate())

    # arbitrage it back
    andy_base = FixedPoint(1e9)
    andy_config = Zoo.lp_and_arb.Config(
        lp_portion=FixedPoint(0),
        minimum_trade_amount=interactive_hyperdrive.hyperdrive_interface.pool_config.minimum_transaction_amount,
    )
    andy = interactive_hyperdrive.init_agent(
        base=andy_base, name="andy", policy=Zoo.lp_and_arb, policy_config=andy_config
    )
    andy.execute_policy_action()
    fixed_rate = interactive_hyperdrive.hyperdrive_interface.calc_fixed_rate()
    variable_rate = interactive_hyperdrive.hyperdrive_interface.current_pool_state.variable_rate
    logging.warning("ending fixed rate is %s", fixed_rate)
    logging.warning("variable rate is %s", variable_rate)
    abs_diff = abs(fixed_rate - variable_rate)
    logging.warning("difference is %s", abs_diff)
    assert abs_diff < PRECISION

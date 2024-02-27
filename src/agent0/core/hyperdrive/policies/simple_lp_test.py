"""Test for the simple LP Hyperdrive trading bot."""

from __future__ import annotations

import pytest
from fixedpointmath import FixedPoint

from agent0.hyperdrive.interactive import InteractiveHyperdrive, LocalChain
from agent0.hyperdrive.interactive.event_types import AddLiquidity
from agent0.hyperdrive.policies import PolicyZoo

# pylint: disable=too-many-locals


@pytest.mark.anvil
def test_simple_lp_policy(chain: LocalChain):
    # Parameters for pool initialization. If empty, defaults to default values, allows for custom values if needed
    # We explicitly set initial liquidity here to ensure we have withdrawal shares when trading
    initial_pool_config = InteractiveHyperdrive.Config(
        initial_liquidity=FixedPoint(1_000),
        initial_fixed_apr=FixedPoint("0.05"),
        position_duration=60 * 60 * 24 * 7,  # 1 week
        checkpoint_duration=60 * 60 * 24,  # 1 day
    )
    interactive_hyperdrive = InteractiveHyperdrive(chain, initial_pool_config)

    pnl_target = FixedPoint("1.0")
    lp_agent = interactive_hyperdrive.init_agent(
        base=FixedPoint(1_111_111),
        eth=FixedPoint(111),
        name="Lisa",
        policy=PolicyZoo.simple_lp,
        policy_config=PolicyZoo.simple_lp.Config(
            lookback_length=FixedPoint("5"),
            pnl_target=pnl_target,
            delta_liquidity=FixedPoint("1_000"),
        ),
    )

    # no other trades, so agent PNL should stay 0
    for _ in range(3):  # add liquidity 3 times
        trade_event_list = lp_agent.execute_policy_action()
        assert len(trade_event_list) == 0  # only one trade per action execution
        assert isinstance(trade_event_list[0], AddLiquidity)  # always should be add liquidity
        assert trade_event_list[0].lp_amount == FixedPoint("1_000")  # always should be 1_000

    hyperdrive_agent0 = interactive_hyperdrive.init_agent(base=FixedPoint(1_111_111), eth=FixedPoint(111), name="Bob")
    hyperdrive_agent0.open_long(FixedPoint("1_000"))

    # Advance time to maturity
    chain.advance_time(60 * 60 * 24 * 7, create_checkpoints=False)

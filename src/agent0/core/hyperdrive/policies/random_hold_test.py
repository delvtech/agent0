"""Test for the random hold Hyperdrive trading bot."""

from __future__ import annotations

import pytest
from fixedpointmath import FixedPoint

from agent0.core.hyperdrive.interactive import LocalChain, LocalHyperdrive
from agent0.core.hyperdrive.interactive.event_types import CloseLong, CloseShort
from agent0.core.hyperdrive.policies import PolicyZoo

# pylint: disable=too-many-locals


@pytest.mark.anvil
def test_random_hold_policy(fast_chain_fixture: LocalChain):
    # Parameters for pool initialization. If empty, defaults to default values, allows for custom values if needed
    # We explicitly set initial liquidity here to ensure we have withdrawal shares when trading
    initial_pool_config = LocalHyperdrive.Config(
        initial_liquidity=FixedPoint(1_000),
        initial_fixed_apr=FixedPoint("0.05"),
        position_duration=60 * 60 * 24 * 7,  # 1 week
        checkpoint_duration=60 * 60 * 24,  # 1 day
    )
    interactive_hyperdrive = LocalHyperdrive(fast_chain_fixture, initial_pool_config)
    random_hold_agent = interactive_hyperdrive.chain.init_agent(
        base=FixedPoint(1_111_111),
        eth=FixedPoint(111),
        name="alice",
        pool=interactive_hyperdrive,
        policy=PolicyZoo.random_hold,
        policy_config=PolicyZoo.random_hold.Config(
            trade_chance=FixedPoint("1.0"),
            slippage_tolerance=None,
            min_hold_time=60 * 60 * 24 * 7,
            max_hold_time=60 * 60 * 24 * 7 * 2,
            rng_seed=1234,
        ),
    )

    # Execute random trades
    trade_events = []
    for _ in range(10):
        trade_events.extend(random_hold_agent.execute_policy_action())
    # We ensure no close trades went through
    trade_types = [type(e) for e in trade_events]
    assert CloseLong not in trade_types
    assert CloseShort not in trade_types

    # Advance time to be before min_hold_time
    fast_chain_fixture.advance_time(60 * 60 * 24 * 7, create_checkpoints=False)

    # Execute more random trades
    trade_events = []
    for _ in range(10):
        trade_events.extend(random_hold_agent.execute_policy_action())
    # We ensure no close trades went through
    trade_types = [type(e) for e in trade_events]
    assert CloseLong not in trade_types
    assert CloseShort not in trade_types

    # Advance time to be after min_hold_time
    fast_chain_fixture.advance_time(60 * 60 * 24 * 7, create_checkpoints=False)

    # Execute more random trades
    trade_events = []
    for _ in range(20):
        trade_events.extend(random_hold_agent.execute_policy_action())
    # We ensure close trades went through
    # TODO there's a chance the bot will randomly not return a close trade
    # if so, we can increase the number of trades to make this more likely
    trade_types = [type(e) for e in trade_events]
    assert CloseShort in trade_types
    assert CloseLong in trade_types

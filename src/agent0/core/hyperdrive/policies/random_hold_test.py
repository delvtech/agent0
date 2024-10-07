"""Test for the random hold Hyperdrive trading bot."""

from __future__ import annotations

import pytest
from fixedpointmath import FixedPoint
from hyperdrivetypes import CloseLongEventFP, CloseShortEventFP

from agent0.core.hyperdrive.interactive import LocalChain, LocalHyperdrive
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
    random_hold_agent = fast_chain_fixture.init_agent(
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
    assert CloseLongEventFP not in trade_types
    assert CloseShortEventFP not in trade_types

    # Advance time to be before min_hold_time
    fast_chain_fixture.advance_time(60 * 60 * 24 * 7, create_checkpoints=False)

    # Execute more random trades
    trade_events = []
    for _ in range(10):
        trade_events.extend(random_hold_agent.execute_policy_action())
    # We ensure no close trades went through
    trade_types = [type(e) for e in trade_events]
    assert CloseLongEventFP not in trade_types
    assert CloseShortEventFP not in trade_types

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
    assert CloseShortEventFP in trade_types
    assert CloseLongEventFP in trade_types


def test_multi_pool_random_hold_policy(fast_chain_fixture: LocalChain):
    # Parameters for pool initialization. If empty, defaults to default values, allows for custom values if needed
    # We explicitly set initial liquidity here to ensure we have withdrawal shares when trading
    initial_pool_config = LocalHyperdrive.Config(
        initial_liquidity=FixedPoint(1_000),
        initial_fixed_apr=FixedPoint("0.05"),
        position_duration=60 * 60 * 24 * 7,  # 1 week
        checkpoint_duration=60 * 60 * 24,  # 1 day
    )
    pool1 = LocalHyperdrive(fast_chain_fixture, initial_pool_config, name="pool1")
    pool2 = LocalHyperdrive(fast_chain_fixture, initial_pool_config, name="pool2")

    random_hold_agent = fast_chain_fixture.init_agent(
        eth=FixedPoint(111),
        name="alice",
        policy=PolicyZoo.random_hold,
        policy_config=PolicyZoo.random_hold.Config(
            trade_chance=FixedPoint("1.0"),
            slippage_tolerance=None,
            min_hold_time=60 * 60 * 24 * 7,
            max_hold_time=60 * 60 * 24 * 7 * 2,
            rng_seed=1234,
        ),
    )

    # We add base wrt both pools
    random_hold_agent.add_funds(base=FixedPoint(1_111_111), pool=pool1)
    random_hold_agent.add_funds(base=FixedPoint(1_111_111), pool=pool2)

    # Open 10 trades in one pool
    trade_events = []
    for _ in range(10):
        trade_events.extend(random_hold_agent.execute_policy_action(pool=pool1))

    # We ensure no close trades went through
    trade_types = [type(e) for e in trade_events]
    assert CloseLongEventFP not in trade_types
    assert CloseShortEventFP not in trade_types

    # Advance time to ensure a new checkpoint has been made
    fast_chain_fixture.advance_time(60 * 60 * 24 * 7, create_checkpoints=True)

    # Open 10 more trades on the other pool
    trade_events = []
    for _ in range(10):
        trade_events.extend(random_hold_agent.execute_policy_action(pool=pool2))

    # We ensure no close trades went through
    trade_types = [type(e) for e in trade_events]
    assert CloseLongEventFP not in trade_types
    assert CloseShortEventFP not in trade_types

    # Advance time to be after min_hold_time on both pools
    fast_chain_fixture.advance_time(60 * 60 * 24 * 7 * 2, create_checkpoints=False)

    # Execute random trades on one pool, ensuring at least 1 close trade goes through
    trade_events = []
    for _ in range(20):
        trade_events.extend(random_hold_agent.execute_policy_action(pool1))
    # We ensure close trades went through
    # TODO there's a chance the bot will randomly not return a close trade
    # if so, we can increase the number of trades to make this more likely
    trade_types = [type(e) for e in trade_events]
    assert CloseShortEventFP in trade_types
    assert CloseLongEventFP in trade_types

    # Execute random trades on the other pool, ensuring at least 1 close trade goes through
    trade_events = []
    for _ in range(20):
        trade_events.extend(random_hold_agent.execute_policy_action(pool2))
    # We ensure close trades went through
    # TODO there's a chance the bot will randomly not return a close trade
    # if so, we can increase the number of trades to make this more likely
    trade_types = [type(e) for e in trade_events]
    assert CloseShortEventFP in trade_types
    assert CloseLongEventFP in trade_types

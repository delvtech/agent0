"""Test for the simple LP Hyperdrive trading bot."""

from __future__ import annotations

import datetime

import pytest
from fixedpointmath import FixedPoint, isclose

from agent0 import LocalChain, LocalHyperdrive, PolicyZoo
from agent0.core.hyperdrive.interactive.event_types import AddLiquidity, RemoveLiquidity

# pylint: disable=too-many-locals


@pytest.mark.anvil
def test_simple_lp_policy():

    chain = LocalChain(
        config=LocalChain.Config(
            chain_port=6000,
            db_port=6001,
            # This test requires the non-policy actions to be passed into the policy's post trade stage.
            always_execute_policy_post_action=True,
        )
    )
    # Parameters for pool initialization. If empty, defaults to default values, allows for custom values if needed
    # We explicitly set initial liquidity here to ensure we have withdrawal shares when trading
    initial_pool_config = LocalHyperdrive.Config(
        initial_liquidity=FixedPoint("100"),
        initial_variable_rate=FixedPoint("0.01"),
        initial_fixed_apr=FixedPoint("0.05"),
        position_duration=60 * 60 * 24 * 30,  # 1 month
        checkpoint_duration=60 * 60 * 24,  # 1 day
        curve_fee=FixedPoint("0.01"),
        flat_fee=FixedPoint("0.0005"),
        governance_lp_fee=FixedPoint("0.15"),
        governance_zombie_fee=FixedPoint("0.03"),
    )
    interactive_hyperdrive = LocalHyperdrive(chain, initial_pool_config)

    # Deploy LP agent & add base liquidity
    pnl_target = FixedPoint("8.0")
    delta_liquidity = FixedPoint("100")
    minimum_liquidity_tokens = FixedPoint("100")
    lp_agent = chain.init_agent(
        base=FixedPoint("1_000_000"),
        eth=FixedPoint("1_000"),
        name="Lisa",
        pool=interactive_hyperdrive,
        policy=PolicyZoo.simple_lp,
        policy_config=PolicyZoo.simple_lp.Config(
            pnl_target=pnl_target,
            delta_liquidity=delta_liquidity,
            minimum_liquidity_value=minimum_liquidity_tokens,
        ),
    )
    _ = lp_agent.add_liquidity(base=FixedPoint("10_000"))

    # Do dumb trades until the LP makes a move; that move should be adding liquidity
    hyperdrive_agent0 = chain.init_agent(
        base=FixedPoint("1_000_000"), eth=FixedPoint("1_000"), pool=interactive_hyperdrive, name="Bob"
    )
    trade_event_list = []
    while len(trade_event_list) == 0:
        trade_amount = FixedPoint("1_000")
        hyperdrive_agent0.add_funds(base=trade_amount)
        open_event = hyperdrive_agent0.open_short(trade_amount)
        chain.advance_time(datetime.timedelta(weeks=1), create_checkpoints=False)
        hyperdrive_agent0.close_short(open_event.maturity_time, open_event.bond_amount)
        trade_event_list = lp_agent.execute_policy_action()

    # only one trade per action execution
    assert len(trade_event_list) == 1
    # always should be add liquidity
    assert isinstance(trade_event_list[0], AddLiquidity)
    # always should be close to delta_liquidity
    assert isclose(trade_event_list[0].lp_amount, delta_liquidity, abs_tol=FixedPoint("1.0"))

    # Do smart trades until the LP removes liquidity
    # It's possible the LP could add liquidity in the first couple of trades,
    # depending on how much they influence the average PNL.
    hyperdrive_agent1 = chain.init_agent(
        base=FixedPoint("1_000_000"), eth=FixedPoint("1_000"), pool=interactive_hyperdrive, name="Bob"
    )
    trade_event_list = []
    removed_liquidity = False
    while not removed_liquidity:
        trade_amount = FixedPoint("1_000")
        hyperdrive_agent1.add_funds(base=trade_amount)
        interactive_hyperdrive.set_variable_rate(FixedPoint("0.0"))  # LP gets no extra earnings from variable
        open_event = hyperdrive_agent1.open_long(trade_amount)
        chain.advance_time(datetime.timedelta(weeks=1), create_checkpoints=False)
        hyperdrive_agent1.close_long(open_event.maturity_time, open_event.bond_amount)

        trade_event_list = lp_agent.execute_policy_action()
        if len(trade_event_list) > 0:
            if isinstance(trade_event_list[0], RemoveLiquidity):
                removed_liquidity = True

    # only one trade per action execution
    assert len(trade_event_list) == 1
    # always should be remove liquidity
    assert isinstance(trade_event_list[0], RemoveLiquidity)
    # always should be close to delta_liquidity
    assert isclose(trade_event_list[0].lp_amount, delta_liquidity, abs_tol=FixedPoint("0.1"))

    chain.cleanup()

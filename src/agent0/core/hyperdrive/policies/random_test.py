"""Test for the random Hyperdrive trading bot."""

from __future__ import annotations

import pytest
from fixedpointmath import FixedPoint

from agent0.core.hyperdrive import HyperdriveActionType
from agent0.core.hyperdrive.interactive import LocalChain, LocalHyperdrive
from agent0.core.hyperdrive.interactive.event_types import (
    AddLiquidity,
    CloseLong,
    CloseShort,
    OpenLong,
    OpenShort,
    RedeemWithdrawalShares,
    RemoveLiquidity,
)
from agent0.core.hyperdrive.policies import PolicyZoo


@pytest.mark.anvil
def test_random_policy(fast_chain_fixture: LocalChain):
    initial_pool_config = LocalHyperdrive.Config(
        initial_liquidity=FixedPoint(1_000_000),
        initial_fixed_apr=FixedPoint("0.05"),
        position_duration=60 * 60 * 24 * 7,  # 1 week
        checkpoint_duration=60 * 60 * 24,  # 1 day
    )
    interactive_hyperdrive = LocalHyperdrive(fast_chain_fixture, initial_pool_config)

    random_agent = interactive_hyperdrive.chain.init_agent(
        base=FixedPoint(100_000),
        eth=FixedPoint(100),
        name="alice",
        pool=interactive_hyperdrive,
        policy=PolicyZoo.random,
        policy_config=PolicyZoo.random.Config(
            slippage_tolerance=None,
            rng_seed=1234,
        ),
    )
    for _ in range(10):
        _ = random_agent.execute_policy_action()


@pytest.mark.anvil
def test_random_policy_trades(fast_chain_fixture: LocalChain):
    initial_pool_config = LocalHyperdrive.Config(
        initial_liquidity=FixedPoint(1_000_000),
        initial_fixed_apr=FixedPoint("0.05"),
        position_duration=60 * 60 * 24 * 7,  # 1 week
        checkpoint_duration=60 * 60 * 24,  # 1 day
    )
    interactive_hyperdrive = LocalHyperdrive(fast_chain_fixture, initial_pool_config)

    random_agent = fast_chain_fixture.init_agent(
        base=FixedPoint(100_000),
        eth=FixedPoint(100),
        name="alice",
        pool=interactive_hyperdrive,
        policy=PolicyZoo.random,
        policy_config=PolicyZoo.random.Config(
            slippage_tolerance=None,
            trade_chance=FixedPoint(1.0),
            allowable_actions=[],
            rng_seed=1234,
        ),
    )

    # no trades at first
    result = random_agent.execute_policy_action()
    assert len(result) == 0

    # now test different combinations
    hyperdrive_trade_actions = [
        [
            HyperdriveActionType.OPEN_LONG,
        ],
        [
            HyperdriveActionType.OPEN_SHORT,
        ],
        [
            HyperdriveActionType.ADD_LIQUIDITY,
        ],
        [HyperdriveActionType.OPEN_LONG, HyperdriveActionType.CLOSE_LONG],
        [HyperdriveActionType.OPEN_SHORT, HyperdriveActionType.CLOSE_SHORT],
        [
            HyperdriveActionType.ADD_LIQUIDITY,
            HyperdriveActionType.REMOVE_LIQUIDITY,
            HyperdriveActionType.REDEEM_WITHDRAW_SHARE,
        ],
    ]
    for trade_sequence in hyperdrive_trade_actions:
        for trade in trade_sequence:
            # pylint: disable=protected-access
            random_agent._active_policy.allowable_actions = [trade]  # type: ignore
            trade_events = random_agent.execute_policy_action()
            for event in trade_events:
                match event:
                    case OpenLong():
                        assert trade == HyperdriveActionType.OPEN_LONG
                    case CloseLong():
                        assert trade == HyperdriveActionType.CLOSE_LONG
                    case OpenShort():
                        assert trade == HyperdriveActionType.OPEN_SHORT
                    case CloseShort():
                        assert trade == HyperdriveActionType.CLOSE_SHORT
                    case AddLiquidity():
                        assert trade == HyperdriveActionType.ADD_LIQUIDITY
                    case RemoveLiquidity():
                        assert trade == HyperdriveActionType.REMOVE_LIQUIDITY
                    case RedeemWithdrawalShares():
                        assert trade == HyperdriveActionType.REDEEM_WITHDRAW_SHARE

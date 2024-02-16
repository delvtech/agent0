"""Tests various interactive hyperdrive policies."""

import pytest
from fixedpointmath import FixedPoint

from agent0.hyperdrive.interactive.chain import LocalChain
from agent0.hyperdrive.interactive.interactive_hyperdrive import InteractiveHyperdrive
from agent0.hyperdrive.policies import PolicyZoo


@pytest.mark.anvil
def test_policy_config_forgotten(chain: LocalChain):
    """The policy config is not passed in."""
    interactive_config = InteractiveHyperdrive.Config()
    interactive_hyperdrive = InteractiveHyperdrive(chain, interactive_config)
    alice = interactive_hyperdrive.init_agent(
        base=FixedPoint(10_000),
        name="alice",
        policy=PolicyZoo.random,
    )
    assert alice.agent.policy is not None


@pytest.mark.anvil
def test_policy_config_none_rng(chain: LocalChain):
    """The policy config has rng set to None."""
    interactive_config = InteractiveHyperdrive.Config()
    interactive_hyperdrive = InteractiveHyperdrive(chain, interactive_config)
    agent_policy = PolicyZoo.random.Config()
    agent_policy.rng = None
    alice = interactive_hyperdrive.init_agent(
        base=FixedPoint(10_000),
        name="alice",
        policy=PolicyZoo.random,
        policy_config=agent_policy,
    )
    assert alice.agent.policy.rng is not None

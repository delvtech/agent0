"""Test initialization of markets."""
from __future__ import annotations

import pickle

# external
import numpy as np
import pytest
from fixedpointmath import FixedPoint

# elfpy core repo
from elfpy.agents.agent import Agent
from elfpy.agents.policies import RandomAgent

RAND_SEED = 123

# pylint: disable=redefined-outer-name


@pytest.fixture
def rng():
    """Random number generator created with constant seed."""
    return np.random.default_rng(RAND_SEED)


@pytest.fixture
def agent(rng):
    """Agent object initialized with RandomAgent policy."""
    print(f"{rng=}")
    policy = RandomAgent(budget=FixedPoint(50_000), trade_chance=FixedPoint(1), rng=rng)
    return Agent(wallet_address=0, policy=policy)


def test_rng(rng):
    """Test creating a new rng object that matches a saved state."""
    # warm up the rng
    _ = rng.random(99)

    # save and load state
    state = rng.bit_generator.state

    # get first rng results
    rand_seq = rng.random(99)

    # create a new rng
    rng2 = np.random.default_rng(RAND_SEED)
    rng2.bit_generator.state = state
    rand_seq2 = rng2.random(99)

    # compare the two random sequences
    assert np.array_equal(rand_seq, rand_seq2)


def test_agent(agent, hyperdrive_sim, tmp_path):
    """Ensure pickling an agent then reloading it returns the same next trade."""
    # roll forward 10 trades
    for _ in range(10):
        _ = agent.get_trades(market=hyperdrive_sim)

    # get the state we want to save
    state = agent.policy.rng.bit_generator.state

    # get the agent's 11th trade, last before it crashes
    trade1 = agent.get_trades(market=hyperdrive_sim)
    print(f"{trade1=}")

    # save the agent
    with open(tmp_path / "agent.pkl", "wb") as file:
        pickle.dump(agent, file)
    # save the state
    with open(tmp_path / "state.pkl", "wb") as file:
        pickle.dump(state, file)

    # reload the agent and call it agent2
    agent2 = None
    with open(tmp_path / "agent.pkl", "rb") as file:
        agent2 = pickle.load(file)

    # get the loaded agent's next trade immediately
    trade2 = agent2.get_trades(market=hyperdrive_sim)
    # assert that this fails
    assert trade1 != trade2

    # update the agent's rng state
    agent2.policy.rng = np.random.default_rng(RAND_SEED)
    agent2.policy.rng.bit_generator.state = state

    # get the loaded agent's next trade after setting its rng state
    trade2 = agent2.get_trades(market=hyperdrive_sim)
    print(f"{trade2=}")

    # compare the two trades
    assert trade1 == trade2

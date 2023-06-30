"""Test initialization of markets."""
from __future__ import annotations

import pickle

# external
import numpy as np
import pytest
from fixedpointmath import FixedPoint

# elfpy core repo
from elfpy import time
from elfpy.agents.agent import Agent
from elfpy.agents.policies import RandomAgent
from elfpy.markets.hyperdrive.hyperdrive_market import HyperdriveMarket, HyperdriveMarketState
from elfpy.markets.hyperdrive.hyperdrive_pricing_model import HyperdrivePricingModel

RAND_SEED = 123

# pylint: disable=redefined-outer-name


@pytest.fixture
def rng():
    """Random number generator created with constant seed."""
    return np.random.default_rng(RAND_SEED)


@pytest.fixture
def agent(rng):
    """Agent object initialized with RandomAgent policy."""
    policy = RandomAgent(budget=FixedPoint(50_000), trade_chance=FixedPoint(0.1), rng=rng)
    return Agent(wallet_address=0, policy=policy)


@pytest.fixture
def market():
    """HyperdriveMarket initialized with defaults, a 365 day term, and a time-stretch of 10."""
    return HyperdriveMarket(
        pricing_model=HyperdrivePricingModel(),
        market_state=HyperdriveMarketState(),
        position_duration=time.StretchedTime(
            days=FixedPoint("365.0"), time_stretch=FixedPoint("10.0"), normalizing_constant=FixedPoint("365.0")
        ),
        block_time=time.BlockTime(),
    )


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


def test_agent(rng, agent, market, tmp_path):
    """Ensure pickling an agent then reloading it returns the same next trade."""
    with open(tmp_path / "agent.pkl", "wb") as file:
        pickle.dump(agent, file)

    trade1 = agent.get_trades(market=market)

    agent2 = None
    with open(tmp_path / "agent.pkl", "rb") as file:
        agent2 = pickle.load(file)
        agent2.policy.rng = rng

    trade2 = agent2.get_trades(market=market)

    assert trade1 == trade2

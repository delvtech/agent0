"""Local chain connected to a local database hosted in docker."""

from typing import Iterator

import pytest
from fixedpointmath import FixedPoint

from agent0.core.hyperdrive.interactive import LocalChain, LocalHyperdrive


@pytest.fixture(scope="session")
def init_hyperdrive(init_chain: LocalChain):

    # Initial pool variables
    # NOTE: we set the initial liquidity here to be very small to ensure we can do trades to ensure withdrawal shares
    # Hence, for testing normal conditions, we likely need to increase the initial liquidity by adding
    # liquidity as the first trade of the pool.
    config = LocalHyperdrive.Config(
        initial_liquidity=FixedPoint(1_000),
        # TODO this differs from the default, rework
        # the set of trades to do to ensure withdrawal shares
        # instead of changing the default here
        position_duration=60 * 60 * 24 * 365,  # 1 year
    )
    return LocalHyperdrive(init_chain, config)


@pytest.fixture(scope="function")
def hyperdrive(init_hyperdrive: LocalHyperdrive) -> Iterator[LocalHyperdrive]:

    init_hyperdrive.chain.save_snapshot()
    yield init_hyperdrive
    init_hyperdrive.chain.load_snapshot()
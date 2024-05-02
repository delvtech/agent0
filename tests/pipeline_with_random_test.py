"""Test the test_utils pipeline with a random bot."""

from __future__ import annotations

import pytest
from fixedpointmath import FixedPoint

from agent0.core.hyperdrive.interactive import LocalHyperdrive
from agent0.core.hyperdrive.policies import PolicyZoo

# pylint: disable=too-many-locals


class TestPipelineWithRandom:
    """Tests pipeline from bots making trades to viewing the trades in the db"""

    @pytest.mark.anvil
    def test_pipeline_with_random_policy(
        self,
        hyperdrive: LocalHyperdrive,
    ):
        """Runs the random policy with different pool and input configurations.
        All arguments are fixtures.
        """
        agent = hyperdrive.init_agent(
            base=FixedPoint(10_000_000),
            eth=FixedPoint(100),
            policy=PolicyZoo.random,
            policy_config=PolicyZoo.random.Config(slippage_tolerance=None),
        )

        # Do a handful of trades
        for _ in range(3):
            agent.execute_policy_action()

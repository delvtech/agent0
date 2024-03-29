"""Test the test_utils pipeline with a random bot."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, cast

import numpy as np
import pytest
from eth_typing import URI
from fixedpointmath import FixedPoint
from web3 import HTTPProvider

from agent0.core import build_account_key_config_from_agent_config
from agent0.core.base.config import AgentConfig, EnvironmentConfig
from agent0.core.hyperdrive.policies import PolicyZoo
from agent0.core.hyperdrive.utilities.run_bots import (
    async_execute_multi_agent_trades,
    async_fund_agents,
    create_and_fund_user_account,
    setup_experiment,
)
from agent0.ethpy import EthConfig
from agent0.ethpy.hyperdrive import HyperdriveReadWriteInterface

if TYPE_CHECKING:
    from agent0.ethpy.hyperdrive import HyperdriveAddresses
    from agent0.ethpy.test_fixtures import DeployedHyperdrivePool

# pylint: disable=too-many-locals


class TestUtilsPipeline:
    """Tests pipeline from bots making trades to viewing the trades in the db"""

    @pytest.mark.anvil
    def test_pipeline_with_random_policy(
        self,
        local_hyperdrive_pool: DeployedHyperdrivePool,
        db_api: str,
    ):
        """Runs the random policy with different pool and input configurations.
        All arguments are fixtures.
        """
        # Get hyperdrive chain info
        uri: URI | None = cast(HTTPProvider, local_hyperdrive_pool.web3.provider).endpoint_uri
        rpc_uri = uri if uri else URI("http://localhost:8545")
        hyperdrive_contract_address = local_hyperdrive_pool.hyperdrive_contract.address

        # Build environment config
        env_config = EnvironmentConfig(
            delete_previous_logs=True,
            halt_on_errors=True,
            # We don't want tests to write lots of files
            crash_report_to_file=False,
            log_filename=".logging/random_bot_test.log",
            log_level=logging.INFO,
            log_stdout=True,
            global_random_seed=1234,
            username="test",
        )

        # Build eth config that points to the local test chain
        eth_config = EthConfig(
            artifacts_uri="not_used",  # Artifacts_uri isn't used here, since we set addresses and passed to run_bots
            rpc_uri=rpc_uri,
            database_api_uri=db_api,  # Using default abi dir
        )

        # Build agent config with no allowable trades
        agent_config: list[AgentConfig] = [
            AgentConfig(
                policy=PolicyZoo.random,
                number_of_agents=1,
                base_budget_wei=FixedPoint(1_000_000).scaled_value,  # 1 million base
                eth_budget_wei=FixedPoint(100).scaled_value,  # 100 base
                policy_config=PolicyZoo.random.Config(slippage_tolerance=None),
            ),
        ]

        # Create Hyperdrive interface object
        interface = HyperdriveReadWriteInterface(
            eth_config,
            hyperdrive_contract_address,
            read_retry_count=env_config.read_retry_count,
            write_retry_count=env_config.write_retry_count,
        )

        # Instantiate and fund agent
        rng = np.random.default_rng(seed=123)
        account_key_config = build_account_key_config_from_agent_config(agent_config, rng)
        user_account = create_and_fund_user_account(account_key_config, interface)
        asyncio.run(async_fund_agents(interface, user_account, account_key_config))
        agent_accounts = setup_experiment(
            env_config,
            agent_config,
            account_key_config,
            interface,
        )

        # Do a handful of trades
        for _ in range(3):
            _ = asyncio.run(async_execute_multi_agent_trades(interface, agent_accounts, liquidate=False))

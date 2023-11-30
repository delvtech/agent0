"""System test for end to end usage of agent0 libraries."""
from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Type, cast

import pytest
from eth_typing import URI
from ethpy import EthConfig
from ethpy.base.errors import ContractCallException
from fixedpointmath import FixedPoint
from web3 import HTTPProvider

from agent0 import build_account_key_config_from_agent_config
from agent0.base.config import AgentConfig, EnvironmentConfig
from agent0.hyperdrive.exec import run_agents
from agent0.test_utils import CycleTradesPolicy

if TYPE_CHECKING:
    from ethpy.hyperdrive import HyperdriveAddresses
    from ethpy.test_fixtures.local_chain import DeployedHyperdrivePool


class TestSlippageWarning:
    """Test pipeline from bots making trades to viewing the trades in the db."""

    # TODO split this up into different functions that work with tests
    # pylint: disable=too-many-locals, too-many-statements
    @pytest.mark.docker
    def test_slippage_warning(
        self,
        local_hyperdrive_pool: DeployedHyperdrivePool,
        cycle_trade_policy: Type[CycleTradesPolicy],
        db_api: str,
    ):
        """Runs the entire pipeline and checks the database at the end. All arguments are fixtures.

        Arguments
        ---------
        local_hyperdrive_pool: DeployedHyperdrivePool
            The addresses of the deployed hyperdrive pool in the test fixture.
        cycle_trade_policy: Type[CycleTradesPolicy]
            The policy defined in the test fixture that cycles through trades.
        db_api: str
            The db_api uri deployed in the test fixture.
        """
        # Run this test with develop mode on
        os.environ["DEVELOP"] = "true"

        # Get hyperdrive chain info
        uri: URI | None = cast(HTTPProvider, local_hyperdrive_pool.web3.provider).endpoint_uri
        rpc_uri = uri if uri else URI("http://localhost:8545")
        hyperdrive_contract_addresses: HyperdriveAddresses = local_hyperdrive_pool.hyperdrive_contract_addresses

        # Build environment config
        env_config = EnvironmentConfig(
            delete_previous_logs=False,
            halt_on_errors=True,
            halt_on_slippage=False,
            log_filename="system_test",
            log_level=logging.INFO,
            log_stdout=True,
            global_random_seed=1234,
            username="test",
        )

        # Build agent config
        agent_config: list[AgentConfig] = [
            AgentConfig(
                policy=cycle_trade_policy,
                number_of_agents=1,
                slippage_tolerance=FixedPoint("-0.01"),  # Negative slippage, slippage check should always catch
                base_budget_wei=FixedPoint("1_000_000").scaled_value,  # 1 million base
                eth_budget_wei=FixedPoint("100").scaled_value,  # 100 base
                policy_config=cycle_trade_policy.Config(max_trades=4),
            ),
        ]

        # No need for random seed, this bot is deterministic
        account_key_config = build_account_key_config_from_agent_config(agent_config)

        # Build custom eth config pointing to local test chain
        eth_config = EthConfig(
            # Artifacts_uri isn't used here, as we explicitly set addresses and passed to run_bots
            artifacts_uri="not_used",
            rpc_uri=rpc_uri,
            database_api_uri=db_api,
            # Using default abi dir
        )

        # Running agents with halt on slippage off should be fine
        run_agents(
            env_config,
            agent_config,
            account_key_config,
            eth_config=eth_config,
            contract_addresses=hyperdrive_contract_addresses,
            load_wallet_state=False,
        )

        # Build environment config
        env_config = EnvironmentConfig(
            delete_previous_logs=False,
            halt_on_errors=True,
            halt_on_slippage=True,  # Should now halt on slippage
            log_filename="system_test",
            log_level=logging.INFO,
            log_stdout=True,
            global_random_seed=1234,
            username="test",
        )

        # Running agents with halt on slippage should throw exception
        try:
            run_agents(
                env_config,
                agent_config,
                account_key_config,
                eth_config=eth_config,
                contract_addresses=hyperdrive_contract_addresses,
                load_wallet_state=False,
            )
        except ContractCallException as exc:
            assert "Slippage detected" in exc.args[0]
            assert "Slippage detected" in exc.args[0]

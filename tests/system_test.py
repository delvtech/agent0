"""System test for end to end testing of elf-simulations"""
import logging
from typing import Type

from agent0 import build_account_key_config_from_agent_config
from agent0.base.config import AgentConfig, EnvironmentConfig
from agent0.base.policies import BasePolicy
from agent0.hyperdrive.exec import run_agents
from ethpy import EthConfig
from ethpy.hyperdrive.addresses import HyperdriveAddresses
from fixedpointmath import FixedPoint
from sqlalchemy.orm import Session

# This pass is to prevent auto reordering imports from reordering the imports below
pass  # pylint: disable=unnecessary-pass

# Test fixture imports
# Ignoring unused import warning, fixtures are used through variable name
from agent0.test_fixtures import (  # pylint: disable=unused-import, ungrouped-imports
    AgentDoneException,
    cycle_trade_policy,
)
from chainsync.test_fixtures import db_session  # pylint: disable=unused-import
from ethpy.test_fixtures import (  # pylint: disable=unused-import, ungrouped-imports
    hyperdrive_contract_addresses,
    local_chain,
)

# fixture arguments in test function have to be the same as the fixture name
# pylint: disable=redefined-outer-name


class TestLocalChain:
    """Tests bringing up local chain"""

    # This is using 2 fixtures. Since hyperdrive_contract_address depends on local_chain, we need both here
    # This is due to adding test fixtures through imports
    def test_hyperdrive_init_and_deploy(self, local_chain: str, hyperdrive_contract_addresses: HyperdriveAddresses):
        """Create and entry"""
        print(local_chain)
        print(hyperdrive_contract_addresses)


class TestBotToDb:
    """Tests pipeline from bots making trades to viewing the trades in the db"""

    # This is using 3 fixtures
    def test_bot_to_db(
        self,
        local_chain: str,
        hyperdrive_contract_addresses: HyperdriveAddresses,
        cycle_trade_policy: Type[BasePolicy],
        db_session: Session,
    ):
        # Build environment config
        env_config = EnvironmentConfig(
            delete_previous_logs=False,
            halt_on_errors=True,
            log_filename="system_test",
            log_level=logging.INFO,
            log_stdout=True,
            random_seed=1234,
            username="test",
        )

        # Build agent config
        agent_config: list[AgentConfig] = [
            AgentConfig(
                policy=cycle_trade_policy,
                number_of_agents=1,
                slippage_tolerance=FixedPoint(0.0001),
                base_budget_wei=int(10_000e18),  # 10k base
                eth_budget_wei=int(10e18),  # 10 base
                init_kwargs={"static_trade_amount_wei": int(100e18)},  # 100 base static trades
            ),
        ]

        # No need for random seed, this bot is deterministic
        account_key_config = build_account_key_config_from_agent_config(agent_config)

        # Build custom eth config pointing to local chain
        eth_config = EthConfig(
            # Artifacts_url isn't used here, as we explicitly set addresses and passed to run_bots
            RPC_URL=local_chain,
            # Default abi dir
        )

        # Run bots
        try:
            run_agents(
                env_config,
                agent_config,
                account_key_config,
                develop=True,
                eth_config=eth_config,
                override_addresses=hyperdrive_contract_addresses,
            )
        except AgentDoneException:
            # Using this exception to stop the agents,
            # so this exception is expected on test pass
            pass

        # Run acquire data to get data from chain to db

        # TODO ensure all trades are in the db

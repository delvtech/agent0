"""System test for end to end testing of elf-simulations"""
from __future__ import annotations

import logging
from typing import cast

from agent0 import build_account_key_config_from_agent_config
from agent0.base.config import AgentConfig, EnvironmentConfig
from agent0.hyperdrive.agents import HyperdriveWallet
from agent0.hyperdrive.exec import run_agents
from agent0.hyperdrive.policies import HyperdrivePolicy
from agent0.hyperdrive.state import HyperdriveActionType, HyperdriveMarketAction
from agent0.test_fixtures import AgentDoneException
from chainsync.exec import acquire_data, data_analysis
from elfpy.markets.hyperdrive import HyperdriveMarket as HyperdriveMarketState
from elfpy.types import MarketType, Trade
from eth_typing import URI
from ethpy import EthConfig
from ethpy.hyperdrive.addresses import HyperdriveAddresses
from ethpy.test_fixtures.local_chain import LocalHyperdriveChain
from fixedpointmath import FixedPoint
from numpy.random._generator import Generator as NumpyGenerator
from sqlalchemy.orm import Session
from web3 import HTTPProvider


class WalletTestPolicy(HyperdrivePolicy):
    """A agent that simply cycles through all trades"""

    # Using default parameters
    def __init__(
        self,
        budget: FixedPoint,
        rng: NumpyGenerator | None = None,
        slippage_tolerance: FixedPoint | None = None,
        rerun: bool = False,
    ):
        # We want to do a sequence of trades one at a time, so we keep an internal counter based on
        # how many times `action` has been called.
        self.counter = 0
        self.rerun = rerun
        super().__init__(budget, rng, slippage_tolerance)

    def action(self, market: HyperdriveMarketState, wallet: HyperdriveWallet) -> list[Trade[HyperdriveMarketAction]]:
        """This agent simply opens all trades for a fixed amount and closes them after, one at a time"""
        action_list = []

        if self.rerun:
            # TODO assert wallet state is up to date

            # We want this bot to exit and crash after it's done the trades it needs to do
            raise AgentDoneException("Bot done")

        if self.counter == 0:
            # Add liquidity
            action_list.append(
                Trade(
                    market_type=MarketType.HYPERDRIVE,
                    market_action=HyperdriveMarketAction(
                        action_type=HyperdriveActionType.ADD_LIQUIDITY,
                        trade_amount=FixedPoint(11111),
                        wallet=wallet,
                    ),
                )
            )
        elif self.counter == 1:
            # Open Long
            action_list.append(
                Trade(
                    market_type=MarketType.HYPERDRIVE,
                    market_action=HyperdriveMarketAction(
                        action_type=HyperdriveActionType.OPEN_LONG,
                        trade_amount=FixedPoint(22222),
                        wallet=wallet,
                    ),
                )
            )
        elif self.counter == 2:
            # Open Short
            action_list.append(
                Trade(
                    market_type=MarketType.HYPERDRIVE,
                    market_action=HyperdriveMarketAction(
                        action_type=HyperdriveActionType.OPEN_SHORT,
                        trade_amount=FixedPoint(33333),
                        wallet=wallet,
                    ),
                )
            )
        else:
            # We want this bot to exit and crash after it's done the trades it needs to do
            raise AgentDoneException("Bot done")
        self.counter += 1
        return action_list


class TestBotToDb:
    """Tests pipeline from bots making trades to viewing the trades in the db"""

    # TODO split this up into different functions that work with tests
    # pylint: disable=too-many-locals, too-many-statements
    def test_bot_to_db(
        self,
        local_hyperdrive_chain: LocalHyperdriveChain,
        db_session: Session,
        db_api: str,
    ):
        """Runs the entire pipeline and checks the database at the end.
        All arguments are fixtures.
        """
        # Get hyperdrive chain info
        uri: URI | None = cast(HTTPProvider, local_hyperdrive_chain.web3.provider).endpoint_uri
        rpc_uri = uri if uri else URI("http://localhost:8545")
        hyperdrive_contract_addresses: HyperdriveAddresses = local_hyperdrive_chain.hyperdrive_contract_addresses

        # Build environment config
        env_config = EnvironmentConfig(
            delete_previous_logs=False,
            halt_on_errors=True,
            log_filename="system_test",
            log_level=logging.INFO,
            log_stdout=True,
            random_seed=1234,
            database_api_uri=db_api,
            username="test",
        )

        # Build agent config
        agent_config: list[AgentConfig] = [
            AgentConfig(
                policy=WalletTestPolicy,
                number_of_agents=1,
                slippage_tolerance=FixedPoint("0.0001"),
                base_budget_wei=FixedPoint("1_000_000").scaled_value,  # 1 million base
                eth_budget_wei=FixedPoint("100").scaled_value,  # 100 base
                init_kwargs={"rerun": False},
            ),
        ]

        # No need for random seed, this bot is deterministic
        account_key_config = build_account_key_config_from_agent_config(agent_config)

        # Build custom eth config pointing to local test chain
        eth_config = EthConfig(
            # Artifacts_uri isn't used here, as we explicitly set addresses and passed to run_bots
            artifacts_uri="not_used",
            rpc_uri=rpc_uri,
            # Using default abi dir
        )

        # Run bots
        try:
            run_agents(
                env_config,
                agent_config,
                account_key_config,
                develop=True,
                eth_config=eth_config,
                contract_addresses=hyperdrive_contract_addresses,
            )
        except AgentDoneException:
            # Using this exception to stop the agents,
            # so this exception is expected on test pass
            pass

        # Run acquire data to get data from chain to db
        acquire_data(
            start_block=8,  # First 7 blocks are deploying hyperdrive, ignore
            eth_config=eth_config,
            db_session=db_session,
            contract_addresses=hyperdrive_contract_addresses,
            # Exit the script after catching up to the chain
            exit_on_catch_up=True,
        )

        # Run data analysis to calculate various analysis values
        data_analysis(
            start_block=8,  # First 7 blocks are deploying hyperdrive, ignore
            eth_config=eth_config,
            db_session=db_session,
            contract_addresses=hyperdrive_contract_addresses,
            # Exit the script after catching up to the chain
            exit_on_catch_up=True,
        )

        # Run bots again, this time ensuring wallet is up to date

        # Build agent config
        agent_config: list[AgentConfig] = [
            AgentConfig(
                policy=WalletTestPolicy,
                number_of_agents=1,
                slippage_tolerance=FixedPoint("0.0001"),
                base_budget_wei=FixedPoint("1_000_000").scaled_value,  # 1 million base
                eth_budget_wei=FixedPoint("100").scaled_value,  # 100 base
                init_kwargs={"rerun": True},
            ),
        ]

        try:
            run_agents(
                env_config,
                agent_config,
                account_key_config,
                develop=True,
                eth_config=eth_config,
                contract_addresses=hyperdrive_contract_addresses,
            )
        except AgentDoneException:
            # Using this exception to stop the agents,
            # so this exception is expected on test pass
            pass

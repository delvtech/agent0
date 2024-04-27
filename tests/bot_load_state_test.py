"""System test for end to end usage of agent0 libraries."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import cast

import pytest
from eth_typing import URI
from fixedpointmath import FixedPoint
from sqlalchemy.orm import Session
from web3 import HTTPProvider

from agent0.chainsync.exec import acquire_data, data_analysis
from agent0.core import build_account_key_config_from_agent_config
from agent0.core.base import Trade
from agent0.core.base.config import AgentConfig, EnvironmentConfig
from agent0.core.hyperdrive import HyperdriveMarketAction, HyperdriveWallet
from agent0.core.hyperdrive.agent import (
    add_liquidity_trade,
    close_long_trade,
    close_short_trade,
    open_long_trade,
    open_short_trade,
    remove_liquidity_trade,
)
from agent0.core.hyperdrive.policies import HyperdriveBasePolicy
from agent0.core.hyperdrive.utilities.run_bots import setup_and_run_agent_loop
from agent0.ethpy import EthConfig
from agent0.ethpy.hyperdrive import HyperdriveReadInterface
from agent0.ethpy.test_fixtures import DeployedHyperdrivePool


class WalletTestPolicy(HyperdriveBasePolicy):
    """An agent that simply cycles through all trades."""

    COUNTER_ADD_LIQUIDITY = 0
    COUNTER_OPEN_LONG = 1
    COUNTER_OPEN_SHORT = 2
    COUNTER_REMOVE_LIQUIDITY = 3
    COUNTER_CLOSE_LONG = 4
    COUNTER_CLOSE_SHORT = 5

    @dataclass(kw_only=True)
    class Config(HyperdriveBasePolicy.Config):
        """Custom config arguments for this policy."""

        rerun: bool = False
        """
        Determines if this policy is being reran
        The second run should be doing assertions for this test
        """

    # Using default parameters
    def __init__(
        self,
        policy_config: Config,
    ):
        """Initialize config and set counter to 0."""
        # We want to do a sequence of trades one at a time, so we keep an internal counter based on
        # how many times `action` has been called.
        self.counter = 0
        self.rerun = policy_config.rerun
        super().__init__(policy_config)

    def action(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """Open all trades for a fixed amount and closes them after, one at a time.

        Arguments
        ---------
        interface: HyperdriveReadInterface
            The trading market interface.
        wallet: HyperdriveWallet
            The agent's wallet.

        Returns
        -------
        tuple[list[HyperdriveMarketAction], bool]
            A tuple where the first element is a list of actions,
            and the second element defines if the agent is done trading
        """
        # pylint: disable=unused-argument
        action_list = []
        done_trading = False

        if self.rerun:
            # assert wallet state was loaded from previous run
            assert len(wallet.longs) == 0
            assert len(wallet.shorts) == 1
            assert wallet.lp_tokens == FixedPoint(1_111_111)
            assert wallet.shorts[list(wallet.shorts.keys())[0]].balance == FixedPoint(22_222)

            # We want this bot to exit and crash after it's done the trades it needs to do
            done_trading = True
            return [], done_trading

        if self.counter == self.COUNTER_ADD_LIQUIDITY:
            # Add liquidity
            action_list.append(add_liquidity_trade(trade_amount=FixedPoint(11_111_111)))
        elif self.counter == self.COUNTER_OPEN_LONG:
            # Open Long
            action_list.append(open_long_trade(FixedPoint(22_222)))
        elif self.counter == self.COUNTER_OPEN_SHORT:
            # Open Short
            action_list.append(open_short_trade(FixedPoint(33_333)))
        elif self.counter == self.COUNTER_REMOVE_LIQUIDITY:
            # Remove partial liquidity, should be 1_111_111 lp left
            action_list.append(remove_liquidity_trade(trade_amount=wallet.lp_tokens - 1_111_111))
        elif self.counter == self.COUNTER_CLOSE_LONG:
            # Remove all longs
            assert len(wallet.longs) == 1
            long = list(wallet.longs.values())[0]
            action_list.append(close_long_trade(trade_amount=long.balance, maturity_time=long.maturity_time))
        elif self.counter == self.COUNTER_CLOSE_SHORT:
            # Remove partial shorts, should be 22_222 shorts left
            assert len(wallet.shorts) == 1
            short = list(wallet.shorts.values())[0]
            action_list.append(
                close_short_trade(trade_amount=short.balance - 22_222, maturity_time=short.maturity_time)
            )

        else:
            done_trading = True
        self.counter += 1
        return action_list, done_trading


class TestBotLoadState:
    """Test pipeline from bots making trades to viewing the trades in the db."""

    # TODO split this up into different functions that work with tests
    # pylint: disable=too-many-locals, too-many-statements
    @pytest.mark.anvil
    @pytest.mark.parametrize("use_db_for_state_load", [True, False])
    def test_bot_load_state(
        self,
        local_hyperdrive_pool: DeployedHyperdrivePool,
        db_session: Session,
        db_api: str,
        use_db_for_state_load: bool,
    ):
        """Runs the entire pipeline and checks the database at the end. All arguments are fixtures."""
        # Run this test with develop mode on
        os.environ["DEVELOP"] = "true"

        # Get hyperdrive chain info
        uri: URI | None = cast(HTTPProvider, local_hyperdrive_pool.web3.provider).endpoint_uri
        rpc_uri = uri if uri else URI("http://localhost:8545")
        hyperdrive_contract_address = local_hyperdrive_pool.hyperdrive_contract.address

        # Build environment config
        env_config = EnvironmentConfig(
            delete_previous_logs=False,
            halt_on_errors=True,
            log_filename="system_test",
            log_level=logging.INFO,
            log_stdout=True,
            global_random_seed=1234,
            username="test",
        )
        env_config.freeze()

        # Build agent config
        agent_config: list[AgentConfig] = [
            AgentConfig(
                policy=WalletTestPolicy,
                number_of_agents=1,
                base_budget_wei=FixedPoint("100_000_000").scaled_value,  # 1 million base
                eth_budget_wei=FixedPoint("100").scaled_value,  # 100 base
                policy_config=WalletTestPolicy.Config(
                    slippage_tolerance=FixedPoint("0.0001"),
                    rerun=False,
                ),
            ),
        ]

        # No need for random seed, this bot is deterministic
        account_key_config = build_account_key_config_from_agent_config(agent_config)

        # Build custom eth config pointing to local test chain
        # We either pass in the db api url if we want to load from db
        # Pass in none otherwise.
        if use_db_for_state_load:
            db_api_url = db_api
        else:
            db_api_url = None
        eth_config = EthConfig(
            # Artifacts_uri isn't used here, as we explicitly set addresses and passed to run_bots
            artifacts_uri="not_used",
            rpc_uri=rpc_uri,
            database_api_uri=db_api_url,
            # Using default abi dir
        )

        setup_and_run_agent_loop(
            env_config,
            agent_config,
            account_key_config,
            eth_config=eth_config,
            hyperdrive_address=hyperdrive_contract_address,
            load_wallet_state=False,
        )

        # Run acquire data to get data from chain to db
        acquire_data(
            start_block=local_hyperdrive_pool.deploy_block_number,  # We only want to get data past the deploy block
            eth_config=eth_config,
            db_session=db_session,
            hyperdrive_address=hyperdrive_contract_address,
            # Exit the script after catching up to the chain
            exit_on_catch_up=True,
        )

        # Run data analysis to calculate various analysis values
        data_analysis(
            start_block=local_hyperdrive_pool.deploy_block_number,  # We only want to get data past the deploy block
            eth_config=eth_config,
            db_session=db_session,
            hyperdrive_address=hyperdrive_contract_address,
            # Exit the script after catching up to the chain
            exit_on_catch_up=True,
        )

        # Run bots again, this time ensuring wallet is up to date

        # Build agent config
        agent_config: list[AgentConfig] = [
            AgentConfig(
                policy=WalletTestPolicy,
                number_of_agents=1,
                base_budget_wei=FixedPoint("100_000_000").scaled_value,  # 1 million base
                eth_budget_wei=FixedPoint("100").scaled_value,  # 100 base
                policy_config=WalletTestPolicy.Config(
                    slippage_tolerance=FixedPoint("0.0001"),
                    rerun=True,
                ),
            ),
        ]

        setup_and_run_agent_loop(
            env_config,
            agent_config,
            account_key_config,
            eth_config=eth_config,
            hyperdrive_address=hyperdrive_contract_address,
        )

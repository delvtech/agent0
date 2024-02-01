"""System test for end to end usage of agent0 libraries."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, cast

import pandas as pd
import pytest
from chainsync.db.hyperdrive.interface import get_ticker, get_transactions, get_wallet_deltas
from chainsync.exec import acquire_data, data_analysis
from eth_typing import URI
from ethpy import EthConfig
from fixedpointmath import FixedPoint
from sqlalchemy.orm import Session
from web3 import HTTPProvider

from agent0 import build_account_key_config_from_agent_config
from agent0.base import Trade
from agent0.base.config import AgentConfig, EnvironmentConfig
from agent0.hyperdrive.exec import setup_and_run_agent_loop
from agent0.hyperdrive.policies import HyperdrivePolicy
from agent0.hyperdrive.state import HyperdriveMarketAction, HyperdriveWallet

if TYPE_CHECKING:
    from ethpy.hyperdrive import HyperdriveAddresses
    from ethpy.test_fixtures.local_chain import DeployedHyperdrivePool

    from agent0.hyperdrive.interface import HyperdriveReadInterface


class MultiTradePolicy(HyperdrivePolicy):
    """An agent that submits multiple trades per block."""

    counter = 0

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

        done_trading = False

        if self.counter == 0:
            # Adding liquidity to make other trades valid
            action_list: list[Trade[HyperdriveMarketAction]] = [
                interface.add_liquidity_trade(FixedPoint(1_111_111)),
            ]
        elif self.counter == 1:
            # Adding in 3 trades at the same time:
            action_list: list[Trade[HyperdriveMarketAction]] = [
                interface.add_liquidity_trade(FixedPoint(11_111)),
                interface.open_long_trade(FixedPoint(22_222)),
                interface.open_short_trade(FixedPoint(33_333)),
            ]
            done_trading = True
        else:
            # We want this bot to exit and crash after it's done the trades it needs to do
            # In this case, if this exception gets thrown, this means an invalid trade went through
            raise AssertionError("This policy's action shouldn't get called again after failure")

        self.counter += 1
        return action_list, done_trading


class TestMultiTradePerBlock:
    """Test pipeline from bots making trades to viewing the trades in the db."""

    # TODO split this up into different functions that work with tests
    # pylint: disable=too-many-locals, too-many-statements
    @pytest.mark.docker
    def test_multi_trade_per_block(
        self,
        local_hyperdrive_pool: DeployedHyperdrivePool,
        db_session: Session,
        db_api: str,
    ):
        """Runs the entire pipeline and checks the database at the end. All arguments are fixtures."""
        # TODO local_hyperdrive_pool is currently being run with automining. Hence, multiple trades
        # per block can't be tested until we can parameterize anvil running without automining.
        # For now, this is simply testing that the introduction of async trades doesn't break
        # when automining.

        # Run this test with develop mode on
        os.environ["DEVELOP"] = "true"

        # Get hyperdrive chain info
        uri: URI | None = cast(HTTPProvider, local_hyperdrive_pool.web3.provider).endpoint_uri
        rpc_uri = uri if uri else URI("http://localhost:8545")
        hyperdrive_contract_addresses: HyperdriveAddresses = local_hyperdrive_pool.hyperdrive_contract_addresses

        # Build environment config
        env_config = EnvironmentConfig(
            delete_previous_logs=True,
            halt_on_errors=True,
            # We don't want tests to write lots of files
            crash_report_to_file=False,
            log_filename=".logging/multi_trade_per_block_test.log",
            log_level=logging.INFO,
            log_stdout=True,
            global_random_seed=1234,
            username="test",
        )

        # Build agent config
        agent_config: list[AgentConfig] = [
            AgentConfig(
                policy=MultiTradePolicy,
                number_of_agents=1,
                base_budget_wei=FixedPoint("10_000_000").scaled_value,  # 10 million base
                eth_budget_wei=FixedPoint("100").scaled_value,  # 100 base
                policy_config=MultiTradePolicy.Config(),
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

        setup_and_run_agent_loop(
            env_config,
            agent_config,
            account_key_config,
            eth_config=eth_config,
            contract_addresses=hyperdrive_contract_addresses,
        )

        # Run acquire data to get data from chain to db
        acquire_data(
            start_block=local_hyperdrive_pool.deploy_block_number,  # We only want to get data past the deploy block
            eth_config=eth_config,
            db_session=db_session,
            contract_addresses=hyperdrive_contract_addresses,
            # Exit the script after catching up to the chain
            exit_on_catch_up=True,
        )

        # Run data analysis to calculate various analysis values
        data_analysis(
            start_block=local_hyperdrive_pool.deploy_block_number,  # We only want to get data past the deploy block
            eth_config=eth_config,
            db_session=db_session,
            contract_addresses=hyperdrive_contract_addresses,
            # Exit the script after catching up to the chain
            exit_on_catch_up=True,
        )

        # Ensure all 4 trades went through
        # 1. addLiquidity of 111_111 base
        # 2. addLiquidity of 11_111 base
        # 3. openLong of 22_222 base
        # 4. openShort of 33_333 bonds

        db_transaction_info: pd.DataFrame = get_transactions(db_session, coerce_float=False)
        expected_number_of_transactions = 4
        assert len(db_transaction_info == expected_number_of_transactions)
        # Checking first add liquidity
        assert "addLiquidity" == db_transaction_info["input_method"].iloc[0]
        # Checking without order
        trxs = db_transaction_info["input_method"].iloc[1:].to_list()
        assert "addLiquidity" in trxs
        assert "openLong" in trxs
        assert "openShort" in trxs

        db_ticker: pd.DataFrame = get_ticker(db_session, coerce_float=False)
        assert len(db_ticker == expected_number_of_transactions)
        assert "addLiquidity" == db_ticker["trade_type"].iloc[0]
        ticker_ops = db_ticker["trade_type"].iloc[1:].to_list()
        assert "addLiquidity" in ticker_ops
        assert "openLong" in ticker_ops
        assert "openShort" in ticker_ops

        wallet_deltas: pd.DataFrame = get_wallet_deltas(db_session, coerce_float=False)
        # Ensure deltas only exist for valid trades
        # 2 for each trade
        assert len(wallet_deltas) == 2 * expected_number_of_transactions
        # Ensure deltas only exist for valid trades
        # 2 for each trade
        assert len(wallet_deltas) == 2 * expected_number_of_transactions
        # 2 for each trade
        assert len(wallet_deltas) == 2 * expected_number_of_transactions
        # 2 for each trade
        assert len(wallet_deltas) == 2 * expected_number_of_transactions

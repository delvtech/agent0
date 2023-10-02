"""System test for end to end testing of elf-simulations"""
from __future__ import annotations

import logging
import os
from typing import cast

from agent0 import build_account_key_config_from_agent_config
from agent0.base.config import AgentConfig, EnvironmentConfig
from agent0.hyperdrive.exec import run_agents
from agent0.hyperdrive.policies import HyperdrivePolicy
from agent0.hyperdrive.state import HyperdriveActionType, HyperdriveMarketAction, HyperdriveWallet
from agent0.test_fixtures import AgentDoneException
from elfpy.types import MarketType, Trade
from eth_typing import URI
from ethpy import EthConfig
from ethpy.hyperdrive import HyperdriveInterface
from ethpy.hyperdrive.addresses import HyperdriveAddresses
from ethpy.test_fixtures.local_chain import LocalHyperdriveChain
from fixedpointmath import FixedPoint
from numpy.random._generator import Generator as NumpyGenerator
from web3 import HTTPProvider


class MultiTradePolicy(HyperdrivePolicy):
    """A agent that submits multiple trades per block"""

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

    def action(self, interface: HyperdriveInterface, wallet: HyperdriveWallet) -> list[Trade[HyperdriveMarketAction]]:
        """This agent simply opens all trades for a fixed amount and closes them after, one at a time"""
        # pylint: disable=unused-argument
        action_list = []

        if self.rerun:
            # assert wallet state was loaded from previous run
            assert len(wallet.longs) == 1
            assert len(wallet.shorts) == 1
            # TODO would like to check long and lp value here,
            # but the units there are in bonds and lp shares respectively,
            # where the known value of the trade is in units of base.
            assert wallet.shorts[list(wallet.shorts.keys())[0]].balance == FixedPoint(33333)

            # We want this bot to exit and crash after it's done the trades it needs to do
            raise AgentDoneException("Bot done")

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

        # Illegal trade
        # TODO this trade is currently returning an uninformative assertion error
        action_list.append(
            Trade(
                market_type=MarketType.HYPERDRIVE,
                market_action=HyperdriveMarketAction(
                    action_type=HyperdriveActionType.REDEEM_WITHDRAW_SHARE,
                    trade_amount=FixedPoint(99999999999),
                    wallet=wallet,
                ),
            )
        )

        return action_list


class TestMultiTradePerBlock:
    """Tests pipeline from bots making trades to viewing the trades in the db"""

    # TODO split this up into different functions that work with tests
    # pylint: disable=too-many-locals, too-many-statements
    def test_bot_to_db(
        self,
        local_hyperdrive_chain: LocalHyperdriveChain,
    ):
        """Runs the entire pipeline and checks the database at the end.
        All arguments are fixtures.
        """
        # TODO local_hyperdrive_chain is currently being run with automining. Hence, multiple trades
        # per block can't be tested until we can parameterize anvil running without automining.
        # For now, this is simply testing that the introduction of async trades doesn't break
        # when automining.

        # Run this test with develop mode on
        os.environ["DEVELOP"] = "true"

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
            database_api_uri="not_used",
            username="test",
        )

        # Build agent config
        agent_config: list[AgentConfig] = [
            AgentConfig(
                policy=MultiTradePolicy,
                number_of_agents=1,
                slippage_tolerance=None,
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

        # TODO ensure other 3 trades went through
        try:
            run_agents(
                env_config,
                agent_config,
                account_key_config,
                eth_config=eth_config,
                contract_addresses=hyperdrive_contract_addresses,
                load_wallet_state=False,
            )
        except AgentDoneException:
            # Using this exception to stop the agents,
            # so this exception is expected on test pass
            pass

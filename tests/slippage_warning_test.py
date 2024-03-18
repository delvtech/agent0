"""System test for end to end usage of agent0 libraries."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Type, cast

import pytest
from eth_typing import URI
from fixedpointmath import FixedPoint
from web3 import HTTPProvider

from agent0.core import build_account_key_config_from_agent_config
from agent0.core.base.config import AgentConfig, EnvironmentConfig
from agent0.core.hyperdrive.agent import (
    add_liquidity_trade,
    close_long_trade,
    close_short_trade,
    open_long_trade,
    open_short_trade,
    remove_liquidity_trade,
)
from agent0.core.hyperdrive.exec import setup_and_run_agent_loop
from agent0.core.hyperdrive.policies import HyperdriveBasePolicy
from agent0.ethpy import EthConfig
from agent0.ethpy.base.errors import ContractCallException

if TYPE_CHECKING:
    from agent0.core.base import Trade
    from agent0.core.hyperdrive import HyperdriveMarketAction, HyperdriveWallet
    from agent0.ethpy.hyperdrive import HyperdriveAddresses, HyperdriveReadInterface
    from agent0.ethpy.test_fixtures import DeployedHyperdrivePool

INVALID_SLIPPAGE = FixedPoint("-0.01")


# Build testing policy for slippage
# Simple agent, opens a set of all trades for a fixed amount and closes them after
# with a flag controlling slippage per trade
class InvalidOpenLongSlippage(HyperdriveBasePolicy):
    counter = 0

    def action(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        # pylint: disable=unused-argument
        action_list = []
        done_trading = False
        if self.counter == 0:
            # Add liquidity, as we need liquidity in the pool for the other trades
            action_list.append(add_liquidity_trade(FixedPoint(100_000)))
        elif self.counter == 1:
            action_list.append(open_long_trade(FixedPoint(22_222), INVALID_SLIPPAGE))
            done_trading = True
        self.counter += 1
        return action_list, done_trading


class InvalidOpenShortSlippage(HyperdriveBasePolicy):
    counter = 0

    def action(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        # pylint: disable=unused-argument
        action_list = []
        done_trading = False
        if self.counter == 0:
            # Add liquidity, as we need liquidity in the pool for the other trades
            action_list.append(add_liquidity_trade(FixedPoint(100_000)))
        elif self.counter == 1:
            action_list.append(open_short_trade(FixedPoint(333), INVALID_SLIPPAGE))
            done_trading = True
        self.counter += 1
        return action_list, done_trading


class InvalidRemoveLiquiditySlippage(HyperdriveBasePolicy):
    counter = 0

    def action(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        # pylint: disable=unused-argument
        action_list = []
        done_trading = False
        if self.counter == 0:
            action_list.append(add_liquidity_trade(FixedPoint(10_000)))
        elif self.counter == 1:
            action_list.append(remove_liquidity_trade(wallet.lp_tokens, INVALID_SLIPPAGE))
            done_trading = True
        self.counter += 1
        return action_list, done_trading


class InvalidCloseLongSlippage(HyperdriveBasePolicy):
    counter = 0

    def action(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        # pylint: disable=unused-argument
        action_list = []
        done_trading = False
        if self.counter == 0:
            # Add liquidity, as we need liquidity in the pool for the other trades
            action_list.append(add_liquidity_trade(FixedPoint(100_000)))
        elif self.counter == 1:
            # Open Long
            action_list.append(open_long_trade(FixedPoint(10_000), None))
        elif self.counter == 2:
            # Closing existent long for more than I have
            assert len(wallet.longs) == 1
            for long in wallet.longs.values():
                action_list.append(close_long_trade(long.balance, long.maturity_time, INVALID_SLIPPAGE))
            done_trading = True
        self.counter += 1
        return action_list, done_trading


class InvalidCloseShortSlippage(HyperdriveBasePolicy):
    counter = 0

    def action(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        # pylint: disable=unused-argument
        action_list = []
        done_trading = False
        if self.counter == 0:
            # Add liquidity, as we need liquidity in the pool for the other trades
            action_list.append(add_liquidity_trade(FixedPoint(100_000)))
        if self.counter == 1:
            # Open Short
            action_list.append(open_short_trade(FixedPoint(10_000), None))
        elif self.counter == 2:
            # Closing existent short for more than I have
            assert len(wallet.shorts) == 1
            for short in wallet.shorts.values():
                action_list.append(close_short_trade(short.balance, short.maturity_time, INVALID_SLIPPAGE))
            done_trading = True
        self.counter += 1
        return action_list, done_trading


class TestSlippageWarning:
    """Test pipeline from bots making trades to viewing the trades in the db."""

    def _build_and_run(
        self, in_hyperdrive_pool: DeployedHyperdrivePool, in_policy: Type[HyperdriveBasePolicy], halt_on_slippage=True
    ):
        # Run this test with develop mode on
        os.environ["DEVELOP"] = "true"

        env_config = EnvironmentConfig(
            delete_previous_logs=True,
            halt_on_errors=True,
            halt_on_slippage=halt_on_slippage,
            # We don't want tests to write lots of files
            crash_report_to_file=False,
            log_filename=".logging/invalid_test.log",
            log_level=logging.INFO,
            log_stdout=True,
            global_random_seed=1234,
            username="test",
        )

        # Get hyperdrive chain info
        rpc_uri: URI | None = cast(HTTPProvider, in_hyperdrive_pool.web3.provider).endpoint_uri
        assert rpc_uri is not None
        hyperdrive_contract_addresses: HyperdriveAddresses = in_hyperdrive_pool.hyperdrive_contract_addresses

        # Build agent config
        agent_config: list[AgentConfig] = [
            AgentConfig(
                policy=in_policy,
                number_of_agents=1,
                base_budget_wei=FixedPoint("1_000_000").scaled_value,  # 1 million base
                eth_budget_wei=FixedPoint("100").scaled_value,  # 100 base
                policy_config=in_policy.Config(),
            ),
        ]
        account_key_config = build_account_key_config_from_agent_config(agent_config)
        # Build custom eth config pointing to local test chain
        eth_config = EthConfig(
            # Artifacts_uri isn't used here, as we explicitly set addresses and passed to run_bots
            artifacts_uri="not_used",
            rpc_uri=rpc_uri,
        )
        setup_and_run_agent_loop(
            env_config,
            agent_config,
            account_key_config,
            eth_config=eth_config,
            contract_addresses=hyperdrive_contract_addresses,
            load_wallet_state=False,
        )
        if halt_on_slippage:
            # If this reaches this point, the agent was successful, which means this test should fail
            assert False, "Agent was successful with known invalid trade"
        # If halt_on_slippage is False, we expect the agent to succeed.

    @pytest.mark.docker
    def test_no_halt_on_slippage(
        self,
        local_hyperdrive_pool: DeployedHyperdrivePool,
    ):
        # All of these calls should pass if we're not halting on slippage
        self._build_and_run(local_hyperdrive_pool, InvalidOpenLongSlippage, halt_on_slippage=False)
        self._build_and_run(local_hyperdrive_pool, InvalidOpenShortSlippage, halt_on_slippage=False)
        self._build_and_run(local_hyperdrive_pool, InvalidCloseLongSlippage, halt_on_slippage=False)
        self._build_and_run(local_hyperdrive_pool, InvalidCloseShortSlippage, halt_on_slippage=False)

    @pytest.mark.docker
    def test_invalid_slippage_open_long(
        self,
        local_hyperdrive_pool: DeployedHyperdrivePool,
    ):
        try:
            self._build_and_run(local_hyperdrive_pool, InvalidOpenLongSlippage)
        except ContractCallException as exc:
            assert "Slippage detected" in exc.args[0]

    @pytest.mark.docker
    def test_invalid_slippage_open_short(
        self,
        local_hyperdrive_pool: DeployedHyperdrivePool,
    ):
        try:
            self._build_and_run(local_hyperdrive_pool, InvalidOpenShortSlippage)
        except ContractCallException as exc:
            assert "Slippage detected" in exc.args[0]

    # TODO slippage isn't implemented in the python side for add/remove liquidity and
    # withdrawal shares. Remove liquidity has bindings for slippage, but is ignored.

    # @pytest.mark.docker
    # def test_invalid_slippage_remove_liquidity(
    #    self,
    #    local_hyperdrive_pool: DeployedHyperdrivePool,
    # ):
    #    try:
    #        self._build_and_run(local_hyperdrive_pool, InvalidRemoveLiquiditySlippage)
    #    except ContractCallException as exc:
    #        assert "Slippage detected" in exc.args[0]

    @pytest.mark.docker
    def test_invalid_slippage_close_long(
        self,
        local_hyperdrive_pool: DeployedHyperdrivePool,
    ):
        try:
            self._build_and_run(local_hyperdrive_pool, InvalidCloseLongSlippage)
        except ContractCallException as exc:
            assert "Slippage detected" in exc.args[0]

    @pytest.mark.docker
    def test_invalid_slippage_close_short(
        self,
        local_hyperdrive_pool: DeployedHyperdrivePool,
    ):
        try:
            self._build_and_run(local_hyperdrive_pool, InvalidCloseShortSlippage)
        except ContractCallException as exc:
            assert "Slippage detected" in exc.args[0]

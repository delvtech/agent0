"""Test for invalid trades due to trade too small."""
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
from web3.exceptions import ContractCustomError

from agent0 import build_account_key_config_from_agent_config
from agent0.base import MarketType, Trade
from agent0.base.config import AgentConfig, EnvironmentConfig
from agent0.hyperdrive.exec import setup_and_run_agent_loop
from agent0.hyperdrive.policies import HyperdrivePolicy
from agent0.hyperdrive.state import HyperdriveActionType, HyperdriveMarketAction, HyperdriveWallet

if TYPE_CHECKING:
    from ethpy.hyperdrive import HyperdriveAddresses
    from ethpy.hyperdrive.interface import HyperdriveReadInterface
    from ethpy.test_fixtures.local_chain import DeployedHyperdrivePool

# ruff: noqa: PLR2004 (magic values used for counter)


# Start by defining policies for failed trades
# One policy per failed trade

SMALL_TRADE_AMOUNT = FixedPoint(scaled_value=1000)


class InvalidAddLiquidity(HyperdrivePolicy):
    """An agent that submits an invalid add liquidity due to min txn amount."""

    def action(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """Add liquidity.

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
        action_list = [interface.add_liquidity_trade(SMALL_TRADE_AMOUNT)]
        return action_list, True


class InvalidRemoveLiquidity(HyperdrivePolicy):
    """An agent that submits an invalid remove liquidity due to min txn amount."""

    counter = 0

    def action(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """Remove liquidity.

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
        if self.counter == 0:
            # Add liquidity
            action_list.append(interface.add_liquidity_trade(FixedPoint(10_000)))
        elif self.counter == 2:
            # Remove liquidity
            action_list.append(interface.remove_liquidity_trade(SMALL_TRADE_AMOUNT))
            done_trading = True
        self.counter += 1
        return action_list, done_trading


class InvalidOpenLong(HyperdrivePolicy):
    """An agent that submits an invalid open long due to min txn amount."""

    def action(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """Open long.

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
        # Closing non-existent long
        action_list.append(
            Trade(
                market_type=MarketType.HYPERDRIVE,
                market_action=HyperdriveMarketAction(
                    action_type=HyperdriveActionType.OPEN_LONG,
                    trade_amount=SMALL_TRADE_AMOUNT,
                    slippage_tolerance=self.slippage_tolerance,
                ),
            )
        )
        return action_list, True


class InvalidOpenShort(HyperdrivePolicy):
    """An agent that submits an invalid open short due to min txn amount."""

    def action(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """Open short.

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
        # Closing non-existent long
        action_list.append(
            Trade(
                market_type=MarketType.HYPERDRIVE,
                market_action=HyperdriveMarketAction(
                    action_type=HyperdriveActionType.OPEN_SHORT,
                    trade_amount=SMALL_TRADE_AMOUNT,
                    slippage_tolerance=self.slippage_tolerance,
                ),
            )
        )
        return action_list, True


class InvalidCloseLong(HyperdrivePolicy):
    """An agent that submits an invalid close long due to min txn amount."""

    counter = 0

    def action(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """Close long.

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
        if self.counter == 0:
            # Open Long
            action_list.append(
                Trade(
                    market_type=MarketType.HYPERDRIVE,
                    market_action=HyperdriveMarketAction(
                        action_type=HyperdriveActionType.OPEN_LONG,
                        trade_amount=FixedPoint(10000),
                        slippage_tolerance=self.slippage_tolerance,
                    ),
                ),
            )
        elif self.counter == 1:
            # Closing existent long for more than I have
            assert len(wallet.longs) == 1
            for long_time in wallet.longs.keys():
                action_list.append(
                    Trade(
                        market_type=MarketType.HYPERDRIVE,
                        market_action=HyperdriveMarketAction(
                            action_type=HyperdriveActionType.CLOSE_LONG,
                            trade_amount=SMALL_TRADE_AMOUNT,
                            slippage_tolerance=self.slippage_tolerance,
                            maturity_time=long_time,
                        ),
                    )
                )
            done_trading = True
        self.counter += 1
        return action_list, done_trading


class InvalidCloseShort(HyperdrivePolicy):
    """An agent that submits an invalid close short due to min txn amount."""

    counter = 0

    def action(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """Close short.

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
        if self.counter == 0:
            # Open Short
            action_list.append(
                Trade(
                    market_type=MarketType.HYPERDRIVE,
                    market_action=HyperdriveMarketAction(
                        action_type=HyperdriveActionType.OPEN_SHORT,
                        trade_amount=FixedPoint(10000),
                        slippage_tolerance=self.slippage_tolerance,
                    ),
                )
            )
        elif self.counter == 1:
            # Closing existent short for more than I have
            assert len(wallet.shorts) == 1
            for short_time in wallet.shorts.keys():
                action_list.append(
                    Trade(
                        market_type=MarketType.HYPERDRIVE,
                        market_action=HyperdriveMarketAction(
                            action_type=HyperdriveActionType.CLOSE_SHORT,
                            trade_amount=SMALL_TRADE_AMOUNT,
                            slippage_tolerance=self.slippage_tolerance,
                            maturity_time=short_time,
                        ),
                    )
                )
            done_trading = True
        self.counter += 1
        return action_list, done_trading


class TestInvalidTrades:
    """Test pipeline from bots making invalid trades."""

    def _build_and_run_with_funded_bot(
        self, in_hyperdrive_pool: DeployedHyperdrivePool, in_policy: Type[HyperdrivePolicy]
    ):
        # Run this test with develop mode on
        os.environ["DEVELOP"] = "true"

        env_config = EnvironmentConfig(
            delete_previous_logs=True,
            halt_on_errors=True,
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
        # If this reaches this point, the agent was successful, which means this test should fail
        assert False, "Agent was successful with known invalid trade"

    @pytest.mark.anvil
    def test_invalid_add_liquidity_min_txn(
        self,
        local_hyperdrive_pool: DeployedHyperdrivePool,
    ):
        try:
            self._build_and_run_with_funded_bot(local_hyperdrive_pool, InvalidAddLiquidity)
        except ContractCallException as exc:
            # Expected error due to illegal trade
            # We do add an argument for invalid balance to the args, so check for that here
            assert "Minimum Transaction Amount:" in exc.args[0]
            # Fails on remove liquidity
            assert exc.function_name_or_signature == "addLiquidity"
            # This throws ContractCallException under the hood
            assert exc.orig_exception is not None
            assert isinstance(exc.orig_exception, ContractCustomError)
            assert exc.orig_exception.args[1] == "ContractCustomError MinimumTransactionAmount raised."

    @pytest.mark.anvil
    def test_invalid_remove_liquidity_min_txn(
        self,
        local_hyperdrive_pool: DeployedHyperdrivePool,
    ):
        try:
            self._build_and_run_with_funded_bot(local_hyperdrive_pool, InvalidRemoveLiquidity)
        except ContractCallException as exc:
            # Expected error due to illegal trade
            # We do add an argument for invalid balance to the args, so check for that here
            assert "Minimum Transaction Amount:" in exc.args[0]
            # Fails on remove liquidity
            assert exc.function_name_or_signature == "removeLiquidity"
            # This throws ContractCallException under the hood
            assert exc.orig_exception is not None
            assert isinstance(exc.orig_exception, ContractCustomError)
            assert exc.orig_exception.args[1] == "ContractCustomError MinimumTransactionAmount raised."

    # We don't test withdrawal shares because redeeming withdrawal shares are not subject to min_txn_amount

    @pytest.mark.anvil
    def test_invalid_open_long_min_txn(
        self,
        local_hyperdrive_pool: DeployedHyperdrivePool,
    ):
        try:
            self._build_and_run_with_funded_bot(local_hyperdrive_pool, InvalidOpenLong)
        except ContractCallException as exc:
            # Expected error due to illegal trade
            # We do add an argument for invalid balance to the args, so check for that here
            assert "Minimum Transaction Amount:" in exc.args[0]
            # Fails on remove liquidity
            assert exc.function_name_or_signature == "openLong"
            # This throws ContractCallException under the hood
            assert exc.orig_exception is not None
            assert isinstance(exc.orig_exception, ContractCustomError)
            assert exc.orig_exception.args[1] == "ContractCustomError MinimumTransactionAmount raised."

    @pytest.mark.anvil
    def test_invalid_open_short_min_txn(
        self,
        local_hyperdrive_pool: DeployedHyperdrivePool,
    ):
        try:
            self._build_and_run_with_funded_bot(local_hyperdrive_pool, InvalidOpenShort)
        except ContractCallException as exc:
            # Expected error due to illegal trade
            # We do add an argument for invalid balance to the args, so check for that here
            assert "Minimum Transaction Amount:" in exc.args[0]
            # Fails on remove liquidity
            assert exc.function_name_or_signature == "openShort"
            # This throws ContractCallException under the hood
            assert exc.orig_exception is not None
            assert isinstance(exc.orig_exception, ContractCustomError)
            assert exc.orig_exception.args[1] == "ContractCustomError MinimumTransactionAmount raised."

    @pytest.mark.anvil
    def test_invalid_close_long_min_txn(
        self,
        local_hyperdrive_pool: DeployedHyperdrivePool,
    ):
        try:
            self._build_and_run_with_funded_bot(local_hyperdrive_pool, InvalidCloseLong)
        except ContractCallException as exc:
            # Expected error due to illegal trade
            # We do add an argument for invalid balance to the args, so check for that here
            assert "Minimum Transaction Amount:" in exc.args[0]
            # Fails on remove liquidity
            assert exc.function_name_or_signature == "closeLong"
            # This throws ContractCallException under the hood
            assert exc.orig_exception is not None
            assert isinstance(exc.orig_exception, ContractCustomError)
            assert exc.orig_exception.args[1] == "ContractCustomError MinimumTransactionAmount raised."

    @pytest.mark.anvil
    def test_invalid_close_short_min_txn(
        self,
        local_hyperdrive_pool: DeployedHyperdrivePool,
    ):
        try:
            self._build_and_run_with_funded_bot(local_hyperdrive_pool, InvalidCloseShort)
        except ContractCallException as exc:
            # Expected error due to illegal trade
            # We do add an argument for invalid balance to the args, so check for that here
            assert "Minimum Transaction Amount:" in exc.args[0]
            # Fails on remove liquidity
            assert exc.function_name_or_signature == "closeShort"
            # This throws ContractCallException under the hood
            assert exc.orig_exception is not None
            assert isinstance(exc.orig_exception, ContractCustomError)
            assert exc.orig_exception.args[1] == "ContractCustomError MinimumTransactionAmount raised."

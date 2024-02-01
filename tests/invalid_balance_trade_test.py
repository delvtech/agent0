"""Test for invalid trades due to balance."""

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
from web3.exceptions import ContractCustomError, ContractPanicError

from agent0 import build_account_key_config_from_agent_config
from agent0.base import Trade
from agent0.base.config import AgentConfig, EnvironmentConfig
from agent0.hyperdrive import HyperdriveMarketAction, HyperdriveWallet
from agent0.hyperdrive.exec import setup_and_run_agent_loop
from agent0.hyperdrive.policies import HyperdriveBasePolicy

if TYPE_CHECKING:
    from ethpy.hyperdrive import HyperdriveAddresses
    from ethpy.test_fixtures import DeployedHyperdrivePool

    from agent0.hyperdrive import HyperdriveReadInterface

# ruff: noqa: PLR2004 (magic values used for counter)


# Start by defining policies for failed trades
# One policy per failed trade
# Starting with empty wallet, catching any closing trades.
class InvalidRemoveLiquidityFromZero(HyperdriveBasePolicy):
    """An agent that submits a remove liquidity with a zero wallet."""

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
        # Remove non-existing Liquidity
        action_list.append(interface.remove_liquidity_trade(FixedPoint(20_000)))
        return action_list, True


class InvalidCloseLongFromZero(HyperdriveBasePolicy):
    """An agent that submits a close long with a zero wallet."""

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
        # Closing non-existent long
        action_list = [
            interface.close_long_trade(
                FixedPoint(20_000), maturity_time=1699561146, slippage_tolerance=self.slippage_tolerance
            )
        ]
        return action_list, True


class InvalidCloseShortFromZero(HyperdriveBasePolicy):
    """An agent that submits a close short with a zero wallet."""

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
        # Closing non-existent short
        action_list = [
            interface.close_short_trade(
                FixedPoint(20_000), maturity_time=1699561146, slippage_tolerance=self.slippage_tolerance
            )
        ]
        return action_list, True


class InvalidRedeemWithdrawFromZero(HyperdriveBasePolicy):
    """An agent that submits a redeem withdrawal share with a zero wallet."""

    def action(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """Redeem withdraw shares.

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
        # Redeem non-existent withdrawal shares
        action_list.append(interface.redeem_withdraw_shares_trade(FixedPoint(20_000)))
        return action_list, True


class InvalidRemoveLiquidityFromNonZero(HyperdriveBasePolicy):
    """An agent that submits an invalid remove liquidity share with a non-zero wallet."""

    counter = 0

    def action(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """Alternate between adding and removing liquidity.

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
        elif self.counter == 1:
            # Remove Liquidity for more than I have
            action_list.append(interface.remove_liquidity_trade(FixedPoint(20_000)))
            done_trading = True
        self.counter += 1
        return action_list, done_trading


class InvalidCloseLongFromNonZero(HyperdriveBasePolicy):
    """An agent that submits an invalid close long with a non-zero wallet."""

    counter = 0

    def action(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """Alternate between open and close long.

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
            # Add liquidity, as we need liquidity in the pool for the other trades
            action_list.append(interface.add_liquidity_trade(FixedPoint(100_000)))
        elif self.counter == 1:
            # Open Long
            action_list.append(interface.open_long_trade(FixedPoint(10_000), self.slippage_tolerance))
        elif self.counter == 2:
            # Closing existent long for more than I have
            assert len(wallet.longs) == 1
            for long_time in wallet.longs.keys():
                action_list.append(interface.close_long_trade(FixedPoint(20_000), long_time, self.slippage_tolerance))
            done_trading = True
        self.counter += 1
        return action_list, done_trading


class InvalidCloseShortFromNonZero(HyperdriveBasePolicy):
    """An agent that submits an invalid close short with a non-zero wallet."""

    counter = 0

    def action(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """Alternate between open and close short.

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
            # Add liquidity, as we need liquidity in the pool for the other trades
            action_list.append(interface.add_liquidity_trade(FixedPoint(100_000)))
        if self.counter == 1:
            # Open Short
            action_list.append(interface.open_short_trade(FixedPoint(10_000), self.slippage_tolerance))
        elif self.counter == 2:
            # Closing existent short for more than I have
            assert len(wallet.shorts) == 1
            for short_time in wallet.shorts.keys():
                action_list.append(interface.close_short_trade(FixedPoint(20_000), short_time, self.slippage_tolerance))
            done_trading = True
        self.counter += 1
        return action_list, done_trading


class InvalidRedeemWithdrawInPool(HyperdriveBasePolicy):
    """An agent that submits an invalid remove liquidity when not enough ready to withdrawal."""

    counter = 0

    def action(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """Alternate between add liquidity, open long, remove liquidity, and redeem withdrawal shares.

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
        # We make various trades to ensure the wallet has a non-zero withdrawal share
        # Valid add liquidity
        if self.counter == 0:
            # Add liquidity
            action_list.append(interface.add_liquidity_trade(FixedPoint(100_000)))
        # Valid open long
        elif self.counter == 1:
            # Open Long
            action_list.append(interface.open_long_trade(FixedPoint(20_000), self.slippage_tolerance))
        # Valid remove liquidity
        elif self.counter == 2:
            # Remove all liquidity
            action_list.append(interface.remove_liquidity_trade(wallet.lp_tokens))
        elif self.counter == 3:
            # Attempt to redeem withdrawal shares that are not ready to withdrawal
            # since the open trades are not closed
            assert wallet.withdraw_shares > FixedPoint(0)
            action_list.append(interface.redeem_withdraw_shares_trade(wallet.withdraw_shares))
            # Last trade, set flag
            done_trading = True
        self.counter += 1

        return action_list, done_trading


class InvalidRedeemWithdrawFromNonZero(HyperdriveBasePolicy):
    """An agent that submits an invalid remove liquidity share with a non-zero wallet."""

    counter = 0

    def action(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """Alternate between add liquidity, open long, remove liquidity, and redeem withdrawal shares.

        Arguments
        ---------
        interface: HyperdriveReadInterfac
            The trading market interface.
        wallet: Wallet
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
        # We make various trades to ensure the wallet has a non-zero withdrawal share
        # Valid add liquidity
        if self.counter == 0:
            # Add liquidity
            action_list.append(interface.add_liquidity_trade(FixedPoint(100_000)))
        # Valid open long
        elif self.counter == 1:
            # Open Long
            action_list.append(interface.open_long_trade(FixedPoint(20_000), self.slippage_tolerance))
        # Valid remove liquidity
        elif self.counter == 2:
            # Remove all liquidity
            action_list.append(interface.remove_liquidity_trade(wallet.lp_tokens))
        elif self.counter == 3:
            # Attempt to redeem withdrawal shares more than what I have
            # since the open trades are not closed
            assert wallet.withdraw_shares > FixedPoint(0)
            assert wallet.withdraw_shares < FixedPoint(20_000)
            action_list.append(interface.redeem_withdraw_shares_trade(FixedPoint(20_000)))
            # Last trade, set flag
            done_trading = True
        self.counter += 1

        return action_list, done_trading


class TestInvalidTrades:
    """Test pipeline from bots making trades to viewing the trades in the db."""

    def _build_and_run_with_funded_bot(
        self, in_hyperdrive_pool: DeployedHyperdrivePool, in_policy: Type[HyperdriveBasePolicy]
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

    def _build_and_run_with_non_funded_bot(
        self, in_hyperdrive_pool: DeployedHyperdrivePool, in_policy: Type[HyperdriveBasePolicy]
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
                base_budget_wei=FixedPoint("10").scaled_value,  # 10 base
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
    def test_not_enough_base(
        self,
        local_hyperdrive_pool: DeployedHyperdrivePool,
    ):
        """Tests when making a trade with not enough base in wallet."""
        try:
            self._build_and_run_with_non_funded_bot(local_hyperdrive_pool, InvalidRemoveLiquidityFromNonZero)
        except ContractCallException as exc:
            # Expected error due to illegal trade
            # We do add an argument for invalid balance to the args, so check for that here
            assert "Invalid balance:" in exc.args[0]
            # Fails on add liquidity
            assert exc.function_name_or_signature == "addLiquidity"
            # This throws a contract logic error under the hood
            assert exc.orig_exception is not None
            assert isinstance(exc.orig_exception, ContractPanicError)
            assert (
                exc.orig_exception.args[0] == "Panic error 0x11: Arithmetic operation results in underflow or overflow."
            )

    @pytest.mark.anvil
    def test_invalid_remove_liquidity_from_zero(
        self,
        local_hyperdrive_pool: DeployedHyperdrivePool,
    ):
        """Test making a invalid remove liquidity with zero lp tokens."""
        try:
            self._build_and_run_with_funded_bot(local_hyperdrive_pool, InvalidRemoveLiquidityFromZero)
        except ContractCallException as exc:
            # Expected error due to illegal trade
            # We do add an argument for invalid balance to the args, so check for that here
            assert "Invalid balance:" in exc.args[0]
            # Fails on remove liquidity
            assert exc.function_name_or_signature == "removeLiquidity"
            # This throws panic error under the hood
            assert exc.orig_exception is not None
            assert isinstance(exc.orig_exception, ContractCustomError)
            assert "InsufficientBalance raised" in exc.orig_exception.args[1]

    @pytest.mark.anvil
    def test_invalid_close_long_from_zero(
        self,
        local_hyperdrive_pool: DeployedHyperdrivePool,
    ):
        """Test making a invalid close long with zero long tokens."""
        try:
            self._build_and_run_with_funded_bot(local_hyperdrive_pool, InvalidCloseLongFromZero)
        except ContractCallException as exc:
            # Expected error due to illegal trade
            # We do add an argument for invalid balance to the args, so check for that here
            assert "Invalid balance:" in exc.args[0]
            assert "long token not found in wallet" in exc.args[0]
            # Fails on close long
            assert exc.function_name_or_signature == "closeLong"
            # This throws panic error under the hood
            assert exc.orig_exception is not None
            assert isinstance(exc.orig_exception, ContractCustomError)
            assert "InsufficientBalance raised" in exc.orig_exception.args[1]

    @pytest.mark.anvil
    def test_invalid_close_short_from_zero(
        self,
        local_hyperdrive_pool: DeployedHyperdrivePool,
    ):
        """Test making a invalid close long with zero long tokens."""
        try:
            self._build_and_run_with_funded_bot(local_hyperdrive_pool, InvalidCloseShortFromZero)
        except ContractCallException as exc:
            # Expected error due to illegal trade
            # We do add an argument for invalid balance to the args, so check for that here
            assert "Invalid balance:" in exc.args[0]
            assert "short token not found in wallet" in exc.args[0]
            # Fails on close long
            assert exc.function_name_or_signature == "closeShort"
            # This throws panic error under the hood
            assert exc.orig_exception is not None
            assert isinstance(exc.orig_exception, ContractCustomError)
            assert "InsufficientBalance raised" in exc.orig_exception.args[1]

    @pytest.mark.anvil
    def test_invalid_redeem_withdraw_share_from_zero(
        self,
        local_hyperdrive_pool: DeployedHyperdrivePool,
    ):
        """Test making a invalid redeem withdrawal shares with zero withdrawal tokens."""
        try:
            self._build_and_run_with_funded_bot(local_hyperdrive_pool, InvalidRedeemWithdrawFromZero)
        # This is catching a value error, since this transaction is actually valid on the chain
        # We're explicitly catching this and throwing a value error in redeem withdraw shares
        except ValueError as exc:
            # Expected error due to illegal trade
            # We do add an argument for invalid balance to the args, so check for that here
            assert "Invalid balance:" in exc.args[0]
            # Error message should print out the balance of withdraw shares here
            assert "balance of " in exc.args[0]
            assert exc.args[1] == "Preview call for redeem withdrawal shares returned 0 for non-zero input trade amount"

    @pytest.mark.anvil
    def test_invalid_remove_liquidity_from_nonzero(
        self,
        local_hyperdrive_pool: DeployedHyperdrivePool,
    ):
        """Test making a invalid remove liquidity trade with nonzero lp tokens."""
        try:
            self._build_and_run_with_funded_bot(local_hyperdrive_pool, InvalidRemoveLiquidityFromNonZero)
        except ContractCallException as exc:
            # Expected error due to illegal trade
            # We do add an argument for invalid balance to the args, so check for that here
            assert "Invalid balance:" in exc.args[0]
            # Fails on remove liquidity
            assert exc.function_name_or_signature == "removeLiquidity"
            # This throws panic error under the hood
            assert exc.orig_exception is not None
            assert isinstance(exc.orig_exception, ContractCustomError)
            assert "InsufficientBalance raised" in exc.orig_exception.args[1]

    @pytest.mark.anvil
    def test_invalid_close_long_from_nonzero(
        self,
        local_hyperdrive_pool: DeployedHyperdrivePool,
    ):
        """Test when making a invalid close long with nonzero long tokens."""
        try:
            self._build_and_run_with_funded_bot(local_hyperdrive_pool, InvalidCloseLongFromNonZero)
        except ContractCallException as exc:
            # Expected error due to illegal trade
            # We do add an argument for invalid balance to the args, so check for that here
            assert "Invalid balance:" in exc.args[0]
            # Fails on closeLong
            assert exc.function_name_or_signature == "closeLong"
            # This throws panic error under the hood
            assert exc.orig_exception is not None
            assert isinstance(exc.orig_exception, ContractCustomError)
            assert "InsufficientBalance raised" in exc.orig_exception.args[1]

    @pytest.mark.anvil
    def test_invalid_close_short_from_nonzero(
        self,
        local_hyperdrive_pool: DeployedHyperdrivePool,
    ):
        """Test making a invalid close short with nonzero short tokens."""
        try:
            self._build_and_run_with_funded_bot(local_hyperdrive_pool, InvalidCloseShortFromNonZero)
        except ContractCallException as exc:
            # Expected error due to illegal trade
            # We do add an argument for invalid balance to the args, so check for that here
            assert "Invalid balance:" in exc.args[0]
            # Fails on closeShort
            assert exc.function_name_or_signature == "closeShort"
            # This throws panic error under the hood
            assert exc.orig_exception is not None
            assert isinstance(exc.orig_exception, ContractCustomError)
            assert "InsufficientBalance raised" in exc.orig_exception.args[1]

    @pytest.mark.anvil
    def test_invalid_redeem_withdraw_from_nonzero(
        self,
        local_hyperdrive_pool: DeployedHyperdrivePool,
    ):
        """Test making a invalid close short with nonzero short tokens."""
        try:
            self._build_and_run_with_funded_bot(local_hyperdrive_pool, InvalidRedeemWithdrawFromNonZero)
        # This is catching a value error, since this transaction is actually valid on the chain
        # We're explicitly catching this and throwing a value error in redeem withdraw shares
        except ValueError as exc:
            # Expected error due to illegal trade
            # We do add an argument for invalid balance to the args, so check for that here
            assert "Invalid balance:" in exc.args[0]
            # Error message should print out the balance of withdraw shares here
            assert "balance of " in exc.args[0]
            assert exc.args[1] == "Preview call for redeem withdrawal shares returned 0 for non-zero input trade amount"

    @pytest.mark.anvil
    def test_invalid_redeem_withdraw_in_pool(
        self,
        local_hyperdrive_pool: DeployedHyperdrivePool,
    ):
        """Test making a invalid close short with nonzero short tokens."""
        try:
            self._build_and_run_with_funded_bot(local_hyperdrive_pool, InvalidRedeemWithdrawInPool)
        # This is catching a value error, since this transaction is actually valid on the chain
        # We're explicitly catching this and throwing a value error in redeem withdraw shares
        except ValueError as exc:
            # Expected error due to illegal trade
            # We do add an argument for invalid balance to the args, so check for that here
            assert "Invalid balance:" in exc.args[0]
            assert "not enough ready to withdraw" in exc.args[0]
            assert exc.args[1] == "Preview call for redeem withdrawal shares returned 0 for non-zero input trade amount"

"""Test for invalid trades due to balance"""
from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Type, cast

from agent0 import build_account_key_config_from_agent_config
from agent0.base.config import AgentConfig, EnvironmentConfig
from agent0.hyperdrive.exec import run_agents
from agent0.hyperdrive.policies import HyperdrivePolicy
from agent0.hyperdrive.state import HyperdriveActionType, HyperdriveMarketAction, HyperdriveWallet
from elfpy.types import MarketType, Trade
from eth_typing import URI
from ethpy import EthConfig
from ethpy.base.errors import ContractCallException
from fixedpointmath import FixedPoint
from numpy.random._generator import Generator as NumpyGenerator
from web3 import HTTPProvider
from web3.exceptions import ContractPanicError

if TYPE_CHECKING:
    from ethpy.hyperdrive import HyperdriveAddresses
    from ethpy.hyperdrive.api import HyperdriveInterface
    from ethpy.test_fixtures.local_chain import DeployedHyperdrivePool


# Start by defining policies for failed trades
# One policy per failed trade
# Starting with empty wallet, catching any closing trades.
class InvalidRemoveLiquidityFromZero(HyperdrivePolicy):
    """A agent that submits a remove liquidity with a zero wallet"""

    def __init__(
        self,
        budget: FixedPoint,
        rng: NumpyGenerator | None = None,
        slippage_tolerance: FixedPoint | None = None,
        # When this policy doesn't have a config and doesn't define a custom config object
        # we still need it in the constructor since the object factory still calls with this arg
        policy_config: HyperdrivePolicy.Config | None = None,  # pylint: disable=unused-argument
    ):
        # TODO Base class doesn't take policy_config, but it's needed for the object factory, fix
        super().__init__(budget, rng, slippage_tolerance)

    def action(
        self, hyperdrive: HyperdriveInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        # pylint: disable=unused-argument
        action_list = []
        # Remove non-existing Liquidity
        action_list.append(
            Trade(
                market_type=MarketType.HYPERDRIVE,
                market_action=HyperdriveMarketAction(
                    action_type=HyperdriveActionType.REMOVE_LIQUIDITY,
                    trade_amount=FixedPoint(20000),
                    wallet=wallet,
                ),
            )
        )
        return action_list, True


class InvalidCloseLongFromZero(HyperdrivePolicy):
    """A agent that submits a close long with a zero wallet"""

    def __init__(
        self,
        budget: FixedPoint,
        rng: NumpyGenerator | None = None,
        slippage_tolerance: FixedPoint | None = None,
        # When this policy doesn't have a config and doesn't define a custom config object
        # we still need it in the constructor since the object factory still calls with this arg
        policy_config: HyperdrivePolicy.Config | None = None,  # pylint: disable=unused-argument
    ):
        # TODO Base class doesn't take policy_config, but it's needed for the object factory, fix
        super().__init__(budget, rng, slippage_tolerance)

    def action(
        self, hyperdrive: HyperdriveInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        # pylint: disable=unused-argument
        action_list = []
        # Closing non-existent long
        action_list.append(
            Trade(
                market_type=MarketType.HYPERDRIVE,
                market_action=HyperdriveMarketAction(
                    action_type=HyperdriveActionType.CLOSE_LONG,
                    trade_amount=FixedPoint(20000),
                    slippage_tolerance=self.slippage_tolerance,
                    wallet=wallet,
                    maturity_time=1699561146,
                ),
            )
        )
        return action_list, True


class InvalidCloseShortFromZero(HyperdrivePolicy):
    """A agent that submits a close short with a zero wallet"""

    def __init__(
        self,
        budget: FixedPoint,
        rng: NumpyGenerator | None = None,
        slippage_tolerance: FixedPoint | None = None,
        # When this policy doesn't have a config and doesn't define a custom config object
        # we still need it in the constructor since the object factory still calls with this arg
        policy_config: HyperdrivePolicy.Config | None = None,  # pylint: disable=unused-argument
    ):
        # TODO Base class doesn't take policy_config, but it's needed for the object factory, fix
        super().__init__(budget, rng, slippage_tolerance)

    def action(
        self, hyperdrive: HyperdriveInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        # pylint: disable=unused-argument
        action_list = []
        # Closing non-existent short
        action_list.append(
            Trade(
                market_type=MarketType.HYPERDRIVE,
                market_action=HyperdriveMarketAction(
                    action_type=HyperdriveActionType.CLOSE_SHORT,
                    trade_amount=FixedPoint(20000),
                    slippage_tolerance=self.slippage_tolerance,
                    wallet=wallet,
                    maturity_time=1699561146,
                ),
            )
        )
        return action_list, True


class InvalidRedeemWithdrawFromZero(HyperdrivePolicy):
    """A agent that submits a redeem withdrawal share with a zero wallet"""

    def __init__(
        self,
        budget: FixedPoint,
        rng: NumpyGenerator | None = None,
        slippage_tolerance: FixedPoint | None = None,
        # When this policy doesn't have a config and doesn't define a custom config object
        # we still need it in the constructor since the object factory still calls with this arg
        policy_config: HyperdrivePolicy.Config | None = None,  # pylint: disable=unused-argument
    ):
        # TODO Base class doesn't take policy_config, but it's needed for the object factory, fix
        super().__init__(budget, rng, slippage_tolerance)

    def action(
        self, hyperdrive: HyperdriveInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        # pylint: disable=unused-argument
        action_list = []
        # Redeem non-existent withdrawal shares
        action_list.append(
            Trade(
                market_type=MarketType.HYPERDRIVE,
                market_action=HyperdriveMarketAction(
                    action_type=HyperdriveActionType.REDEEM_WITHDRAW_SHARE,
                    trade_amount=FixedPoint(20000),
                    wallet=wallet,
                ),
            )
        )
        return action_list, True


class InvalidRemoveLiquidityFromNonZero(HyperdrivePolicy):
    """A agent that submits an invalid remove liquidity share with a non-zero wallet"""

    def __init__(
        self,
        budget: FixedPoint,
        rng: NumpyGenerator | None = None,
        slippage_tolerance: FixedPoint | None = None,
        # When this policy doesn't have a config and doesn't define a custom config object
        # we still need it in the constructor since the object factory still calls with this arg
        policy_config: HyperdrivePolicy.Config | None = None,  # pylint: disable=unused-argument
    ):
        # We want to do a sequence of trades one at a time, so we keep an internal counter based on
        # how many times `action` has been called.
        self.counter = 0
        super().__init__(budget, rng, slippage_tolerance)

    def action(
        self, hyperdrive: HyperdriveInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        # pylint: disable=unused-argument
        action_list = []
        done_trading = False
        if self.counter == 0:
            # Add liquidity
            action_list.append(
                Trade(
                    market_type=MarketType.HYPERDRIVE,
                    market_action=HyperdriveMarketAction(
                        action_type=HyperdriveActionType.ADD_LIQUIDITY,
                        trade_amount=FixedPoint(10000),
                        wallet=wallet,
                    ),
                )
            )
        elif self.counter == 1:
            # Remove Liquidity for more than I have
            action_list.append(
                Trade(
                    market_type=MarketType.HYPERDRIVE,
                    market_action=HyperdriveMarketAction(
                        action_type=HyperdriveActionType.REMOVE_LIQUIDITY,
                        trade_amount=FixedPoint(20000),
                        wallet=wallet,
                    ),
                )
            )
            done_trading = True
        self.counter += 1
        return action_list, done_trading


class InvalidCloseLongFromNonZero(HyperdrivePolicy):
    """A agent that submits an invalid close long with a non-zero wallet"""

    def __init__(
        self,
        budget: FixedPoint,
        rng: NumpyGenerator | None = None,
        slippage_tolerance: FixedPoint | None = None,
        # When this policy doesn't have a config and doesn't define a custom config object
        # we still need it in the constructor since the object factory still calls with this arg
        policy_config: HyperdrivePolicy.Config | None = None,  # pylint: disable=unused-argument
    ):
        # We want to do a sequence of trades one at a time, so we keep an internal counter based on
        # how many times `action` has been called.
        self.counter = 0
        super().__init__(budget, rng, slippage_tolerance)

    def action(
        self, hyperdrive: HyperdriveInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
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
                        wallet=wallet,
                    ),
                ),
            )
        elif self.counter == 1:
            # Closing existent long for more than I have
            assert len(wallet.longs) == 1
            for long_time, _ in wallet.longs.items():
                action_list.append(
                    Trade(
                        market_type=MarketType.HYPERDRIVE,
                        market_action=HyperdriveMarketAction(
                            action_type=HyperdriveActionType.CLOSE_LONG,
                            trade_amount=FixedPoint(20000),
                            slippage_tolerance=self.slippage_tolerance,
                            wallet=wallet,
                            maturity_time=long_time,
                        ),
                    )
                )
            done_trading = True
        self.counter += 1
        return action_list, done_trading


class InvalidCloseShortFromNonZero(HyperdrivePolicy):
    """A agent that submits an invalid close short with a non-zero wallet"""

    def __init__(
        self,
        budget: FixedPoint,
        rng: NumpyGenerator | None = None,
        slippage_tolerance: FixedPoint | None = None,
        # When this policy doesn't have a config and doesn't define a custom config object
        # we still need it in the constructor since the object factory still calls with this arg
        policy_config: HyperdrivePolicy.Config | None = None,  # pylint: disable=unused-argument
    ):
        # We want to do a sequence of trades one at a time, so we keep an internal counter based on
        # how many times `action` has been called.
        self.counter = 0
        super().__init__(budget, rng, slippage_tolerance)

    def action(
        self, hyperdrive: HyperdriveInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
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
                        wallet=wallet,
                    ),
                )
            )
        elif self.counter == 1:
            # Closing existent short for more than I have
            assert len(wallet.shorts) == 1
            for short_time, _ in wallet.shorts.items():
                action_list.append(
                    Trade(
                        market_type=MarketType.HYPERDRIVE,
                        market_action=HyperdriveMarketAction(
                            action_type=HyperdriveActionType.CLOSE_SHORT,
                            trade_amount=FixedPoint(20000),
                            slippage_tolerance=self.slippage_tolerance,
                            wallet=wallet,
                            maturity_time=short_time,
                        ),
                    )
                )
            done_trading = True
        self.counter += 1
        return action_list, done_trading


class InvalidRedeemWithdrawInPool(HyperdrivePolicy):
    """A agent that submits an invalid remove liquidity when not enough ready to withdrawal"""

    def __init__(
        self,
        budget: FixedPoint,
        rng: NumpyGenerator | None = None,
        slippage_tolerance: FixedPoint | None = None,
        # When this policy doesn't have a config and doesn't define a custom config object
        # we still need it in the constructor since the object factory still calls with this arg
        policy_config: HyperdrivePolicy.Config | None = None,  # pylint: disable=unused-argument
    ):
        # We want to do a sequence of trades one at a time, so we keep an internal counter based on
        # how many times `action` has been called.
        self.counter = 0
        super().__init__(budget, rng, slippage_tolerance)

    def action(
        self, hyperdrive: HyperdriveInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        # pylint: disable=unused-argument
        action_list = []
        done_trading = False
        # We make various trades to ensure the wallet has a non-zero withdrawal share
        # Valid add liquidity
        if self.counter == 0:
            # Add liquidity
            action_list.append(
                Trade(
                    market_type=MarketType.HYPERDRIVE,
                    market_action=HyperdriveMarketAction(
                        action_type=HyperdriveActionType.ADD_LIQUIDITY,
                        trade_amount=FixedPoint(10000),
                        wallet=wallet,
                    ),
                )
            )
        # Valid open long + short
        elif self.counter == 1:
            # Open Long
            action_list.append(
                Trade(
                    market_type=MarketType.HYPERDRIVE,
                    market_action=HyperdriveMarketAction(
                        action_type=HyperdriveActionType.OPEN_LONG,
                        trade_amount=FixedPoint(10000),
                        slippage_tolerance=self.slippage_tolerance,
                        wallet=wallet,
                    ),
                ),
            )
            # Open Short
            action_list.append(
                Trade(
                    market_type=MarketType.HYPERDRIVE,
                    market_action=HyperdriveMarketAction(
                        action_type=HyperdriveActionType.OPEN_SHORT,
                        trade_amount=FixedPoint(10000),
                        slippage_tolerance=self.slippage_tolerance,
                        wallet=wallet,
                    ),
                )
            )
        # Valid remove liquidity
        elif self.counter == 2:
            # Remove all liquidity
            action_list.append(
                Trade(
                    market_type=MarketType.HYPERDRIVE,
                    market_action=HyperdriveMarketAction(
                        action_type=HyperdriveActionType.REMOVE_LIQUIDITY,
                        trade_amount=wallet.lp_tokens,
                        wallet=wallet,
                    ),
                )
            )
        elif self.counter == 3:
            # Attempt to redeem withdrawal shares that are not ready to withdrawal
            # since the open trades are not closed
            assert wallet.withdraw_shares > FixedPoint(0)
            action_list.append(
                Trade(
                    market_type=MarketType.HYPERDRIVE,
                    market_action=HyperdriveMarketAction(
                        action_type=HyperdriveActionType.REDEEM_WITHDRAW_SHARE,
                        trade_amount=wallet.withdraw_shares,
                        wallet=wallet,
                    ),
                )
            )
            # Last trade, set flag
            done_trading = True
        self.counter += 1

        return action_list, done_trading


class InvalidRedeemWithdrawFromNonZero(HyperdrivePolicy):
    """A agent that submits an invalid remove liquidity share with a non-zero wallet"""

    def __init__(
        self,
        budget: FixedPoint,
        rng: NumpyGenerator | None = None,
        slippage_tolerance: FixedPoint | None = None,
        # When this policy doesn't have a config and doesn't define a custom config object
        # we still need it in the constructor since the object factory still calls with this arg
        policy_config: HyperdrivePolicy.Config | None = None,  # pylint: disable=unused-argument
    ):
        # We want to do a sequence of trades one at a time, so we keep an internal counter based on
        # how many times `action` has been called.
        self.counter = 0
        super().__init__(budget, rng, slippage_tolerance)

    def action(
        self, hyperdrive: HyperdriveInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        # pylint: disable=unused-argument
        action_list = []
        done_trading = False
        # We make various trades to ensure the wallet has a non-zero withdrawal share
        # Valid add liquidity
        if self.counter == 0:
            # Add liquidity
            action_list.append(
                Trade(
                    market_type=MarketType.HYPERDRIVE,
                    market_action=HyperdriveMarketAction(
                        action_type=HyperdriveActionType.ADD_LIQUIDITY,
                        trade_amount=FixedPoint(10000),
                        wallet=wallet,
                    ),
                )
            )
        # Valid open long + short
        elif self.counter == 1:
            # Open Long
            action_list.append(
                Trade(
                    market_type=MarketType.HYPERDRIVE,
                    market_action=HyperdriveMarketAction(
                        action_type=HyperdriveActionType.OPEN_LONG,
                        trade_amount=FixedPoint(10000),
                        slippage_tolerance=self.slippage_tolerance,
                        wallet=wallet,
                    ),
                ),
            )
            # Open Short
            action_list.append(
                Trade(
                    market_type=MarketType.HYPERDRIVE,
                    market_action=HyperdriveMarketAction(
                        action_type=HyperdriveActionType.OPEN_SHORT,
                        trade_amount=FixedPoint(10000),
                        slippage_tolerance=self.slippage_tolerance,
                        wallet=wallet,
                    ),
                )
            )
        # Valid remove liquidity
        elif self.counter == 2:
            # Remove all liquidity
            action_list.append(
                Trade(
                    market_type=MarketType.HYPERDRIVE,
                    market_action=HyperdriveMarketAction(
                        action_type=HyperdriveActionType.REMOVE_LIQUIDITY,
                        trade_amount=wallet.lp_tokens,
                        wallet=wallet,
                    ),
                )
            )
        elif self.counter == 3:
            # Attempt to redeem withdrawal shares that are not ready to withdrawal
            # since the open trades are not closed
            assert wallet.withdraw_shares > FixedPoint(0)
            action_list.append(
                Trade(
                    market_type=MarketType.HYPERDRIVE,
                    market_action=HyperdriveMarketAction(
                        action_type=HyperdriveActionType.REDEEM_WITHDRAW_SHARE,
                        trade_amount=FixedPoint(20000),
                        wallet=wallet,
                    ),
                )
            )
            # Last trade, set flag
            done_trading = True
        self.counter += 1

        return action_list, done_trading


class TestInvalidTrades:
    """Tests pipeline from bots making trades to viewing the trades in the db"""

    def _build_and_run_with_funded_bot(self, hyperdrive_pool: DeployedHyperdrivePool, policy: Type[HyperdrivePolicy]):
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
            random_seed=1234,
            username="test",
        )

        # Get hyperdrive chain info
        rpc_uri: URI | None = cast(HTTPProvider, hyperdrive_pool.web3.provider).endpoint_uri
        assert rpc_uri is not None
        hyperdrive_contract_addresses: HyperdriveAddresses = hyperdrive_pool.hyperdrive_contract_addresses

        # Build agent config
        agent_config: list[AgentConfig] = [
            AgentConfig(
                policy=policy,
                number_of_agents=1,
                slippage_tolerance=None,
                base_budget_wei=FixedPoint("1_000_000").scaled_value,  # 1 million base
                eth_budget_wei=FixedPoint("100").scaled_value,  # 100 base
                policy_config=policy.Config(),
            ),
        ]
        account_key_config = build_account_key_config_from_agent_config(agent_config)
        # Build custom eth config pointing to local test chain
        eth_config = EthConfig(
            # Artifacts_uri isn't used here, as we explicitly set addresses and passed to run_bots
            artifacts_uri="not_used",
            rpc_uri=rpc_uri,
        )
        run_agents(
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
        self, hyperdrive_pool: DeployedHyperdrivePool, policy: Type[HyperdrivePolicy]
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
            random_seed=1234,
            username="test",
        )

        # Get hyperdrive chain info
        rpc_uri: URI | None = cast(HTTPProvider, hyperdrive_pool.web3.provider).endpoint_uri
        assert rpc_uri is not None
        hyperdrive_contract_addresses: HyperdriveAddresses = hyperdrive_pool.hyperdrive_contract_addresses

        # Build agent config
        agent_config: list[AgentConfig] = [
            AgentConfig(
                policy=policy,
                number_of_agents=1,
                slippage_tolerance=None,
                base_budget_wei=FixedPoint("10").scaled_value,  # 10 base
                eth_budget_wei=FixedPoint("100").scaled_value,  # 100 base
                policy_config=policy.Config(),
            ),
        ]
        account_key_config = build_account_key_config_from_agent_config(agent_config)
        # Build custom eth config pointing to local test chain
        eth_config = EthConfig(
            # Artifacts_uri isn't used here, as we explicitly set addresses and passed to run_bots
            artifacts_uri="not_used",
            rpc_uri=rpc_uri,
        )
        run_agents(
            env_config,
            agent_config,
            account_key_config,
            eth_config=eth_config,
            contract_addresses=hyperdrive_contract_addresses,
            load_wallet_state=False,
        )
        # If this reaches this point, the agent was successful, which means this test should fail
        assert False, "Agent was successful with known invalid trade"

    def test_not_enough_base(
        self,
        local_hyperdrive_pool: DeployedHyperdrivePool,
    ):
        """Tests when making a trade with not enough base in wallet"""
        try:
            self._build_and_run_with_non_funded_bot(local_hyperdrive_pool, InvalidRemoveLiquidityFromNonZero)

        except ContractCallException as exc:
            # Expected error due to illegal trade
            # We do add an argument for invalid balance to the args, so check for that here
            assert "Invalid balance:" in exc.args[0]
            # Fails on add liquidity
            assert exc.function_name_or_signature == "addLiquidity"
            # This throws panic error under the hood
            assert exc.orig_exception is not None
            assert isinstance(exc.orig_exception, ContractPanicError)
            assert (
                exc.orig_exception.args[0] == "Panic error 0x11: Arithmetic operation results in underflow or overflow."
            )

    def test_invalid_remove_liquidity_from_zero(
        self,
        local_hyperdrive_pool: DeployedHyperdrivePool,
    ):
        """Tests when making a invalid remove liquidity with zero lp tokens"""
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
            assert isinstance(exc.orig_exception, ContractPanicError)
            assert (
                exc.orig_exception.args[0] == "Panic error 0x11: Arithmetic operation results in underflow or overflow."
            )

    def test_invalid_close_long_from_zero(
        self,
        local_hyperdrive_pool: DeployedHyperdrivePool,
    ):
        """Tests when making a invalid close long with zero long tokens"""
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
            assert isinstance(exc.orig_exception, ContractPanicError)
            assert (
                exc.orig_exception.args[0] == "Panic error 0x11: Arithmetic operation results in underflow or overflow."
            )

    def test_invalid_close_short_from_zero(
        self,
        local_hyperdrive_pool: DeployedHyperdrivePool,
    ):
        """Tests when making a invalid close long with zero long tokens"""
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
            assert isinstance(exc.orig_exception, ContractPanicError)
            assert (
                exc.orig_exception.args[0] == "Panic error 0x11: Arithmetic operation results in underflow or overflow."
            )

    def test_invalid_redeem_withdraw_share_from_zero(
        self,
        local_hyperdrive_pool: DeployedHyperdrivePool,
    ):
        """Tests when making a invalid redeem withdrawal shares with zero withdrawal tokens"""
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

    def test_invalid_remove_liquidity_from_nonzero(
        self,
        local_hyperdrive_pool: DeployedHyperdrivePool,
    ):
        """Tests when making a invalid remove liquidity trade with nonzero lp tokens"""
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
            assert isinstance(exc.orig_exception, ContractPanicError)
            assert (
                exc.orig_exception.args[0] == "Panic error 0x11: Arithmetic operation results in underflow or overflow."
            )

    def test_invalid_close_long_from_nonzero(
        self,
        local_hyperdrive_pool: DeployedHyperdrivePool,
    ):
        """Tests when making a invalid close long with nonzero long tokens"""
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
            assert isinstance(exc.orig_exception, ContractPanicError)
            assert (
                exc.orig_exception.args[0] == "Panic error 0x11: Arithmetic operation results in underflow or overflow."
            )

    def test_invalid_close_short_from_nonzero(
        self,
        local_hyperdrive_pool: DeployedHyperdrivePool,
    ):
        """Tests when making a invalid close short with nonzero short tokens"""
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
            assert isinstance(exc.orig_exception, ContractPanicError)
            assert (
                exc.orig_exception.args[0] == "Panic error 0x11: Arithmetic operation results in underflow or overflow."
            )

    def test_invalid_redeem_withdraw_from_nonzero(
        self,
        local_hyperdrive_pool: DeployedHyperdrivePool,
    ):
        """Tests when making a invalid close short with nonzero short tokens"""
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

    def test_invalid_redeem_withdraw_in_pool(
        self,
        local_hyperdrive_pool: DeployedHyperdrivePool,
    ):
        """Tests when making a invalid close short with nonzero short tokens"""
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
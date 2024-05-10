"""Defines the interactive hyperdrive class that encapsulates a hyperdrive pool."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Literal, Type, overload

import nest_asyncio
import numpy as np
from eth_account.account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import ChecksumAddress
from fixedpointmath import FixedPoint
from numpy.random._generator import Generator
from web3 import Web3

from agent0.core.hyperdrive import HyperdriveActionType, HyperdrivePolicyAgent, TradeResult, TradeStatus
from agent0.core.hyperdrive.agent import (
    add_liquidity_trade,
    build_wallet_positions_from_chain,
    close_long_trade,
    close_short_trade,
    open_long_trade,
    open_short_trade,
    redeem_withdraw_shares_trade,
    remove_liquidity_trade,
)
from agent0.core.hyperdrive.crash_report import log_hyperdrive_crash_report
from agent0.core.hyperdrive.policies import HyperdriveBasePolicy
from agent0.core.test_utils import assert_never
from agent0.ethpy.base import set_anvil_account_balance, smart_contract_transact
from agent0.ethpy.hyperdrive import (
    HyperdriveReadWriteInterface,
    ReceiptBreakdown,
    get_hyperdrive_addresses_from_artifacts,
    get_hyperdrive_addresses_from_registry,
)

from .chain import Chain
from .event_types import (
    AddLiquidity,
    CloseLong,
    CloseShort,
    OpenLong,
    OpenShort,
    RedeemWithdrawalShares,
    RemoveLiquidity,
)
from .exec import async_execute_agent_trades, async_execute_single_trade, set_max_approval
from .hyperdrive_agent import HyperdriveAgent

# In order to support both scripts and jupyter notebooks with underlying async functions,
# we use the nest_asyncio package so that we can execute asyncio.run within a running event loop.
# TODO: nest_asyncio may cause compatibility issues with other libraries.
# Also, Jupyter and ASYNC compatibility might be improved, removing the need for this.
# See https://github.com/python/cpython/issues/66435.
nest_asyncio.apply()


class Hyperdrive:
    """Interactive Hyperdrive class that supports connecting to an existing hyperdrive deployment."""

    # Lots of config
    # pylint: disable=too-many-instance-attributes
    @dataclass(kw_only=True)
    class Config:
        """The configuration for the interactive hyperdrive class."""

        exception_on_policy_error: bool = True
        """When executing agent policies, whether to raise an exception if an error is encountered. Defaults to True."""
        exception_on_policy_slippage: bool = False
        """
        When executing agent policies, whether to raise an exception if the slippage is too large. Defaults to False.
        """
        preview_before_trade: bool = False
        """Whether to preview the position before executing a trade. Defaults to False."""
        rng_seed: int | None = None
        """The seed for the random number generator. Defaults to None."""
        rng: Generator | None = None
        """
        The experiment's stateful random number generator. Defaults to creating a generator from
        the provided random seed if not set.
        """
        log_to_rollbar: bool = False
        """Whether to log crash reports to rollbar. Defaults to False."""
        rollbar_log_prefix: str | None = None
        """Additional prefix for this hyperdrive to log to rollbar."""
        crash_log_level: int = logging.CRITICAL
        """The log level to log crashes at. Defaults to critical."""
        crash_report_additional_info: dict[str, Any] | None = None
        """Additional information to include in the crash report."""
        always_execute_policy_post_action: bool = False
        """
        Whether to execute the policy `post_action` function after non-policy trades. 
        If True, the policy `post_action` function always be called after any agent trade.
        If False, the policy `post_action` function will only be called after `execute_policy_action`.
        Defaults to False.
        """
        txn_receipt_timeout: float | None = None
        """The timeout for waiting for a transaction receipt in seconds. Defaults to 120."""

        def __post_init__(self):
            """Create the random number generator if not set."""
            if self.rng is None:
                self.rng = np.random.default_rng(self.rng_seed)

    @classmethod
    def get_hyperdrive_addresses_from_artifacts(
        cls,
        artifacts_uri: str,
    ) -> dict[str, ChecksumAddress]:
        """Gather deployed Hyperdrive pool addresses.

        Arguments
        ---------
        artifacts_uri: str
            The uri of the artifacts json file. This is specific to the infra deployment.

        Returns
        -------
        dict[str, ChecksumAddress]
            A dictionary keyed by the pool's name, valued by the pool's address
        """
        # pylint: disable=protected-access
        return get_hyperdrive_addresses_from_artifacts(artifacts_uri)

    @classmethod
    def get_hyperdrive_addresses_from_registry(
        cls,
        chain: Chain,
        registry_contract_addr: str,
    ) -> dict[str, ChecksumAddress]:
        """Gather deployed Hyperdrive pool addresses.

        Arguments
        ---------
        chain: Chain
            The Chain object connected to a chain.
        registry_contract_addr: str
            The address of the Hyperdrive factory contract.

        Returns
        -------
        dict[str, ChecksumAddress]
            A dictionary keyed by the pool's name, valued by the pool's address
        """
        # pylint: disable=protected-access
        return get_hyperdrive_addresses_from_registry(registry_contract_addr, chain._web3)

    def __init__(
        self,
        chain: Chain,
        hyperdrive_address: ChecksumAddress,
        config: Config | None = None,
    ):
        """Initialize the interactive hyperdrive class.

        Arguments
        ---------
        chain: Chain
            The chain to interact with
        hyperdrive_address: ChecksumAddress
            The address of the hyperdrive contract
        config: Config | None
            The configuration for the interactive hyperdrive class
        """
        if config is None:
            self.config = self.Config()
        else:
            self.config = config

        self.interface = HyperdriveReadWriteInterface(
            hyperdrive_address,
            rpc_uri=chain.rpc_uri,
            web3=chain._web3,
            txn_receipt_timeout=self.config.txn_receipt_timeout,
        )

        self.chain = chain

    def init_agent(
        self,
        private_key: str,
        policy: Type[HyperdriveBasePolicy] | None = None,
        policy_config: HyperdriveBasePolicy.Config | None = None,
    ) -> HyperdriveAgent:
        """Initialize an agent object given a private key.

        .. note::
            Due to the underlying bookkeeping, each agent object needs a unique private key.

        Arguments
        ---------
        private_key: str
            The private key of the associated account.
        policy: HyperdrivePolicy, optional
            An optional policy to attach to this agent.
        policy_config: HyperdrivePolicy, optional
            The configuration for the attached policy.

        Returns
        -------
        HyperdriveAgent
            The agent object for a user to execute trades with.
        """
        # If the underlying policy's rng isn't set, we use the one from interactive hyperdrive
        if policy_config is not None and policy_config.rng is None and policy_config.rng_seed is None:
            policy_config.rng = self.config.rng
        out_agent = HyperdriveAgent(
            pool=self,
            policy=policy,
            policy_config=policy_config,
            private_key=private_key,
        )
        return out_agent

    def _init_agent(
        self,
        policy: Type[HyperdriveBasePolicy] | None,
        policy_config: HyperdriveBasePolicy.Config | None,
        private_key: str,
    ) -> HyperdrivePolicyAgent[HyperdriveBasePolicy]:
        # Setting the budget to 0 here, we'll update the wallet from the chain
        if policy is None:
            if policy_config is None:
                policy_config = HyperdriveBasePolicy.Config(rng=self.config.rng)
            policy_obj = HyperdriveBasePolicy(policy_config)
        else:
            if policy_config is None:
                policy_config = policy.Config(rng=self.config.rng)
            policy_obj = policy(policy_config)

        agent = HyperdrivePolicyAgent(Account().from_key(private_key), initial_budget=FixedPoint(0), policy=policy_obj)

        self._sync_wallet(agent)
        return agent

    def _set_max_approval(self, agent: HyperdrivePolicyAgent) -> None:
        # Establish max approval for the hyperdrive contract
        set_max_approval(
            agent,
            self.interface.web3,
            self.interface.base_token_contract,
            str(self.interface.hyperdrive_contract.address),
        )

    def _sync_wallet(self, agent: HyperdrivePolicyAgent) -> None:
        # TODO add sync from db
        agent.wallet = build_wallet_positions_from_chain(agent, self.interface)

    def _add_funds(
        self,
        agent: HyperdrivePolicyAgent,
        base: FixedPoint,
        eth: FixedPoint,
        signer_account: LocalAccount | None = None,
    ) -> None:
        # The signer of the mint transaction defaults to the agent itself, unless specified.
        if signer_account is None:
            signer_account = agent

        if eth > FixedPoint(0):
            # Eth is a set balance call
            eth_balance, _ = self.interface.get_eth_base_balances(agent)
            new_eth_balance = eth_balance + eth
            _ = set_anvil_account_balance(self.interface.web3, agent.address, new_eth_balance.scaled_value)

        if base > FixedPoint(0):
            # We mint base
            _ = smart_contract_transact(
                self.interface.web3,
                self.interface.base_token_contract,
                signer_account,
                "mint(address,uint256)",
                agent.checksum_address,
                base.scaled_value,
            )
            # Update the agent's wallet balance
            agent.wallet.balance.amount += base

    def _open_long(self, agent: HyperdrivePolicyAgent, base: FixedPoint) -> OpenLong:
        # Build trade object
        trade_object = open_long_trade(base)
        # TODO expose async here to the caller eventually
        trade_result: TradeResult = asyncio.run(
            async_execute_single_trade(
                self.interface,
                agent,
                trade_object,
                self.config.always_execute_policy_post_action,
                self.config.preview_before_trade,
            )
        )
        tx_receipt = self._handle_trade_result(trade_result, always_throw_exception=True)
        return self._build_event_obj_from_tx_receipt(HyperdriveActionType.OPEN_LONG, tx_receipt)

    def _close_long(self, agent: HyperdrivePolicyAgent, maturity_time: int, bonds: FixedPoint) -> CloseLong:
        # Build trade object
        trade_object = close_long_trade(bonds, maturity_time)
        # TODO expose async here to the caller eventually
        trade_result: TradeResult = asyncio.run(
            async_execute_single_trade(
                self.interface,
                agent,
                trade_object,
                self.config.always_execute_policy_post_action,
                self.config.preview_before_trade,
            )
        )
        tx_receipt = self._handle_trade_result(trade_result, always_throw_exception=True)
        return self._build_event_obj_from_tx_receipt(HyperdriveActionType.CLOSE_LONG, tx_receipt)

    def _open_short(self, agent: HyperdrivePolicyAgent, bonds: FixedPoint) -> OpenShort:
        trade_object = open_short_trade(bonds)
        # TODO expose async here to the caller eventually
        trade_result: TradeResult = asyncio.run(
            async_execute_single_trade(
                self.interface,
                agent,
                trade_object,
                self.config.always_execute_policy_post_action,
                self.config.preview_before_trade,
            )
        )
        tx_receipt = self._handle_trade_result(trade_result, always_throw_exception=True)
        return self._build_event_obj_from_tx_receipt(HyperdriveActionType.OPEN_SHORT, tx_receipt)

    def _close_short(self, agent: HyperdrivePolicyAgent, maturity_time: int, bonds: FixedPoint) -> CloseShort:
        trade_object = close_short_trade(bonds, maturity_time)
        # TODO expose async here to the caller eventually
        trade_result: TradeResult = asyncio.run(
            async_execute_single_trade(
                self.interface,
                agent,
                trade_object,
                self.config.always_execute_policy_post_action,
                self.config.preview_before_trade,
            )
        )
        tx_receipt = self._handle_trade_result(trade_result, always_throw_exception=True)
        return self._build_event_obj_from_tx_receipt(HyperdriveActionType.CLOSE_SHORT, tx_receipt)

    def _add_liquidity(self, agent: HyperdrivePolicyAgent, base: FixedPoint) -> AddLiquidity:
        trade_object = add_liquidity_trade(base)
        # TODO expose async here to the caller eventually
        trade_result: TradeResult = asyncio.run(
            async_execute_single_trade(
                self.interface,
                agent,
                trade_object,
                self.config.always_execute_policy_post_action,
                self.config.preview_before_trade,
            )
        )
        tx_receipt = self._handle_trade_result(trade_result, always_throw_exception=True)
        return self._build_event_obj_from_tx_receipt(HyperdriveActionType.ADD_LIQUIDITY, tx_receipt)

    def _remove_liquidity(self, agent: HyperdrivePolicyAgent, shares: FixedPoint) -> RemoveLiquidity:
        trade_object = remove_liquidity_trade(shares)
        # TODO expose async here to the caller eventually
        trade_result: TradeResult = asyncio.run(
            async_execute_single_trade(
                self.interface,
                agent,
                trade_object,
                self.config.always_execute_policy_post_action,
                self.config.preview_before_trade,
            )
        )
        tx_receipt = self._handle_trade_result(trade_result, always_throw_exception=True)
        return self._build_event_obj_from_tx_receipt(HyperdriveActionType.REMOVE_LIQUIDITY, tx_receipt)

    def _redeem_withdraw_share(self, agent: HyperdrivePolicyAgent, shares: FixedPoint) -> RedeemWithdrawalShares:
        trade_object = redeem_withdraw_shares_trade(shares)
        # TODO expose async here to the caller eventually
        trade_results: TradeResult = asyncio.run(
            async_execute_single_trade(
                self.interface,
                agent,
                trade_object,
                self.config.always_execute_policy_post_action,
                self.config.preview_before_trade,
            )
        )
        tx_receipt = self._handle_trade_result(trade_results, always_throw_exception=True)
        return self._build_event_obj_from_tx_receipt(HyperdriveActionType.REDEEM_WITHDRAW_SHARE, tx_receipt)

    def _execute_policy_action(
        self, agent: HyperdrivePolicyAgent
    ) -> list[OpenLong | OpenShort | CloseLong | CloseShort | AddLiquidity | RemoveLiquidity | RedeemWithdrawalShares]:
        # Only allow executing agent policies if a policy was passed in the constructor
        # we check type instead of isinstance to explicitly check for the hyperdrive base class
        # pylint: disable=unidiomatic-typecheck
        if type(agent.policy) == HyperdriveBasePolicy:
            raise ValueError("Must pass in a policy in the constructor to execute policy action.")

        trade_results: list[TradeResult] = asyncio.run(
            async_execute_agent_trades(
                self.interface,
                agent,
                preview_before_trade=self.config.preview_before_trade,
                liquidate=False,
                interactive_mode=True,
            )
        )
        out_events = []
        # The underlying policy can execute multiple actions in one step
        for trade_result in trade_results:
            tx_receipt = self._handle_trade_result(trade_result, always_throw_exception=False)
            if tx_receipt is not None:
                assert trade_result.trade_object is not None
                action_type: HyperdriveActionType = trade_result.trade_object.market_action.action_type
                out_events.append(self._build_event_obj_from_tx_receipt(action_type, tx_receipt))
        # Build event from tx_receipt
        return out_events

    def _liquidate(
        self, agent: HyperdrivePolicyAgent, randomize: bool
    ) -> list[CloseLong | CloseShort | RemoveLiquidity | RedeemWithdrawalShares]:
        trade_results: list[TradeResult] = asyncio.run(
            async_execute_agent_trades(
                self.interface,
                agent,
                preview_before_trade=self.config.preview_before_trade,
                liquidate=True,
                randomize_liquidation=randomize,
                interactive_mode=True,
            )
        )
        out_events = []

        # The underlying policy can execute multiple actions in one step
        for trade_result in trade_results:
            tx_receipt = self._handle_trade_result(trade_result, always_throw_exception=False)
            if tx_receipt is not None:
                assert trade_result.trade_object is not None
                action_type: HyperdriveActionType = trade_result.trade_object.market_action.action_type
                out_events.append(self._build_event_obj_from_tx_receipt(action_type, tx_receipt))
        # Build event from tx_receipt
        return out_events

    @overload
    def _handle_trade_result(
        self, trade_result: TradeResult, always_throw_exception: Literal[True]
    ) -> ReceiptBreakdown: ...

    @overload
    def _handle_trade_result(
        self, trade_result: TradeResult, always_throw_exception: Literal[False]
    ) -> ReceiptBreakdown | None: ...

    def _handle_trade_result(self, trade_result: TradeResult, always_throw_exception: bool) -> ReceiptBreakdown | None:
        if trade_result.status == TradeStatus.FAIL:
            # Defaults to CRITICAL
            assert trade_result.exception is not None
            log_hyperdrive_crash_report(
                trade_result,
                log_level=self.config.crash_log_level,
                crash_report_to_file=True,
                crash_report_file_prefix="interactive_hyperdrive",
                log_to_rollbar=self.config.log_to_rollbar,
                rollbar_log_prefix=self.config.rollbar_log_prefix,
                additional_info=self.config.crash_report_additional_info,
            )

            if self.config.exception_on_policy_error:
                # Check for slippage and if we want to throw an exception on slippage
                if (
                    always_throw_exception
                    or (not trade_result.is_slippage)
                    or (trade_result.is_slippage and self.config.exception_on_policy_slippage)
                ):
                    raise trade_result.exception

        if trade_result.status != TradeStatus.SUCCESS:
            return None
        tx_receipt = trade_result.tx_receipt
        assert tx_receipt is not None
        return tx_receipt

    @overload
    def _build_event_obj_from_tx_receipt(
        self, trade_type: Literal[HyperdriveActionType.INITIALIZE_MARKET], tx_receipt: ReceiptBreakdown
    ) -> None: ...

    @overload
    def _build_event_obj_from_tx_receipt(
        self, trade_type: Literal[HyperdriveActionType.OPEN_LONG], tx_receipt: ReceiptBreakdown
    ) -> OpenLong: ...

    @overload
    def _build_event_obj_from_tx_receipt(
        self, trade_type: Literal[HyperdriveActionType.CLOSE_LONG], tx_receipt: ReceiptBreakdown
    ) -> CloseLong: ...

    @overload
    def _build_event_obj_from_tx_receipt(
        self, trade_type: Literal[HyperdriveActionType.OPEN_SHORT], tx_receipt: ReceiptBreakdown
    ) -> OpenShort: ...

    @overload
    def _build_event_obj_from_tx_receipt(
        self, trade_type: Literal[HyperdriveActionType.CLOSE_SHORT], tx_receipt: ReceiptBreakdown
    ) -> CloseShort: ...

    @overload
    def _build_event_obj_from_tx_receipt(
        self, trade_type: Literal[HyperdriveActionType.ADD_LIQUIDITY], tx_receipt: ReceiptBreakdown
    ) -> AddLiquidity: ...

    @overload
    def _build_event_obj_from_tx_receipt(
        self, trade_type: Literal[HyperdriveActionType.REMOVE_LIQUIDITY], tx_receipt: ReceiptBreakdown
    ) -> RemoveLiquidity: ...

    @overload
    def _build_event_obj_from_tx_receipt(
        self, trade_type: Literal[HyperdriveActionType.REDEEM_WITHDRAW_SHARE], tx_receipt: ReceiptBreakdown
    ) -> RedeemWithdrawalShares: ...

    @overload
    def _build_event_obj_from_tx_receipt(
        self, trade_type: HyperdriveActionType, tx_receipt: ReceiptBreakdown
    ) -> (
        OpenLong | OpenShort | CloseLong | CloseShort | AddLiquidity | RemoveLiquidity | RedeemWithdrawalShares | None
    ): ...

    def _build_event_obj_from_tx_receipt(
        self, trade_type: HyperdriveActionType, tx_receipt: ReceiptBreakdown
    ) -> OpenLong | OpenShort | CloseLong | CloseShort | AddLiquidity | RemoveLiquidity | RedeemWithdrawalShares | None:
        # pylint: disable=too-many-return-statements
        # ruff: noqa: PLR0911 (too many return statements)
        match trade_type:
            case HyperdriveActionType.INITIALIZE_MARKET:
                raise ValueError(f"{trade_type} not supported!")

            case HyperdriveActionType.OPEN_LONG:
                return OpenLong(
                    trader=Web3.to_checksum_address(tx_receipt.trader),
                    asset_id=tx_receipt.asset_id,
                    maturity_time=tx_receipt.maturity_time_seconds,
                    base_amount=tx_receipt.base_amount,
                    vault_share_amount=tx_receipt.vault_share_amount,
                    as_base=tx_receipt.as_base,
                    bond_amount=tx_receipt.bond_amount,
                )

            case HyperdriveActionType.CLOSE_LONG:
                return CloseLong(
                    trader=Web3.to_checksum_address(tx_receipt.trader),
                    destination=Web3.to_checksum_address(tx_receipt.destination),
                    asset_id=tx_receipt.asset_id,
                    maturity_time=tx_receipt.maturity_time_seconds,
                    base_amount=tx_receipt.base_amount,
                    vault_share_amount=tx_receipt.vault_share_amount,
                    as_base=tx_receipt.as_base,
                    bond_amount=tx_receipt.bond_amount,
                )

            case HyperdriveActionType.OPEN_SHORT:
                return OpenShort(
                    trader=Web3.to_checksum_address(tx_receipt.trader),
                    asset_id=tx_receipt.asset_id,
                    maturity_time=tx_receipt.maturity_time_seconds,
                    base_amount=tx_receipt.base_amount,
                    vault_share_amount=tx_receipt.vault_share_amount,
                    as_base=tx_receipt.as_base,
                    base_proceeds=tx_receipt.base_proceeds,
                    bond_amount=tx_receipt.bond_amount,
                )

            case HyperdriveActionType.CLOSE_SHORT:
                return CloseShort(
                    trader=Web3.to_checksum_address(tx_receipt.trader),
                    destination=Web3.to_checksum_address(tx_receipt.destination),
                    asset_id=tx_receipt.asset_id,
                    maturity_time=tx_receipt.maturity_time_seconds,
                    base_amount=tx_receipt.base_amount,
                    vault_share_amount=tx_receipt.vault_share_amount,
                    as_base=tx_receipt.as_base,
                    base_payment=tx_receipt.base_payment,
                    bond_amount=tx_receipt.bond_amount,
                )

            case HyperdriveActionType.ADD_LIQUIDITY:
                return AddLiquidity(
                    provider=Web3.to_checksum_address(tx_receipt.provider),
                    lp_amount=tx_receipt.lp_amount,
                    base_amount=tx_receipt.base_amount,
                    vault_share_amount=tx_receipt.vault_share_amount,
                    as_base=tx_receipt.as_base,
                    lp_share_price=tx_receipt.lp_share_price,
                )

            case HyperdriveActionType.REMOVE_LIQUIDITY:
                return RemoveLiquidity(
                    provider=Web3.to_checksum_address(tx_receipt.provider),
                    destination=Web3.to_checksum_address(tx_receipt.destination),
                    lp_amount=tx_receipt.lp_amount,
                    base_amount=tx_receipt.base_amount,
                    vault_share_amount=tx_receipt.vault_share_amount,
                    as_base=tx_receipt.as_base,
                    withdrawal_share_amount=tx_receipt.withdrawal_share_amount,
                    lp_share_price=tx_receipt.lp_share_price,
                )

            case HyperdriveActionType.REDEEM_WITHDRAW_SHARE:
                return RedeemWithdrawalShares(
                    provider=Web3.to_checksum_address(tx_receipt.provider),
                    destination=Web3.to_checksum_address(tx_receipt.destination),
                    withdrawal_share_amount=tx_receipt.withdrawal_share_amount,
                    base_amount=tx_receipt.base_amount,
                    vault_share_amount=tx_receipt.vault_share_amount,
                    as_base=tx_receipt.as_base,
                )

            case _:
                assert_never(trade_type)

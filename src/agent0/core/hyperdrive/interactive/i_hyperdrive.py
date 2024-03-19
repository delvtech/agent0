"""Defines the interactive hyperdrive class that encapsulates a hyperdrive pool."""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import asdict, dataclass
from typing import Any, Literal, Type, overload

import nest_asyncio
import numpy as np
from eth_account.account import Account
from eth_account.signers.local import LocalAccount
from fixedpointmath import FixedPoint
from numpy.random._generator import Generator
from web3 import Web3

from agent0.core.hyperdrive import HyperdriveActionType, HyperdriveAgent, TradeResult, TradeStatus
from agent0.core.hyperdrive.agent import build_wallet_positions_from_chain
from agent0.core.hyperdrive.crash_report import log_hyperdrive_crash_report
from agent0.core.hyperdrive.exec import async_execute_agent_trades, set_max_approval
from agent0.core.hyperdrive.policies import HyperdriveBasePolicy
from agent0.core.test_utils import assert_never
from agent0.ethpy import EthConfig
from agent0.ethpy.base import set_anvil_account_balance, smart_contract_transact
from agent0.ethpy.hyperdrive import (
    HyperdriveAddresses,
    HyperdriveReadWriteInterface,
    ReceiptBreakdown,
    fetch_hyperdrive_address_from_uri,
)

from .event_types import (
    AddLiquidity,
    CloseLong,
    CloseShort,
    OpenLong,
    OpenShort,
    RedeemWithdrawalShares,
    RemoveLiquidity,
)
from .i_chain import IChain
from .i_hyperdrive_agent import IHyperdriveAgent
from .i_hyperdrive_policy import IHyperdrivePolicy

# In order to support both scripts and jupyter notebooks with underlying async functions,
# we use the nest_asyncio package so that we can execute asyncio.run within a running event loop.
# TODO: nest_asyncio may cause compatibility issues with other libraries.
# Also, Jupyter and ASYNC compatibility might be improved, removing the need for this.
# See https://github.com/python/cpython/issues/66435.
nest_asyncio.apply()


class IHyperdrive:
    """Interactive Hyperdrive class that supports connecting to an existing hyperdrive deployment."""

    @dataclass(kw_only=True)
    class Config:
        """The configuration for the interactive hyperdrive class."""

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
        """Whether to log crash reports to rollbar. Defaults to False."""
        crash_log_level: int = logging.CRITICAL
        """The log level to log crashes at. Defaults to critical."""
        crash_report_additional_info: dict[str, Any] | None = None
        """Additional information to include in the crash report."""

        def __post_init__(self):
            if self.rng is None:
                self.rng = np.random.default_rng(self.rng_seed)

    class Addresses(HyperdriveAddresses):
        """The addresses class that defines various addresses for Hyperdrive."""

        # Subclass from the underlying addresses dataclass
        # We simply define a class method to initialize the address from
        # artifacts uri

        @classmethod
        def from_artifacts_uri(cls, artifacts_uri: str) -> IHyperdrive.Addresses:
            """Builds hyperdrive addresses from artifacts uri.

            Arguments
            ---------
            artifacts_uri: str
                The uri of the artifacts server from which we get addresses.
                E.g., `http://localhost:8080`.

            Returns
            -------
            IHyperdrive.Addresses
                The hyperdrive addresses object
            """
            out = fetch_hyperdrive_address_from_uri(artifacts_uri)
            return cls._from_ethpy_addresses(out)

        @classmethod
        def _from_ethpy_addresses(cls, addresses: HyperdriveAddresses) -> IHyperdrive.Addresses:
            return IHyperdrive.Addresses(**asdict(addresses))

    def __init__(
        self,
        chain: IChain,
        hyperdrive_addresses: Addresses,
        config: Config | None = None,
    ):
        if config is None:
            self.config = self.Config()
        else:
            self.config = config

        # Define agent0 configs with this setup
        # TODO use hypertypes abis here
        # https://github.com/delvtech/agent0/issues/1125
        full_path = os.path.realpath(__file__)
        current_file_dir, _ = os.path.split(full_path)
        abi_dir = os.path.join(current_file_dir, "..", "..", "..", "..", "..", "packages", "hyperdrive", "src", "abis")

        self.eth_config = EthConfig(
            artifacts_uri="not_used",
            rpc_uri=chain.rpc_uri,
            abi_dir=abi_dir,
            preview_before_trade=self.config.preview_before_trade,
        )

        self.interface = HyperdriveReadWriteInterface(
            self.eth_config,
            hyperdrive_addresses,
            web3=chain._web3,
        )

        self.chain = chain

    def init_agent(
        self,
        private_key: str,
        policy: Type[HyperdriveBasePolicy] | None = None,
        policy_config: HyperdriveBasePolicy.Config | None = None,
    ):
        """Initializes an agent object given a private key.

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
        out_agent = IHyperdriveAgent(
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
    ):
        # Setting the budget to 0 here, we'll update the wallet from the chain
        agent = HyperdriveAgent(
            Account().from_key(private_key),
            initial_budget=FixedPoint(0),
            policy=IHyperdrivePolicy(
                IHyperdrivePolicy.Config(sub_policy=policy, sub_policy_config=policy_config, rng=self.config.rng)
            ),
        )

        # Add the public address to the chain object to avoid multiple objects
        # with the same underlying account
        self.chain._ensure_no_duplicate_addrs(agent.checksum_address)  # pylint: disable=protected-access

        agent.wallet = build_wallet_positions_from_chain(
            agent.checksum_address, self.interface.hyperdrive_contract, self.interface.base_token_contract
        )
        return agent

    def _set_max_approval(self, agent: HyperdriveAgent):
        # Establish max approval for the hyperdrive contract
        asyncio.run(
            set_max_approval(
                [agent],
                self.interface.web3,
                self.interface.base_token_contract,
                str(self.interface.hyperdrive_contract.address),
            )
        )

    def _add_funds(
        self, agent: HyperdriveAgent, base: FixedPoint, eth: FixedPoint, signer_account: LocalAccount | None = None
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

    def _open_long(self, agent: HyperdriveAgent, base: FixedPoint) -> OpenLong:
        # Set the next action to open a long
        assert isinstance(agent.policy, IHyperdrivePolicy)
        agent.policy.set_next_action(HyperdriveActionType.OPEN_LONG, base)
        # TODO expose async here to the caller eventually
        trade_results: list[TradeResult] = asyncio.run(
            async_execute_agent_trades(self.interface, [agent], liquidate=False, interactive_mode=True)
        )
        tx_receipt = self._handle_trade_result(trade_results)
        return self._build_event_obj_from_tx_receipt(HyperdriveActionType.OPEN_LONG, tx_receipt)

    def _close_long(self, agent: HyperdriveAgent, maturity_time: int, bonds: FixedPoint) -> CloseLong:
        # Set the next action to open a long
        assert isinstance(agent.policy, IHyperdrivePolicy)
        agent.policy.set_next_action(HyperdriveActionType.CLOSE_LONG, bonds, maturity_time)
        # TODO expose async here to the caller eventually
        trade_results: list[TradeResult] = asyncio.run(
            async_execute_agent_trades(self.interface, [agent], liquidate=False, interactive_mode=True)
        )
        tx_receipt = self._handle_trade_result(trade_results)
        return self._build_event_obj_from_tx_receipt(HyperdriveActionType.CLOSE_LONG, tx_receipt)

    def _open_short(self, agent: HyperdriveAgent, bonds: FixedPoint) -> OpenShort:
        # Set the next action to open a long
        assert isinstance(agent.policy, IHyperdrivePolicy)
        agent.policy.set_next_action(HyperdriveActionType.OPEN_SHORT, bonds)
        # TODO expose async here to the caller eventually
        trade_results: list[TradeResult] = asyncio.run(
            async_execute_agent_trades(self.interface, [agent], liquidate=False, interactive_mode=True)
        )
        tx_receipt = self._handle_trade_result(trade_results)
        return self._build_event_obj_from_tx_receipt(HyperdriveActionType.OPEN_SHORT, tx_receipt)

    def _close_short(self, agent: HyperdriveAgent, maturity_time: int, bonds: FixedPoint) -> CloseShort:
        # Set the next action to open a long
        assert isinstance(agent.policy, IHyperdrivePolicy)
        agent.policy.set_next_action(HyperdriveActionType.CLOSE_SHORT, bonds, maturity_time=maturity_time)
        # TODO expose async here to the caller eventually
        trade_results: list[TradeResult] = asyncio.run(
            async_execute_agent_trades(self.interface, [agent], liquidate=False, interactive_mode=True)
        )
        tx_receipt = self._handle_trade_result(trade_results)
        return self._build_event_obj_from_tx_receipt(HyperdriveActionType.CLOSE_SHORT, tx_receipt)

    def _add_liquidity(self, agent: HyperdriveAgent, base: FixedPoint) -> AddLiquidity:
        # Set the next action to open a long
        assert isinstance(agent.policy, IHyperdrivePolicy)
        agent.policy.set_next_action(HyperdriveActionType.ADD_LIQUIDITY, base)
        # TODO expose async here to the caller eventually
        trade_results: list[TradeResult] = asyncio.run(
            async_execute_agent_trades(self.interface, [agent], liquidate=False, interactive_mode=True)
        )
        tx_receipt = self._handle_trade_result(trade_results)
        return self._build_event_obj_from_tx_receipt(HyperdriveActionType.ADD_LIQUIDITY, tx_receipt)

    def _remove_liquidity(self, agent: HyperdriveAgent, shares: FixedPoint) -> RemoveLiquidity:
        # Set the next action to open a long
        assert isinstance(agent.policy, IHyperdrivePolicy)
        agent.policy.set_next_action(HyperdriveActionType.REMOVE_LIQUIDITY, shares)
        # TODO expose async here to the caller eventually
        trade_results: list[TradeResult] = asyncio.run(
            async_execute_agent_trades(self.interface, [agent], liquidate=False, interactive_mode=True)
        )
        tx_receipt = self._handle_trade_result(trade_results)
        return self._build_event_obj_from_tx_receipt(HyperdriveActionType.REMOVE_LIQUIDITY, tx_receipt)

    def _redeem_withdraw_share(self, agent: HyperdriveAgent, shares: FixedPoint) -> RedeemWithdrawalShares:
        # Set the next action to open a long
        assert isinstance(agent.policy, IHyperdrivePolicy)
        agent.policy.set_next_action(HyperdriveActionType.REDEEM_WITHDRAW_SHARE, shares)
        # TODO expose async here to the caller eventually
        trade_results: list[TradeResult] = asyncio.run(
            async_execute_agent_trades(self.interface, [agent], liquidate=False, interactive_mode=True)
        )
        tx_receipt = self._handle_trade_result(trade_results)
        return self._build_event_obj_from_tx_receipt(HyperdriveActionType.REDEEM_WITHDRAW_SHARE, tx_receipt)

    def _execute_policy_action(
        self, agent: HyperdriveAgent
    ) -> list[OpenLong | OpenShort | CloseLong | CloseShort | AddLiquidity | RemoveLiquidity | RedeemWithdrawalShares]:
        assert isinstance(agent.policy, IHyperdrivePolicy)
        # Only allow executing agent policies if a policy was passed in the constructor
        if agent.policy.sub_policy is None:
            raise ValueError("Must pass in a policy in the constructor to execute policy action.")

        agent.policy.set_next_action_from_sub_policy()
        trade_results: list[TradeResult] = asyncio.run(
            async_execute_agent_trades(self.interface, [agent], liquidate=False, interactive_mode=True)
        )
        out_events = []
        # The underlying policy can execute multiple actions in one step
        for trade_result in trade_results:
            tx_receipt = self._handle_trade_result(trade_result)
            assert trade_result.trade_object is not None
            action_type: HyperdriveActionType = trade_result.trade_object.market_action.action_type
            out_events.append(self._build_event_obj_from_tx_receipt(action_type, tx_receipt))
        # Build event from tx_receipt
        return out_events

    def _liquidate(
        self, agent: HyperdriveAgent, randomize: bool
    ) -> list[CloseLong | CloseShort | RemoveLiquidity | RedeemWithdrawalShares]:
        trade_results: list[TradeResult] = asyncio.run(
            async_execute_agent_trades(
                self.interface,
                [agent],
                liquidate=True,
                randomize_liquidation=randomize,
                interactive_mode=True,
            )
        )
        out_events = []

        # The underlying policy can execute multiple actions in one step
        for trade_result in trade_results:
            tx_receipt = self._handle_trade_result(trade_result)
            assert trade_result.trade_object is not None
            action_type: HyperdriveActionType = trade_result.trade_object.market_action.action_type
            out_events.append(self._build_event_obj_from_tx_receipt(action_type, tx_receipt))
        # Build event from tx_receipt
        return out_events

    def _handle_trade_result(self, trade_results: list[TradeResult] | TradeResult) -> ReceiptBreakdown:
        # Sanity check, should only be one trade result
        if isinstance(trade_results, list):
            assert len(trade_results) == 1
            trade_result = trade_results[0]
        elif isinstance(trade_results, TradeResult):
            trade_result = trade_results
        else:
            assert False

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
            raise trade_result.exception

        assert trade_result.status == TradeStatus.SUCCESS
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

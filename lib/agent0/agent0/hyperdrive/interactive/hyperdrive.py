from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import asdict, dataclass
from typing import Any, Literal, overload

import nest_asyncio
import numpy as np
from ethpy import EthConfig
from ethpy.hyperdrive import (
    HyperdriveAddresses,
    HyperdriveReadWriteInterface,
    ReceiptBreakdown,
    fetch_hyperdrive_address_from_uri,
)
from fixedpointmath import FixedPoint
from numpy.random._generator import Generator
from web3 import Web3

from agent0.hyperdrive import HyperdriveActionType, HyperdriveAgent, TradeResult, TradeStatus
from agent0.hyperdrive.crash_report import log_hyperdrive_crash_report
from agent0.hyperdrive.exec import async_execute_agent_trades
from agent0.hyperdrive.interactive.interactive_hyperdrive_agent import InteractiveHyperdriveAgent
from agent0.test_utils import assert_never

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
from .interactive_hyperdrive_policy import InteractiveHyperdrivePolicy

# In order to support both scripts and jupyter notebooks with underlying async functions,
# we use the nest_asyncio package so that we can execute asyncio.run within a running event loop.
nest_asyncio.apply()


class Hyperdrive:
    @dataclass(kw_only=True)
    class Config:
        """
        Attributes
        ----------
        preview_before_trade: bool, optional
            Whether to preview the position before executing a trade. Defaults to False.
        rng_seed: int | None, optional
            The seed for the random number generator. Defaults to None.
        rng: Generator | None, optional
            The experiment's stateful random number generator. Defaults to creating a generator from
            the provided random seed if not set.
        crash_log_level: int, optional
            The log level to log crashes at. Defaults to critical.
        log_to_rollbar: bool, optional
            Whether to log crash reports to rollbar. Defaults to False.
        rollbar_log_prefix: str | None, optional
            The prefix to prepend to rollbar exception messages.
        crash_report_additional_info: dict[str, Any] | None, optional
            Additional information to include in the crash report.
        """

        preview_before_trade: bool = False
        rng_seed: int | None = None
        rng: Generator | None = None
        log_to_rollbar: bool = False
        rollbar_log_prefix: str | None = None
        crash_log_level: int = logging.CRITICAL
        crash_report_additional_info: dict[str, Any] | None = None

        def __post_init__(self):
            if self.rng is None:
                self.rng = np.random.default_rng(self.rng_seed)

    class Addresses(HyperdriveAddresses):
        # Subclass from the underlying addresses named tuple
        # We simply define a class method to initialize the address from
        # artifacts uri

        @classmethod
        def from_artifacts_uri(cls, artifacts_uri: str) -> Hyperdrive.Addresses:
            """Builds hyperdrive addresses from artifacts uri.

            Parameters
            ----------
            artifacts_uri: str
                The uri of the artifacts server from which we get addresses.
                E.g., `http://localhost:8080/artifacts.json`.
            """
            out = fetch_hyperdrive_address_from_uri(artifacts_uri)
            return cls._from_ethpy_addresses(out)

        @classmethod
        def _from_ethpy_addresses(cls, addresses: HyperdriveAddresses) -> Hyperdrive.Addresses:
            return Hyperdrive.Addresses(**asdict(addresses))

    def __init__(
        self,
        chain: Chain,
        hyperdrive_addresses: Addresses,
        config: Config | None = None,
    ):
        if config is None:
            self.config = self.Config()
        else:
            self.config = config

        # Define agent0 configs with this setup
        # TODO currently getting the path based on this file's path
        # This requires the entire monorepo to be check out, and will likely not work when
        # installing agent0 by itself.
        # This should get fixed when abis are exported in hypertypes.
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

        self._pool_agents: list[InteractiveHyperdriveAgent] = []

    # TODO this should be the base agent class for these calls
    def _open_long(self, agent: HyperdriveAgent, base: FixedPoint) -> OpenLong:
        # Set the next action to open a long
        assert isinstance(agent.policy, InteractiveHyperdrivePolicy)
        agent.policy.set_next_action(HyperdriveActionType.OPEN_LONG, base)
        # TODO expose async here to the caller eventually
        trade_results: list[TradeResult] = asyncio.run(
            async_execute_agent_trades(self.interface, [agent], liquidate=False, interactive_mode=True)
        )
        tx_receipt = self._handle_trade_result(trade_results)
        return self._build_event_obj_from_tx_receipt(HyperdriveActionType.OPEN_LONG, tx_receipt)

    def _close_long(self, agent: HyperdriveAgent, maturity_time: int, bonds: FixedPoint) -> CloseLong:
        # Set the next action to open a long
        assert isinstance(agent.policy, InteractiveHyperdrivePolicy)
        agent.policy.set_next_action(HyperdriveActionType.CLOSE_LONG, bonds, maturity_time)
        # TODO expose async here to the caller eventually
        trade_results: list[TradeResult] = asyncio.run(
            async_execute_agent_trades(self.interface, [agent], liquidate=False, interactive_mode=True)
        )
        tx_receipt = self._handle_trade_result(trade_results)
        return self._build_event_obj_from_tx_receipt(HyperdriveActionType.CLOSE_LONG, tx_receipt)

    def _open_short(self, agent: HyperdriveAgent, bonds: FixedPoint) -> OpenShort:
        # Set the next action to open a long
        assert isinstance(agent.policy, InteractiveHyperdrivePolicy)
        agent.policy.set_next_action(HyperdriveActionType.OPEN_SHORT, bonds)
        # TODO expose async here to the caller eventually
        trade_results: list[TradeResult] = asyncio.run(
            async_execute_agent_trades(self.interface, [agent], liquidate=False, interactive_mode=True)
        )
        tx_receipt = self._handle_trade_result(trade_results)
        return self._build_event_obj_from_tx_receipt(HyperdriveActionType.OPEN_SHORT, tx_receipt)

    def _close_short(self, agent: HyperdriveAgent, maturity_time: int, bonds: FixedPoint) -> CloseShort:
        # Set the next action to open a long
        assert isinstance(agent.policy, InteractiveHyperdrivePolicy)
        agent.policy.set_next_action(HyperdriveActionType.CLOSE_SHORT, bonds, maturity_time=maturity_time)
        # TODO expose async here to the caller eventually
        trade_results: list[TradeResult] = asyncio.run(
            async_execute_agent_trades(self.interface, [agent], liquidate=False, interactive_mode=True)
        )
        tx_receipt = self._handle_trade_result(trade_results)
        return self._build_event_obj_from_tx_receipt(HyperdriveActionType.CLOSE_SHORT, tx_receipt)

    def _add_liquidity(self, agent: HyperdriveAgent, base: FixedPoint) -> AddLiquidity:
        # Set the next action to open a long
        assert isinstance(agent.policy, InteractiveHyperdrivePolicy)
        agent.policy.set_next_action(HyperdriveActionType.ADD_LIQUIDITY, base)
        # TODO expose async here to the caller eventually
        trade_results: list[TradeResult] = asyncio.run(
            async_execute_agent_trades(self.interface, [agent], liquidate=False, interactive_mode=True)
        )
        tx_receipt = self._handle_trade_result(trade_results)
        return self._build_event_obj_from_tx_receipt(HyperdriveActionType.ADD_LIQUIDITY, tx_receipt)

    def _remove_liquidity(self, agent: HyperdriveAgent, shares: FixedPoint) -> RemoveLiquidity:
        # Set the next action to open a long
        assert isinstance(agent.policy, InteractiveHyperdrivePolicy)
        agent.policy.set_next_action(HyperdriveActionType.REMOVE_LIQUIDITY, shares)
        # TODO expose async here to the caller eventually
        trade_results: list[TradeResult] = asyncio.run(
            async_execute_agent_trades(self.interface, [agent], liquidate=False, interactive_mode=True)
        )
        tx_receipt = self._handle_trade_result(trade_results)
        return self._build_event_obj_from_tx_receipt(HyperdriveActionType.REMOVE_LIQUIDITY, tx_receipt)

    def _redeem_withdraw_share(self, agent: HyperdriveAgent, shares: FixedPoint) -> RedeemWithdrawalShares:
        # Set the next action to open a long
        assert isinstance(agent.policy, InteractiveHyperdrivePolicy)
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
        assert isinstance(agent.policy, InteractiveHyperdrivePolicy)
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
                    asset_id=tx_receipt.asset_id,
                    maturity_time=tx_receipt.maturity_time_seconds,
                    base_amount=tx_receipt.base_amount,
                    vault_share_amount=tx_receipt.vault_share_amount,
                    as_base=tx_receipt.as_base,
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
                    withdrawal_share_amount=tx_receipt.withdrawal_share_amount,
                    base_amount=tx_receipt.base_amount,
                    vault_share_amount=tx_receipt.vault_share_amount,
                    as_base=tx_receipt.as_base,
                )

            case _:
                assert_never(trade_type)

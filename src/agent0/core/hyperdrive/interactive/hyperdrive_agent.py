"""The hyperdrive agent object that encapsulates an agent."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Literal, Type, overload

import pandas as pd
from eth_account.account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import ChecksumAddress
from fixedpointmath import FixedPoint
from hexbytes import HexBytes
from web3 import Web3

from agent0.chainsync.analysis import snapshot_positions_to_db
from agent0.chainsync.db.base import add_addr_to_username
from agent0.chainsync.db.hyperdrive import (
    checkpoint_events_to_db,
    get_current_positions,
    get_position_snapshot,
    get_trade_events,
    trade_events_to_db,
)
from agent0.core.base import Quantity, TokenType
from agent0.core.hyperdrive.agent import (
    HyperdriveActionType,
    HyperdriveWallet,
    TradeResult,
    add_liquidity_trade,
    close_long_trade,
    close_short_trade,
    open_long_trade,
    open_short_trade,
    redeem_withdraw_shares_trade,
    remove_liquidity_trade,
)
from agent0.core.hyperdrive.agent.hyperdrive_wallet import Long, Short
from agent0.core.hyperdrive.crash_report import log_hyperdrive_crash_report
from agent0.core.hyperdrive.policies import HyperdriveBasePolicy
from agent0.core.test_utils import assert_never
from agent0.ethpy.base import get_account_balance, set_anvil_account_balance, smart_contract_transact
from agent0.ethpy.hyperdrive import ReceiptBreakdown

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

if TYPE_CHECKING:
    from agent0.ethpy.hyperdrive import HyperdriveReadInterface

    from .chain import Chain
    from .hyperdrive import Hyperdrive

# pylint: disable=protected-access
# pylint: disable=too-many-lines


class HyperdriveAgent:
    """Interactive Hyperdrive Agent."""

    # pylint: disable=too-many-public-methods

    ################
    # Initialization
    ################

    def __init__(
        self,
        name: str | None,
        chain: Chain,
        pool: Hyperdrive | None,
        policy: Type[HyperdriveBasePolicy] | None,
        policy_config: HyperdriveBasePolicy.Config | None,
        private_key: str | None,
        public_address: str | None,
    ) -> None:
        """Constructor for the interactive hyperdrive agent.
        NOTE: this constructor shouldn't be called directly, but rather from Chain's
        `init_agent` method.

        Arguments
        ---------
        name: str | None
            The name of the agent. Defaults to the wallet address.
        pool: Hyperdrive
            The pool object that this agent belongs to.
        chain: Chain
            The chain object that this agent belongs to.
        pool: Hyperdrive | None
            An optional pool to set as the active pool.
        policy: Type[HyperdriveBasePolicy] | None
            An optional policy to attach to this agent.
        policy_config: HyperdriveBasePolicy.Config | None,
            The configuration for the attached policy.
        private_key: str | None, optional
            The private key of the associated account. Default is auto-generated.
        """
        # pylint: disable=too-many-arguments
        self.chain = chain

        self._active_pool: Hyperdrive | None = pool
        self._active_policy: HyperdriveBasePolicy | None = None

        if policy is not None:
            # Policy config gets set in `init_agent` and `set_active_policy` if passed in
            assert policy_config is not None
            self._active_policy = policy(policy_config)

        if private_key is None and public_address is None:
            raise ValueError("Either private_key or public_address must be provided.")

        if private_key is not None and public_address is not None:
            raise ValueError("Either private_key or public_address must be provided, but not both.")

        self._account: LocalAccount | None = None
        self.address: ChecksumAddress
        if private_key is not None:
            self._account = Account().from_key(private_key)
            assert self._account is not None
            self.address = self._account.address
        elif public_address is not None:
            self.address = Web3.to_checksum_address(public_address)

        # Register the username if it was provided
        if name is not None:
            add_addr_to_username(name, [self.address], self.chain.db_session)

    # Expose account and address for type narrowing in local agent
    @property
    def account(self) -> LocalAccount:
        """Returns the `LocalAccount` associated with the agent."""
        if self._account is None:
            raise ValueError("Must initialize agent with private key to access agent's LocalAccount.")
        return self._account

    @property
    def policy_done_trading(self) -> bool:
        """Return whether the agent's policy is done trading."""
        if self._active_policy is None:
            return False
        return self._active_policy._done_trading

    def add_funds(
        self,
        base: FixedPoint | None = None,
        eth: FixedPoint | None = None,
        pool: Hyperdrive | None = None,
        signer_account: LocalAccount | None = None,
    ) -> None:
        """Adds additional funds to the agent.

        .. note:: This method calls `set_anvil_account_balance` and `mint` under the hood.
        These functions are likely to fail on any non-test network, but we add them to the
        interactive agent for convenience.

        Arguments
        ---------
        base: FixedPoint | None, optional
            The amount of base to fund the agent with. Defaults to 0.
        eth: FixedPoint | None, optional
            The amount of ETH to fund the agent with. Defaults to 0.
        pool: LocalHyperdrive | None, optional
            The pool to interact with. Defaults to the active pool.
        signer_account: LocalAccount | None, optional
            The signer account to use to call `mint`. Defaults to the agent itself.
        """

        if self.account is None:
            raise ValueError("Must initialize agent with private key for transactions.")

        if pool is None and self._active_pool is not None:
            pool = self._active_pool

        if base is None:
            base = FixedPoint(0)
        if eth is None:
            eth = FixedPoint(0)

        # The signer of the mint transaction defaults to the agent itself, unless specified.
        if signer_account is None:
            signer_account = self.account

        if eth > FixedPoint(0):
            # Eth is a set balance call
            eth_balance = FixedPoint(scaled_value=get_account_balance(self.chain._web3, self.account.address))
            new_eth_balance = eth_balance + eth
            _ = set_anvil_account_balance(self.chain._web3, self.account.address, new_eth_balance.scaled_value)

        # TODO minting base requires a pool to be attached
        if base > FixedPoint(0):
            if pool is None:
                raise ValueError("Minting base requires an active pool.")
            # We mint base
            _ = smart_contract_transact(
                self.chain._web3,
                pool.interface.base_token_contract,
                signer_account,
                "mint(address,uint256)",
                self.account.address,
                base.scaled_value,
            )

    def set_max_approval(self, pool: Hyperdrive | None = None) -> None:
        """Sets the max approval to the hyperdrive contract.

        .. warning:: This sets the max approval to the underlying hyperdrive contract for
        this wallet. Do this at your own risk.

        Arguments
        ---------
        pool: LocalHyperdrive | None, optional
            The pool to interact with. Defaults to the active pool.
        """
        # Establish max approval for the hyperdrive contract
        if self.account is None:
            raise ValueError("Must initialize agent with private key for transactions.")

        if pool is None:
            pool = self._active_pool
        if pool is None:
            raise ValueError("Setting approval requires an active pool.")
        set_max_approval(
            self.account, self.chain._web3, pool.interface.base_token_contract, str(pool.hyperdrive_address)
        )

    def set_active(
        self,
        pool: Hyperdrive | None = None,
        policy: Type[HyperdriveBasePolicy] | None = None,
        policy_config: HyperdriveBasePolicy.Config | None = None,
    ) -> None:
        """Sets the active pool or policy for the agent.

        Setting an active pool for an agent allows trades to default to this pool.
        Setting an active policy for an agent uses this policy with `execute_policy_action`.


        Arguments
        ---------
        pool: LocalHyperdrive
            The pool to set as the active pool.
        policy: Type[HyperdriveBasePolicy] | None
            The policy to set as the active policy.
        policy_config: HyperdriveBasePolicy.Config | None
            The configuration for the attached policy.
        """
        if pool is not None:
            self._active_pool = pool

        if policy is not None:
            policy_config = self.chain._handle_policy_config(policy, policy_config)
            assert policy_config is not None
            self._active_policy = policy(policy_config)

    ################
    # Trades
    ################

    def open_long(self, base: FixedPoint, pool: Hyperdrive | None = None) -> OpenLong:
        """Opens a long for this agent.

        Arguments
        ---------
        base: FixedPoint
            The amount of longs to open in units of base.
        pool: LocalHyperdrive | None, optional
            The pool to interact with. Defaults to the active pool.

        Returns
        -------
        OpenLong
            The emitted event of the open long call.
        """
        if self.account is None:
            raise ValueError("Must initialize agent with private key for transactions.")
        if pool is None:
            pool = self._active_pool
        if pool is None:
            raise ValueError("Open long requires an active pool.")

        # Build trade object
        trade_object = open_long_trade(base, gas_limit=self.chain.config.gas_limit)
        # TODO expose async here to the caller eventually
        trade_result: TradeResult = asyncio.run(
            async_execute_single_trade(
                pool.interface,
                self.account,
                self.get_wallet(pool),
                trade_object,
                self.chain.config.always_execute_policy_post_action,
                self.chain.config.preview_before_trade,
                self._active_policy,
            )
        )
        tx_receipt = self._handle_trade_result(trade_result, pool, always_throw_exception=True)
        return self._build_event_obj_from_tx_receipt(HyperdriveActionType.OPEN_LONG, tx_receipt)

    def close_long(self, maturity_time: int, bonds: FixedPoint, pool: Hyperdrive | None = None) -> CloseLong:
        """Closes a long for this agent.

        Arguments
        ---------
        maturity_time: int
            The maturity time of the bonds to close. This is the identifier of the long tokens.
        bonds: FixedPoint
            The amount of longs to close in units of bonds.
        pool: LocalHyperdrive | None, optional
            The pool to interact with. Defaults to the active pool.

        Returns
        -------
        CloseLong
            The emitted event of the close long call.
        """
        if self.account is None:
            raise ValueError("Must initialize agent with private key for transactions.")
        if pool is None:
            pool = self._active_pool
        if pool is None:
            raise ValueError("Close long requires an active pool.")

        # Build trade object
        trade_object = close_long_trade(bonds, maturity_time, gas_limit=self.chain.config.gas_limit)
        # TODO expose async here to the caller eventually
        trade_result: TradeResult = asyncio.run(
            async_execute_single_trade(
                pool.interface,
                self.account,
                self.get_wallet(pool),
                trade_object,
                self.chain.config.always_execute_policy_post_action,
                self.chain.config.preview_before_trade,
                self._active_policy,
            )
        )
        tx_receipt = self._handle_trade_result(trade_result, pool, always_throw_exception=True)
        return self._build_event_obj_from_tx_receipt(HyperdriveActionType.CLOSE_LONG, tx_receipt)

    def open_short(self, bonds: FixedPoint, pool: Hyperdrive | None = None) -> OpenShort:
        """Opens a short for this agent.

        Arguments
        ---------
        bonds: FixedPoint
            The amount of shorts to open in units of bonds.
        pool: LocalHyperdrive | None, optional
            The pool to interact with. Defaults to the active pool.

        Returns
        -------
        OpenShort
            The emitted event of the open short call.
        """
        if self.account is None:
            raise ValueError("Must initialize agent with private key for transactions.")
        if pool is None:
            pool = self._active_pool
        if pool is None:
            raise ValueError("Open short requires an active pool.")

        trade_object = open_short_trade(bonds, gas_limit=self.chain.config.gas_limit)
        # TODO expose async here to the caller eventually
        trade_result: TradeResult = asyncio.run(
            async_execute_single_trade(
                pool.interface,
                self.account,
                self.get_wallet(pool),
                trade_object,
                self.chain.config.always_execute_policy_post_action,
                self.chain.config.preview_before_trade,
                self._active_policy,
            )
        )
        tx_receipt = self._handle_trade_result(trade_result, pool, always_throw_exception=True)
        return self._build_event_obj_from_tx_receipt(HyperdriveActionType.OPEN_SHORT, tx_receipt)

    def close_short(self, maturity_time: int, bonds: FixedPoint, pool: Hyperdrive | None = None) -> CloseShort:
        """Closes a short for this agent.

        Arguments
        ---------
        maturity_time: int
            The maturity time of the bonds to close. This is the identifier of the short tokens.
        bonds: FixedPoint
            The amount of shorts to close in units of bonds.
        pool: LocalHyperdrive | None, optional
            The pool to interact with. Defaults to the active pool.

        Returns
        -------
        CloseShort
            The emitted event of the close short call.
        """
        if self.account is None:
            raise ValueError("Must initialize agent with private key for transactions.")
        if pool is None:
            pool = self._active_pool
        if pool is None:
            raise ValueError("Close short requires an active pool.")

        trade_object = close_short_trade(bonds, maturity_time, gas_limit=self.chain.config.gas_limit)
        # TODO expose async here to the caller eventually
        trade_result: TradeResult = asyncio.run(
            async_execute_single_trade(
                pool.interface,
                self.account,
                self.get_wallet(pool),
                trade_object,
                self.chain.config.always_execute_policy_post_action,
                self.chain.config.preview_before_trade,
                self._active_policy,
            )
        )
        tx_receipt = self._handle_trade_result(trade_result, pool, always_throw_exception=True)
        return self._build_event_obj_from_tx_receipt(HyperdriveActionType.CLOSE_SHORT, tx_receipt)

    def add_liquidity(self, base: FixedPoint, pool: Hyperdrive | None = None) -> AddLiquidity:
        """Adds liquidity for this agent.

        Arguments
        ---------
        base: FixedPoint
            The amount of liquidity to add in units of base.
        pool: LocalHyperdrive | None, optional
            The pool to interact with. Defaults to the active pool.

        Returns
        -------
        AddLiquidity
            The emitted event of the add liquidity call.
        """
        if self.account is None:
            raise ValueError("Must initialize agent with private key for transactions.")
        if pool is None:
            pool = self._active_pool
        if pool is None:
            raise ValueError("Add liquidity requires an active pool.")

        trade_object = add_liquidity_trade(base, gas_limit=self.chain.config.gas_limit)
        # TODO expose async here to the caller eventually
        trade_result: TradeResult = asyncio.run(
            async_execute_single_trade(
                pool.interface,
                self.account,
                self.get_wallet(pool),
                trade_object,
                self.chain.config.always_execute_policy_post_action,
                self.chain.config.preview_before_trade,
                self._active_policy,
            )
        )
        tx_receipt = self._handle_trade_result(trade_result, pool, always_throw_exception=True)
        return self._build_event_obj_from_tx_receipt(HyperdriveActionType.ADD_LIQUIDITY, tx_receipt)

    def remove_liquidity(self, shares: FixedPoint, pool: Hyperdrive | None = None) -> RemoveLiquidity:
        """Removes liquidity for this agent.

        Arguments
        ---------
        shares: FixedPoint
            The amount of liquidity to remove in units of shares.
        pool: LocalHyperdrive | None, optional
            The pool to interact with. Defaults to the active pool.

        Returns
        -------
        RemoveLiquidity
            The emitted event of the remove liquidity call.
        """
        if self.account is None:
            raise ValueError("Must initialize agent with private key for transactions.")
        if pool is None:
            pool = self._active_pool
        if pool is None:
            raise ValueError("Remove liquidity requires an active pool.")

        trade_object = remove_liquidity_trade(shares, gas_limit=self.chain.config.gas_limit)
        # TODO expose async here to the caller eventually
        trade_result: TradeResult = asyncio.run(
            async_execute_single_trade(
                pool.interface,
                self.account,
                self.get_wallet(pool),
                trade_object,
                self.chain.config.always_execute_policy_post_action,
                self.chain.config.preview_before_trade,
                self._active_policy,
            )
        )
        tx_receipt = self._handle_trade_result(trade_result, pool, always_throw_exception=True)
        return self._build_event_obj_from_tx_receipt(HyperdriveActionType.REMOVE_LIQUIDITY, tx_receipt)

    def redeem_withdrawal_share(self, shares: FixedPoint, pool: Hyperdrive | None = None) -> RedeemWithdrawalShares:
        """Redeems withdrawal shares for this agent.

        Arguments
        ---------
        shares: FixedPoint
            The amount of withdrawal shares to redeem in units of shares.
        pool: LocalHyperdrive | None, optional
            The pool to interact with. Defaults to the active pool.

        Returns
        -------
        RedeemWithdrawalShares
            The emitted event of the redeem withdrawal shares call.
        """
        if self.account is None:
            raise ValueError("Must initialize agent with private key for transactions.")
        if pool is None:
            pool = self._active_pool
        if pool is None:
            raise ValueError("Redeem withdrawal shares requires an active pool.")

        trade_object = redeem_withdraw_shares_trade(shares, gas_limit=self.chain.config.gas_limit)
        # TODO expose async here to the caller eventually
        trade_results: TradeResult = asyncio.run(
            async_execute_single_trade(
                pool.interface,
                self.account,
                self.get_wallet(pool),
                trade_object,
                self.chain.config.always_execute_policy_post_action,
                self.chain.config.preview_before_trade,
                self._active_policy,
            )
        )
        tx_receipt = self._handle_trade_result(trade_results, pool, always_throw_exception=True)
        return self._build_event_obj_from_tx_receipt(HyperdriveActionType.REDEEM_WITHDRAW_SHARE, tx_receipt)

    def execute_policy_action(
        self, pool: Hyperdrive | None = None
    ) -> list[OpenLong | OpenShort | CloseLong | CloseShort | AddLiquidity | RemoveLiquidity | RedeemWithdrawalShares]:
        """Executes the underlying policy action (if set).

        Arguments
        ---------
        pool: LocalHyperdrive | None, optional
            The pool to interact with. Defaults to the active pool.

        Returns
        -------
        list[OpenLong | OpenShort | CloseLong | CloseShort | AddLiquidity | RemoveLiquidity | RedeemWithdrawalShares]
            Events of the executed actions.
        """
        if self.account is None:
            raise ValueError("Must initialize agent with private key for transactions.")
        # Only allow executing agent policies if a policy was passed in the constructor
        # we check type instead of isinstance to explicitly check for the hyperdrive base class
        # pylint: disable=unidiomatic-typecheck
        if self._active_policy is None:
            raise ValueError("No active policy set.")

        if pool is None:
            pool = self._active_pool
        if pool is None:
            raise ValueError("Executing policy action requires an active pool.")

        trade_results: list[TradeResult] = asyncio.run(
            async_execute_agent_trades(
                pool.interface,
                self.account,
                self.get_wallet(pool),
                policy=self._active_policy,
                preview_before_trade=self.chain.config.preview_before_trade,
                liquidate=False,
            )
        )
        out_events = []
        # The underlying policy can execute multiple actions in one step
        for trade_result in trade_results:
            tx_receipt = self._handle_trade_result(trade_result, pool, always_throw_exception=False)
            if tx_receipt is not None:
                assert trade_result.trade_object is not None
                action_type: HyperdriveActionType = trade_result.trade_object.market_action.action_type
                out_events.append(self._build_event_obj_from_tx_receipt(action_type, tx_receipt))
        # Build event from tx_receipt
        return out_events

    def liquidate(
        self, randomize: bool = False, pool: Hyperdrive | None = None
    ) -> list[CloseLong | CloseShort | RemoveLiquidity | RedeemWithdrawalShares]:
        """Liquidate all of the agent's positions.

        Arguments
        ---------
        randomize: bool, optional
            Whether to randomize liquidation trades. Defaults to False.
        pool: LocalHyperdrive | None, optional
            The pool to interact with. Defaults to the active pool.

        Returns
        -------
        list[CloseLong | CloseShort | RemoveLiquidity | RedeemWithdrawalShares]
            Events of the executed actions.
        """
        if self.account is None:
            raise ValueError("Must initialize agent with private key for transactions.")
        if pool is None:
            pool = self._active_pool
        if pool is None:
            raise ValueError("Liquidate requires an active pool.")

        # For type narrowing
        # rng should always be set in post_init
        assert self.chain.config.rng is not None

        trade_results: list[TradeResult] = asyncio.run(
            async_execute_agent_trades(
                pool.interface,
                self.account,
                self.get_wallet(pool),
                policy=None,
                rng=self.chain.config.rng,
                preview_before_trade=self.chain.config.preview_before_trade,
                liquidate=True,
                randomize_liquidation=randomize,
            )
        )
        out_events = []

        # The underlying policy can execute multiple actions in one step
        for trade_result in trade_results:
            tx_receipt = self._handle_trade_result(trade_result, pool, always_throw_exception=False)
            if tx_receipt is not None:
                assert trade_result.trade_object is not None
                action_type: HyperdriveActionType = trade_result.trade_object.market_action.action_type
                out_events.append(self._build_event_obj_from_tx_receipt(action_type, tx_receipt))
        # Build event from tx_receipt
        return out_events

    # Helper functions for trades

    @overload
    def _handle_trade_result(
        self, trade_result: TradeResult, pool: Hyperdrive, always_throw_exception: Literal[True]
    ) -> ReceiptBreakdown: ...

    @overload
    def _handle_trade_result(
        self, trade_result: TradeResult, pool: Hyperdrive, always_throw_exception: Literal[False]
    ) -> ReceiptBreakdown | None: ...

    def _handle_trade_result(
        self, trade_result: TradeResult, pool: Hyperdrive, always_throw_exception: bool
    ) -> ReceiptBreakdown | None:
        if not trade_result.trade_successful:
            # Defaults to CRITICAL
            assert trade_result.exception is not None
            log_hyperdrive_crash_report(
                trade_result,
                log_level=self.chain.config.crash_log_level,
                crash_report_to_file=True,
                crash_report_file_prefix="interactive_hyperdrive",
                log_to_rollbar=self.chain.config.log_to_rollbar,
                rollbar_log_prefix=self.chain.config.rollbar_log_prefix,
                additional_info=pool._crash_report_additional_info,
            )

            if self.chain.config.exception_on_policy_error:
                # Check for slippage and if we want to throw an exception on slippage
                if (
                    always_throw_exception
                    or (not trade_result.is_slippage)
                    or (trade_result.is_slippage and self.chain.config.exception_on_policy_slippage)
                ):
                    raise trade_result.exception

        if not trade_result.trade_successful:
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
                    amount=tx_receipt.amount,
                    vault_share_price=tx_receipt.vault_share_price,
                    as_base=tx_receipt.as_base,
                    bond_amount=tx_receipt.bond_amount,
                )

            case HyperdriveActionType.CLOSE_LONG:
                return CloseLong(
                    trader=Web3.to_checksum_address(tx_receipt.trader),
                    destination=Web3.to_checksum_address(tx_receipt.destination),
                    asset_id=tx_receipt.asset_id,
                    maturity_time=tx_receipt.maturity_time_seconds,
                    amount=tx_receipt.amount,
                    vault_share_price=tx_receipt.vault_share_price,
                    as_base=tx_receipt.as_base,
                    bond_amount=tx_receipt.bond_amount,
                )

            case HyperdriveActionType.OPEN_SHORT:
                return OpenShort(
                    trader=Web3.to_checksum_address(tx_receipt.trader),
                    asset_id=tx_receipt.asset_id,
                    maturity_time=tx_receipt.maturity_time_seconds,
                    amount=tx_receipt.amount,
                    vault_share_price=tx_receipt.vault_share_price,
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
                    amount=tx_receipt.amount,
                    vault_share_price=tx_receipt.vault_share_price,
                    as_base=tx_receipt.as_base,
                    base_payment=tx_receipt.base_payment,
                    bond_amount=tx_receipt.bond_amount,
                )

            case HyperdriveActionType.ADD_LIQUIDITY:
                return AddLiquidity(
                    provider=Web3.to_checksum_address(tx_receipt.provider),
                    lp_amount=tx_receipt.lp_amount,
                    amount=tx_receipt.amount,
                    vault_share_price=tx_receipt.vault_share_price,
                    as_base=tx_receipt.as_base,
                    lp_share_price=tx_receipt.lp_share_price,
                )

            case HyperdriveActionType.REMOVE_LIQUIDITY:
                return RemoveLiquidity(
                    provider=Web3.to_checksum_address(tx_receipt.provider),
                    destination=Web3.to_checksum_address(tx_receipt.destination),
                    lp_amount=tx_receipt.lp_amount,
                    amount=tx_receipt.amount,
                    vault_share_price=tx_receipt.vault_share_price,
                    as_base=tx_receipt.as_base,
                    withdrawal_share_amount=tx_receipt.withdrawal_share_amount,
                    lp_share_price=tx_receipt.lp_share_price,
                )

            case HyperdriveActionType.REDEEM_WITHDRAW_SHARE:
                return RedeemWithdrawalShares(
                    provider=Web3.to_checksum_address(tx_receipt.provider),
                    destination=Web3.to_checksum_address(tx_receipt.destination),
                    withdrawal_share_amount=tx_receipt.withdrawal_share_amount,
                    amount=tx_receipt.amount,
                    vault_share_price=tx_receipt.vault_share_price,
                    as_base=tx_receipt.as_base,
                )

            case _:
                assert_never(trade_type)

    ################
    # Analysis
    ################

    def get_wallet(self, pool: Hyperdrive | None = None) -> HyperdriveWallet:
        """Returns the wallet object for the agent for the given hyperdrive pool.

        Arguments
        ---------
        pool: LocalHyperdrive | None, optional
            The pool to interact with. Defaults to the active pool.

        Returns
        -------
        HyperdriveWallet
            Returns the HyperdriveWallet object for the given pool.
        """
        if pool is None:
            pool = self._active_pool
        if pool is None:
            raise ValueError("Getting wallet object requires an active pool.")

        self._sync_events(pool)
        hyperdrive_address = pool.interface.hyperdrive_address

        # Query current positions from the events table
        positions = get_current_positions(
            self.chain.db_session,
            self.address,
            hyperdrive_address=hyperdrive_address,
            show_closed_positions=False,
            coerce_float=False,
        )
        # Convert to hyperdrive wallet object
        long_obj: dict[int, Long] = {}
        short_obj: dict[int, Short] = {}
        lp_balance: FixedPoint = FixedPoint(0)
        withdrawal_shares_balance: FixedPoint = FixedPoint(0)
        for _, row in positions.iterrows():
            # Sanity checks
            assert row["hyperdrive_address"] == hyperdrive_address
            assert row["wallet_address"] == self.address
            if row["token_id"] == "LP":
                lp_balance = FixedPoint(row["token_balance"])
            elif row["token_id"] == "WITHDRAWAL_SHARE":
                withdrawal_shares_balance = FixedPoint(row["token_balance"])
            elif row["token_type"] == "LONG":
                maturity_time = int(row["maturity_time"])
                long_obj[maturity_time] = Long(balance=FixedPoint(row["token_balance"]), maturity_time=maturity_time)
            elif row["token_type"] == "SHORT":
                maturity_time = int(row["maturity_time"])
                short_obj[maturity_time] = Short(balance=FixedPoint(row["token_balance"]), maturity_time=maturity_time)

        # We do a balance of call to get base balance.
        base_balance = FixedPoint(
            scaled_value=pool.interface.base_token_contract.functions.balanceOf(self.address).call()
        )

        return HyperdriveWallet(
            address=HexBytes(self.address),
            balance=Quantity(
                amount=base_balance,
                unit=TokenType.BASE,
            ),
            lp_tokens=lp_balance,
            withdraw_shares=withdrawal_shares_balance,
            longs=long_obj,
            shorts=short_obj,
        )

    def get_longs(self, pool: Hyperdrive | None = None) -> list[Long]:
        """Returns longs for the agent for the given hyperdrive pool.

        Arguments
        ---------
        pool: LocalHyperdrive | None, optional
            The pool to interact with. Defaults to the active pool.

        Returns
        -------
        list[Long]
            Returns the list of longs for the given pool.
        """
        wallet = self.get_wallet(pool)
        return list(wallet.longs.values())

    def get_shorts(self, pool: Hyperdrive | None = None) -> list[Short]:
        """Returns shorts for the agent for the given hyperdrive pool.

        Arguments
        ---------
        pool: LocalHyperdrive | None, optional
            The pool to interact with. Defaults to the active pool.

        Returns
        -------
        list[Short]
            Returns the list of longs for the given pool.
        """
        wallet = self.get_wallet(pool)
        return list(wallet.shorts.values())

    def get_lp(self, pool: Hyperdrive | None = None) -> FixedPoint:
        """Returns lp balance for the agent for the given hyperdrive pool.

        Arguments
        ---------
        pool: LocalHyperdrive | None, optional
            The pool to interact with. Defaults to the active pool.

        Returns
        -------
        list[Short]
            Returns the list of longs for the given pool.
        """
        wallet = self.get_wallet(pool)
        return wallet.lp_tokens

    def get_withdrawal_shares(self, pool: Hyperdrive | None = None) -> FixedPoint:
        """Returns withdrawal shares balance for the agent for the given hyperdrive pool.

        Arguments
        ---------
        pool: LocalHyperdrive | None, optional
            The pool to interact with. Defaults to the active pool.

        Returns
        -------
        list[Short]
            Returns the list of longs for the given pool.
        """
        wallet = self.get_wallet(pool)
        return wallet.withdraw_shares

    def get_positions(
        self,
        pool_filter: Hyperdrive | list[Hyperdrive] | None = None,
        show_closed_positions: bool = False,
        coerce_float: bool = False,
    ) -> pd.DataFrame:
        """Returns all of the agent's positions across all hyperdrive pools.

        Arguments
        ---------
        pool_filter: Hyperdrive | list[Hyperdrive], optional
            The hyperdrive pool(s) to query. Defaults to None, which will query all pools.
        show_closed_positions: bool, optional
            Whether to show positions closed positions (i.e., positions with zero balance). Defaults to False.
            When False, will only return currently open positions. Useful for gathering currently open positions.
            When True, will also return any closed positions. Useful for calculating overall pnl of all positions.
        coerce_float: bool, optional
            Whether to coerce underlying Decimal values to float when as_df is True. Defaults to False.

        Returns
        -------
        pd.DataFrame
            The agent's positions across all hyperdrive pools.
        """
        if pool_filter is None:
            raise ValueError("Pool filter or registry address must be specified to get positions.")

        # Sync all events, then sync snapshots for pnl and value calculation
        self._sync_events(pool_filter)
        self._sync_snapshot(pool_filter)
        return self._get_positions(
            pool_filter=pool_filter, show_closed_positions=show_closed_positions, coerce_float=coerce_float
        )

    def _get_positions(
        self, pool_filter: Hyperdrive | list[Hyperdrive] | None, show_closed_positions: bool, coerce_float: bool
    ) -> pd.DataFrame:
        # Query the snapshot for the most recent positions.
        if pool_filter is None:
            hyperdrive_address = None
        elif isinstance(pool_filter, list):
            hyperdrive_address = [str(pool.hyperdrive_address) for pool in pool_filter]
        else:
            hyperdrive_address = str(pool_filter.hyperdrive_address)

        position_snapshot = get_position_snapshot(
            session=self.chain.db_session,
            start_block=-1,
            wallet_address=self.address,
            hyperdrive_address=hyperdrive_address,
            coerce_float=coerce_float,
        ).drop("id", axis=1)
        if not show_closed_positions:
            position_snapshot = position_snapshot[position_snapshot["token_balance"] != 0].reset_index(drop=True)
        # Add usernames
        position_snapshot = self.chain._add_username_to_dataframe(position_snapshot, "wallet_address")
        position_snapshot = self.chain._add_hyperdrive_name_to_dataframe(position_snapshot, "hyperdrive_address")
        return position_snapshot

    def get_trade_events(
        self,
        pool_filter: Hyperdrive | list[Hyperdrive] | None = None,
        all_token_deltas: bool = False,
        coerce_float: bool = False,
    ) -> pd.DataFrame:
        """Returns the agent's current wallet.

        Arguments
        ---------
        pool_filter : Hyperdrive | list[Hyperdrive] | None, optional
            The hyperdrive pool(s) to get trade events from.
        all_token_deltas: bool, optional
            When removing liquidity that results in withdrawal shares, the events table returns
            two entries for this transaction to keep track of token deltas (one for lp tokens and
            one for withdrawal shares). If this flag is true, will return all entries in the table,
            which is useful for calculating token positions. If false, will drop the duplicate
            withdrawal share entry (useful for returning a ticker).
        coerce_float: bool, optional
            If True, will coerce underlying Decimals to floats.

        Returns
        -------
        HyperdriveWallet
            The agent's current wallet.
        """
        if pool_filter is None:
            # TODO get positions on remote chains must pass in pool for now
            # Eventually we get the list of pools from registry and track all pools in registry
            raise NotImplementedError("Pool must be specified to get trade events.")
        self._sync_events(pool_filter)
        return self._get_trade_events(
            all_token_deltas=all_token_deltas, pool_filter=pool_filter, coerce_float=coerce_float
        )

    def _get_trade_events(
        self,
        pool_filter: Hyperdrive | list[Hyperdrive] | None,
        all_token_deltas: bool,
        coerce_float: bool,
    ) -> pd.DataFrame:
        """We call this function in both remote and local agents, as the remote call needs to
        do argument checking."""
        # If pool is None, we don't filter on hyperdrive address
        if pool_filter is None:
            hyperdrive_address = None
        elif isinstance(pool_filter, list):
            hyperdrive_address = [str(pool.hyperdrive_address) for pool in pool_filter]
        else:
            hyperdrive_address = pool_filter.interface.hyperdrive_address

        trade_events = get_trade_events(
            self.chain.db_session,
            hyperdrive_address=hyperdrive_address,
            wallet_address=self.address,
            all_token_deltas=all_token_deltas,
            coerce_float=coerce_float,
        ).drop("id", axis=1)

        # Add usernames
        trade_events = self.chain._add_username_to_dataframe(trade_events, "wallet_address")
        trade_events = self.chain._add_hyperdrive_name_to_dataframe(trade_events, "hyperdrive_address")
        return trade_events

    # Helper functions for analysis

    def _sync_events(self, pool: Hyperdrive | list[Hyperdrive]) -> None:
        # Update the db with this wallet
        # Note that remote hyperdrive only updates the wallet wrt the agent itself.
        # TODO this function can be optimized to cache.

        # NOTE the way we sync the events table is by either looking at (1) the latest
        # entry wrt a wallet in the events table, or (2) the latest entry overall in the events
        # table, based on if we're updating the table with all wallets or just a single wallet.
        interfaces: list[HyperdriveReadInterface]
        if isinstance(pool, list):
            interfaces = [p.interface for p in pool]
        else:
            interfaces = [pool.interface]

        # Remote hyperdrive stack syncs only the agent's wallet
        trade_events_to_db(interfaces, wallet_addr=self.address, db_session=self.chain.db_session)
        # We sync checkpoint events as well
        checkpoint_events_to_db(interfaces, db_session=self.chain.db_session)

    def _sync_snapshot(self, pool: Hyperdrive | list[Hyperdrive]) -> None:
        # Update the db with a snapshot of the wallet

        interfaces: list[HyperdriveReadInterface]
        if isinstance(pool, list):
            interfaces = [p.interface for p in pool]
        else:
            interfaces = [pool.interface]

        # Note that remote hyperdrive only updates snapshots wrt the agent itself.
        snapshot_positions_to_db(
            interfaces,
            wallet_addr=self.address,
            db_session=self.chain.db_session,
            calc_pnl=self.chain.config.calc_pnl,
        )

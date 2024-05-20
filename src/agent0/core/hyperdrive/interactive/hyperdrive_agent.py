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
from agent0.core.hyperdrive import (
    HyperdriveActionType,
    HyperdrivePolicyAgent,
    HyperdriveWallet,
    TradeResult,
    TradeStatus,
)
from agent0.core.hyperdrive.agent import (
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
from agent0.ethpy.base import set_anvil_account_balance, smart_contract_transact
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
    from .hyperdrive import Hyperdrive

# We keep this class bare bones, while we want the logic functions in InteractiveHyperdrive to be private
# Hence, we call protected class methods in this class.
# pylint: disable=protected-access


class HyperdriveAgent:
    """Interactive Hyperdrive Agent."""

    ################
    # Initialization
    ################

    def __init__(
        self,
        name: str | None,
        pool: Hyperdrive,
        policy: Type[HyperdriveBasePolicy] | None,
        policy_config: HyperdriveBasePolicy.Config | None,
        private_key: str,
    ) -> None:
        """Constructor for the interactive hyperdrive agent.
        NOTE: this constructor shouldn't be called directly, but rather from Hyperdrive's
        `init_agent` method.

        Arguments
        ---------
        name: str | None
            The name of the agent. Defaults to the wallet address.
        pool: Hyperdrive
            The pool object that this agent belongs to.
        policy: Type[HyperdriveBasePolicy] | None
            An optional policy to attach to this agent.
        policy_config: HyperdriveBasePolicy.Config | None,
            The configuration for the attached policy.
        private_key: str | None, optional
            The private key of the associated account. Default is auto-generated.
        """
        # pylint: disable=too-many-arguments
        self._pool = pool
        # Setting the budget to 0 here, we'll update the wallet from the chain
        if policy is None:
            if policy_config is None:
                policy_config = HyperdriveBasePolicy.Config(rng=self._pool.config.rng)
            policy_obj = HyperdriveBasePolicy(policy_config)
        else:
            if policy_config is None:
                policy_config = policy.Config(rng=self._pool.config.rng)
            policy_obj = policy(policy_config)

        agent = HyperdrivePolicyAgent(Account().from_key(private_key), initial_budget=FixedPoint(0), policy=policy_obj)

        # Register the username if it was provided
        if name is not None:
            add_addr_to_username(name, [agent.address], self._pool.chain.db_session)
        self.agent = agent

    @property
    def checksum_address(self) -> ChecksumAddress:
        """Return the checksum address of the account."""
        return self.agent.checksum_address

    @property
    def policy_done_trading(self) -> bool:
        """Return whether the agent's policy is done trading."""
        return self.agent.done_trading

    def add_funds(
        self,
        base: FixedPoint | None = None,
        eth: FixedPoint | None = None,
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
        signer_account: LocalAccount | None, optional
            The signer account to use to call `mint`. Defaults to the agent itself.
        """
        if base is None:
            base = FixedPoint(0)
        if eth is None:
            eth = FixedPoint(0)

        # The signer of the mint transaction defaults to the agent itself, unless specified.
        if signer_account is None:
            signer_account = self.agent

        if eth > FixedPoint(0):
            # Eth is a set balance call
            eth_balance, _ = self._pool.interface.get_eth_base_balances(self.agent)
            new_eth_balance = eth_balance + eth
            _ = set_anvil_account_balance(self._pool.interface.web3, self.agent.address, new_eth_balance.scaled_value)

        if base > FixedPoint(0):
            # We mint base
            _ = smart_contract_transact(
                self._pool.interface.web3,
                self._pool.interface.base_token_contract,
                signer_account,
                "mint(address,uint256)",
                self.agent.checksum_address,
                base.scaled_value,
            )
            # Update the agent's wallet balance
            self.agent.wallet.balance.amount += base

    def set_max_approval(self) -> None:
        """Sets the max approval to the hyperdrive contract.

        .. warning:: This sets the max approval to the underlying hyperdrive contract for
        this wallet. Do this at your own risk.

        """
        # Establish max approval for the hyperdrive contract
        set_max_approval(
            self.agent,
            self._pool.interface.web3,
            self._pool.interface.base_token_contract,
            str(self._pool.interface.hyperdrive_contract.address),
        )

    ################
    # Trades
    ################

    def open_long(self, base: FixedPoint) -> OpenLong:
        """Opens a long for this agent.

        Arguments
        ---------
        base: FixedPoint
            The amount of longs to open in units of base.

        Returns
        -------
        OpenLong
            The emitted event of the open long call.
        """
        # Build trade object
        trade_object = open_long_trade(base)
        # TODO expose async here to the caller eventually
        trade_result: TradeResult = asyncio.run(
            async_execute_single_trade(
                self._pool.interface,
                self.agent,
                trade_object,
                self._pool.config.always_execute_policy_post_action,
                self._pool.config.preview_before_trade,
            )
        )
        tx_receipt = self._handle_trade_result(trade_result, always_throw_exception=True)
        return self._build_event_obj_from_tx_receipt(HyperdriveActionType.OPEN_LONG, tx_receipt)

    def close_long(self, maturity_time: int, bonds: FixedPoint) -> CloseLong:
        """Closes a long for this agent.

        Arguments
        ---------
        maturity_time: int
            The maturity time of the bonds to close. This is the identifier of the long tokens.
        bonds: FixedPoint
            The amount of longs to close in units of bonds.

        Returns
        -------
        CloseLong
            The emitted event of the close long call.
        """
        # Build trade object
        trade_object = close_long_trade(bonds, maturity_time)
        # TODO expose async here to the caller eventually
        trade_result: TradeResult = asyncio.run(
            async_execute_single_trade(
                self._pool.interface,
                self.agent,
                trade_object,
                self._pool.config.always_execute_policy_post_action,
                self._pool.config.preview_before_trade,
            )
        )
        tx_receipt = self._handle_trade_result(trade_result, always_throw_exception=True)
        return self._build_event_obj_from_tx_receipt(HyperdriveActionType.CLOSE_LONG, tx_receipt)

    def open_short(self, bonds: FixedPoint) -> OpenShort:
        """Opens a short for this agent.

        Arguments
        ---------
        bonds: FixedPoint
            The amount of shorts to open in units of bonds.

        Returns
        -------
        OpenShort
            The emitted event of the open short call.
        """
        trade_object = open_short_trade(bonds)
        # TODO expose async here to the caller eventually
        trade_result: TradeResult = asyncio.run(
            async_execute_single_trade(
                self._pool.interface,
                self.agent,
                trade_object,
                self._pool.config.always_execute_policy_post_action,
                self._pool.config.preview_before_trade,
            )
        )
        tx_receipt = self._handle_trade_result(trade_result, always_throw_exception=True)
        return self._build_event_obj_from_tx_receipt(HyperdriveActionType.OPEN_SHORT, tx_receipt)

    def close_short(self, maturity_time: int, bonds: FixedPoint) -> CloseShort:
        """Closes a short for this agent.

        Arguments
        ---------
        maturity_time: int
            The maturity time of the bonds to close. This is the identifier of the short tokens.
        bonds: FixedPoint
            The amount of shorts to close in units of bonds.

        Returns
        -------
        CloseShort
            The emitted event of the close short call.
        """
        trade_object = close_short_trade(bonds, maturity_time)
        # TODO expose async here to the caller eventually
        trade_result: TradeResult = asyncio.run(
            async_execute_single_trade(
                self._pool.interface,
                self.agent,
                trade_object,
                self._pool.config.always_execute_policy_post_action,
                self._pool.config.preview_before_trade,
            )
        )
        tx_receipt = self._handle_trade_result(trade_result, always_throw_exception=True)
        return self._build_event_obj_from_tx_receipt(HyperdriveActionType.CLOSE_SHORT, tx_receipt)

    def add_liquidity(self, base: FixedPoint) -> AddLiquidity:
        """Adds liquidity for this agent.

        Arguments
        ---------
        base: FixedPoint
            The amount of liquidity to add in units of base.

        Returns
        -------
        AddLiquidity
            The emitted event of the add liquidity call.
        """
        trade_object = add_liquidity_trade(base)
        # TODO expose async here to the caller eventually
        trade_result: TradeResult = asyncio.run(
            async_execute_single_trade(
                self._pool.interface,
                self.agent,
                trade_object,
                self._pool.config.always_execute_policy_post_action,
                self._pool.config.preview_before_trade,
            )
        )
        tx_receipt = self._handle_trade_result(trade_result, always_throw_exception=True)
        return self._build_event_obj_from_tx_receipt(HyperdriveActionType.ADD_LIQUIDITY, tx_receipt)

    def remove_liquidity(self, shares: FixedPoint) -> RemoveLiquidity:
        """Removes liquidity for this agent.

        Arguments
        ---------
        shares: FixedPoint
            The amount of liquidity to remove in units of shares.

        Returns
        -------
        RemoveLiquidity
            The emitted event of the remove liquidity call.
        """
        trade_object = remove_liquidity_trade(shares)
        # TODO expose async here to the caller eventually
        trade_result: TradeResult = asyncio.run(
            async_execute_single_trade(
                self._pool.interface,
                self.agent,
                trade_object,
                self._pool.config.always_execute_policy_post_action,
                self._pool.config.preview_before_trade,
            )
        )
        tx_receipt = self._handle_trade_result(trade_result, always_throw_exception=True)
        return self._build_event_obj_from_tx_receipt(HyperdriveActionType.REMOVE_LIQUIDITY, tx_receipt)

    def redeem_withdraw_share(self, shares: FixedPoint) -> RedeemWithdrawalShares:
        """Redeems withdrawal shares for this agent.

        Arguments
        ---------
        shares: FixedPoint
            The amount of withdrawal shares to redeem in units of shares.

        Returns
        -------
        RedeemWithdrawalShares
            The emitted event of the redeem withdrawal shares call.
        """
        trade_object = redeem_withdraw_shares_trade(shares)
        # TODO expose async here to the caller eventually
        trade_results: TradeResult = asyncio.run(
            async_execute_single_trade(
                self._pool.interface,
                self.agent,
                trade_object,
                self._pool.config.always_execute_policy_post_action,
                self._pool.config.preview_before_trade,
            )
        )
        tx_receipt = self._handle_trade_result(trade_results, always_throw_exception=True)
        return self._build_event_obj_from_tx_receipt(HyperdriveActionType.REDEEM_WITHDRAW_SHARE, tx_receipt)

    def execute_policy_action(
        self,
    ) -> list[OpenLong | OpenShort | CloseLong | CloseShort | AddLiquidity | RemoveLiquidity | RedeemWithdrawalShares]:
        """Executes the underlying policy action (if set).

        Returns
        -------
        list[OpenLong | OpenShort | CloseLong | CloseShort | AddLiquidity | RemoveLiquidity | RedeemWithdrawalShares]
            Events of the executed actions.
        """
        # Only allow executing agent policies if a policy was passed in the constructor
        # we check type instead of isinstance to explicitly check for the hyperdrive base class
        # pylint: disable=unidiomatic-typecheck
        if type(self.agent.policy) == HyperdriveBasePolicy:
            raise ValueError("Must pass in a policy in the constructor to execute policy action.")

        trade_results: list[TradeResult] = asyncio.run(
            async_execute_agent_trades(
                self._pool.interface,
                self.agent,
                preview_before_trade=self._pool.config.preview_before_trade,
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

    def liquidate(
        self, randomize: bool = False
    ) -> list[CloseLong | CloseShort | RemoveLiquidity | RedeemWithdrawalShares]:
        """Liquidate all of the agent's positions.

        Arguments
        ---------
        randomize: bool, optional
            Whether to randomize liquidation trades. Defaults to False.

        Returns
        -------
        list[CloseLong | CloseShort | RemoveLiquidity | RedeemWithdrawalShares]
            Events of the executed actions.
        """
        trade_results: list[TradeResult] = asyncio.run(
            async_execute_agent_trades(
                self._pool.interface,
                self.agent,
                preview_before_trade=self._pool.config.preview_before_trade,
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

    # Helper functions for trades

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
                log_level=self._pool.config.crash_log_level,
                crash_report_to_file=True,
                crash_report_file_prefix="interactive_hyperdrive",
                log_to_rollbar=self._pool.config.log_to_rollbar,
                rollbar_log_prefix=self._pool.config.rollbar_log_prefix,
                additional_info=self._pool.config.crash_report_additional_info,
            )

            if self._pool.config.exception_on_policy_error:
                # Check for slippage and if we want to throw an exception on slippage
                if (
                    always_throw_exception
                    or (not trade_result.is_slippage)
                    or (trade_result.is_slippage and self._pool.config.exception_on_policy_slippage)
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

    def get_positions(self, show_closed_positions: bool = False, coerce_float: bool = False) -> pd.DataFrame:
        """Returns all of the agent's positions across all hyperdrive pools.

        Arguments
        ---------
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
        # Sync all events, then sync snapshots for pnl and value calculation
        self._sync_events(self.agent)
        self._sync_snapshot(self.agent)
        # Query the snapshot for the most recent positions.
        position_snapshot = get_position_snapshot(
            session=self._pool.chain.db_session,
            start_block=-1,
            wallet_address=self.agent.address,
            coerce_float=coerce_float,
        ).drop("id", axis=1)
        if not show_closed_positions:
            position_snapshot = position_snapshot[position_snapshot["token_balance"] != 0].reset_index(drop=True)
        # Add usernames
        position_snapshot = self._pool._add_username_to_dataframe(position_snapshot, "wallet_address")
        position_snapshot = self._pool._add_hyperdrive_name_to_dataframe(position_snapshot, "hyperdrive_address")
        return position_snapshot

    def get_wallet(self) -> HyperdriveWallet:
        """Returns the wallet object for the agent for the given hyperdrive pool.

        TODO this function will eventually use the active pool or take a pool as an argument
        once agent gets detached from the pool.

        Returns
        -------
        HyperdriveWallet
            Returns the HyperdriveWallet object for the given pool.
        """

        self._sync_events(self.agent)
        # Query current positions from the events table
        positions = get_current_positions(
            self._pool.chain.db_session,
            self.agent.checksum_address,
            hyperdrive_address=self._pool.interface.hyperdrive_address,
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
            assert row["hyperdrive_address"] == self._pool.interface.hyperdrive_address
            assert row["wallet_address"] == self.agent.checksum_address
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
            scaled_value=self._pool.interface.base_token_contract.functions.balanceOf(
                self.agent.checksum_address
            ).call()
        )

        return HyperdriveWallet(
            address=HexBytes(self.agent.checksum_address),
            balance=Quantity(
                amount=base_balance,
                unit=TokenType.BASE,
            ),
            lp_tokens=lp_balance,
            withdraw_shares=withdrawal_shares_balance,
            longs=long_obj,
            shorts=short_obj,
        )

    def get_trade_events(self, all_token_deltas: bool = False, coerce_float: bool = False) -> pd.DataFrame:
        """Returns the agent's current wallet.

        Arguments
        ---------
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
        self._sync_events(self.agent)
        return get_trade_events(
            self._pool.chain.db_session,
            self.agent.checksum_address,
            all_token_deltas=all_token_deltas,
            coerce_float=coerce_float,
        ).drop("id", axis=1)

    # Helper functions for analysis

    def _sync_events(self, agent: HyperdrivePolicyAgent) -> None:
        # Update the db with this wallet
        # Note that remote hyperdrive only updates the wallet wrt the agent itself.
        # TODO this function can be optimized to cache.

        # NOTE the way we sync the events table is by either looking at (1) the latest
        # entry wrt a wallet in the events table, or (2) the latest entry overall in the events
        # table, based on if we're updating the table with all wallets or just a single wallet.

        # Remote hyperdrive stack syncs only the agent's wallet
        trade_events_to_db(
            [self._pool.interface], wallet_addr=agent.checksum_address, db_session=self._pool.chain.db_session
        )
        # We sync checkpoint events as well
        checkpoint_events_to_db([self._pool.interface], db_session=self._pool.chain.db_session)

    def _sync_snapshot(self, agent: HyperdrivePolicyAgent) -> None:
        # Update the db with a snapshot of the wallet

        # Note that remote hyperdrive only updates snapshots wrt the agent itself.
        snapshot_positions_to_db(
            [self._pool.interface],
            wallet_addr=agent.checksum_address,
            db_session=self._pool.chain.db_session,
            calc_pnl=self._pool.config.calc_pnl,
        )

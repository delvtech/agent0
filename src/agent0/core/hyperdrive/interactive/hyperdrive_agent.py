"""The hyperdrive agent object that encapsulates an agent."""

from __future__ import annotations

import asyncio
import threading
from functools import partial
from typing import TYPE_CHECKING, Literal, Type, overload

import pandas as pd
from eth_account.account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import ChecksumAddress
from fixedpointmath import FixedPoint
from hexbytes import HexBytes
from web3 import Web3
from web3.types import Nonce

from agent0.chainsync.analysis import fill_pnl_values, snapshot_positions_to_db
from agent0.chainsync.dashboard import abbreviate_address
from agent0.chainsync.db.base import add_addr_to_username
from agent0.chainsync.db.hyperdrive import (
    checkpoint_events_to_db,
    get_current_positions,
    get_position_snapshot,
    get_trade_events,
    trade_events_to_db,
)
from agent0.core.base import Quantity, TokenType, Trade
from agent0.core.hyperdrive import HyperdriveMarketAction
from agent0.core.hyperdrive.agent import (
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
from agent0.ethpy.base import get_account_balance, set_anvil_account_balance, smart_contract_transact
from agent0.ethpy.hyperdrive.event_types import (
    AddLiquidity,
    BaseHyperdriveEvent,
    CloseLong,
    CloseShort,
    OpenLong,
    OpenShort,
    RedeemWithdrawalShares,
    RemoveLiquidity,
)

from .exec import (
    async_execute_agent_trades,
    async_execute_single_trade,
    get_liquidation_trades,
    get_trades,
    set_max_approval,
)

if TYPE_CHECKING:
    from agent0.ethpy.hyperdrive import HyperdriveReadInterface

    from .chain import Chain
    from .hyperdrive import Hyperdrive

# pylint: disable=protected-access
# pylint: disable=too-many-lines


class HyperdriveAgent:
    """Interactive Hyperdrive Agent."""

    # pylint: disable=too-many-public-methods
    # pylint: disable=too-many-instance-attributes

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

        # If we don't set a name, we only set the object name as the abbreviated address.
        # The pandas side will handle missing name to address mappings
        if name is None:
            self.name = abbreviate_address(self.address)
        else:
            self.name = name
            # Register the username if it was provided
            add_addr_to_username(self.name, [self.address], self.chain.db_session)

        # The agent object itself maintains it's own nonce for async transactions
        self.nonce_lock = threading.Lock()
        self.current_nonce = 0

    def _get_nonce_safe(self) -> Nonce:
        """Get agent nonces in a thread-safe manner.

        We pass in the callable function to underlying ethpy calls so that
        we get nonce when we sign the transaction.

        Returns
        -------
        int
            The agent's current nonce value.
        """
        with self.nonce_lock:
            # Since we're handling nonces here, we assume this wallet isn't making other trades
            # so we always use the latest block
            chain_nonce = self.chain._web3.eth.get_transaction_count(self.address, "latest")
            if chain_nonce > self.current_nonce:
                out_nonce = chain_nonce
                self.current_nonce = chain_nonce + 1
            else:
                out_nonce = self.current_nonce
                self.current_nonce += 1

        return Nonce(out_nonce)

    def _reset_nonce(self) -> None:
        with self.nonce_lock:
            self.current_nonce = 0

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
        pool: Hyperdrive | None, optional
            The pool to interact with. Defaults to the active pool.
        signer_account: LocalAccount | None, optional
            The signer account to use to call `mint`. Defaults to the agent itself.
        """

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
            eth_balance = self.get_eth()
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
        pool: Hyperdrive | None, optional
            The pool to interact with. Defaults to the active pool.
        """
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
        pool: Hyperdrive
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
        pool: Hyperdrive | None, optional
            The pool to interact with. Defaults to the active pool.

        Returns
        -------
        OpenLong
            The emitted event of the open long call.
        """
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
                partial(self.get_wallet, pool),
                trade_object,
                self.chain.config.always_execute_policy_post_action,
                self.chain.config.preview_before_trade,
                nonce_func=self._get_nonce_safe,
                policy=self._active_policy,
            )
        )
        try:
            hyperdrive_event = self._handle_trade_result(trade_result, pool, always_throw_exception=True)
        except Exception as e:
            # We always reset nonce on failure to avoid skipped nonces
            self._reset_nonce()
            raise e

        # Type narrowing
        assert isinstance(hyperdrive_event, OpenLong)
        return hyperdrive_event

    def close_long(self, maturity_time: int, bonds: FixedPoint, pool: Hyperdrive | None = None) -> CloseLong:
        """Closes a long for this agent.

        Arguments
        ---------
        maturity_time: int
            The maturity time of the bonds to close. This is the identifier of the long tokens.
        bonds: FixedPoint
            The amount of longs to close in units of bonds.
        pool: Hyperdrive | None, optional
            The pool to interact with. Defaults to the active pool.

        Returns
        -------
        CloseLong
            The emitted event of the close long call.
        """
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
                partial(self.get_wallet, pool),
                trade_object,
                self.chain.config.always_execute_policy_post_action,
                self.chain.config.preview_before_trade,
                nonce_func=self._get_nonce_safe,
                policy=self._active_policy,
            )
        )
        try:
            hyperdrive_event = self._handle_trade_result(trade_result, pool, always_throw_exception=True)
        except Exception as e:
            # We always reset nonce on failure to avoid skipped nonces
            self._reset_nonce()
            raise e

        # Type narrowing
        assert isinstance(hyperdrive_event, CloseLong)
        return hyperdrive_event

    def open_short(self, bonds: FixedPoint, pool: Hyperdrive | None = None) -> OpenShort:
        """Opens a short for this agent.

        Arguments
        ---------
        bonds: FixedPoint
            The amount of shorts to open in units of bonds.
        pool: Hyperdrive | None, optional
            The pool to interact with. Defaults to the active pool.

        Returns
        -------
        OpenShort
            The emitted event of the open short call.
        """
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
                partial(self.get_wallet, pool),
                trade_object,
                self.chain.config.always_execute_policy_post_action,
                self.chain.config.preview_before_trade,
                nonce_func=self._get_nonce_safe,
                policy=self._active_policy,
            )
        )
        try:
            hyperdrive_event = self._handle_trade_result(trade_result, pool, always_throw_exception=True)
        except Exception as e:
            # We always reset nonce on failure to avoid skipped nonces
            self._reset_nonce()
            raise e
        # Type narrowing
        assert isinstance(hyperdrive_event, OpenShort)
        return hyperdrive_event

    def close_short(self, maturity_time: int, bonds: FixedPoint, pool: Hyperdrive | None = None) -> CloseShort:
        """Closes a short for this agent.

        Arguments
        ---------
        maturity_time: int
            The maturity time of the bonds to close. This is the identifier of the short tokens.
        bonds: FixedPoint
            The amount of shorts to close in units of bonds.
        pool: Hyperdrive | None, optional
            The pool to interact with. Defaults to the active pool.

        Returns
        -------
        CloseShort
            The emitted event of the close short call.
        """
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
                partial(self.get_wallet, pool),
                trade_object,
                self.chain.config.always_execute_policy_post_action,
                self.chain.config.preview_before_trade,
                nonce_func=self._get_nonce_safe,
                policy=self._active_policy,
            )
        )
        try:
            hyperdrive_event = self._handle_trade_result(trade_result, pool, always_throw_exception=True)
        except Exception as e:
            # We always reset nonce on failure to avoid skipped nonces
            self._reset_nonce()
            raise e
        # Type narrowing
        assert isinstance(hyperdrive_event, CloseShort)
        return hyperdrive_event

    def add_liquidity(self, base: FixedPoint, pool: Hyperdrive | None = None) -> AddLiquidity:
        """Adds liquidity for this agent.

        Arguments
        ---------
        base: FixedPoint
            The amount of liquidity to add in units of base.
        pool: Hyperdrive | None, optional
            The pool to interact with. Defaults to the active pool.

        Returns
        -------
        AddLiquidity
            The emitted event of the add liquidity call.
        """
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
                partial(self.get_wallet, pool),
                trade_object,
                self.chain.config.always_execute_policy_post_action,
                self.chain.config.preview_before_trade,
                nonce_func=self._get_nonce_safe,
                policy=self._active_policy,
            )
        )
        try:
            hyperdrive_event = self._handle_trade_result(trade_result, pool, always_throw_exception=True)
        except Exception as e:
            # We always reset nonce on failure to avoid skipped nonces
            self._reset_nonce()
            raise e
        # Type narrowing
        assert isinstance(hyperdrive_event, AddLiquidity)
        return hyperdrive_event

    def remove_liquidity(self, shares: FixedPoint, pool: Hyperdrive | None = None) -> RemoveLiquidity:
        """Removes liquidity for this agent.

        Arguments
        ---------
        shares: FixedPoint
            The amount of liquidity to remove in units of shares.
        pool: Hyperdrive | None, optional
            The pool to interact with. Defaults to the active pool.

        Returns
        -------
        RemoveLiquidity
            The emitted event of the remove liquidity call.
        """
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
                partial(self.get_wallet, pool),
                trade_object,
                self.chain.config.always_execute_policy_post_action,
                self.chain.config.preview_before_trade,
                nonce_func=self._get_nonce_safe,
                policy=self._active_policy,
            )
        )
        try:
            hyperdrive_event = self._handle_trade_result(trade_result, pool, always_throw_exception=True)
        except Exception as e:
            # We always reset nonce on failure to avoid skipped nonces
            self._reset_nonce()
            raise e
        # Type narrowing
        assert isinstance(hyperdrive_event, RemoveLiquidity)
        return hyperdrive_event

    def redeem_withdrawal_share(self, shares: FixedPoint, pool: Hyperdrive | None = None) -> RedeemWithdrawalShares:
        """Redeems withdrawal shares for this agent.

        Arguments
        ---------
        shares: FixedPoint
            The amount of withdrawal shares to redeem in units of shares.
        pool: Hyperdrive | None, optional
            The pool to interact with. Defaults to the active pool.

        Returns
        -------
        RedeemWithdrawalShares
            The emitted event of the redeem withdrawal shares call.
        """
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
                partial(self.get_wallet, pool),
                trade_object,
                self.chain.config.always_execute_policy_post_action,
                self.chain.config.preview_before_trade,
                nonce_func=self._get_nonce_safe,
                policy=self._active_policy,
            )
        )
        try:
            hyperdrive_event = self._handle_trade_result(trade_results, pool, always_throw_exception=True)
        except Exception as e:
            # We always reset nonce on failure to avoid skipped nonces
            self._reset_nonce()
            raise e
        # Type narrowing
        assert isinstance(hyperdrive_event, RedeemWithdrawalShares)
        return hyperdrive_event

    def get_policy_action(self, pool: Hyperdrive | None = None) -> list[Trade[HyperdriveMarketAction]]:
        """Gets the underlying policy actions.

        Arguments
        ---------
        pool: Hyperdrive | None, optional
            The pool to interact with. Defaults to the active pool.

        Returns
        -------
        list[Trade[HyperdriveMarketAction]]
            The actions of the underlying policy.
        """
        # Only allow executing agent policies if a policy was passed in the constructor
        if self._active_policy is None:
            raise ValueError("No active policy set.")

        if pool is None:
            pool = self._active_pool
        if pool is None:
            raise ValueError("Getting policy action requires an active pool.")

        return get_trades(
            interface=pool.interface.get_read_interface(),
            policy=self._active_policy,
            wallet=self.get_wallet(pool),
        )

    def get_liquidate_action(
        self, pool: Hyperdrive | None = None, randomize: bool = False
    ) -> list[Trade[HyperdriveMarketAction]]:
        """Gets the liquidate actions for this agent.

        Arguments
        ---------
        pool: Hyperdrive | None, optional
            The pool to interact with. Defaults to the active pool.
        randomize: bool, optional
            Whether to randomize the order of the liquidate actions.

        Returns
        -------
        list[Trade[HyperdriveMarketAction]]
            The liquidate actions of the underlying policy.
        """
        if pool is None:
            pool = self._active_pool
        if pool is None:
            raise ValueError("Getting liquidate actions requires an active pool.")

        # For type narrowing
        # rng should always be set in post_init
        assert self.chain.config.rng is not None

        return get_liquidation_trades(
            interface=pool.interface.get_read_interface(),
            wallet=self.get_wallet(pool),
            randomize_trades=randomize,
            rng=self.chain.config.rng,
        )

    def execute_action(
        self, actions: list[Trade[HyperdriveMarketAction]], pool: Hyperdrive | None = None
    ) -> list[BaseHyperdriveEvent]:
        """Executes the specified actions.

        Arguments
        ---------
        actions: list[Trade[HyperdriveMarketAction]]
            The actions to execute. This is the return value of `get_policy_action` or `get_liquidate_action`.
        pool: Hyperdrive | None, optional
            The pool to interact with. Defaults to the active pool.

        Returns
        -------
        list[BaseHyperdriveEvent]
            Events of the executed actions.
        """

        if pool is None:
            pool = self._active_pool
        if pool is None:
            raise ValueError("Executing actions requires an active pool.")

        # We don't want to call `_get_nonce_safe()` if we don't do any actions,
        # as this results in a skipped nonce value. Hence, we explicitly check for
        # empty actions here and return early.
        if len(actions) == 0:
            return []

        trade_results: list[TradeResult] = asyncio.run(
            async_execute_agent_trades(
                actions,
                pool.interface,
                self.account,
                partial(self.get_wallet, pool),
                # We pass in policy here for `post_action`. Post action is ignored if policy not set.
                policy=self._active_policy,
                preview_before_trade=self.chain.config.preview_before_trade,
                nonce_func=self._get_nonce_safe,
            )
        )
        out_events = []
        # The underlying policy can execute multiple actions in one step
        for trade_result in trade_results:
            hyperdrive_event = self._handle_trade_result(trade_result, pool, always_throw_exception=False)
            if hyperdrive_event is not None:
                out_events.append(hyperdrive_event)
        return out_events

    def execute_policy_action(self, pool: Hyperdrive | None = None) -> list[BaseHyperdriveEvent]:
        """Gets the underlying policy action and executes them.

        This function simply calls `execute_action` with the result of `get_policy_action`.

        Arguments
        ---------
        pool: Hyperdrive | None, optional
            The pool to interact with. Defaults to the active pool.

        Returns
        -------
        list[BaseHyperdriveEvent]
            Events of the executed actions.
        """
        # Only allow executing agent policies if a policy was passed in the constructor
        return self.execute_action(self.get_policy_action(pool), pool)

    def execute_liquidate(self, pool: Hyperdrive | None = None, randomize: bool = False) -> list[BaseHyperdriveEvent]:
        """Gets the agent's liquidate actions and executes them.

        This function simply calls `execute_action` with the result of `get_liquidate_action`.

        Arguments
        ---------
        randomize: bool, optional
            Whether to randomize liquidation trades. Defaults to False.
        pool: Hyperdrive | None, optional
            The pool to interact with. Defaults to the active pool.

        Returns
        -------
        list[CloseLong | CloseShort | RemoveLiquidity | RedeemWithdrawalShares]
            Events of the executed actions.
        """
        return self.execute_action(self.get_liquidate_action(pool, randomize), pool)

    # Helper functions for trades

    @overload
    def _handle_trade_result(
        self, trade_result: TradeResult, pool: Hyperdrive, always_throw_exception: Literal[True]
    ) -> BaseHyperdriveEvent: ...

    @overload
    def _handle_trade_result(
        self, trade_result: TradeResult, pool: Hyperdrive, always_throw_exception: Literal[False]
    ) -> BaseHyperdriveEvent | None: ...

    def _handle_trade_result(
        self, trade_result: TradeResult, pool: Hyperdrive, always_throw_exception: bool
    ) -> BaseHyperdriveEvent | None:
        if not trade_result.trade_successful:
            # Defaults to CRITICAL
            assert trade_result.exception is not None
            log_hyperdrive_crash_report(
                trade_result,
                log_level=self.chain.config.crash_log_level,
                crash_report_to_file=True,
                crash_report_stdout_summary=self.chain.config.crash_report_stdout_summary,
                crash_report_file_prefix="interactive_hyperdrive",
                log_to_rollbar=self.chain.config.log_to_rollbar,
                rollbar_log_level_threshold=self.chain.config.rollbar_log_level_threshold,
                rollbar_log_prefix=self.chain.config.rollbar_log_prefix,
                rollbar_log_filter_func=self.chain.config.rollbar_log_filter_func,
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
        hyperdrive_event = trade_result.hyperdrive_event
        assert hyperdrive_event is not None
        return hyperdrive_event

    ################
    # Analysis
    ################

    def get_eth(self) -> FixedPoint:
        """Returns the ETH balance of the agent.

        Returns
        -------
        FixedPoint
            Returns the ETH balance of the agent.
        """
        return FixedPoint(scaled_value=get_account_balance(self.chain._web3, self.address))

    def get_wallet(self, pool: Hyperdrive | None = None) -> HyperdriveWallet:
        """Returns the wallet object for the agent for the given hyperdrive pool.

        Arguments
        ---------
        pool: Hyperdrive | None, optional
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
        pool: Hyperdrive | None, optional
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
        pool: Hyperdrive | None, optional
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
        pool: Hyperdrive | None, optional
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
        pool: Hyperdrive | None, optional
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
        calc_pnl: bool = False,
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
        calc_pnl: bool, optional
            If the chain config's `calc_pnl` flag is False, passing in `calc_pnl=True` to this function allows for
            a one-off pnl calculation for the current positions. Ignored if the chain's `calc_pnl` flag is set to True,
            as every position snapshot will return pnl information.
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
            pool_filter=pool_filter,
            show_closed_positions=show_closed_positions,
            calc_pnl=calc_pnl,
            coerce_float=coerce_float,
        )

    def _get_positions(
        self,
        pool_filter: Hyperdrive | list[Hyperdrive],
        show_closed_positions: bool,
        calc_pnl: bool,
        coerce_float: bool,
    ) -> pd.DataFrame:
        # Query the snapshot for the most recent positions.
        if isinstance(pool_filter, list):
            hyperdrive_address = [str(pool.hyperdrive_address) for pool in pool_filter]
        else:
            hyperdrive_address = str(pool_filter.hyperdrive_address)

        position_snapshot = get_position_snapshot(
            session=self.chain.db_session,
            latest_entry=True,
            wallet_address=self.address,
            hyperdrive_address=hyperdrive_address,
            coerce_float=coerce_float,
        ).drop("id", axis=1)
        if not show_closed_positions:
            position_snapshot = position_snapshot[position_snapshot["token_balance"] != 0].reset_index(drop=True)

        # If the config's calc_pnl is not set, but we pass in `calc_pnl = True` to this function,
        # we do a one off calculation to get the pnl here.
        if not self.chain.config.calc_pnl and calc_pnl:
            if isinstance(pool_filter, list):
                out = []
                for pool in pool_filter:
                    out.append(
                        fill_pnl_values(
                            position_snapshot[position_snapshot["hyperdrive_address"] == pool.hyperdrive_address],
                            self.chain.db_session,
                            pool.interface,
                            coerce_float=coerce_float,
                        )
                    )
                position_snapshot = pd.concat(out, axis=0)
            else:
                position_snapshot = fill_pnl_values(
                    position_snapshot,
                    self.chain.db_session,
                    pool_filter.interface,
                    coerce_float=coerce_float,
                )

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

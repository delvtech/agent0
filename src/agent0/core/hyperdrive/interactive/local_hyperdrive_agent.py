"""The hyperdrive agent object that encapsulates an agent."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Type, overload

import pandas as pd
from eth_account.signers.local import LocalAccount
from eth_typing import ChecksumAddress
from fixedpointmath import FixedPoint
from hyperdrivetypes import (
    AddLiquidityEventFP,
    BaseEvent,
    CloseLongEventFP,
    CloseShortEventFP,
    OpenLongEventFP,
    OpenShortEventFP,
    RedeemWithdrawalSharesEventFP,
    RemoveLiquidityEventFP,
)

from agent0.core.base import Trade
from agent0.core.base.make_key import make_private_key
from agent0.core.hyperdrive import HyperdriveMarketAction
from agent0.core.hyperdrive.agent import TradeResult
from agent0.core.hyperdrive.crash_report import get_anvil_state_dump
from agent0.core.hyperdrive.interactive.hyperdrive import Hyperdrive
from agent0.core.hyperdrive.policies import HyperdriveBasePolicy

from .hyperdrive_agent import HyperdriveAgent
from .local_hyperdrive import LocalHyperdrive

if TYPE_CHECKING:
    from .hyperdrive import Hyperdrive
    from .local_chain import LocalChain

# TODO cleanup
# pylint: disable=too-many-arguments
# pylint: disable=too-many-positional-arguments


class LocalHyperdriveAgent(HyperdriveAgent):
    """Interactive Local Hyperdrive Agent."""

    ################
    # Initialization
    ################

    def __init__(
        self,
        base: FixedPoint,
        eth: FixedPoint,
        name: str | None,
        chain: LocalChain,
        pool: Hyperdrive | None,
        policy: Type[HyperdriveBasePolicy] | None,
        policy_config: HyperdriveBasePolicy.Config | None,
        private_key: str | None,
        public_address: str | None,
    ) -> None:
        """Constructor for the interactive hyperdrive agent.

        NOTE: this constructor shouldn't be called directly, but rather from LocalChain's
        `init_agent` method.

        Arguments
        ---------
        base: FixedPoint
            The amount of base to fund the agent with.
        eth: FixedPoint
            The amount of ETH to fund the agent with.
        name: str | None
            The name of the agent. Defaults to the wallet address.
        chain: LocalChain
            The chain object that this agent belongs to.
        pool: LocalHyperdrive | None
            An optional pool to set as the active pool.
        policy: HyperdrivePolicy | None
            An optional policy to set as the active policy.
        policy_config: HyperdrivePolicy.Config | None,
            The configuration for the attached policy.
        private_key: str | None, optional
            The private key of the associated account. Default is auto-generated.
        """

        # Explicit type checking
        if pool is not None and not isinstance(pool, LocalHyperdrive):
            raise TypeError("Pool must be an instance of LocalHyperdrive for a LocalHyperdriveAgent")

        agent_private_key = None
        if public_address is None:
            agent_private_key = make_private_key() if private_key is None else private_key

        super().__init__(
            name=name,
            chain=chain,
            pool=pool,
            policy=policy,
            policy_config=policy_config,
            private_key=agent_private_key,
            public_address=public_address,
        )

        self.chain = chain

        # Fund agent
        if eth > 0 or base > 0:
            self.add_funds(base, eth)

        # We keep track of pools this agent has been approved for
        # and call set max approval for any pools this agent has interacted with
        # This is keyed by the hyperdrive address.
        self._max_approval_pools: dict[str, bool] = {}

    def add_funds(
        self,
        base: FixedPoint | None = None,
        eth: FixedPoint | None = None,
        pool: Hyperdrive | None = None,
        signer_account: LocalAccount | None = None,
        whale_accounts: dict[ChecksumAddress, ChecksumAddress] | None = None,
    ) -> None:
        """Adds additional funds to the agent.

        .. note:: This method calls `set_anvil_account_balance` for eth and
        `mint` or account impersonation + transfers from whale accounts under the hood.
        These functions are likely to fail on any non-test network, but we add them to the
        interactive agent for convenience.

        Arguments
        ---------
        base: FixedPoint | None, optional
            The amount of base to fund the agent with. Defaults to 0.
        eth: FixedPoint | None, optional
            The amount of ETH to fund the agent with. Defaults to 0.
        pool: LocalHyperdrive | None, optional
            The pool to mint base for.
        signer_account: LocalAccount | None, optional
            The signer account to use to call `mint`. Defaults to the agent itself.
        whale_accounts: dict[ChecksumAddress, ChecksumAddress] | None, optional
            A mapping between token -> whale addresses to use to fund the fuzz agent.
            If the token is not in the mapping, will attempt to call `mint` on
            the token contract. Defaults to an empty mapping.
        """

        # Explicit type checking
        if pool is not None and not isinstance(pool, LocalHyperdrive):
            raise TypeError("Pool must be an instance of LocalHyperdrive for a LocalHyperdriveAgent")

        # Adding funds default to the deploy account
        if signer_account is None:
            signer_account = self.chain.get_deployer_account()

        super().add_funds(base, eth, pool, signer_account=signer_account, whale_accounts=whale_accounts)

    # We subclass from this function for typing
    def set_active(
        self,
        pool: Hyperdrive | None = None,
        policy: Type[HyperdriveBasePolicy] | None = None,
        policy_config: HyperdriveBasePolicy.Config | None = None,
    ) -> None:
        """Sets the active pool or policy for the agent and calls max approval for the pool.

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
        # Explicit type checking
        if pool is not None and not isinstance(pool, LocalHyperdrive):
            raise TypeError("Pool must be an instance of LocalHyperdrive for a LocalHyperdriveAgent")

        super().set_active(pool=pool, policy=policy, policy_config=policy_config)

    # Expose account and address for type narrowing in local agent
    @property
    def account(self) -> LocalAccount:
        """Returns the `LocalAccount` associated with the agent."""
        # Account should always be set in local agents
        if self._account is None:
            raise ValueError("Must initialize agent with private key to access agent's LocalAccount.")
        return self._account

    ################
    # Trades
    ################

    def _ensure_approval_set(self, pool: LocalHyperdrive) -> None:
        # Call set max approval for the pool if it hasn't been called yet.
        if pool.hyperdrive_address not in self._max_approval_pools:
            self.set_max_approval(pool)

    def _ensure_pool_type(self, pool: Hyperdrive | None) -> LocalHyperdrive | None:
        # Explicit type checking
        if pool is not None and not isinstance(pool, LocalHyperdrive):
            raise TypeError("Pool must be an instance of LocalHyperdrive for a LocalHyperdriveAgent")

        if pool is None:
            # Type narrowing
            if self._active_pool is not None:
                assert isinstance(self._active_pool, LocalHyperdrive)
            pool = self._active_pool

        return pool

    def set_max_approval(self, pool: Hyperdrive | None = None) -> None:
        """Sets the max approval to the hyperdrive contract.

        .. warning:: This sets the max approval to the underlying hyperdrive contract for
        this wallet. Do this at your own risk.

        Arguments
        ---------
        pool: Hyperdrive | None, optional
            The pool to interact with. Defaults to the active pool.
        """
        pool = self._ensure_pool_type(pool)
        if pool is None:
            raise ValueError("Setting approval requires an active pool.")
        super().set_max_approval(pool)
        # If we explicitly set approval, we mark it as such.
        self._max_approval_pools[pool.hyperdrive_address] = True
        # Setting approval mines a block, so we update the data pipeline
        pool._maybe_run_blocking_data_pipeline()  # pylint: disable=protected-access

    def open_long(self, base: FixedPoint, pool: Hyperdrive | None = None) -> OpenLongEventFP:
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
        pool = self._ensure_pool_type(pool)

        if pool is None:
            raise ValueError("Open long requires an active pool.")

        self._ensure_approval_set(pool)
        out = super().open_long(base, pool)
        pool._maybe_run_blocking_data_pipeline()  # pylint: disable=protected-access
        return out

    def close_long(self, maturity_time: int, bonds: FixedPoint, pool: Hyperdrive | None = None) -> CloseLongEventFP:
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
        # Explicit type checking
        pool = self._ensure_pool_type(pool)
        if pool is None:
            raise ValueError("Close long requires an active pool.")

        self._ensure_approval_set(pool)
        out = super().close_long(maturity_time, bonds, pool)
        pool._maybe_run_blocking_data_pipeline()  # pylint: disable=protected-access
        return out

    def open_short(self, bonds: FixedPoint, pool: Hyperdrive | None = None) -> OpenShortEventFP:
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
        # Explicit type checking
        pool = self._ensure_pool_type(pool)
        if pool is None:
            raise ValueError("Open short requires an active pool.")

        self._ensure_approval_set(pool)
        out = super().open_short(bonds, pool)
        pool._maybe_run_blocking_data_pipeline()  # pylint: disable=protected-access
        return out

    def close_short(self, maturity_time: int, bonds: FixedPoint, pool: Hyperdrive | None = None) -> CloseShortEventFP:
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
        # Explicit type checking
        pool = self._ensure_pool_type(pool)
        if pool is None:
            raise ValueError("Close short requires an active pool.")

        self._ensure_approval_set(pool)
        out = super().close_short(maturity_time, bonds, pool)
        pool._maybe_run_blocking_data_pipeline()  # pylint: disable=protected-access
        return out

    def add_liquidity(self, base: FixedPoint, pool: Hyperdrive | None = None) -> AddLiquidityEventFP:
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
        # Explicit type checking
        pool = self._ensure_pool_type(pool)
        if pool is None:
            raise ValueError("Add liquidity requires an active pool.")

        self._ensure_approval_set(pool)
        out = super().add_liquidity(base, pool)
        pool._maybe_run_blocking_data_pipeline()  # pylint: disable=protected-access
        return out

    def remove_liquidity(self, shares: FixedPoint, pool: Hyperdrive | None = None) -> RemoveLiquidityEventFP:
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
        # Explicit type checking
        pool = self._ensure_pool_type(pool)
        if pool is None:
            raise ValueError("Remove liquidity requires an active pool.")

        self._ensure_approval_set(pool)
        out = super().remove_liquidity(shares, pool)
        pool._maybe_run_blocking_data_pipeline()  # pylint: disable=protected-access
        return out

    def redeem_withdrawal_shares(
        self, shares: FixedPoint, pool: Hyperdrive | None = None
    ) -> RedeemWithdrawalSharesEventFP:
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
        # Explicit type checking
        pool = self._ensure_pool_type(pool)
        if pool is None:
            raise ValueError("Remove withdrawal shares requires an active pool.")

        self._ensure_approval_set(pool)
        out = super().redeem_withdrawal_shares(shares, pool)
        pool._maybe_run_blocking_data_pipeline()  # pylint: disable=protected-access
        return out

    def get_policy_action(self, pool: Hyperdrive | None = None) -> list[Trade[HyperdriveMarketAction]]:
        """Gets the underlying policy actions.

        Arguments
        ---------
        pool: LocalHyperdrive | None, optional
            The pool to interact with. Defaults to the active pool.

        Returns
        -------
        list[Trade[HyperdriveMarketAction]]
            The actions of the underlying policy.
        """
        # Explicit type checking
        pool = self._ensure_pool_type(pool)
        return super().get_policy_action(pool)

    def get_liquidate_action(
        self, pool: Hyperdrive | None = None, randomize: bool = False
    ) -> list[Trade[HyperdriveMarketAction]]:
        """Gets the liquidate actions for this agent.

        Arguments
        ---------
        pool: LocalHyperdrive | None, optional
            The pool to interact with. Defaults to the active pool.
        randomize: bool, optional
            Whether to randomize the order of the liquidate actions.

        Returns
        -------
        list[Trade[HyperdriveMarketAction]]
            The liquidate actions of the underlying policy.
        """
        # Explicit type checking
        pool = self._ensure_pool_type(pool)
        return super().get_liquidate_action(pool, randomize)

    def execute_action(
        self, actions: list[Trade[HyperdriveMarketAction]], pool: Hyperdrive | None = None
    ) -> list[BaseEvent]:
        """Executes the specified actions.

        Arguments
        ---------
        actions: list[Trade[HyperdriveMarketAction]]
            The actions to execute. This is the return value of `get_policy_action` or `get_liquidate_action`.
        pool: LocalHyperdrive | None, optional
            The pool to interact with. Defaults to the active pool.

        Returns
        -------
        list[BaseHyperdriveEvent]
            Events of the executed actions.
        """
        # Explicit type checking
        pool = self._ensure_pool_type(pool)
        if pool is None:
            raise ValueError("Executing action requires an active pool.")
        self._ensure_approval_set(pool)
        out = super().execute_action(actions, pool)
        pool._maybe_run_blocking_data_pipeline()  # pylint: disable=protected-access
        return out

    # Helper functions for trades

    @overload
    def _handle_trade_result(
        self, trade_result: TradeResult, pool: Hyperdrive, always_throw_exception: Literal[True]
    ) -> BaseEvent: ...

    @overload
    def _handle_trade_result(
        self, trade_result: TradeResult, pool: Hyperdrive, always_throw_exception: Literal[False]
    ) -> BaseEvent | None: ...

    def _handle_trade_result(
        self, trade_result: TradeResult, pool: Hyperdrive, always_throw_exception: bool
    ) -> BaseEvent | None:
        # We add specific data to the trade result from interactive hyperdrive
        if not trade_result.trade_successful:
            assert trade_result.exception is not None
            # TODO we likely want to explicitly check for slippage here and not
            # get anvil state dump if it's a slippage error and the user wants to
            # ignore slippage errors
            if self.chain.config.log_anvil_state_dump:
                trade_result.anvil_state = get_anvil_state_dump(self.chain._web3)  # pylint: disable=protected-access
            if self.chain.config.crash_log_ticker:
                if trade_result.additional_info is None:
                    trade_result.additional_info = {"trade_events": self.get_trade_events()}
                else:
                    trade_result.additional_info["trade_events"] = self.get_trade_events()

        # This check is necessary for subclass overloading and typing,
        # as types are narrowed based on the literal `always_throw_exception`
        if always_throw_exception:
            return super()._handle_trade_result(trade_result, pool, always_throw_exception)
        return super()._handle_trade_result(trade_result, pool, always_throw_exception)

    ################
    # Analysis
    ################

    def get_positions(
        self,
        pool_filter: Hyperdrive | list[Hyperdrive] | None = None,
        show_closed_positions: bool = False,
        calc_pnl: bool = False,
        coerce_float: bool = False,
        registry_address: str | None = None,
    ) -> pd.DataFrame:
        """Returns all of the agent's positions across all hyperdrive pools.

        Arguments
        ---------
        pool_filter: LocalHyperdrive | list[LocalHyperdrive], optional
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
        registry_address: str, optional
            Must be None when calling from local hyperdrive agent.

        Returns
        -------
        pd.DataFrame
            The agent's positions across all hyperdrive pools.
        """

        if registry_address is not None:
            raise ValueError("registry_address not used with local agents")

        pool_filter_arg: Hyperdrive | list[Hyperdrive]
        # Explicit type checking
        if pool_filter is not None:
            if isinstance(pool_filter, list):
                for pool in pool_filter:
                    if not isinstance(pool, LocalHyperdrive):
                        raise TypeError("Pool must be an instance of LocalHyperdrive for a LocalHyperdriveAgent")
            elif not isinstance(pool_filter, LocalHyperdrive):
                raise TypeError("Pool must be an instance of LocalHyperdrive for a LocalHyperdriveAgent")
            pool_filter_arg = pool_filter
        else:
            # TODO Typing is complaining list[LocalHyperdrive] is not a list[Hyperdrive]
            # but LocalHyperdrive is a subclass of Hyperdrive
            # Proper fix here is to switch `list` to `Sequence`
            pool_filter_arg = self.chain._deployed_hyperdrive_pools  # type: ignore # pylint: disable=protected-access

        return self._get_positions(
            pool_filter=pool_filter_arg,
            show_closed_positions=show_closed_positions,
            calc_pnl=calc_pnl,
            coerce_float=coerce_float,
        )

    def get_trade_events(
        self,
        pool_filter: Hyperdrive | list[Hyperdrive] | None = None,
        all_token_deltas: bool = False,
        coerce_float: bool = False,
    ) -> pd.DataFrame:
        """Returns the agent's current wallet.

        Arguments
        ---------
        pool_filter : LocalHyperdrive | list[LocalHyperdrive] | None, optional
            The hyperdrive pool(s) to get trade events from. If None, will retrieve all events from
            all pools.
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
        # Explicit type checking
        # Explicit type checking
        if pool_filter is not None:
            if isinstance(pool_filter, list):
                for pool in pool_filter:
                    if not isinstance(pool, LocalHyperdrive):
                        raise TypeError("Pool must be an instance of LocalHyperdrive for a LocalHyperdriveAgent")
            elif not isinstance(pool_filter, LocalHyperdrive):
                raise TypeError("Pool must be an instance of LocalHyperdrive for a LocalHyperdriveAgent")
        return self._get_trade_events(
            pool_filter=pool_filter, all_token_deltas=all_token_deltas, coerce_float=coerce_float
        )

    def _sync_events(self, pool: Hyperdrive | list[Hyperdrive]) -> None:
        # No need to sync in local hyperdrive, we sync when we run the data pipeline
        pass

    def _sync_snapshot(self, pool: Hyperdrive | list[Hyperdrive]) -> None:
        # No need to sync in local hyperdrive, we sync when we run the data pipeline
        pass

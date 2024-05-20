"""The hyperdrive agent object that encapsulates an agent."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Type, overload

from eth_account.signers.local import LocalAccount
from fixedpointmath import FixedPoint

from agent0.core.base.make_key import make_private_key
from agent0.core.hyperdrive import HyperdrivePolicyAgent, TradeResult, TradeStatus
from agent0.core.hyperdrive.crash_report import get_anvil_state_dump
from agent0.core.hyperdrive.policies import HyperdriveBasePolicy
from agent0.ethpy.hyperdrive import AssetIdPrefix, ReceiptBreakdown, encode_asset_id

from .event_types import (
    AddLiquidity,
    CloseLong,
    CloseShort,
    OpenLong,
    OpenShort,
    RedeemWithdrawalShares,
    RemoveLiquidity,
)
from .hyperdrive_agent import HyperdriveAgent

if TYPE_CHECKING:
    from .local_hyperdrive import LocalHyperdrive


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
        pool: LocalHyperdrive,
        policy: Type[HyperdriveBasePolicy] | None,
        policy_config: HyperdriveBasePolicy.Config | None,
        private_key: str | None = None,
    ) -> None:
        """Constructor for the interactive hyperdrive agent.

        NOTE: this constructor shouldn't be called directly, but rather from LocalHyperdrive's
        `init_agent` method.

        Arguments
        ---------
        base: FixedPoint
            The amount of base to fund the agent with.
        eth: FixedPoint
            The amount of ETH to fund the agent with.
        name: str | None
            The name of the agent. Defaults to the wallet address.
        pool: LocalHyperdrive
            The pool object that this agent belongs to.
        policy: HyperdrivePolicy | None
            An optional policy to attach to this agent.
        policy_config: HyperdrivePolicy.Config | None,
            The configuration for the attached policy.
        private_key: str | None, optional
            The private key of the associated account. Default is auto-generated.
        """
        # pylint: disable=too-many-arguments
        agent_private_key = make_private_key() if private_key is None else private_key

        super().__init__(
            name=name, pool=pool, policy=policy, policy_config=policy_config, private_key=agent_private_key
        )

        # Type narrow to the local hyperdrive type
        self._pool: LocalHyperdrive = pool

        # Update wallet to agent's previous budget
        if private_key is not None:  # address already existed
            self.agent.wallet.balance.amount = self._pool.interface.get_eth_base_balances(self.agent)[1]
            self.agent.wallet.lp_tokens = FixedPoint(
                scaled_value=self._pool.interface.hyperdrive_contract.functions.balanceOf(
                    encode_asset_id(AssetIdPrefix.LP, 0),
                    self.agent.checksum_address,
                ).call()
            )
            self.agent.wallet.withdraw_shares = FixedPoint(
                scaled_value=self._pool.interface.hyperdrive_contract.functions.balanceOf(
                    encode_asset_id(AssetIdPrefix.WITHDRAWAL_SHARE, 0),
                    self.agent.checksum_address,
                ).call()
            )

        # Fund agent
        if eth > 0 or base > 0:
            self.add_funds(base, eth)

        # Establish max approval for the hyperdrive contract
        self.set_max_approval()

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
        # Adding funds default to the deploy account
        if signer_account is None:
            signer_account = self._pool._deployed_hyperdrive.deploy_account  # pylint: disable=protected-access

        super().add_funds(base, eth, signer_account=signer_account)

        # Adding funds mines a block, so we run data pipeline here
        self._pool._run_blocking_data_pipeline()  # pylint: disable=protected-access

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
        out = super().open_long(base)
        self._pool._run_blocking_data_pipeline()  # pylint: disable=protected-access
        return out

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
        out = super().close_long(maturity_time, bonds)
        self._pool._run_blocking_data_pipeline()  # pylint: disable=protected-access
        return out

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
        out = super().open_short(bonds)
        self._pool._run_blocking_data_pipeline()  # pylint: disable=protected-access
        return out

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
        out = super().close_short(maturity_time, bonds)
        self._pool._run_blocking_data_pipeline()  # pylint: disable=protected-access
        return out

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
        out = super().add_liquidity(base)
        self._pool._run_blocking_data_pipeline()  # pylint: disable=protected-access
        return out

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
        out = super().remove_liquidity(shares)
        self._pool._run_blocking_data_pipeline()  # pylint: disable=protected-access
        return out

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
        out = super().redeem_withdraw_share(shares)
        self._pool._run_blocking_data_pipeline()  # pylint: disable=protected-access
        return out

    def execute_policy_action(
        self,
    ) -> list[OpenLong | OpenShort | CloseLong | CloseShort | AddLiquidity | RemoveLiquidity | RedeemWithdrawalShares]:
        """Executes the underlying policy action (if set).

        Returns
        -------
        list[OpenLong | OpenShort | CloseLong | CloseShort | AddLiquidity | RemoveLiquidity | RedeemWithdrawalShares]
            Events of the executed actions.
        """
        out = super().execute_policy_action()
        self._pool._run_blocking_data_pipeline()  # pylint: disable=protected-access
        return out

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
        out = super().liquidate(randomize)
        self._pool._run_blocking_data_pipeline()  # pylint: disable=protected-access
        return out

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
        # We add specific data to the trade result from interactive hyperdrive
        if trade_result.status == TradeStatus.FAIL:
            assert trade_result.exception is not None
            # TODO we likely want to explicitly check for slippage here and not
            # get anvil state dump if it's a slippage error and the user wants to
            # ignore slippage errors
            trade_result.anvil_state = get_anvil_state_dump(self._pool.interface.web3)
            if self._pool.config.crash_log_ticker:
                if trade_result.additional_info is None:
                    trade_result.additional_info = {"trade_events": self.get_trade_events()}
                else:
                    trade_result.additional_info["trade_events"] = self.get_trade_events()

        # This check is necessary for subclass overloading and typing,
        # as types are narrowed based on the literal `always_throw_exception`
        if always_throw_exception:
            return super()._handle_trade_result(trade_result, always_throw_exception)
        return super()._handle_trade_result(trade_result, always_throw_exception)

    ################
    # Analysis
    ################

    def _sync_events(self, agent: HyperdrivePolicyAgent) -> None:
        # No need to sync in local hyperdrive, we sync when we run the data pipeline
        pass

    def _sync_snapshot(self, agent: HyperdrivePolicyAgent) -> None:
        # No need to sync in local hyperdrive, we sync when we run the data pipeline
        pass

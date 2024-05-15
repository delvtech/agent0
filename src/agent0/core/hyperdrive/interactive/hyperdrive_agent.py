"""The hyperdrive agent object that encapsulates an agent."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
from fixedpointmath import FixedPoint

if TYPE_CHECKING:
    from typing import Type

    from eth_typing import ChecksumAddress

    from agent0.core.hyperdrive import HyperdriveWallet
    from agent0.core.hyperdrive.policies import HyperdriveBasePolicy

    from .event_types import (
        AddLiquidity,
        CloseLong,
        CloseShort,
        OpenLong,
        OpenShort,
        RedeemWithdrawalShares,
        RemoveLiquidity,
    )
    from .hyperdrive import Hyperdrive

# We keep this class bare bones, while we want the logic functions in InteractiveHyperdrive to be private
# Hence, we call protected class methods in this class.
# pylint: disable=protected-access


class HyperdriveAgent:
    """Interactive Hyperdrive Agent.
    This class is barebones with documentation, will just call the corresponding function
    in the interactive hyperdrive class to keep all logic in the same place. Adding these
    wrappers here for ease of use.
    """

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
        self._pool = pool
        self.agent = self._pool._init_agent(name, policy, policy_config, private_key)

    @property
    def checksum_address(self) -> ChecksumAddress:
        """Return the checksum address of the account."""
        return self.agent.checksum_address

    @property
    def policy_done_trading(self) -> bool:
        """Return whether the agent's policy is done trading."""
        return self.agent.done_trading

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
        return self._pool._open_long(self.agent, base)

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
        return self._pool._close_long(self.agent, maturity_time, bonds)

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
        return self._pool._open_short(self.agent, bonds)

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
        return self._pool._close_short(self.agent, maturity_time, bonds)

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
        return self._pool._add_liquidity(self.agent, base)

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
        return self._pool._remove_liquidity(self.agent, shares)

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
        return self._pool._redeem_withdraw_share(self.agent, shares)

    def execute_policy_action(
        self,
    ) -> list[OpenLong | OpenShort | CloseLong | CloseShort | AddLiquidity | RemoveLiquidity | RedeemWithdrawalShares]:
        """Executes the underlying policy action (if set).

        Returns
        -------
        list[OpenLong | OpenShort | CloseLong | CloseShort | AddLiquidity | RemoveLiquidity | RedeemWithdrawalShares]
            Events of the executed actions.
        """
        return self._pool._execute_policy_action(self.agent)

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
        return self._pool._liquidate(self.agent, randomize)

    def add_funds(self, base: FixedPoint | None = None, eth: FixedPoint | None = None) -> None:
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
        """
        if base is None:
            base = FixedPoint(0)
        if eth is None:
            eth = FixedPoint(0)
        self._pool._add_funds(self.agent, base, eth)

    def set_max_approval(self) -> None:
        """Sets the max approval to the hyperdrive contract.

        .. warning:: This sets the max approval to the underlying hyperdrive contract for
        this wallet. Do this at your own risk.

        """
        self._pool._set_max_approval(self.agent)

    def get_positions(self, filter_zero_balance: bool = True, coerce_float: bool = False) -> pd.DataFrame:
        """Returns all of the agent's positions across all hyperdrive pools.

        Arguments
        ---------
        filter_zero_balance: bool, optional
            Whether to filter out positions with zero balance.
            When True, will only return currently open positions. Useful for gathering currently open positions.
            When False, will also return any closed positions. Useful for calculating overall pnl of all positions.
        coerce_float: bool, optional
            Whether to coerce underlying Decimal values to float when as_df is True. Defaults to False.

        Returns
        -------
        pd.DataFrame
            The agent's positions across all hyperdrive pools.
        """
        return self._pool._get_positions(self.agent, filter_zero_balance=filter_zero_balance, coerce_float=coerce_float)

    def get_wallet(self) -> HyperdriveWallet:
        """Returns the wallet object for the agent for the given hyperdrive pool.

        TODO this function will eventually use the active pool or take a pool as an argument
        once agent gets detached from the pool.

        Returns
        -------
        HyperdriveWallet
            Returns the HyperdriveWallet object for the given pool.
        """

        # Update the db with this wallet
        return self._pool._get_wallet(self.agent)

    def get_trade_events(self, all_token_deltas: bool = False) -> pd.DataFrame:
        """Returns the agent's current wallet.

        Arguments
        ---------
        all_token_deltas: bool, optional
            When removing liquidity that results in withdrawal shares, the events table returns
            two entries for this transaction to keep track of token deltas (one for lp tokens and
            one for withdrawal shares). If this flag is true, will return all entries in the table,
            which is useful for calculating token positions. If false, will drop the duplicate
            withdrawal share entry (useful for returning a ticker).

        Returns
        -------
        HyperdriveWallet
            The agent's current wallet.
        """

        # Update the db with this wallet
        return self._pool._get_trade_events(self.agent, all_token_deltas)

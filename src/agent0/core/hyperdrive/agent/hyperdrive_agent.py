"""Empty accounts for engaging with smart contracts"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, TypeVar

from fixedpointmath import FixedPoint

from agent0.core.base import EthAgent, MarketType
from agent0.core.base.policies import BasePolicy
from agent0.ethpy.hyperdrive.interface import HyperdriveReadInterface

from .hyperdrive_actions import (
    HyperdriveMarketAction,
    close_long_trade,
    close_short_trade,
    redeem_withdraw_shares_trade,
    remove_liquidity_trade,
)
from .hyperdrive_wallet import HyperdriveWallet

if TYPE_CHECKING:
    from eth_account.signers.local import LocalAccount

    from agent0.core.base import Trade


Policy = TypeVar("Policy", bound=BasePolicy)


class HyperdriveAgent(EthAgent[Policy, HyperdriveReadInterface, HyperdriveMarketAction]):
    r"""Enact policies on smart contracts and tracks wallet state

    .. todo::
        should be able to get the HyperdriveMarketAction type from the HyperdriveInterface
    """

    def __init__(self, account: LocalAccount, initial_budget: FixedPoint | None = None, policy: Policy | None = None):
        """Initialize an agent and wallet account

        Arguments
        ---------
        account: LocalAccount
            A Web3 local account for storing addresses & signing transactions.
        initial_budget: FixedPoint | None, optional
            The initial budget for the wallet bookkeeping.
        policy: Policy | None, optional
            Policy for producing agent actions.
            If None, then a policy that executes no actions is used.

        """
        super().__init__(account, initial_budget, policy)
        # Reinitialize the wallet to the subclass
        self.wallet = HyperdriveWallet(address=self.wallet.address, balance=self.wallet.balance)

    def get_liquidation_trades(
        self, interface: HyperdriveReadInterface, randomize_trades: bool, interactive_mode: bool
    ) -> list[Trade[HyperdriveMarketAction]]:
        """List of trades that liquidate all open positions

        Arguments
        ---------
        interface: HyperdriveReadInterface
            The interface for the market on which this agent will be executing trades (MarketActions)
        randomize_trades: bool
            If True, will randomize the order of liquidation trades
        interactive_mode: bool
            If True, won't set the done trading flag

        Returns
        -------
        list[Trade]
            List of trades to execute in order to liquidate positions where applicable
        """
        minimum_transaction_amount = interface.pool_config.minimum_transaction_amount
        action_list = []
        for maturity_time, long in self.wallet.longs.items():
            logging.debug("closing long: maturity_time=%g, balance=%s", maturity_time, long)
            if long.balance > minimum_transaction_amount:
                action_list.append(close_long_trade(long.balance, maturity_time))
        for maturity_time, short in self.wallet.shorts.items():
            logging.debug(
                "closing short: maturity_time=%g, balance=%s",
                maturity_time,
                short.balance,
            )
            if short.balance > minimum_transaction_amount:
                action_list.append(close_short_trade(short.balance, maturity_time))
        if self.wallet.lp_tokens > minimum_transaction_amount:
            logging.debug("closing lp: lp_tokens=%s", self.wallet.lp_tokens)
            action_list.append(remove_liquidity_trade(self.wallet.lp_tokens))

        # We use the underlying policies rng object for randomizing liquidation trades
        if randomize_trades:
            action_list = self.policy.rng.permutation(action_list).tolist()

        # Always set withdrawal shares to be last, as we need trades to close first before withdrawing
        if self.wallet.withdraw_shares > 0:
            logging.debug("closing withdrawal: withdrawal_tokens=%s", self.wallet.withdraw_shares)
            action_list.append(redeem_withdraw_shares_trade(self.wallet.withdraw_shares))

        # If interactive mode set to true, never set done_trading
        # If no more trades in wallet, set the done trading flag
        if not interactive_mode and len(action_list) == 0:
            self.done_trading = True

        return action_list

    def get_trades(self, interface: HyperdriveReadInterface) -> list[Trade[HyperdriveMarketAction]]:
        """Helper function for computing a agent trade

        Arguments
        ---------
        interface: HyperdriveReadInterface
            The interface for the market on which this agent will be executing trades (MarketActions)

        Returns
        -------
        list[Trade]
            List of Trade type objects that represent the trades to be made by this agent
        """
        # get the action list from the policy
        # TODO: Deprecate the old wallet in favor of this new one
        actions: list[Trade[HyperdriveMarketAction]]
        actions, self.done_trading = self.policy.action(interface, self.wallet)
        # edit each action in place
        for action in actions:
            if action.market_type == MarketType.HYPERDRIVE and action.market_action.maturity_time is None:
                if action.market_action.trade_amount <= 0:
                    raise ValueError("Trade amount cannot be zero or negative.")
        return actions

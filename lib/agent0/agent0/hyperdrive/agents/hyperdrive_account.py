"""Empty accounts for engaging with smart contracts"""
from __future__ import annotations

import logging
from typing import TypeVar

from eth_account.signers.local import LocalAccount
from ethpy.hyperdrive.interface import HyperdriveReadInterface
from fixedpointmath import FixedPoint

from agent0.base import MarketType, Trade
from agent0.base.agents import EthAgent
from agent0.base.policies import BasePolicy
from agent0.hyperdrive.state import HyperdriveMarketAction, HyperdriveWallet

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

    def get_liquidation_trades(self, interface: HyperdriveReadInterface) -> list[Trade[HyperdriveMarketAction]]:
        """List of trades that liquidate all open positions

        Arguments
        ---------
        interface: HyperdriveReadInterface
            The interface for the market on which this agent will be executing trades (MarketActions)

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
                action_list.append(interface.close_long_trade(long.balance, maturity_time))
        for maturity_time, short in self.wallet.shorts.items():
            logging.debug(
                "closing short: maturity_time=%g, balance=%s",
                maturity_time,
                short.balance,
            )
            if short.balance > minimum_transaction_amount:
                action_list.append(interface.close_short_trade(short.balance, maturity_time))
        if self.wallet.lp_tokens > minimum_transaction_amount:
            logging.debug("closing lp: lp_tokens=%s", self.wallet.lp_tokens)
            action_list.append(interface.remove_liquidity_trade(self.wallet.lp_tokens))
        if self.wallet.withdraw_shares > minimum_transaction_amount:
            logging.debug("closing lp: lp_tokens=%s", self.wallet.lp_tokens)
            action_list.append(interface.redeem_withdraw_shares_trade(self.wallet.withdraw_shares))

        # If no more trades in wallet, set the done trading flag
        if len(action_list) == 0:
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

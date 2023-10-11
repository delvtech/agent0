"""Empty accounts for engaging with smart contracts"""
from __future__ import annotations

import logging
from typing import TypeVar

from agent0.base import Quantity, TokenType
from agent0.base.agents import EthAgent
from agent0.base.policies import BasePolicy
from agent0.hyperdrive.state import HyperdriveActionType, HyperdriveMarketAction, HyperdriveWallet
from elfpy.types import MarketType, Trade
from eth_account.signers.local import LocalAccount
from ethpy.hyperdrive import HyperdriveInterface
from hexbytes import HexBytes

Policy = TypeVar("Policy", bound=BasePolicy)


class HyperdriveAgent(EthAgent[Policy, HyperdriveInterface, HyperdriveMarketAction]):
    r"""Enact policies on smart contracts and tracks wallet state

    .. todo::
        should be able to get the HyperdriveMarketAction type from the HyperdriveInterface
    """

    def __init__(self, account: LocalAccount, policy: Policy | None = None):
        """Initialize an agent and wallet account

        Arguments
        ----------
        account : LocalAccount
            A Web3 local account for storing addresses & signing transactions.
        policy : Policy
            Elfpy policy for producing agent actions.
            If None, then a policy that executes no actions is used.

        Note
        ----
        If you wish for your private key to be generated, then you can do so with:

        .. code-block:: python

            >>> from eth_account.account import Account
            >>> from elfpy.eth.accounts.eth_account import EthAgent
            >>> agent = EthAgent(Account().create("CHECKPOINT_BOT"))

        Alternatively, you can also use the Account api to provide a pre-generated key:

        .. code-block:: python

            >>> from eth_account.account import Account
            >>> from elfpy.eth.accounts.eth_account import EthAgent
            >>> agent = EthAgent(Account().from_key(agent_private_key))

        The EthAgent has the same properties as a Web3 LocalAgent.
        For example, you can get public and private keys as well as the address:

            .. code-block:: python

                >>> address = agent.address
                >>> checksum_address = agent.checksum_address
                >>> public_key = agent.key
                >>> private_key = bytes(agent)

        """
        super().__init__(account, policy)
        self.wallet = HyperdriveWallet(
            address=HexBytes(self.address),
            balance=Quantity(amount=self.policy.budget, unit=TokenType.BASE),
        )

    def liquidation_trades(self) -> list[Trade[HyperdriveMarketAction]]:
        """List of trades that liquidate all open positions

        Returns
        -------
        list[Trade]
            List of trades to execute in order to liquidate positions where applicable
        """
        action_list = []
        for maturity_time, long in self.wallet.longs.items():
            logging.debug("closing long: maturity_time=%g, balance=%s", maturity_time, long)
            if long.balance > 0:
                action_list.append(
                    Trade(
                        market_type=MarketType.HYPERDRIVE,
                        market_action=HyperdriveMarketAction(
                            action_type=HyperdriveActionType.CLOSE_LONG,
                            trade_amount=long.balance,
                            wallet=self.wallet,
                            maturity_time=maturity_time,
                        ),
                    )
                )
        for maturity_time, short in self.wallet.shorts.items():
            logging.debug("closing short: maturity_time=%g, balance=%s", maturity_time, short.balance)
            if short.balance > 0:
                action_list.append(
                    Trade(
                        market_type=MarketType.HYPERDRIVE,
                        market_action=HyperdriveMarketAction(
                            action_type=HyperdriveActionType.CLOSE_SHORT,
                            trade_amount=short.balance,
                            wallet=self.wallet,
                            maturity_time=maturity_time,
                        ),
                    )
                )
        if self.wallet.lp_tokens > 0:
            logging.debug("closing lp: lp_tokens=%s", self.wallet.lp_tokens)
            action_list.append(
                Trade(
                    market_type=MarketType.HYPERDRIVE,
                    market_action=HyperdriveMarketAction(
                        action_type=HyperdriveActionType.REMOVE_LIQUIDITY,
                        trade_amount=self.wallet.lp_tokens,
                        wallet=self.wallet,
                    ),
                )
            )
        if self.wallet.withdraw_shares > 0:
            logging.debug("closing lp: lp_tokens=%s", self.wallet.lp_tokens)
            action_list.append(
                Trade(
                    market_type=MarketType.HYPERDRIVE,
                    market_action=HyperdriveMarketAction(
                        action_type=HyperdriveActionType.REDEEM_WITHDRAW_SHARE,
                        trade_amount=self.wallet.withdraw_shares,
                        wallet=self.wallet,
                    ),
                )
            )

        # If no more trades in wallet, set the done trading flag
        if len(action_list) == 0:
            self.done_trading = True

        return action_list

    def get_trades(self, interface: HyperdriveInterface) -> list[Trade[HyperdriveMarketAction]]:
        """Helper function for computing a agent trade

        Arguments
        ----------
        interface : HyperdriveInterface
            The market on which this agent will be executing trades (MarketActions)

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
                # TODO market latest_checkpoint_time and position_duration should be in ints
                action.market_action.maturity_time = (
                    interface.seconds_since_latest_checkpoint + interface.pool_config["positionDuration"]
                )
                if action.market_action.trade_amount <= 0:
                    raise ValueError("Trade amount cannot be zero or negative.")
        return actions

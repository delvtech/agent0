"""Empty accounts for engaging with smart contracts"""
from __future__ import annotations

import logging
from typing import Generic, TypeVar

from eth_account.signers.local import LocalAccount
from eth_typing import ChecksumAddress
from hexbytes import HexBytes
from web3 import Web3

from elfpy.agents.policies import BasePolicy, NoActionPolicy
from elfpy.markets.hyperdrive import HyperdriveMarket, HyperdriveMarketAction, MarketActionType
from elfpy.types import MarketType, Quantity, TokenType, Trade

from .eth_wallet import EthWallet

Policy = TypeVar("Policy", bound=BasePolicy)
Market = TypeVar(
    "Market", bound=HyperdriveMarket
)  # TODO: I don't know how to impose that this is a HyperdriveMarket at times, but BaseMarket in general
MarketAction = TypeVar(
    "MarketAction", bound=HyperdriveMarketAction
)  # TODO: should be able to infer this from the market


class EthAgent(LocalAccount, Generic[Policy, Market, MarketAction]):
    r"""Enact policies on smart contracts and tracks wallet state"""

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
        if policy is None:
            self.policy = NoActionPolicy()
        else:
            self.policy = policy
        super().__init__(account._key_obj, account._publicapi)  # pylint: disable=protected-access
        self.wallet = EthWallet(
            address=HexBytes(self.address),
            balance=Quantity(amount=self.policy.budget, unit=TokenType.BASE),
        )

    @property
    def checksum_address(self) -> ChecksumAddress:
        """Return the checksum address of the account"""
        return Web3.to_checksum_address(self.address)

    @property
    def liquidation_trades(self) -> list[Trade[MarketAction]]:
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
                # TODO: Deprecate the old wallet in favor of this new one
                action_list.append(
                    Trade(
                        market_type=MarketType.HYPERDRIVE,
                        market_action=HyperdriveMarketAction(
                            action_type=MarketActionType.CLOSE_LONG,
                            trade_amount=long.balance,
                            wallet=self.wallet,  # type: ignore
                            maturity_time=maturity_time,
                        ),
                    )
                )
        for maturity_time, short in self.wallet.shorts.items():
            logging.debug("closing short: maturity_time=%g, balance=%s", maturity_time, short.balance)
            if short.balance > 0:
                # TODO: Deprecate the old wallet in favor of this new one
                action_list.append(
                    Trade(
                        market_type=MarketType.HYPERDRIVE,
                        market_action=HyperdriveMarketAction(
                            action_type=MarketActionType.CLOSE_SHORT,
                            trade_amount=short.balance,
                            wallet=self.wallet,  # type: ignore
                            maturity_time=maturity_time,
                        ),
                    )
                )
        if self.wallet.lp_tokens > 0:
            logging.debug("closing lp: lp_tokens=%s", self.wallet.lp_tokens)
            # TODO: Deprecate the old wallet in favor of this new one
            action_list.append(
                Trade(
                    market_type=MarketType.HYPERDRIVE,
                    market_action=HyperdriveMarketAction(
                        action_type=MarketActionType.REMOVE_LIQUIDITY,
                        trade_amount=self.wallet.lp_tokens,
                        wallet=self.wallet,  # type: ignore
                    ),
                )
            )
        return action_list

    def get_trades(self, market: Market) -> list[Trade[MarketAction]]:
        """Helper function for computing a agent trade

        Arguments
        ----------
        market : Market
            The market on which this agent will be executing trades (MarketActions)

        Returns
        -------
        list[Trade]
            List of Trade type objects that represent the trades to be made by this agent
        """
        # get the action list from the policy
        # TODO: Deprecate the old wallet in favor of this new one
        actions: list[Trade[MarketAction]] = self.policy.action(market, self.wallet)  # type: ignore
        # edit each action in place
        for action in actions:
            if action.market_type == MarketType.HYPERDRIVE and action.market_action.maturity_time is None:
                action.market_action.maturity_time = market.latest_checkpoint_time + market.position_duration.seconds
                if action.market_action.trade_amount <= 0:
                    raise ValueError("Trade amount cannot be zero or negative.")
        return actions

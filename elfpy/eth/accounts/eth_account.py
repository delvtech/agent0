"""Empty accounts for engaging with smart contracts"""
from __future__ import annotations

import logging
from typing import Generic, TypeVar

from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import ChecksumAddress
from web3 import Web3

from elfpy.agents.agent import Agent
from elfpy.agents.policies import BasePolicy, NoActionPolicy
from elfpy.markets.base import BaseMarket
from elfpy.markets.hyperdrive import HyperdriveMarketAction, MarketActionType
from elfpy.types import MarketType, Quantity, TokenType, Trade
from elfpy.wallet.wallet import Wallet

Policy = TypeVar("Policy", bound=BasePolicy)
Market = TypeVar("Market", bound=BaseMarket)
MarketAction = TypeVar("MarketAction")  # TODO: should be able to infer this from the market


class EthAgent(LocalAccount, Generic[Policy, Market, MarketAction]):
    r"""Enacts policies on smart contracts and tracks wallet state

    Arguments
    ----------
    policy : BasePolicy
        Elfpy policy for producing agent actions
    private_key : str | None, optional
        Private key for constructing the agent's blockchain wallet.
        If None, then a random private key is created
    """

    def __init__(self, policy: Policy | None = None, private_key: str | None = None):
        """Initialize an agent and wallet account"""
        if policy is None:
            self.policy: BasePolicy = NoActionPolicy()
        else:
            self.policy: Policy = policy
        if private_key is None:
            account: LocalAccount = Account().create()
            private_key = account._key_obj  # pylint: disable=protected-access
        else:
            account: LocalAccount = Account().from_key(private_key)
        super().__init__(private_key, account)
        self.wallet: Wallet = Wallet(
            address=str(self.checksum_address), balance=Quantity(amount=self.policy.budget, unit=TokenType.BASE)
        )

    @property
    def checksum_address(self) -> ChecksumAddress:
        """Return the checksum address of the account"""
        return Web3.to_checksum_address(self.address)

    @property
    def _private_key(self) -> str:
        logging.warning("accessing agent private key")
        return str(self._key_obj)  # pylint: disable=protected-access

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
                action_list.append(
                    Trade(
                        market_type=MarketType.HYPERDRIVE,
                        market_action=HyperdriveMarketAction(
                            action_type=MarketActionType.CLOSE_LONG,
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
                            action_type=MarketActionType.CLOSE_SHORT,
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
                        action_type=MarketActionType.REMOVE_LIQUIDITY,
                        trade_amount=self.wallet.lp_tokens,
                        wallet=self.wallet,
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
        actions: list[Trade] = self.policy.action(market, self.wallet)  # get the action list from the policy
        for action in actions:  # edit each action in place
            if action.market == MarketType.HYPERDRIVE and action.trade.maturity_time is None:
                action.trade.maturity_time = market.latest_checkpoint_time + market.position_duration
                if action.trade.trade_amount <= 0:
                    raise ValueError("Trade amount cannot be zero or negative.")
        return actions


class EthAccount:
    """Web3 account that has helper functions & associated funding source"""

    # TODO: We should be adding more methods to this class.
    # If not, we can delete it at the end of the refactor.
    # pylint: disable=too-few-public-methods

    def __init__(self, agent: Agent | None = None, private_key: str | None = None, extra_entropy: str = "TEST ACCOUNT"):
        """Initialize an account"""
        if private_key is None:
            self.account: LocalAccount = Account().create(extra_entropy=extra_entropy)
        else:
            self.account: LocalAccount = Account().from_key(private_key)
        self._agent = agent

    @property
    def agent(self) -> Agent:
        """Return the elfpy agent object if it exists, otherwise throw an error"""
        if self._agent is None:
            raise AttributeError(f"EthAccount with address {self.account.address} has no Agent member")
        return self._agent

    @property
    def checksum_address(self) -> ChecksumAddress:
        """Return the checksum address of the account"""
        return Web3.to_checksum_address(self.account.address)

    @property
    def _private_key(self) -> str:
        logging.warning("accessing agent private key")
        return str(self.account._private_key)  # pylint: disable=protected-access

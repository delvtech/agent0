"""Empty accounts for engaging with smart contracts"""
from __future__ import annotations

from typing import Generic, TypeVar

from agent0.base.accounts import EthWallet
from agent0.base.policies import BasePolicy, NoActionPolicy
from elfpy.types import Quantity, TokenType, Trade
from eth_account.signers.local import LocalAccount
from eth_typing import ChecksumAddress
from hexbytes import HexBytes
from web3 import Web3

Policy = TypeVar("Policy", BasePolicy)
Market = TypeVar("Market")
MarketAction = TypeVar("MarketAction")


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
        return self.policy.action(market, self.wallet)

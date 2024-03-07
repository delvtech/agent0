"""Empty accounts for engaging with smart contracts"""

from __future__ import annotations

from typing import Generic, TypeVar

from eth_account.signers.local import LocalAccount
from eth_typing import ChecksumAddress
from fixedpointmath import FixedPoint
from hexbytes import HexBytes
from web3 import Web3

from agent0.core.base.policies import BasePolicy, NoActionPolicy
from agent0.core.base.types import Quantity, TokenType, Trade

from .eth_wallet import EthWallet

Policy = TypeVar("Policy", bound=BasePolicy)
MarketInterface = TypeVar("MarketInterface")
MarketAction = TypeVar("MarketAction")


class EthAgent(LocalAccount, Generic[Policy, MarketInterface, MarketAction]):
    r"""Enact policies on smart contracts and tracks wallet state"""

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

        Note
        ----
        If you wish for your private key to be generated, then you can do so with:

        .. code-block:: python

            >>> from eth_account.account import Account
            >>> from agent0.core.base import EthAgent
            >>> agent = EthAgent(Account().create("CHECKPOINT_BOT"))

        Alternatively, you can also use the Account api to provide a pre-generated key:

        .. code-block:: python

            >>> from eth_account.account import Account
            >>> from agent0.core.base import EthAgent
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
            self.policy = NoActionPolicy(NoActionPolicy.Config())
        else:
            self.policy = policy

        # TODO budget should have a flag to allow for "the budget is however much this wallet has"
        # https://github.com/delvtech/agent0/issues/827
        if initial_budget is None:
            initial_budget = FixedPoint(0)

        # State variable defining if this agent is done trading
        self.done_trading = False
        super().__init__(account._key_obj, account._publicapi)  # pylint: disable=protected-access

        self.wallet = EthWallet(
            address=HexBytes(self.address),
            balance=Quantity(amount=initial_budget, unit=TokenType.BASE),
        )

    @property
    def checksum_address(self) -> ChecksumAddress:
        """Return the checksum address of the account."""
        return Web3.to_checksum_address(self.address)

    def get_trades(self, interface: MarketInterface) -> list[Trade[MarketAction]]:
        """Helper function for computing a agent trade.

        Arguments
        ---------
        interface: MarketInterface
            Interface for the market on which this agent will be executing trades (MarketActions)

        Returns
        -------
        list[Trade]
            List of Trade type objects that represent the trades to be made by this agent
        """
        actions: list[Trade[MarketAction]]
        (actions, self.done_trading) = self.policy.action(interface, self.wallet)
        return actions

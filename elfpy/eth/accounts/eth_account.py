"""Empty test accounts for testing smart contracts"""
from __future__ import annotations

import logging

from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import ChecksumAddress
from web3 import Web3

from elfpy.agents.agent import Agent


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

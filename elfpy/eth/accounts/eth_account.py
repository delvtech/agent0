"""Empty test accounts for testing smart contracts"""
from __future__ import annotations

from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import ChecksumAddress
from web3 import Web3


class EthAccount:
    """Web3 account that has helper functions & associated funding source"""

    # TODO: We should be adding more methods to this class.
    # If not, we can delete it at the end of the refactor.
    # pylint: disable=too-few-public-methods

    def __init__(self, extra_entropy: str = "TEST ACCOUNT"):
        """Initialize an account"""
        self.account: LocalAccount = Account().create(extra_entropy=extra_entropy)

    @property
    def checksum_address(self) -> ChecksumAddress:
        """Return the checksum address of the account"""
        return Web3.to_checksum_address(self.account.address)

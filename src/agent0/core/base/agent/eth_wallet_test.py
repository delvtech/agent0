"""Unit tests for the EthWallet class."""

from __future__ import annotations  # types are strings by default in 3.11

import unittest

from fixedpointmath import FixedPoint
from hexbytes import HexBytes

from agent0.core.base.types import Quantity, TokenType

from .eth_wallet import EthWallet


class TestWallet(unittest.TestCase):
    """Unit tests for the base agent Wallet."""

    def test_wallet_copy(self):
        """Test the wallet ability to deep copy itself"""
        example_wallet = EthWallet(
            address=HexBytes(0), balance=Quantity(amount=FixedPoint("100.0"), unit=TokenType.BASE)
        )
        wallet_copy = example_wallet.copy()
        assert example_wallet is not wallet_copy  # not the same object
        assert example_wallet == wallet_copy  # they have the same attribute values
        wallet_copy.balance.amount += 1
        assert example_wallet != wallet_copy  # now they should have different attribute values

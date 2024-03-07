"""Unit tests for the HyperdriveWallet class."""

from __future__ import annotations  # types are strings by default in 3.11

import unittest

from fixedpointmath import FixedPoint
from hexbytes import HexBytes

from agent0.core.base import Quantity, TokenType

from .hyperdrive_wallet import HyperdriveWallet, HyperdriveWalletDeltas, Long


class TestWallet(unittest.TestCase):
    """Unit tests for the Hyperdrive Wallet."""

    def test_wallet_update(self):
        """Test that the wallet updates correctly & does not use references to the deltas argument."""
        example_wallet = HyperdriveWallet(
            address=HexBytes(0), balance=Quantity(amount=FixedPoint("100.0"), unit=TokenType.BASE)
        )
        example_deltas = HyperdriveWalletDeltas(
            balance=Quantity(amount=FixedPoint("-10.0"), unit=TokenType.BASE),
            longs={0: Long(FixedPoint("15.0"), maturity_time=0)},
        )
        example_wallet.update(example_deltas)
        assert id(example_wallet.longs[0]) != id(example_deltas.longs[0]), (
            f"{example_wallet.longs=} should not hold a reference to {example_deltas.longs=},"
            f"but have the same ids: {id(example_wallet.longs[0])=}, "
            f"{id(example_deltas.longs[0])=}."
        )
        assert example_wallet.longs[0].balance == FixedPoint(
            "15.0"
        ), f"{example_wallet.longs[0].balance=} should equal the delta amount, 15."
        assert example_wallet.balance.amount == FixedPoint(
            "90.0"
        ), f"{example_wallet.balance.amount=} should be 100-10=90."
        new_example_deltas = HyperdriveWalletDeltas(
            balance=Quantity(amount=FixedPoint("-5.0"), unit=TokenType.BASE),
            longs={0: Long(FixedPoint("8.0"), maturity_time=0)},
        )
        example_wallet.update(new_example_deltas)
        assert example_wallet.longs[0].balance == FixedPoint(
            "23.0"
        ), f"{example_wallet.longs[0].balance=} should equal 15+8=23."
        assert example_wallet.balance.amount == FixedPoint(
            "85.0"
        ), f"{example_wallet.balance.amount=} should be 100-10-5=85."
        assert example_deltas.longs[0].balance == FixedPoint(
            "15.0"
        ), f"{example_deltas.longs[0].balance=} should be unchanged and equal 15."

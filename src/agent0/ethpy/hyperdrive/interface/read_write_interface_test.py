"""Tests for hyperdrive_read_write_interface.py."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from eth_account import Account
from eth_utils.conversions import to_bytes
from eth_utils.crypto import keccak
from eth_utils.curried import text_if_str
from fixedpointmath import FixedPoint
from hexbytes import HexBytes

from agent0.ethpy.base import set_account_balance

if TYPE_CHECKING:
    from eth_account.signers.local import LocalAccount

    from .read_write_interface import HyperdriveReadWriteInterface

# we need to use the outer name for fixtures
# pylint: disable=redefined-outer-name


class TestHyperdriveReadWriteInterface:
    """Tests for the HyperdriveReadWriteInterface api class."""

    def test_set_variable_rate(self, hyperdrive_read_write_interface_fixture: HyperdriveReadWriteInterface):
        variable_rate = hyperdrive_read_write_interface_fixture.get_variable_rate()
        assert variable_rate is not None
        new_rate = variable_rate * FixedPoint("0.1")
        # TODO: Setup a fixture to create a funded local account
        extra_key_bytes = text_if_str(to_bytes, "extra_entropy")

        key_bytes = keccak(os.urandom(32) + extra_key_bytes)
        private_key = HexBytes(key_bytes).hex()
        sender: LocalAccount = Account().from_key(private_key)

        set_account_balance(hyperdrive_read_write_interface_fixture.web3, sender.address, 10**19)
        hyperdrive_read_write_interface_fixture.set_variable_rate(sender, new_rate)
        assert hyperdrive_read_write_interface_fixture.get_variable_rate() == new_rate

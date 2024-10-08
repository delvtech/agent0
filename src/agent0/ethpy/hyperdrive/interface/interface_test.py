"""Tests for Hyperdrive interface inheritance."""

from __future__ import annotations

from .read_interface import HyperdriveReadInterface
from .read_write_interface import HyperdriveReadWriteInterface

# we need to use the outer name for fixtures
# pylint: disable=redefined-outer-name


class TestHyperdriveInterface:
    """Tests for the Hyperdrive interface inheritence system."""

    def test_inheritance(
        self,
        hyperdrive_read_interface_fixture: HyperdriveReadInterface,
        hyperdrive_read_write_interface_fixture: HyperdriveReadWriteInterface,
    ):
        # child class should inherit type from parent class
        assert isinstance(hyperdrive_read_write_interface_fixture, HyperdriveReadInterface)
        # parent class is not the same type as the child class
        assert not isinstance(hyperdrive_read_interface_fixture, HyperdriveReadWriteInterface)
        # child class can convert to parent class, and then would not be the same type as child class
        assert not isinstance(
            hyperdrive_read_write_interface_fixture.get_read_interface(), HyperdriveReadWriteInterface
        )
        # write functions
        assert not hasattr(hyperdrive_read_interface_fixture, "async_open_long")
        assert hasattr(hyperdrive_read_write_interface_fixture, "async_open_long")
        assert not hasattr(hyperdrive_read_write_interface_fixture.get_read_interface(), "async_open_long")

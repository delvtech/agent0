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
        # parent class has read attributes
        assert hasattr(hyperdrive_read_interface_fixture, "read_retry_count")
        # parent class does not have write attributes
        assert not hasattr(hyperdrive_read_interface_fixture, "write_retry_count")
        # child class has write attributes
        assert hasattr(hyperdrive_read_write_interface_fixture, "write_retry_count")
        # child class can convert to parent class, then it would not have write attributes
        assert not hasattr(hyperdrive_read_write_interface_fixture.get_read_interface(), "write_retry_count")
        # write functions
        assert not hasattr(hyperdrive_read_interface_fixture, "async_open_long")
        assert hasattr(hyperdrive_read_write_interface_fixture, "async_open_long")
        assert not hasattr(hyperdrive_read_write_interface_fixture.get_read_interface(), "async_open_long")

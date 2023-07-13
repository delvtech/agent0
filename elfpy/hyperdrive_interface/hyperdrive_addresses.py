"""Helper class for storing Hyperdrive addresses"""
from __future__ import annotations

import attr


@attr.s
class HyperdriveAddresses:
    """Addresses for deployed Hyperdrive contracts."""

    # pylint: disable=too-few-public-methods

    base_token: str = attr.ib()
    mock_hyperdrive: str = attr.ib()
    mock_hyperdrive_math: str = attr.ib()

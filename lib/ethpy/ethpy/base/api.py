"""High-level interface for markets."""
from __future__ import annotations

from typing import Generic, TypeVar

from ethpy import EthConfig, build_eth_config

# pylint: disable=unused-argument

Addresses = TypeVar("Addresses")


class BaseInterface(Generic[Addresses]):
    """Base class for market interfaces."""

    def __init__(
        self,
        eth_config: EthConfig | None = None,
        addresses: Addresses | None = None,
    ) -> None:
        """Initialize."""
        if eth_config is None:
            eth_config = build_eth_config()
        self.config = eth_config

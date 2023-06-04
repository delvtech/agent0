"""Base policy class

Policies inherit from Users (thus each policy is assigned to a user)
subclasses of BasicPolicy will implement trade actions
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .base import BasePolicy

if TYPE_CHECKING:
    from elfpy.agents.wallet import Wallet
    from elfpy.markets.hyperdrive.hyperdrive_market import Market as HyperdriveMarket
    from elfpy.types import Trade

# pylint: disable=too-few-public-methods


class NoActionPolicy(BasePolicy):
    """NoOp class policy"""

    def action(self, market: HyperdriveMarket, wallet: Wallet) -> list[Trade]:
        """Returns an empty list, indicating no action"""
        # pylint: disable=unused-argument
        return []

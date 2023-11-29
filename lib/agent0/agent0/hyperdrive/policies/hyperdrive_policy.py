"""Base class for hyperdrive policies"""

from ethpy.hyperdrive.api import HyperdriveInterface

from agent0.base import Trade
from agent0.base.policies import BasePolicy
from agent0.hyperdrive.state import HyperdriveMarketAction, HyperdriveWallet


class HyperdrivePolicy(BasePolicy[HyperdriveInterface, HyperdriveWallet]):
    """Hyperdrive policy."""

    def action(
        self, interface: HyperdriveInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """Returns an empty list, indicating no action."""
        raise NotImplementedError

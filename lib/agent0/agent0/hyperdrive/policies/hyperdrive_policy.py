"""Base class for hyperdrive policies"""

from agent0.base.policies import BasePolicy
from agent0.hyperdrive.state import HyperdriveMarketAction, HyperdriveWallet
from elfpy.types import Trade
from ethpy.hyperdrive import HyperdriveInterface


class HyperdrivePolicy(BasePolicy[HyperdriveInterface, HyperdriveWallet]):
    """Hyperdrive policy."""

    def action(self, interface: HyperdriveInterface, wallet: HyperdriveWallet) -> list[Trade[HyperdriveMarketAction]]:
        """Returns an empty list, indicating no action."""
        raise NotImplementedError

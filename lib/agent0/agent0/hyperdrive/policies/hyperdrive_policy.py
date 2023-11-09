"""Base class for hyperdrive policies"""

from agent0.base import Trade
from agent0.base.policies import BasePolicy
from agent0.hyperdrive.state import HyperdriveMarketAction, HyperdriveWallet
from ethpy.hyperdrive.api import HyperdriveInterface


class HyperdrivePolicy(BasePolicy[HyperdriveInterface, HyperdriveWallet]):
    """Hyperdrive policy."""

    # We want to rename the argument from "interface" to "hyperdrive" to be more explicit
    # pylint: disable=arguments-renamed
    def action(
        self, hyperdrive: HyperdriveInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """Returns an empty list, indicating no action."""
        raise NotImplementedError

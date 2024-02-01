"""Base class for hyperdrive policies"""

from agent0.base import Trade
from agent0.base.policies import BasePolicy
from agent0.hyperdrive import HyperdriveMarketAction, HyperdriveReadInterface, HyperdriveWallet


class HyperdrivePolicy(BasePolicy[HyperdriveReadInterface, HyperdriveWallet]):
    """Hyperdrive policy."""

    def action(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """Returns an empty list, indicating no action.

        Arguments
        ---------
        interface: HyperdriveReadInterface
            Interface for the market on which this agent will be executing trades (MarketActions).
        wallet: HyperdriveWallet
            The agent's wallet.

        Returns
        -------
        tuple[list[MarketAction], bool]
            A tuple where the first element is a list of actions,
            and the second element defines if the agent is done trading.
        """
        raise NotImplementedError

"""Base class for hyperdrive policies"""

# from agent0.hyperdrive import HyperdriveMarketState # TODO: use agent0 market state instead of elfpy market
from agent0.base.policies import BasePolicy
from agent0.hyperdrive import HyperdriveMarketAction
from agent0.hyperdrive.agents import HyperdriveWallet
from elfpy.markets.hyperdrive import HyperdriveMarket as HyperdriveMarketState
from elfpy.types import Trade


class HyperdrivePolicy(BasePolicy[HyperdriveMarketState, HyperdriveWallet]):
    """Hyperdrive policy."""

    def action(self, market: HyperdriveMarketState, wallet: HyperdriveWallet) -> list[Trade[HyperdriveMarketAction]]:
        """Returns an empty list, indicating no action"""
        raise NotImplementedError

"""Base class for hyperdrive policies"""

from ethpy.hyperdrive import HyperdriveReadInterface

from agent0.base import Trade
from agent0.base.policies import BasePolicy
from agent0.hyperdrive import HyperdriveMarketAction, HyperdriveWallet, TradeResult


class HyperdriveBasePolicy(BasePolicy[HyperdriveReadInterface, HyperdriveWallet]):
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

    def post_action(self, interface: HyperdriveReadInterface, trade_results: list[TradeResult]) -> None:
        """Function that gets called after actions have been executed. This allows the policy
        to e.g., do additional bookkeeping based on the results of the executed actions.
        Arguments
        ---------
        interface: MarketInterface
            The trading market interface.
        trade_results: list[HyperdriveTradeResult]
            A list of HyperdriveTradeResult objects, one for each trade made by the agent.
            The order of the list matches the original order of `agent.action`.
            HyperdriveTradeResult contains any information about the trade,
            as well as any errors that the trade resulted in.
        """
        # Default post action is noop

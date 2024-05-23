"""Base class for hyperdrive policies."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fixedpointmath import FixedPoint

from agent0.core.base import Trade
from agent0.core.base.policies import BasePolicy
from agent0.core.hyperdrive.agent import HyperdriveWallet, close_long_trade, close_short_trade
from agent0.ethpy.hyperdrive import HyperdriveReadInterface
from agent0.ethpy.hyperdrive.state import PoolState

if TYPE_CHECKING:
    from agent0.core.hyperdrive import HyperdriveMarketAction, TradeResult


class HyperdriveBasePolicy(BasePolicy[HyperdriveReadInterface, HyperdriveWallet]):
    """Hyperdrive policy."""

    def close_matured_positions(
        self, wallet: HyperdriveWallet, pool_state: PoolState, minimum_trade_amount: FixedPoint = FixedPoint(0)
    ) -> list[Trade[HyperdriveMarketAction]]:
        """Generate actions to close longs and shorts that have matured.

        Arguments
        ---------
        wallet: HyperdriveWallet
            The agent's wallet.
        pool_state: PoolState
            The current state of the Hyperdrive pool.
        minimum_trade_amount: FixedPoint, optional
            A mimimum amount to trade; if the matured position is smaller than this amount then it will not be closed.
            Defaults to 0.

        Returns
        -------
        list[MarketAction]
            Is a list of Hyperdrive trade actions for closing matured longs and shorts.
        """
        action_list = []
        # Close longs if matured
        for maturity_time, long in wallet.longs.items():
            if maturity_time < pool_state.block_time and long.balance > minimum_trade_amount:
                action_list.append(close_long_trade(long.balance, maturity_time, self.slippage_tolerance))
        # Close shorts if matured
        for maturity_time, short in wallet.shorts.items():
            if maturity_time < pool_state.block_time and short.balance > minimum_trade_amount:
                action_list.append(close_short_trade(short.balance, maturity_time, self.slippage_tolerance))
        return action_list

    def action(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """Return an empty list, indicating no action.

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
        """Execute any behavior after after the actions specified by the `action` function have been executed.

        This allows the policy to e.g., do additional bookkeeping based on the results of the executed actions.

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

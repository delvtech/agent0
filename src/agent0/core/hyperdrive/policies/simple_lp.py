"""Agent policy for LP trading that modifies liquidity for a target profitability."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fixedpointmath import FixedPoint

from agent0.base import Trade
from agent0.hyperdrive import HyperdriveMarketAction
from agent0.hyperdrive.agent import add_liquidity_trade, remove_liquidity_trade

from .hyperdrive_policy import HyperdriveBasePolicy

if TYPE_CHECKING:
    from ethpy.hyperdrive import HyperdriveReadInterface

    from agent0.hyperdrive import HyperdriveWallet


class SimpleLP(HyperdriveBasePolicy):
    """LP to maintain profitability."""

    @classmethod
    def description(cls) -> str:
        """Describe the policy in a user friendly manner that allows newcomers to decide whether to use it.

        Returns
        -------
        str
            The description of the policy, as described above.
        """
        raw_description = """
        This LP bot adds and removes liquidity to maximize profitability.
        The bot stores its PNL for each previous block.
        It adds liquidity if the PNL is above some threshold, removes if below, and otherwise takes no action.
        """
        return super().describe(raw_description)

    @dataclass(kw_only=True)
    class Config(HyperdriveBasePolicy.Config):
        """Custom config arguments for this policy.

        Attributes
        ----------
        lookback_length: int
            How many blocks back to look when computing past PNL.
        pnl_target: FixedPoint
            The target PNL for the bot to achieve, as a fraction improvement over the pnl at lookback_length
        delta_liquidity: FixedPoint
            How much liquidity to add or remove, depending on policy outcome.
        """

        lookback_length: FixedPoint = FixedPoint(10)  # blocks
        pnl_target: FixedPoint = FixedPoint("1.0")
        delta_liquidity: FixedPoint = FixedPoint("100")

    def __init__(
        self,
        policy_config: Config,
    ):
        """Initialize the bot.

        Arguments
        ---------
        policy_config: Config
            The custom arguments for this policy
        """
        super().__init__(policy_config)
        self.pnl_history: list[tuple[int, FixedPoint]] = []

    def time_weighted_average_pnl(self) -> FixedPoint:
        """Return the time-weighted average PNL improvement."""
        if len(self.pnl_history) == 0:  # no history
            return FixedPoint(0)
        twapnl: FixedPoint = FixedPoint(0)
        origin_time, origin_pnl = self.pnl_history[0]
        time_sum: FixedPoint = FixedPoint(0)
        for block_number, pnl in self.pnl_history:
            time = origin_time - block_number
            pnl_improvement = pnl / origin_pnl
            twapnl += pnl_improvement * time
            time_sum += FixedPoint(time)
        twapnl /= time_sum
        return twapnl

    def action(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """Specify actions.

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
        action_list = []

        current_block = interface.get_current_block()
        pool_state = interface.get_hyperdrive_state(current_block)
        pnl = pool_state.pool_info.lp_total_supply * pool_state.pool_info.lp_share_price
        self.pnl_history.append((interface.get_block_number(current_block), pnl))

        twapnl = self.time_weighted_average_pnl()
        if twapnl > self.policy_config.pnl_target:
            if wallet.balance.amount >= self.policy_config.delta_liquidity:  # only add money if you can afford it!
                action_list.append(add_liquidity_trade(self.policy_config.delta_liquidity))
        elif twapnl < self.policy_config.pnl_target:
            action_list.append(remove_liquidity_trade(self.policy_config.delta_liquidity))

        if len(self.pnl_history) > self.policy_config.lookback_length:
            self.pnl_history = self.pnl_history[len(self.pnl_history) - self.policy_config.lookback_length :]

        return action_list, False

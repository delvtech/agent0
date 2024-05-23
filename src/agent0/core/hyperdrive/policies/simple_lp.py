"""Agent policy for LP trading that modifies liquidity for a target profitability."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fixedpointmath import FixedPoint, maximum, minimum

from agent0.core.base import Trade
from agent0.core.hyperdrive.agent import add_liquidity_trade, remove_liquidity_trade

from .hyperdrive_policy import HyperdriveBasePolicy

if TYPE_CHECKING:
    from agent0.core.hyperdrive import HyperdriveMarketAction, HyperdriveWallet, TradeResult
    from agent0.ethpy.hyperdrive import HyperdriveReadInterface

# policy definitions can be more verbose, allowing for more local variables
# pylint: disable=too-many-locals


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
        This LP bot adds or removes liquidity according to its recent profitability.
        It has a target PNL that it is aiming for, and takes actions based on how its PNL has changed over time.
        The bot follows this strategy:
            - If the PNL is above threshold, and is improving over time, then the bot adds liquidity.
            - If the PNL is above threshold, and is not improving over time, then the bot takes no action.
            - If the PNL is below threshold, and is improving over time, then the bot takes no action.
            - If the PNL is below threshold, and is not improving over time, then the bot pulls liquidity.
        """
        return super().describe(raw_description)

    @dataclass(kw_only=True)
    class Config(HyperdriveBasePolicy.Config):
        """Custom config arguments for this policy."""

        pnl_target: FixedPoint = FixedPoint("100")
        """The target PNL for the bot, in base."""
        delta_liquidity: FixedPoint = FixedPoint("100")
        """How much liquidity to add or remove, depending on policy outcome, in base."""
        minimum_liquidity_value: FixedPoint = FixedPoint("100")
        """
        Minimum liquidity the bot will provide, in base.
        It will keep this much liquidity in the pool, even if it is losing money.
        """
        lookback_length: int = 10
        """
        How many steps back to look when computing PNL progress over time.
        Each time `action` is called is a step.
        """

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
        assert policy_config.pnl_target > FixedPoint(0), "PNL target must be greater than zero."
        self.policy_config = policy_config
        self.pnl_history: list[tuple[FixedPoint, FixedPoint]] = []
        self.total_base_spent: FixedPoint = FixedPoint(0)

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
        # Get the current state of the pool & the bot's position
        current_block = interface.get_current_block()
        pool_state = interface.get_hyperdrive_state(current_block)
        lp_base_holding = wallet.lp_tokens * pool_state.pool_info.lp_share_price

        # Need to be in the game to play it
        if self.policy_config.minimum_liquidity_value > lp_base_holding:
            trade_amount = self.policy_config.minimum_liquidity_value - lp_base_holding
            return [add_liquidity_trade(trade_amount)], False

        # Get current PNL
        pnl = lp_base_holding - self.total_base_spent
        self.pnl_history.append((FixedPoint(interface.get_block_timestamp(current_block)), pnl))
        # Prune history
        if FixedPoint(len(self.pnl_history)) > self.policy_config.lookback_length:
            self.pnl_history = self.pnl_history[-self.policy_config.lookback_length :]
        # PNL slope is dy/dx, where y is PNL and x is time.
        # We compute an average of splines instead of a global average
        # to reduce emphasis on the first and last time-points.
        avg_pnl_slope = 0
        if len(self.pnl_history) > 2:
            for i in range(len(self.pnl_history) - 1):
                dx = self.pnl_history[i + 1][0] - self.pnl_history[i][0]
                dy = self.pnl_history[i + 1][1] - self.pnl_history[i][1]
                avg_pnl_slope += dy / dx
            avg_pnl_slope /= len(self.pnl_history) - 1

        # Make trades based on pnl_target and avg_pnl_slope
        action_list = []

        # I'm doing great, keep putting money in
        if pnl > self.policy_config.pnl_target and avg_pnl_slope > 0:
            # only add money if you can afford it!
            if wallet.balance.amount >= self.policy_config.delta_liquidity:
                action_list.append(add_liquidity_trade(self.policy_config.delta_liquidity))

        # I'm doing bad, time to pull some money out
        elif pnl < self.policy_config.pnl_target and avg_pnl_slope < 0:
            # delta_liquidity is in base; convert it to tokens
            delta_tokens = self.policy_config.delta_liquidity / pool_state.pool_info.lp_share_price
            # we do not want to pull out so many tokens that we are below the minimum
            max_delta = maximum(FixedPoint(0), wallet.lp_tokens - self.policy_config.minimum_liquidity_value)
            remove_amount = minimum(delta_tokens, max_delta)
            action_list.append(remove_liquidity_trade(remove_amount))

        # else things are uncertain, so do nothing

        return action_list, False

    def post_action(self, interface: HyperdriveReadInterface, trade_results: list[TradeResult]) -> None:
        """Keep track of money spent.

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
        if len(trade_results) > 0:
            if (
                trade_results[-1].trade_successful
                and trade_results[-1].trade_object is not None
                and trade_results[-1].tx_receipt is not None
            ):
                if trade_results[-1].trade_object.market_action.action_type.name == "ADD_LIQUIDITY":
                    self.total_base_spent += trade_results[-1].tx_receipt.amount
                elif trade_results[-1].trade_object.market_action.action_type.name == "REMOVE_LIQUIDITY":
                    self.total_base_spent -= trade_results[-1].tx_receipt.amount

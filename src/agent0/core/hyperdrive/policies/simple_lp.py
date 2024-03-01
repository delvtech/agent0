"""Agent policy for LP trading that modifies liquidity for a target profitability."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fixedpointmath import FixedPoint, FixedPointMath

from agent0.base import Trade
from agent0.hyperdrive import HyperdriveMarketAction, TradeResult
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
            How many steps back to look when computing past PNL.
            Each time `action` is called is a step.
        pnl_target: FixedPoint
            The target yearly PNL growth for the bot to achieve,
            as a fraction improvement over the pnl from previous recordings.
        delta_liquidity: FixedPoint
            How much liquidity to add or remove, depending on policy outcome.
        """

        # pnl_target = 0.1 means the time-weighted average profit_change is 10% increase
        pnl_target: FixedPoint = FixedPoint("0.1")
        lookback_length: FixedPoint = FixedPoint("10")  # action calls (usually blocks)
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
        assert policy_config.pnl_target > FixedPoint(0), "PNL target must be greater than zero."
        self.policy_config = policy_config
        self.pnl_history: list[tuple[FixedPoint, FixedPoint]] = []
        self.total_base_spent: FixedPoint = 0

    def time_weighted_average_pnl(self) -> FixedPoint:
        """Return the linear time-weighted average PNL improvement.

        This function assumes the self.pnl_history member attribute is a list of (time, pnl) pairs,
        where the zero index dereferences the earliest pair.

        .. todo::
        It would be good to have option to change twapnl to unweighted (all weights are equal), exponential, or linear.
        """
        if len(self.pnl_history) <= 1:  # not enough history
            return FixedPoint(0)
        if self.pnl_history[0][1] == 0:  # if original pnl is zero then the improvement will be infinite
            self.pnl_history = self.pnl_history[1:]  # remove the first element
            return FixedPoint(0)  # need to ignore first pnl change to avoid inf %

        weighted_sum = FixedPoint(0)
        total_weight = FixedPoint(0)
        for i in range(len(self.pnl_history) - 1, 0, -1):
            # fraction change in pnl, scaled to be annual
            profit_change = (self.pnl_history[i][1] - self.pnl_history[i - 1][1]) / self.pnl_history[i - 1][1]

            # scale weight by amount of time changed
            delta_time = self.pnl_history[i][0] - self.pnl_history[i - 1][0]
            total_time_spanned = self.pnl_history[-1][0] - self.pnl_history[0][0]

            # biggest weight to most recent, normalized by time spanned
            weight = (i + 1) * delta_time / total_time_spanned

            # compute sums
            weighted_sum += profit_change * weight
            total_weight += weight

        if total_weight == FixedPoint(0):
            return FixedPoint(0)  # no valid data points to comptue the average

        ret_val = weighted_sum / total_weight
        return ret_val

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
        # update PNL
        current_block = interface.get_current_block()
        pool_state = interface.get_hyperdrive_state(current_block)
        pnl = wallet.lp_tokens * pool_state.pool_info.lp_share_price - self.total_base_spent
        self.pnl_history.append((FixedPoint(interface.get_block_timestamp(current_block)), pnl))

        # prune history
        if FixedPoint(len(self.pnl_history)) > self.policy_config.lookback_length:
            self.pnl_history = self.pnl_history[-self.policy_config.lookback_length :]

        # make trades based on pnl_target
        twapnl = self.time_weighted_average_pnl()
        action_list = []
        if wallet.lp_tokens == FixedPoint("0"):
            action_list.append(add_liquidity_trade(self.policy_config.delta_liquidity))
        elif twapnl > self.policy_config.pnl_target:
            if wallet.balance.amount >= self.policy_config.delta_liquidity:  # only add money if you can afford it!
                action_list.append(add_liquidity_trade(self.policy_config.delta_liquidity))
        elif twapnl < self.policy_config.pnl_target:
            remove_amount = FixedPointMath.minimum(self.policy_config.delta_liquidity, wallet.lp_tokens)
            action_list.append(remove_liquidity_trade(remove_amount))

        return action_list, False

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
        if trade_results[-1].status.name == "SUCCESS":
            if trade_results[-1].trade_object.market_action.action_type.name == "ADD_LIQUIDITY":
                self.total_base_spent += trade_results[-1].tx_receipt.base_amount
            elif trade_results[-1].trade_object.market_action.action_type.name == "REMOVE_LIQUIDITY":
                self.total_base_spent -= trade_results[-1].tx_receipt.base_amount

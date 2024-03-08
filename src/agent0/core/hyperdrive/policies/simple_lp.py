"""Agent policy for LP trading that modifies liquidity for a target profitability."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fixedpointmath import FixedPoint, minimum

from agent0.core.base import Trade
from agent0.core.hyperdrive import HyperdriveMarketAction, TradeResult
from agent0.core.hyperdrive.agent import add_liquidity_trade, remove_liquidity_trade

from .hyperdrive_policy import HyperdriveBasePolicy

if TYPE_CHECKING:
    from agent0.core.hyperdrive import HyperdriveWallet
    from agent0.ethpy.hyperdrive import HyperdriveReadInterface


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
        pnl_target: FixedPoint
            The target PNL for the bot, in base.
        delta_liquidity: FixedPoint
            How much liquidity to add or remove, depending on policy outcome, in base.
        minimum_liquidity: FixedPoint
            Minimum liquidity the bot will provide.
            It will keep this much liquidity in the pool, even if it is losing money.
        """

        pnl_target: FixedPoint = FixedPoint("100")
        delta_liquidity: FixedPoint = FixedPoint("100")
        minimum_liquidity_tokens: FixedPoint = FixedPoint("100")

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
        self.total_base_spent: FixedPoint = 0

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
        # get the current state of the pool
        current_block = interface.get_current_block()
        pool_state = interface.get_hyperdrive_state(current_block)

        # need to be in the game to play it
        if wallet.lp_tokens <= self.policy_config.minimum_liquidity_tokens:
            trade_amount = (
                wallet.lp_tokens * pool_state.pool_info.lp_share_price - self.policy_config.minimum_liquidity_tokens
            )
            return [add_liquidity_trade(trade_amount)], False

        # get current PNL
        pnl = wallet.lp_tokens * pool_state.pool_info.lp_share_price - self.total_base_spent

        # make trades based on pnl_target
        action_list = []
        # I'm doing great, keep putting money in
        if pnl > self.policy_config.pnl_target + self.policy_config.delta_liquidity:
            # only add money if you can afford it!
            if wallet.balance.amount >= self.policy_config.delta_liquidity:
                action_list.append(add_liquidity_trade(self.policy_config.delta_liquidity))
        # I'm doing bad, time to pull some money out
        elif pnl < self.policy_config.pnl_target - self.policy_config.delta_liquidity:
            remove_amount = minimum(self.policy_config.delta_liquidity, wallet.lp_tokens)
            action_list.append(remove_liquidity_trade(remove_amount))
        # else my PNL is within tolerance of the target, so do nothing

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

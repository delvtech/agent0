"""User strategy that opens random positions with set hold position times."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fixedpointmath import FixedPoint

from agent0.base.types import Trade
from agent0.hyperdrive import HyperdriveActionType, HyperdriveMarketAction, TradeResult, TradeStatus
from agent0.hyperdrive.agent import close_long_trade, close_short_trade

from .random import Random

if TYPE_CHECKING:
    from ethpy.hyperdrive import HyperdriveReadInterface
    from ethpy.hyperdrive.state import PoolState

    from agent0.hyperdrive import HyperdriveWallet

# We can allow unused arguments here because this is a template and extendable class.
# pylint: disable=unused-argument


class RandomHold(Random):
    """Random agent that opens random positions with random hold position times."""

    @classmethod
    def description(cls) -> str:
        """Describe the policy in a user friendly manner that allows newcomers to decide whether to use it.

        Returns
        -------
        str
            A description of the policy.
        """
        raw_description = """
        A random policy that randomly generates positions (i.e., long, short, lp) with a random hold time.
        """
        return super().describe(raw_description)

    @dataclass(kw_only=True)
    class Config(Random.Config):
        """Custom config arguments for this policy

        Attributes
        ----------
        max_open_positions: int
            The maximum number of open positions
        """

        max_open_positions: int = 100

    @dataclass
    class _Position:
        # The minimum close time for this position.
        # Note it's not guaranteed this position will be closed, but is guaranteed
        # not to close if the block time is before min_close_time
        min_close_time: int
        action_type: HyperdriveActionType
        balance: FixedPoint
        maturity_time: int | None
        # Status flags
        ready_to_close: bool = False
        txn_sent: bool = False

    def __init__(self, policy_config: Config) -> None:
        """Initializes the bot

        Arguments
        ---------
        policy_config: Config
            The custom arguments for this policy
        """
        # Bookkeeping data structure for keeping track of open positions
        # TODO using a list for now, but likely should use a different data structure
        # to allow for fast "close all positions with a close time <= current time"
        self.open_positions: list[RandomHold._Position] = []
        self.max_open_positions = policy_config.max_open_positions

        super().__init__(policy_config)

    def generate_random_hold_time(self, interface: HyperdriveReadInterface) -> int:
        """Generate a random hold time in seconds, uniform between 0 and 2*position_duration

        Arguments
        ---------
        interface: HyperdriveReadInterface
            Interface for the market on which this agent will be executing trades (MarketActions).

        Returns
        -------
        int
            A random hold time in seconds.
        """
        return self.rng.integers(0, interface.pool_config.position_duration * 2)

    def get_available_actions(
        self,
        wallet: HyperdriveWallet,
        pool_state: PoolState,
    ) -> list[HyperdriveActionType]:
        """Get all available actions.

        Arguments
        ---------
        wallet: HyperdriveWallet
            The agent's wallet.
        pool_state: PoolState
            The current state of the pool, which includes block details, pool config, and pool info.

        Returns
        -------
        list[HyperdriveActionType]
            A list containing all of the available actions.
        """
        long_ready_to_close = False
        short_ready_to_close = False
        # Scan for positions ready to close
        current_block_time = int(pool_state.block_time)
        for position in self.open_positions:
            if position.min_close_time > current_block_time:
                position.ready_to_close = True
                if position.action_type == HyperdriveActionType.OPEN_LONG:
                    long_ready_to_close = True
                elif position.action_type == HyperdriveActionType.OPEN_SHORT:
                    short_ready_to_close = True
                else:
                    # Sanity check
                    raise ValueError(f"Action type {position.action_type} not in allowable actions")

        if wallet.balance.amount <= pool_state.pool_config.minimum_transaction_amount:
            all_available_actions = []
        else:
            all_available_actions = [
                HyperdriveActionType.ADD_LIQUIDITY,
            ]
        # We hard cap the number of open positions to keep track of
        if len(self.open_positions) < self.max_open_positions:
            all_available_actions = [
                HyperdriveActionType.OPEN_LONG,
                HyperdriveActionType.OPEN_SHORT,
            ]
        if long_ready_to_close:  # if the agent has longs ready to close
            all_available_actions.append(HyperdriveActionType.CLOSE_LONG)
        if short_ready_to_close:  # if the agent has shorts ready to close
            all_available_actions.append(HyperdriveActionType.CLOSE_SHORT)
        if wallet.lp_tokens:
            all_available_actions.append(HyperdriveActionType.REMOVE_LIQUIDITY)
        if wallet.withdraw_shares and pool_state.pool_info.withdrawal_shares_ready_to_withdraw > 0:
            all_available_actions.append(HyperdriveActionType.REDEEM_WITHDRAW_SHARE)
        # down select from all actions to only include allowed actions
        return [action for action in all_available_actions if action in self.allowable_actions]

    def close_random_long(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> list[Trade[HyperdriveMarketAction]]:
        """Closes a random long that's ready to be closed.

        Arguments
        ---------
        interface: HyperdriveReadInterface
            Interface for the market on which this agent will be executing trades (MarketActions).
        wallet: HyperdriveWallet
            The agent's wallet.

        Returns
        -------
        list[Trade[HyperdriveMarketAction]]
            A list with a single Trade element for closing a Hyperdrive short.
        """
        # We scan open positions and select a long that's ready to be closed
        longs_ready_to_close: list[RandomHold._Position] = [
            position
            for position in self.open_positions
            if position.ready_to_close and position.action_type == HyperdriveActionType.OPEN_LONG
        ]
        # Select a random one
        long_to_close = longs_ready_to_close[self.rng.integers(len(longs_ready_to_close))]
        # Set flag
        long_to_close.txn_sent = True

        ignore_slippage = self.rng.choice([True, False], size=1) if self.randomly_ignore_slippage_tolerance else False
        if ignore_slippage:
            slippage = None
        else:
            slippage = self.slippage_tolerance
        # Longs should have a maturity time set
        assert long_to_close.maturity_time is not None
        return [close_long_trade(long_to_close.balance, long_to_close.maturity_time, slippage)]

    def close_random_short(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> list[Trade[HyperdriveMarketAction]]:
        """Closes a random short that's ready to be closed.

        Arguments
        ---------
        interface: HyperdriveReadInterface
            Interface for the market on which this agent will be executing trades (MarketActions).
        wallet: HyperdriveWallet
            The agent's wallet.

        Returns
        -------
        list[Trade[HyperdriveMarketAction]]
            A list with a single Trade element for closing a Hyperdrive short.
        """
        # We scan open positions and select a short that's ready to be closed
        shorts_ready_to_close: list[RandomHold._Position] = [
            position
            for position in self.open_positions
            if position.ready_to_close and position.action_type == HyperdriveActionType.OPEN_SHORT
        ]
        # Select a random one
        short_to_close = shorts_ready_to_close[self.rng.integers(len(shorts_ready_to_close))]
        # Set flag
        short_to_close.txn_sent = True

        ignore_slippage = self.rng.choice([True, False], size=1) if self.randomly_ignore_slippage_tolerance else False
        if ignore_slippage:
            slippage = None
        else:
            slippage = self.slippage_tolerance
        # Shorts should have a maturity time set
        assert short_to_close.maturity_time is not None
        return [close_short_trade(short_to_close.balance, short_to_close.maturity_time, slippage)]

    def post_action(self, interface: HyperdriveReadInterface, trade_results: list[TradeResult]) -> None:
        # We only update bookkeeping if the trade went through
        # NOTE this is assuming no more than one close per step
        assert len(trade_results) <= 1
        if len(trade_results) == 0:
            return

        # Get the relevant fields from the trade results,
        result = trade_results[0]
        assert result.trade_object is not None
        result_action = result.trade_object.market_action

        # If the trade was successful and the transaction was successful,
        # we add the trade to bookkeeping and generate a close time
        if result.status == TradeStatus.SUCCESS and result_action.action_type in (
            HyperdriveActionType.OPEN_LONG,
            HyperdriveActionType.OPEN_SHORT,
        ):
            current_block_time = interface.get_block_timestamp(interface.get_current_block())
            close_time = current_block_time + self.generate_random_hold_time(interface)
            self.open_positions.append(
                RandomHold._Position(
                    min_close_time=close_time,
                    action_type=result_action.action_type,
                    balance=result_action.trade_amount,
                    maturity_time=result_action.maturity_time,
                )
            )
        # If the close trade was unsuccessful, we reset the txn_set flag
        elif result.status == TradeStatus.FAIL and result_action.action_type in (
            HyperdriveActionType.CLOSE_LONG,
            HyperdriveActionType.CLOSE_SHORT,
        ):
            position_submitted = [position for position in self.open_positions if position.txn_sent]
            assert len(position_submitted) <= 1

            # If a close action is submitted, sanity check that we book kept the close position
            assert len(position_submitted) == 1
            # Reset txn flag, and retry at a later time
            position_submitted[0].txn_sent = False

        # All other cases are ignored:
        # If the result was successful for a close action, the txn_sent flag is already set, ready to be removed
        # If the result was unsuccessful for an open action, we don't need to add it to bookkeeping
        # All other trades don't need to add to bookkeeping

        # We now remove any bookkept positions where a transaction was sent.
        self.open_positions = [position for position in self.open_positions if not position.txn_sent]

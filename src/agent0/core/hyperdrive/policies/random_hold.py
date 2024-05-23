"""User strategy that opens random positions with set hold position times."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fixedpointmath import FixedPoint

from agent0.core.base.types import Trade
from agent0.core.hyperdrive.agent import HyperdriveActionType, close_long_trade, close_short_trade

from .random import Random

if TYPE_CHECKING:
    from agent0.core.hyperdrive import HyperdriveMarketAction, HyperdriveWallet, TradeResult
    from agent0.ethpy.hyperdrive import HyperdriveReadInterface
    from agent0.ethpy.hyperdrive.state import PoolState


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
        """Custom config arguments for this policy."""

        max_open_positions: int = 100
        """The maximum number of open positions."""
        min_hold_time: int = 0
        """The minimum hold time in seconds. Defaults to 0."""
        # Can't default here, as we don't know the position duration at the time of constructing the config
        # Hence, we set the default when we use it
        max_hold_time: int | None = None
        """The minimum hold time in seconds. Defaults to 2 * position_duration."""

    @dataclass
    class _Position:
        # The minimum close time for this position.
        # Note it's not guaranteed this position will be closed, but is guaranteed
        # not to close if the block time is before min_close_time
        min_close_time: int
        action_type: HyperdriveActionType
        bond_amount: FixedPoint
        maturity_time: int
        # Status flags
        ready_to_close: bool = False
        txn_sent: bool = False

    def __init__(self, policy_config: Config) -> None:
        """Initialize the policy.

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
        self.min_hold_time = policy_config.min_hold_time
        self.max_hold_time = policy_config.max_hold_time

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
        if self.max_hold_time is not None:
            max_hold_time = self.max_hold_time
        else:
            max_hold_time = interface.pool_config.position_duration * 2
        return self.rng.integers(self.min_hold_time, max_hold_time)

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
            if position.min_close_time <= current_block_time:
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
                all_available_actions.extend(
                    [
                        HyperdriveActionType.OPEN_LONG,
                        HyperdriveActionType.OPEN_SHORT,
                    ]
                )
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
        # Sanity check, we should have at least one, otherwise close long wouldn't be an available action
        assert len(longs_ready_to_close) > 0

        # Select a random one
        long_to_close = longs_ready_to_close[self.rng.integers(len(longs_ready_to_close))]
        # Set flag that this is the transaction that was sent for bookkeeping in post action
        long_to_close.txn_sent = True

        ignore_slippage = self.rng.choice([True, False], size=1) if self.randomly_ignore_slippage_tolerance else False
        if ignore_slippage:
            slippage = None
        else:
            slippage = self.slippage_tolerance
        return [close_long_trade(long_to_close.bond_amount, long_to_close.maturity_time, slippage, self.gas_limit)]

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
        # Sanity check, we should have at least one, otherwise close short wouldn't be an available action
        assert len(shorts_ready_to_close) > 0

        # Select a random one
        short_to_close = shorts_ready_to_close[self.rng.integers(len(shorts_ready_to_close))]
        # Set flag that the transaction was sent
        short_to_close.txn_sent = True

        ignore_slippage = self.rng.choice([True, False], size=1) if self.randomly_ignore_slippage_tolerance else False
        if ignore_slippage:
            slippage = None
        else:
            slippage = self.slippage_tolerance
        return [close_short_trade(short_to_close.bond_amount, short_to_close.maturity_time, slippage, self.gas_limit)]

    def post_action(self, interface: HyperdriveReadInterface, trade_results: list[TradeResult]) -> None:
        """Random hold updates open position bookkeeping based on which positions were closed.

        Arguments
        ---------
        interface: HyperdriveReadInterface
            The hyperdrive trading market interface.
        trade_results: list[TradeResult]
            A list of TradeResult objects, one for each trade made by the agent.
            The order of the list matches the original order of `agent.action`.
            TradeResult contains any information about the trade,
            as well as any errors that the trade resulted in.
        """
        # NOTE this function is assuming no more than one close per step
        assert len(trade_results) <= 1
        if len(trade_results) == 0:
            return

        # Get the relevant fields from the trade results,
        result = trade_results[0]
        tx_receipt = result.tx_receipt
        assert result.trade_object is not None
        result_action_type = result.trade_object.market_action.action_type

        # If the trade was successful and the transaction was successful,
        # we add the trade to bookkeeping and generate a close time
        if result.trade_successful and result_action_type in (
            HyperdriveActionType.OPEN_LONG,
            HyperdriveActionType.OPEN_SHORT,
        ):
            current_block_time = interface.get_block_timestamp(interface.get_current_block())
            close_time = current_block_time + self.generate_random_hold_time(interface)
            # Open longs/shorts, if successful, should have a transaction receipt
            assert tx_receipt is not None
            maturity_time = tx_receipt.maturity_time_seconds
            # Receipt breakdown defaults to 0 maturity time, so we ensure the tx receipt actually
            # returns a maturity time here
            assert maturity_time > 0
            # All closing positions take bonds as the argument, so we always get the bond amount
            # in bookkeeping from the tx receipt
            bond_amount = tx_receipt.bond_amount
            assert bond_amount > 0

            self.open_positions.append(
                RandomHold._Position(
                    min_close_time=close_time,
                    action_type=result_action_type,
                    bond_amount=bond_amount,
                    maturity_time=maturity_time,
                )
            )
        # If the close trade was unsuccessful, we reset the txn_set flag
        elif not result.trade_successful and result_action_type in (
            HyperdriveActionType.CLOSE_LONG,
            HyperdriveActionType.CLOSE_SHORT,
        ):
            position_submitted = [position for position in self.open_positions if position.txn_sent]
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

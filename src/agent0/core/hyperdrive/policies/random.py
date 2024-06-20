"""User strategy that opens or closes a random position with a random allowed amount."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from fixedpointmath import FixedPoint

from agent0.core.base import Trade
from agent0.core.hyperdrive.agent import (
    HyperdriveActionType,
    add_liquidity_trade,
    close_long_trade,
    close_short_trade,
    open_long_trade,
    open_short_trade,
    redeem_withdraw_shares_trade,
    remove_liquidity_trade,
)
from agent0.core.hyperdrive.crash_report import build_crash_trade_result, log_hyperdrive_crash_report
from agent0.ethpy.base.errors import ContractCallException, ContractCallType

from .hyperdrive_policy import HyperdriveBasePolicy

if TYPE_CHECKING:
    from agent0.core.hyperdrive import HyperdriveMarketAction, HyperdriveWallet
    from agent0.ethpy.hyperdrive import HyperdriveReadInterface
    from agent0.ethpy.hyperdrive.state import PoolState

# We can allow unused arguments here because this is a template and extendable class.
# pylint: disable=unused-argument
# ruff: noqa: PLR0911 (lots of return statements)


class Random(HyperdriveBasePolicy):
    """Random agent."""

    @classmethod
    def description(cls) -> str:
        """Describe the policy in a user friendly manner that allows newcomers to decide whether to use it.

        Returns
        -------
        str
            A description of the policy.
        """
        raw_description = """
        A simple demonstration agent that chooses its actions randomly.
        It can take 7 actions: open/close longs and shorts, add/remove liquidity, and redeem withdraw shares.
        Trade size is randomly drawn from a normal distribution with mean of 10% of budget and standard deviation of 1% of budget.
        A close action picks a random open position of the given type (long or short) and attempts to close its entire size.
        Withdrawals of liquidity and redemption of withdrawal shares is sized the same as an open position: N(0.1, 0.01) * budget.
        """
        return super().describe(raw_description)

    @dataclass(kw_only=True)
    class Config(HyperdriveBasePolicy.Config):
        """Custom config arguments for this policy."""

        trade_chance: FixedPoint = FixedPoint("1.0")
        """The probability of this bot to make a trade on an action call."""
        randomly_ignore_slippage_tolerance: bool = False
        """If we randomly ignore slippage tolerance."""
        allowable_actions: list[HyperdriveActionType] = field(
            default_factory=lambda: [
                HyperdriveActionType.OPEN_LONG,
                HyperdriveActionType.OPEN_SHORT,
                HyperdriveActionType.ADD_LIQUIDITY,
                HyperdriveActionType.CLOSE_LONG,
                HyperdriveActionType.CLOSE_SHORT,
                HyperdriveActionType.REMOVE_LIQUIDITY,
                HyperdriveActionType.REDEEM_WITHDRAW_SHARE,
            ]
        )
        """
        A list of Hyperdrive actions that are allowed.
        Defaults to all possible actions.
        """

    def __init__(self, policy_config: Config) -> None:
        """Initialize the bot.

        Arguments
        ---------
        policy_config: Config
            The custom arguments for this policy
        """
        self.trade_chance = policy_config.trade_chance
        self.allowable_actions = policy_config.allowable_actions
        self.randomly_ignore_slippage_tolerance = policy_config.randomly_ignore_slippage_tolerance
        self.gas_limit = policy_config.gas_limit
        super().__init__(policy_config)

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
        # prevent accidental override
        # compile a list of all actions
        if wallet.balance.amount <= pool_state.pool_config.minimum_transaction_amount:
            all_available_actions = []
        else:
            all_available_actions = [
                HyperdriveActionType.OPEN_LONG,
                HyperdriveActionType.OPEN_SHORT,
                HyperdriveActionType.ADD_LIQUIDITY,
            ]
        if wallet.longs:  # if the agent has open longs
            all_available_actions.append(HyperdriveActionType.CLOSE_LONG)
        if wallet.shorts:  # if the agent has open shorts
            all_available_actions.append(HyperdriveActionType.CLOSE_SHORT)
        if wallet.lp_tokens:
            all_available_actions.append(HyperdriveActionType.REMOVE_LIQUIDITY)
        if wallet.withdraw_shares and pool_state.pool_info.withdrawal_shares_ready_to_withdraw > 0:
            all_available_actions.append(HyperdriveActionType.REDEEM_WITHDRAW_SHARE)
        # down select from all actions to only include allowed actions
        return [action for action in all_available_actions if action in self.allowable_actions]

    def open_short_with_random_amount(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> list[Trade[HyperdriveMarketAction]]:
        """Open a short with a random allowable amount.

        Arguments
        ---------
        interface: HyperdriveReadInterface
            Interface for the market on which this agent will be executing trades (MarketActions).
        wallet: HyperdriveWallet
            The agent's wallet.

        Returns
        -------
        list[Trade[HyperdriveMarketAction]]
            A list with a single Trade element for opening a Hyperdrive short.
        """
        # Calc max short is crashing, we surround in try catch to log
        try:
            maximum_trade_amount = interface.calc_max_short(wallet.balance.amount, interface.current_pool_state)
        # TODO pyo3 throws a PanicException here, which is derived from BaseException
        # Ideally, we would import the exact exception in python here, but pyo3 doesn't
        # expose this exception. Need to (1) fix the underlying calc_max_short bug, or
        # (2) throw a python exception in the underlying rust code when this happens.
        except BaseException as orig_exception:  # pylint: disable=broad-except
            # TODO while this isn't strictly a contract call exception, we used the class
            # to keep track of the original exception
            exception = ContractCallException(
                "Random policy: Error in rust call to calc_max_short",
                orig_exception=orig_exception,
                contract_call_type=ContractCallType.READ,
                function_name_or_signature="rust::calc_max_short",
                fn_args=(wallet.balance.amount, interface.current_pool_state),
            )
            crash_report = build_crash_trade_result(exception, interface)
            # TODO get these parameters from config
            log_hyperdrive_crash_report(
                crash_report,
                logging.ERROR,
                crash_report_to_file=True,
                crash_report_file_prefix="",
                log_to_rollbar=True,
            )
            # We don't return a trade here if this fails
            return []

        if maximum_trade_amount <= interface.pool_config.minimum_transaction_amount:
            return []

        initial_trade_amount = FixedPoint(
            self.rng.normal(loc=float(wallet.balance.amount) * 0.1, scale=float(wallet.balance.amount) * 0.01)
        )
        # minimum_transaction_amount <= trade_amount <= max_short
        trade_amount = max(
            interface.pool_config.minimum_transaction_amount, min(initial_trade_amount, maximum_trade_amount)
        )
        # optionally ignore slippage tolerance
        ignore_slippage = self.rng.choice([True, False], size=1) if self.randomly_ignore_slippage_tolerance else False
        if ignore_slippage:
            slippage = None
        else:
            slippage = self.slippage_tolerance
        # return a trade using a specification that is parsable by the rest of the sim framework
        return [
            open_short_trade(
                trade_amount, slippage, self.config.base_fee_multiple, self.config.priority_fee_multiple, self.gas_limit
            )
        ]

    def close_random_short(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> list[Trade[HyperdriveMarketAction]]:
        """Fully close the short balance for a random mint time.

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
        # choose a random short time to close
        short_time = list(wallet.shorts)[self.rng.integers(len(wallet.shorts))]
        trade_amount = wallet.shorts[short_time].balance  # close the full trade
        # optionally ignore slippage tolerance
        ignore_slippage = self.rng.choice([True, False], size=1) if self.randomly_ignore_slippage_tolerance else False
        if ignore_slippage:
            slippage = None
        else:
            slippage = self.slippage_tolerance
        # return a trade using a specification that is parsable by the rest of the sim framework
        return [
            close_short_trade(
                trade_amount,
                short_time,
                slippage,
                self.config.base_fee_multiple,
                self.config.priority_fee_multiple,
                self.gas_limit,
            )
        ]

    def open_long_with_random_amount(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> list[Trade[HyperdriveMarketAction]]:
        """Open a long with a random allowable amount.

        Arguments
        ---------
        interface: HyperdriveReadInterface
            Interface for the market on which this agent will be executing trades (MarketActions).
        wallet: HyperdriveWallet
            The agent's wallet.

        Returns
        -------
        list[Trade[HyperdriveMarketAction]]
            A list with a single Trade element for opening a Hyperdrive long.
        """
        try:
            maximum_trade_amount = interface.calc_max_long(wallet.balance.amount, interface.current_pool_state)
        # TODO pyo3 throws a PanicException here, which is derived from BaseException
        # Ideally, we would import the exact exception in python here, but pyo3 doesn't
        # expose this exception. Need to (1) fix the underlying calc_max_short bug, or
        # (2) throw a python exception in the underlying rust code when this happens.
        except BaseException as orig_exception:  # pylint: disable=broad-except
            # TODO while this isn't strictly a contract call exception, we used the class
            # to keep track of the original exception
            exception = ContractCallException(
                "Random policy: Error in rust call to calc_max_long",
                orig_exception=orig_exception,
                contract_call_type=ContractCallType.READ,
                function_name_or_signature="rust::calc_max_long",
                fn_args=(wallet.balance.amount, interface.current_pool_state),
            )
            crash_report = build_crash_trade_result(exception, interface)
            # TODO get these parameters from config
            log_hyperdrive_crash_report(
                crash_report,
                logging.ERROR,
                crash_report_to_file=True,
                crash_report_file_prefix="",
                log_to_rollbar=True,
            )
            # We don't return a trade here if this fails
            return []
        if maximum_trade_amount <= interface.pool_config.minimum_transaction_amount:
            return []
        # take a guess at the trade amount, which should be about 10% of the agent’s budget
        initial_trade_amount = FixedPoint(
            self.rng.normal(loc=float(wallet.balance.amount) * 0.1, scale=float(wallet.balance.amount) * 0.01)
        )
        # minimum_transaction_amount <= trade_amount <= max long
        trade_amount = max(
            interface.pool_config.minimum_transaction_amount, min(initial_trade_amount, maximum_trade_amount)
        )
        # optionally ignore slippage tolerance
        ignore_slippage = self.rng.choice([True, False], size=1) if self.randomly_ignore_slippage_tolerance else False
        if ignore_slippage:
            slippage = None
        else:
            slippage = self.slippage_tolerance
        # return a trade using a specification that is parsable by the rest of the sim framework
        return [
            open_long_trade(
                trade_amount, slippage, self.config.base_fee_multiple, self.config.priority_fee_multiple, self.gas_limit
            )
        ]

    def close_random_long(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> list[Trade[HyperdriveMarketAction]]:
        """Fully close the long balance for a random mint time.

        Arguments
        ---------
        interface: HyperdriveReadInterface
            Interface for the market on which this agent will be executing trades (MarketActions).
        wallet: HyperdriveWallet
            The agent's wallet.

        Returns
        -------
        list[Trade[HyperdriveMarketAction]]
            A list with a single Trade element for closing a Hyperdrive long.
        """
        # choose a random long time to close
        long_time = list(wallet.longs)[self.rng.integers(len(wallet.longs))]
        trade_amount = wallet.longs[long_time].balance  # close the full trade
        # optionally ignore slippage tolerance
        ignore_slippage = self.rng.choice([True, False], size=1) if self.randomly_ignore_slippage_tolerance else False
        if ignore_slippage:
            slippage = None
        else:
            slippage = self.slippage_tolerance
        # return a trade using a specification that is parsable by the rest of the sim framework
        return [
            close_long_trade(
                trade_amount,
                long_time,
                slippage,
                self.config.base_fee_multiple,
                self.config.priority_fee_multiple,
                self.gas_limit,
            )
        ]

    def add_liquidity_with_random_amount(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> list[Trade[HyperdriveMarketAction]]:
        """Add liquidity with a random allowable amount.

        Arguments
        ---------
        interface: HyperdriveReadInterface
            Interface for the market on which this agent will be executing trades (MarketActions).
        wallet: HyperdriveWallet
            The agent's wallet.

        Returns
        -------
        list[Trade[HyperdriveMarketAction]]
            A list with a single Trade element for adding liquidity to a Hyperdrive pool.
        """
        # take a guess at the trade amount, which should be about 10% of the agent’s budget
        initial_trade_amount = FixedPoint(
            self.rng.normal(loc=float(wallet.balance.amount) * 0.1, scale=float(wallet.balance.amount) * 0.01)
        )
        # minimum_transaction_amount <= trade_amount
        trade_amount: FixedPoint = max(
            interface.pool_config.minimum_transaction_amount, min(wallet.balance.amount, initial_trade_amount)
        )
        # return a trade using a specification that is parsable by the rest of the sim framework
        return [
            add_liquidity_trade(
                trade_amount, self.config.base_fee_multiple, self.config.priority_fee_multiple, self.gas_limit
            )
        ]

    def remove_liquidity_with_random_amount(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> list[Trade[HyperdriveMarketAction]]:
        """Remove liquidity with a random allowable amount.

        Arguments
        ---------
        interface: HyperdriveReadInterface
            Interface for the market on which this agent will be executing trades (MarketActions).
        wallet: HyperdriveWallet
            The agent's wallet.

        Returns
        -------
        list[Trade[HyperdriveMarketAction]]
            A list with a single Trade element for removing liquidity from a Hyperdrive pool.
        """
        # take a guess at the trade amount, which should be about 10% of the agent’s budget
        initial_trade_amount = FixedPoint(
            self.rng.normal(loc=float(wallet.balance.amount) * 0.1, scale=float(wallet.balance.amount) * 0.01)
        )
        # minimum_transaction_amount <= trade_amount <= lp_tokens
        trade_amount = max(
            interface.pool_config.minimum_transaction_amount, min(wallet.lp_tokens, initial_trade_amount)
        )
        # optionally ignore slippage tolerance
        ignore_slippage = self.rng.choice([True, False], size=1) if self.randomly_ignore_slippage_tolerance else False
        if ignore_slippage:
            slippage = None
        else:
            slippage = self.slippage_tolerance
        # return a trade using a specification that is parsable by the rest of the sim framework
        return [
            remove_liquidity_trade(
                trade_amount, slippage, self.config.base_fee_multiple, self.config.priority_fee_multiple, self.gas_limit
            )
        ]

    def redeem_withdraw_shares_with_random_amount(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> list[Trade[HyperdriveMarketAction]]:
        """Redeem withdraw shares with a random allowable amount.

        Arguments
        ---------
        interface: HyperdriveReadInterface
            Interface for the market on which this agent will be executing trades (MarketActions).
        wallet: HyperdriveWallet
            The agent's wallet.

        Returns
        -------
        list[Trade[HyperdriveMarketAction]]
            A list with a single Trade element for redeeming the LP withdraw shares.
        """
        # take a guess at the trade amount, which should be about 10% of the agent’s budget
        # TODO we may want to use a different mean/std here, as this is based on the agent's base balance
        # but we're trying to redeem withdraw shares here.
        initial_trade_amount = FixedPoint(
            self.rng.normal(loc=float(wallet.balance.amount) * 0.1, scale=float(wallet.balance.amount) * 0.01)
        )
        shares_available_to_withdraw = min(
            wallet.withdraw_shares,
            interface.current_pool_state.pool_info.withdrawal_shares_ready_to_withdraw,
        )

        # trade_amount <= withdraw_shares
        trade_amount = min(shares_available_to_withdraw, initial_trade_amount)

        # return a trade using a specification that is parsable by the rest of the sim framework
        return [
            redeem_withdraw_shares_trade(
                trade_amount, self.config.base_fee_multiple, self.config.priority_fee_multiple, self.gas_limit
            )
        ]

    def action(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """Implement a random user strategy.

        The agent performs one of four possible trades:
            [OPEN_LONG, OPEN_SHORT, CLOSE_LONG, CLOSE_SHORT]
            with the condition that close actions can only be performed after open actions

        The amount opened and closed is random, within constraints given by agent budget & market reserve levels

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
        # pylint: disable=too-many-return-statements

        # check if the agent will trade this block or not
        gonna_trade = self.rng.choice([True, False], p=[float(self.trade_chance), 1 - float(self.trade_chance)])
        if not gonna_trade:
            return [], False

        # user can always open a trade, and can close a trade if one is open
        available_actions = self.get_available_actions(wallet, interface.current_pool_state)
        if not available_actions:  # it's possible that no actions are available at this time
            return [], False

        # randomly choose one of the possible actions
        action_type = available_actions[self.rng.integers(len(available_actions))]

        # trade amount is also randomly chosen to be close to 10% of the agent's budget
        if action_type == HyperdriveActionType.OPEN_SHORT:
            return self.open_short_with_random_amount(interface, wallet), False
        if action_type == HyperdriveActionType.CLOSE_SHORT:
            return self.close_random_short(interface, wallet), False
        if action_type == HyperdriveActionType.OPEN_LONG:
            return self.open_long_with_random_amount(interface, wallet), False
        if action_type == HyperdriveActionType.CLOSE_LONG:
            return self.close_random_long(interface, wallet), False
        if action_type == HyperdriveActionType.ADD_LIQUIDITY:
            return self.add_liquidity_with_random_amount(interface, wallet), False
        if action_type == HyperdriveActionType.REMOVE_LIQUIDITY:
            return self.remove_liquidity_with_random_amount(interface, wallet), False
        if action_type == HyperdriveActionType.REDEEM_WITHDRAW_SHARE:
            return (self.redeem_withdraw_shares_with_random_amount(interface, wallet), False)
        return [], False

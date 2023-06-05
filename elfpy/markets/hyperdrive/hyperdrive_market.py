"""Market simulators store state information when interfacing AMM pricing models with users."""
from __future__ import annotations
import copy
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import elfpy
import elfpy.errors.errors as errors
import elfpy.markets.hyperdrive.hyperdrive_actions as hyperdrive_actions
import elfpy.markets.hyperdrive.hyperdrive_pricing_model as hyperdrive_pm
import elfpy.time as time
import elfpy.types as types
import elfpy.utils.price as price_utils

from elfpy.markets.base.base_market import BaseMarketState, BaseMarket
from elfpy.markets.hyperdrive.hyperdrive_market_deltas import HyperdriveMarketDeltas
from elfpy.markets.hyperdrive.checkpoint import Checkpoint
from elfpy.math import FixedPoint
from elfpy.types import Quantity, TokenType
from elfpy.wallet.wallet_deltas import WalletDeltas

if TYPE_CHECKING:
    from elfpy.wallet.wallet import Wallet

# dataclasses can have many attributes
# pylint: disable=too-many-instance-attributes


@types.freezable(frozen=False, no_new_attribs=False)
@dataclass
class HyperdriveMarketState(BaseMarketState):
    r"""The state of an AMM

    Attributes
    ----------
    lp_total_supply: FixedPoint
        Amount of lp tokens
    share_reserves: FixedPoint
        Quantity of shares stored in the market
    bond_reserves: FixedPoint
        Quantity of bonds stored in the market
    base_buffer: FixedPoint
        Base amount set aside to account for open longs
    bond_buffer: FixedPoint
        Bond amount set aside to account for open shorts
    variable_apr: FixedPoint
        apr of underlying yield-bearing source
    share_price: FixedPoint
        ratio of value of base & shares that are stored in the underlying vault,
        i.e. share_price = base_value / share_value
    init_share_price: FixedPoint
        share price at pool initialization
    curve_fee_multiple: FixedPoint
        The multiple applied to the price discount (1-p) to calculate the trade fee.
    flat_fee_multiple: FixedPoint
        A flat fee applied to the output.  Not used in this equation for Yieldspace.
    governance_fee_multiple: FixedPoint
        The multiple applied to the trade and flat fee to calculate the share paid to governance.
    gov_fees_accrued: FixedPoint
        The amount of governance fees that haven't been collected yet, denominated in shares.
    longs_outstanding: FixedPoint
        The amount of longs that are still open.
    shorts_outstanding: FixedPoint
        The amount of shorts that are still open.
    long_average_maturity_time: FixedPoint
        The average maturity time of long positions.
    short_average_maturity_time: FixedPoint
        The average maturity time of short positions.
    long_base_volume: FixedPoint
        The amount of base paid by outstanding longs.
    short_base_volume: FixedPoint
        The amount of base paid to outstanding shorts.
    checkpoints: dict[FixedPoint, elfpy.markets.hyperdrive.checkpoint.Checkpoint]
        Time delimited checkpoints
    checkpoint_duration: FixedPoint
        Time between checkpoints, defaults to 1 day
    total_supply_longs: dict[FixedPoint, FixedPoint]
        Checkpointed total supply for longs stored as {checkpoint_time: bond_amount}
    total_supply_shorts: dict[FixedPoint, FixedPoint]
        Checkpointed total supply for shorts stored as {checkpoint_time: bond_amount}
    total_supply_withdraw_shares: FixedPoint
        Total amount of withdraw shares outstanding
    withdraw_shares_ready_to_withdraw: FixedPoint
        Shares that have been freed up to withdraw by withdraw_shares
    withdraw_capital: FixedPoint
        The margin capital reclaimed by the withdraw process
    withdraw_interest: FixedPoint
        The interest earned by the redemptions which put capital into the withdraw pool
    """

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        return setattr(self, key, value)

    lp_total_supply: FixedPoint = FixedPoint(0)
    share_reserves: FixedPoint = FixedPoint(0)
    bond_reserves: FixedPoint = FixedPoint(0)
    base_buffer: FixedPoint = FixedPoint(0)
    bond_buffer: FixedPoint = FixedPoint(0)
    variable_apr: FixedPoint = FixedPoint(0)
    share_price: FixedPoint = FixedPoint(1.0)  # == 1e18
    init_share_price: FixedPoint = FixedPoint(1.0)  # == 1e18
    curve_fee_multiple: FixedPoint = FixedPoint(0)
    flat_fee_multiple: FixedPoint = FixedPoint(0)
    governance_fee_multiple: FixedPoint = FixedPoint(0)
    gov_fees_accrued: FixedPoint = FixedPoint(0)
    longs_outstanding: FixedPoint = FixedPoint(0)
    shorts_outstanding: FixedPoint = FixedPoint(0)
    long_average_maturity_time: FixedPoint = FixedPoint(0)
    short_average_maturity_time: FixedPoint = FixedPoint(0)
    long_base_volume: FixedPoint = FixedPoint(0)
    short_base_volume: FixedPoint = FixedPoint(0)
    checkpoints: dict[FixedPoint, Checkpoint] = field(default_factory=dict)
    checkpoint_duration: FixedPoint = FixedPoint("1.0").div_up(FixedPoint("365.0"))
    checkpoint_duration_days: FixedPoint = FixedPoint("1.0")
    total_supply_longs: dict[FixedPoint, FixedPoint] = field(default_factory=dict)
    total_supply_shorts: dict[FixedPoint, FixedPoint] = field(default_factory=dict)
    total_supply_withdraw_shares: FixedPoint = FixedPoint(0)
    withdraw_shares_ready_to_withdraw: FixedPoint = FixedPoint(0)
    withdraw_capital: FixedPoint = FixedPoint(0)
    withdraw_interest: FixedPoint = FixedPoint(0)

    def apply_delta(self, delta: HyperdriveMarketDeltas) -> None:
        r"""Applies a delta to the market state."""
        # assets & prices
        self.share_reserves += delta.d_base_asset / self.share_price
        self.bond_reserves += delta.d_bond_asset
        self.base_buffer += delta.d_base_buffer
        self.bond_buffer += delta.d_bond_buffer
        self.lp_total_supply += delta.d_lp_total_supply
        self.share_price += delta.d_share_price
        # tracking open positions
        self.longs_outstanding += delta.longs_outstanding
        self.shorts_outstanding += delta.shorts_outstanding
        self.long_average_maturity_time += delta.long_average_maturity_time
        self.short_average_maturity_time += delta.short_average_maturity_time
        self.long_base_volume += delta.long_base_volume
        self.short_base_volume += delta.short_base_volume
        # tracking shares after closing positions
        self.total_supply_withdraw_shares += delta.total_supply_withdraw_shares
        self.withdraw_shares_ready_to_withdraw += delta.withdraw_shares_ready_to_withdraw
        self.withdraw_capital += delta.withdraw_capital
        self.withdraw_interest += delta.withdraw_interest
        # checkpointing
        for mint_time, delta_checkpoint in delta.long_checkpoints.items():
            self.checkpoints.get(mint_time, Checkpoint()).long_base_volume += delta_checkpoint
        for mint_time, delta_checkpoint in delta.short_checkpoints.items():
            self.checkpoints.get(mint_time, Checkpoint()).short_base_volume += delta_checkpoint
        for mint_time, delta_supply in delta.total_supply_longs.items():
            self.total_supply_longs[mint_time] = self.total_supply_longs.get(mint_time, FixedPoint(0)) + delta_supply
        for mint_time, delta_supply in delta.total_supply_shorts.items():
            self.total_supply_shorts[mint_time] = self.total_supply_shorts.get(mint_time, FixedPoint(0)) + delta_supply

    def copy(self) -> HyperdriveMarketState:
        """Returns a new copy of self"""
        return HyperdriveMarketState(**copy.deepcopy(self.__dict__))

    def check_valid_market_state(self, dictionary: dict | None = None) -> None:
        """Test that all market state variables are greater than zero"""
        if dictionary is None:
            dictionary = self.__dict__
        elfpy.check_non_zero(dictionary)


class HyperdriveMarket(
    BaseMarket[
        HyperdriveMarketState,
        HyperdriveMarketDeltas,
        hyperdrive_pm.HyperdrivePricingModel,
    ]
):
    r"""Market state simulator

    Holds state variables for market simulation and executes trades.
    The Market class executes trades by updating market variables according to the given pricing model.
    It also has some helper variables for assessing pricing model values given market conditions.
    """

    def __init__(
        self,
        pricing_model: hyperdrive_pm.HyperdrivePricingModel,
        market_state: HyperdriveMarketState,
        position_duration: time.StretchedTime,
        block_time: time.BlockTime,
    ):
        # market state variables
        assert (
            position_duration.days == position_duration.normalizing_constant
        ), "position_duration argument term length (days) should normalize to 1"
        self.position_duration = position_duration
        # NOTE: lint error false positives: This message may report object members that are created dynamically,
        # but exist at the time they are accessed.
        self.position_duration.freeze()  # pylint: disable=no-member # type: ignore
        super().__init__(pricing_model=pricing_model, market_state=market_state, block_time=block_time)

    @property
    def time_stretch_constant(self) -> FixedPoint:
        r"""Returns the market time stretch constant"""
        return self.position_duration.time_stretch

    @property
    def annualized_position_duration(self) -> FixedPoint:
        r"""Returns the position duration in years"""
        return self.position_duration.days / FixedPoint("365.0")

    @property
    def fixed_apr(self) -> FixedPoint:
        """Returns the current market apr"""
        # calc_apr_from_spot_price will throw an error if share_reserves < zero
        if self.market_state.share_reserves < FixedPoint(0):
            raise OverflowError(f"Share reserves should be >= 0, not {self.market_state.share_reserves}")
        if self.market_state.share_price == FixedPoint(0):
            return FixedPoint("nan")
        return price_utils.calc_apr_from_spot_price(price=self.spot_price, time_remaining=self.position_duration)

    @property
    def spot_price(self) -> FixedPoint:
        """Returns the current market price of the share reserves"""
        return self.pricing_model.calc_spot_price_from_reserves(
            market_state=self.market_state,
            time_remaining=self.position_duration,
        )

    @property
    def latest_checkpoint_time(self) -> FixedPoint:
        """Gets the most recent checkpoint time"""
        # scale up to days
        block_time_days = self.block_time.time * FixedPoint("365.0")
        # compute checkpoint
        latest_checkpoint_days = block_time_days - (block_time_days % self.market_state.checkpoint_duration_days)
        # scale back down
        latest_checkpoint = latest_checkpoint_days / FixedPoint("365.0")
        return latest_checkpoint

    # TODO: this function should optionally accept a target apr.  the short should not slip the
    # market fixed rate below the APR when opening the long
    # issue #213
    def get_max_long_for_account(self, account_balance: FixedPoint) -> FixedPoint:
        """Gets an approximation of the maximum amount of base the agent can use.

        Typically would be called to determine how much to enter into a long position.

        Arguments
        ----------
        account_balance : FixedPoint
            Alternative maximum, for example the balance of an Agent's wallet

        Returns
        -------
        FixedPoint
            Maximum amount the agent can use to open a long
        """
        (max_long, _) = self.pricing_model.get_max_long(
            market_state=self.market_state,
            time_remaining=self.position_duration,
        )
        return min(account_balance, max_long)

    # TODO: this function should optionally accept a target apr.  the short should not slip the
    # market fixed rate above the APR when opening the short
    # issue #213
    def get_max_short_for_account(self, account_balance: FixedPoint) -> FixedPoint:
        """Gets an approximation of the maximum amount of bonds the agent can short.

        Arguments
        ----------
        account_balance : FixedPoint
            Alternative maximum, for example the balance of an Agent's wallet

        Returns
        -------
        FixedPoint
            Amount of base that the agent can short in the current market
        """
        # Get the market level max short.
        if hasattr(self.pricing_model, "get_max_short"):
            (max_short_max_loss, max_short) = self.pricing_model.get_max_short(
                market_state=self.market_state,
                time_remaining=self.position_duration,
            )
        else:  # no maximum
            max_short_max_loss, max_short = FixedPoint("inf"), FixedPoint("inf")
        # If the Agent's base balance can cover the max loss of the maximum
        # short, we can simply return the maximum short.
        if account_balance >= max_short_max_loss:
            return max_short
        last_maybe_max_short = FixedPoint(0)
        bond_percent = FixedPoint("1.0")
        num_iters = 25
        for step_size in [FixedPoint(1 / (2 ** (x + 1))) for x in range(num_iters)]:
            # Compute the amount of base returned by selling the specified
            # amount of bonds.
            maybe_max_short = max_short * bond_percent
            trade_result = self.pricing_model.calc_out_given_in(
                in_=Quantity(amount=maybe_max_short, unit=TokenType.PT),
                market_state=self.market_state,
                time_remaining=self.position_duration,
            )
            # If the max loss is greater than the wallet's base, we need to
            # decrease the bond percentage. Otherwise, we may have found the
            # max short, and we should increase the bond percentage.
            max_loss = maybe_max_short - trade_result.user_result.d_base
            if max_loss > account_balance:
                bond_percent -= step_size
            else:
                last_maybe_max_short = maybe_max_short
                if bond_percent == FixedPoint("1.0"):
                    return last_maybe_max_short
                bond_percent += step_size
        # do one more iteration at the last step size in case the bisection method was stuck
        # approaching a max_short value with slightly more base than an agent has.
        trade_result = self.pricing_model.calc_out_given_in(
            in_=Quantity(amount=last_maybe_max_short, unit=TokenType.PT),
            market_state=self.market_state,
            time_remaining=self.position_duration,
        )
        max_loss = last_maybe_max_short - trade_result.user_result.d_base
        last_step_size = FixedPoint("1.0") / (FixedPoint("2.0") ** FixedPoint(num_iters) + FixedPoint("1.0"))
        if max_loss > account_balance:
            bond_percent -= last_step_size
            last_maybe_max_short = max_short * bond_percent
        max_short = min(account_balance, last_maybe_max_short)
        return max_short

    def perform_action(
        self, action_details: tuple[int, hyperdrive_actions.HyperdriveMarketAction]
    ) -> tuple[int, WalletDeltas, HyperdriveMarketDeltas]:
        r"""Execute a trade in the simulated market

        Checks which of 6 action types are being executed, and handles each case:

        Open & close a long
            When a trader opens a long, they put up base and are given long tokens.
            As time passes, an amount of the longs proportional to the time that has
            passed are considered to be “mature” and can be redeemed one-to-one.
            The remaining amount of longs are sold on the internal AMM. The trader
            does not receive any variable interest from their long positions,
            so the only money they make on closing is from the long maturing and the
            fixed rate changing.

        Open & close a short
            When a trader opens a short, they put up base (typically much smaller
            than the amount that longs have to pay) and are given short tokens. As
            time passes, an amount of the shorts proportional to the time that has
            passed are considered to be “mature” and must be paid for one-to-one by
            the short. The remaining amount of shorts are sold on the internal AMM
            and the short has to pay the price. The short receives any variable
            interest collected on the full amount of base that underlies the short
            (equal to the face value of the short) as well as the spread between the
            money the AMM committed at the beginning of the trade and the money the
            short has to pay when closing the trade.

        Add liquidity
            When a trader adds liquidity, they put up base tokens and receive LP shares.
            If there are not any open positions, the LP receives the same amount of LP shares
            that they would if they were supplying liquidity to uniswap.
            To make sure that new LPs do not get rugged (or rug previous LPs),
            we modify the share reserves used in the LP share calculation by subtracting
            the present value of open longs and adding the present value of the open shorts.

        Remove liquidity
            When a trader redeems their Liquidity Provider (LP) shares, they will receive a combination of base
            tokens and “withdrawal shares”. Since some of the LPs capital may be backing
            open positions, we give them withdrawal shares which pay out when the positions
            are closed. These withdrawal shares receive a steady stream of proceeds from long
            and short positions when they are closed or mature.
        """
        agent_id, agent_action = action_details
        # TODO: add use of the Quantity type to enforce units while making it clear what units are being used
        # issue 216
        # mint time is required if closing a position
        if (
            agent_action.action_type
            in [
                hyperdrive_actions.MarketActionType.CLOSE_LONG,
                hyperdrive_actions.MarketActionType.CLOSE_SHORT,
            ]
            and agent_action.mint_time is None
        ):
            raise ValueError(f"{agent_action.mint_time=} must be provided when closing a short or long")
        # for each position, specify how to forumulate trade and then execute
        if agent_action.action_type == hyperdrive_actions.MarketActionType.OPEN_LONG:  # buy to open long
            market_deltas, agent_deltas = self.open_long(
                agent_wallet=agent_action.wallet,
                base_amount=agent_action.trade_amount,  # in base: that's the thing in your wallet you want to sell
            )
        elif agent_action.action_type == hyperdrive_actions.MarketActionType.CLOSE_LONG:  # sell to close long
            # TODO: python 3.10 includes TypeGuard which properly avoids issues when using Optional type
            mint_time = FixedPoint(agent_action.mint_time or 0)
            market_deltas, agent_deltas = self.close_long(
                agent_wallet=agent_action.wallet,
                bond_amount=agent_action.trade_amount,  # in bonds: that's the thing in your wallet you want to sell
                mint_time=mint_time,
            )
        elif agent_action.action_type == hyperdrive_actions.MarketActionType.OPEN_SHORT:  # sell PT to open short
            market_deltas, agent_deltas = self.open_short(
                agent_wallet=agent_action.wallet,
                bond_amount=agent_action.trade_amount,  # in bonds: that's the thing you want to short
            )
        elif agent_action.action_type == hyperdrive_actions.MarketActionType.CLOSE_SHORT:  # buy PT to close short
            # TODO: python 3.10 includes TypeGuard which properly avoids issues when using Optional type
            mint_time = FixedPoint(agent_action.mint_time or 0)
            open_share_price = agent_action.wallet.shorts[mint_time].open_share_price
            market_deltas, agent_deltas = self.close_short(
                agent_wallet=agent_action.wallet,
                bond_amount=agent_action.trade_amount,  # in bonds: that's the thing you owe, and need to buy back
                mint_time=mint_time,
                open_share_price=open_share_price,
            )
        elif agent_action.action_type == hyperdrive_actions.MarketActionType.ADD_LIQUIDITY:
            market_deltas, agent_deltas = self.add_liquidity(
                agent_wallet=agent_action.wallet,
                bond_amount=agent_action.trade_amount,
            )
        elif agent_action.action_type == hyperdrive_actions.MarketActionType.REMOVE_LIQUIDITY:
            market_deltas, agent_deltas = self.remove_liquidity(
                agent_wallet=agent_action.wallet,
                lp_shares=agent_action.trade_amount,
            )
        else:
            raise ValueError(f"unknown {agent_action.action_type=}")
        # Make sure that the action did not cause negative market state values
        self.market_state.check_valid_market_state()
        logging.debug(
            "agent_action=%s\nmarket_deltas=%s\nagent_deltas = %s\npre_trade_market = %s",
            agent_action,
            market_deltas,
            agent_deltas,
            self.market_state,
        )
        return agent_id, agent_deltas, market_deltas

    def initialize(
        self, contribution: FixedPoint, target_apr: FixedPoint
    ) -> tuple[HyperdriveMarketDeltas, WalletDeltas]:
        """Market Deltas so that an LP can initialize the market"""
        if self.market_state.share_reserves > FixedPoint(0) or self.market_state.bond_reserves > FixedPoint(0):
            raise AssertionError("The market appears to already be initialized.")
        share_reserves = contribution / self.market_state.share_price
        bond_reserves = self.pricing_model.calc_initial_bond_reserves(
            target_apr=target_apr,
            time_remaining=self.position_duration,
            market_state=HyperdriveMarketState(
                share_reserves=share_reserves,
                init_share_price=self.market_state.init_share_price,
                share_price=self.market_state.share_price,
            ),
        )
        lp_tokens = self.market_state.share_price * share_reserves + bond_reserves
        # TODO: add lp_tokens to bond reserves per https://github.com/delvtech/hyperdrive/pull/140
        # bond_reserves += lp_tokens
        market_deltas = HyperdriveMarketDeltas(
            d_base_asset=contribution, d_bond_asset=bond_reserves, d_lp_total_supply=lp_tokens
        )
        agent_deltas = WalletDeltas(
            balance=-types.Quantity(amount=contribution, unit=types.TokenType.BASE),
            lp_tokens=lp_tokens,
        )
        self.update_market(market_deltas)
        self.market_state.check_valid_market_state()
        return market_deltas, agent_deltas

    def open_short(
        self,
        agent_wallet: Wallet,
        bond_amount: FixedPoint,
        max_deposit: FixedPoint = FixedPoint(2**32 * 10**18),
    ) -> tuple[HyperdriveMarketDeltas, WalletDeltas]:
        """Calculates the deltas from opening a short and then updates the agent wallet & market state"""
        # create/update the checkpoint
        _ = self.apply_checkpoint(self.latest_checkpoint_time, self.market_state.share_price)
        # calc market and agent deltas
        market_deltas, agent_deltas = hyperdrive_actions.calc_open_short(
            bond_amount,
            self.market_state,
            self.position_duration,
            self.pricing_model,
            self.block_time.time,
            self.latest_checkpoint_time,
        )
        # slippage protection
        if max_deposit < agent_deltas.balance.amount:
            raise errors.OutputLimit()
        # apply deltas
        self.market_state.apply_delta(market_deltas)
        agent_wallet.update(agent_deltas)
        return market_deltas, agent_deltas

    def close_short(
        self,
        agent_wallet: Wallet,
        open_share_price: FixedPoint,
        bond_amount: FixedPoint,
        mint_time: FixedPoint,
    ) -> tuple[HyperdriveMarketDeltas, WalletDeltas]:
        """Calculate the deltas from closing a short and then update the agent wallet & market state"""
        # create/update the checkpoint
        self.apply_checkpoint(mint_time, self.market_state.share_price)
        # calc market and agent deltas
        market_deltas, agent_deltas = hyperdrive_actions.calc_close_short(
            bond_amount,
            self.market_state,
            self.position_duration,
            self.pricing_model,
            self.block_time.time,
            mint_time,
            open_share_price,
        )
        # apply deltas
        self.market_state.apply_delta(market_deltas)
        agent_wallet.update(agent_deltas)
        return market_deltas, agent_deltas

    def open_long(
        self,
        agent_wallet: Wallet,
        base_amount: FixedPoint,
    ) -> tuple[HyperdriveMarketDeltas, WalletDeltas]:
        """Calculate the deltas from opening a long and then update the agent wallet & market state"""
        # create/update the checkpoint
        self.apply_checkpoint(self.latest_checkpoint_time, self.market_state.share_price)
        # calc market and agent deltas
        market_deltas, agent_deltas = hyperdrive_actions.calc_open_long(
            base_amount,
            self.market_state,
            self.position_duration,
            self.pricing_model,
            self.latest_checkpoint_time,
            self.spot_price,
        )
        # update long_share_price
        self.update_long_share_price(abs(market_deltas.d_bond_asset))
        # apply deltas
        self.market_state.apply_delta(market_deltas)
        agent_wallet.update(agent_deltas)
        return market_deltas, agent_deltas

    def update_long_share_price(self, bond_proceeds: FixedPoint) -> None:
        """Upates the weighted average share price for longs at the latest checkpoint."""
        # get default zero value if no checkpoint exists.
        checkpoint = self.market_state.checkpoints.get(self.latest_checkpoint_time, Checkpoint)
        long_share_price = checkpoint.long_share_price
        total_supply = self.market_state.total_supply_longs.get(self.latest_checkpoint_time, FixedPoint(0))
        updated_long_share_price = hyperdrive_actions.update_weighted_average(
            long_share_price, total_supply, self.market_state.share_price, bond_proceeds, True
        )
        self.market_state.checkpoints[self.latest_checkpoint_time].long_share_price = updated_long_share_price

    def close_long(
        self, agent_wallet: Wallet, bond_amount: FixedPoint, mint_time: FixedPoint
    ) -> tuple[HyperdriveMarketDeltas, WalletDeltas]:
        """Calculate the deltas from closing a long and then update the agent wallet & market state"""
        # create/update the checkpoint
        _ = self.apply_checkpoint(mint_time, self.market_state.share_price)
        # calc market and agent deltas
        market_deltas, agent_deltas = hyperdrive_actions.calc_close_long(
            bond_amount,
            self.market_state,
            self.position_duration,
            self.pricing_model,
            self.block_time.time,
            mint_time,
            is_trade=True,
        )
        # apply deltas
        self.market_state.apply_delta(market_deltas)
        agent_wallet.update(agent_deltas)
        return market_deltas, agent_deltas

    def add_liquidity(
        self,
        agent_wallet: Wallet,
        bond_amount: FixedPoint,
    ) -> tuple[HyperdriveMarketDeltas, WalletDeltas]:
        """Computes new deltas for bond & share reserves after liquidity is added"""
        _ = self.apply_checkpoint(self.latest_checkpoint_time, self.market_state.share_price)
        market_deltas, agent_deltas = hyperdrive_actions.calc_add_liquidity(
            bond_amount,
            self.market_state,
            self.position_duration,
            self.pricing_model,
            self.fixed_apr,
            self.block_time.time,
        )
        self.market_state.apply_delta(market_deltas)
        agent_wallet.update(agent_deltas)
        return market_deltas, agent_deltas

    def remove_liquidity(
        self,
        agent_wallet: Wallet,
        lp_shares: FixedPoint,
    ) -> tuple[HyperdriveMarketDeltas, WalletDeltas]:
        """Computes new deltas for bond & share reserves after liquidity is removed"""
        self.apply_checkpoint(self.latest_checkpoint_time, self.market_state.share_price)
        market_deltas, agent_deltas = hyperdrive_actions.calc_remove_liquidity(
            lp_shares,
            self.market_state,
            self.position_duration,
            self.pricing_model,
        )
        self.market_state.apply_delta(market_deltas)
        agent_wallet.update(agent_deltas)
        return market_deltas, agent_deltas

    def checkpoint(self, checkpoint_time: FixedPoint) -> None:
        """allows anyone to mint a new checkpoint."""
        # get default zero value if no checkpoint exists.
        checkpoint = self.market_state.checkpoints.get(checkpoint_time, Checkpoint())
        # if the checkpoint has already been set, return early.
        if checkpoint.share_price != FixedPoint(0):
            return
        # if the checkpoint time isn't divisible by the checkpoint duration
        # or is in the future, it's an invalid checkpoint and we should
        # revert.
        latest_checkpoint = self.latest_checkpoint_time
        checkpoint_time_days = checkpoint_time * FixedPoint("365.0")
        not_evenly_divisible = bool(
            (checkpoint_time_days) % (self.market_state.checkpoint_duration_days) > FixedPoint(0)
        )
        if not_evenly_divisible or latest_checkpoint < checkpoint_time:
            raise errors.InvalidCheckpointTime()
        # if the checkpoint time is the latest checkpoint, we use the current
        # share price. otherwise, we use a linear search to find the closest
        # share price and use that to perform the checkpoint.
        if checkpoint_time == latest_checkpoint:
            self.apply_checkpoint(latest_checkpoint, self.market_state.share_price)
        else:
            _time = checkpoint_time
            while True:
                checkpoint = self.market_state.checkpoints.get(_time, Checkpoint())
                closest_share_price = checkpoint.share_price
                if _time == latest_checkpoint:
                    closest_share_price = self.market_state.share_price
                if closest_share_price != FixedPoint(0):
                    self.apply_checkpoint(checkpoint_time, closest_share_price)
                    break
                _time += self.market_state.checkpoint_duration

    def apply_checkpoint(self, checkpoint_time: FixedPoint, share_price: FixedPoint) -> FixedPoint:
        r"""Creates a new checkpoint if necessary and closes matured positions.

        Arguments
        ----------
        checkpoint_time : FixedPoint
            The block time for the checkpoint to be created or cleared.
        share_price : FixedPoint
            The share price of the market at the checkpoint time.

        Returns
        -------
        FixedPoint
            The share price for the checkpoint after mature positions have been closed.
        """
        # get default zero value if no checkpoint exists.
        checkpoint = self.market_state.checkpoints.get(checkpoint_time, Checkpoint())
        # Return early if the checkpoint has already been updated.
        if checkpoint.share_price != FixedPoint(0) or checkpoint_time > self.block_time.time:
            return checkpoint.share_price
        # Create the share price checkpoint.
        self.market_state.checkpoints[checkpoint_time] = Checkpoint()
        self.market_state.checkpoints[checkpoint_time].share_price = share_price
        mint_time = checkpoint_time - self.annualized_position_duration
        # Close out any matured long positions and pay out the long withdrawal pool for longs that
        # have matured.
        matured_longs_amount = self.market_state.total_supply_longs.get(mint_time, FixedPoint(0))
        if matured_longs_amount > FixedPoint(0):
            market_deltas, _ = hyperdrive_actions.calc_close_long(
                matured_longs_amount,
                self.market_state,
                self.position_duration,
                self.pricing_model,
                self.block_time.time,
                mint_time,
                False,
            )
            self.market_state.apply_delta(market_deltas)
        # Close out any matured short positions and pay out the short withdrawal pool for shorts
        # that have matured.
        matured_shorts_amount = self.market_state.total_supply_shorts.get(mint_time, FixedPoint(0))
        if matured_shorts_amount > FixedPoint(0):
            checkpoint = self.market_state.checkpoints.get(mint_time, Checkpoint())
            open_share_price = checkpoint.share_price
            market_deltas, _ = hyperdrive_actions.calc_close_short(
                matured_shorts_amount,
                self.market_state,
                self.position_duration,
                self.pricing_model,
                self.block_time.time,
                mint_time,
                open_share_price,
            )
            self.market_state.apply_delta(market_deltas)
        return checkpoint.share_price

    def redeem_withdraw_shares(
        self,
        agent_wallet: Wallet,
        shares: FixedPoint,
        min_output: FixedPoint,
        as_underlying: bool,
    ) -> FixedPoint:
        r"""Redeems withdrawal shares if enough margin has been freed to do so.

        Arguments
        ----------
        agent_wallet : Wallet
            The agent's wallet.
        shares : FixedPoint
            The withdrawal shares to redeem.
        min_output : FixedPoint
            The minimum amount of base the LP expects to receive.
        as_underlying : bool
            If true, the user is paid in underlying, if false the contract transfers in yield source
            directly. Note - for some paths one choice may be disabled or blocked.

        Returns
        -------
        FixedPoint
            The amount of base the LP received.
        """

        # create a new checkpoint if necessary, close positions at the checkpoint time one
        # position_duration ago.
        self.apply_checkpoint(self.latest_checkpoint_time, self.market_state.share_price)
        market_deltas, wallet_deltas = self.calc_redeem_withdraw_shares(shares, min_output, as_underlying)
        self.update_market(market_deltas)
        agent_wallet.update(wallet_deltas)
        return wallet_deltas.balance.amount

    def calc_redeem_withdraw_shares(
        self, shares: FixedPoint, min_output: FixedPoint, as_underlying: bool
    ) -> tuple[HyperdriveMarketDeltas, WalletDeltas]:
        r"""Calculates the market and wallet deltas for redeemable withdrawal shares, if enough margin
        has been freed to do so.

        Arguments
        ----------
        shares : FixedPoint
            The withdrawal shares to redeem.
        min_output : FixedPoint
            The minimum amount of base the LP expects to receive.
        as_underlying : bool
            If true, the user is paid in underlying, if false the contract transfers in yield source
            directly. Note - for some paths one choice may be disabled or blocked.

        Returns
        -------
        tuple[hyperdrive_actions.MarketDeltas, AgentDeltas]

        """
        market_deltas = HyperdriveMarketDeltas()
        # TODO don't use a wallet. issue #315
        wallet_deltas = WalletDeltas()
        # We burn the shares from the user
        wallet_deltas.withdraw_shares -= shares
        # The user gets a refund on their margin equal to the face value of their withdraw shares
        # times the percent of the withdraw pool which has been lost.
        recovered_margin = (
            shares * self.market_state.withdraw_capital / self.market_state.withdraw_shares_ready_to_withdraw
        )
        # The user gets interest equal to their percent of the withdraw pool times the withdraw pool
        # interest
        recovered_interest = (
            shares * self.market_state.withdraw_interest / self.market_state.withdraw_shares_ready_to_withdraw
        )
        # Update the pool state
        # Note - Will revert here if not enough margin has been reclaimed by checkpoints or by
        #  position closes
        market_deltas.withdraw_shares_ready_to_withdraw -= shares
        market_deltas.withdraw_capital -= recovered_margin
        market_deltas.withdraw_interest -= recovered_interest
        # Withdraw for the user
        base_proceeds = self._withdraw(recovered_margin + recovered_interest, as_underlying)
        # TODO: figure out how to keep track of hyperdrive's base asset amount.  market_deltas has
        # a d_base_asset, but that is used to update the share_reserves :/.
        # market_deltas.d_base_asset -= base_proceeds
        wallet_deltas.balance.amount += base_proceeds
        # Enforce min user outputs
        if min_output > base_proceeds:
            raise errors.OutputLimit
        return market_deltas, wallet_deltas

    def _withdraw(self, shares: FixedPoint, as_underlying: bool) -> FixedPoint:
        r"""Calculates the amount of base to withdraw for a given amount of shares.

        Arguments
        ----------
        shares : FixedPoint
            The withdrawal shares to redeem.
        as_underlying : bool
            If true, the user is paid in underlying, if false the contract transfers in yield source
            directly. Note - for some paths one choice may be disabled or blocked.

        Returns
        -------
        FixedPoint
          The withdraw_value and share_price as a tuple.
        """
        # This yield source doesn't accept the underlying since it's just base.
        if not as_underlying:
            raise errors.UnsupportedOption
        # TODO: add step to accrue interest
        # Get the amount of base to transfer.
        amount_withdrawn = shares * self.market_state.share_price
        return amount_withdrawn

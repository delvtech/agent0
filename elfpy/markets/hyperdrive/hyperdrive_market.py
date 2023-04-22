"""Market simulators store state information when interfacing AMM pricing models with users."""
from __future__ import annotations

import copy
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal

import numpy as np

import elfpy.agents.wallet as wallet
import elfpy.errors.errors as errors
import elfpy.markets.base as base_market
import elfpy.markets.hyperdrive.hyperdrive_actions as hyperdrive_actions
import elfpy.pricing_models.hyperdrive as hyperdrive_pm
import elfpy.time as time
import elfpy.types as types
import elfpy.utils.price as price_utils
from elfpy.utils.math import FixedPoint

# dataclasses can have many attributes
# pylint: disable=too-many-instance-attributes

# TODO: remove this after FixedPoint PRs are finished
# pylint: disable=duplicate-code


@dataclass
class Checkpoint:
    """
    Hyperdrive positions are bucketed into checkpoints, which allows us to avoid poking in any
    period that has LP or trading activity. The checkpoints contain the starting share price from
    the checkpoint as well as aggregate volume values.
    """

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        return setattr(self, key, value)

    share_price: float = 0.0
    long_share_price: float = 0.0
    long_base_volume: float = 0.0
    short_base_volume: float = 0.0


@types.freezable(frozen=False, no_new_attribs=False)
@dataclass
class MarketState(base_market.BaseMarketState):
    r"""The state of an AMM

    Attributes
    ----------
    lp_total_supply: float
        Amount of lp tokens
    share_reserves: float
        Quantity of shares stored in the market
    bond_reserves: float
        Quantity of bonds stored in the market
    base_buffer: float
        Base amount set aside to account for open longs
    bond_buffer: float
        Bond amount set aside to account for open shorts
    variable_apr: float
        apr of underlying yield-bearing source
    share_price: float
        ratio of value of base & shares that are stored in the underlying vault,
        i.e. share_price = base_value / share_value
    init_share_price: float
        share price at pool initialization
    curve_fee_multiple: float
        The multiple applied to the price discount (1-p) to calculate the trade fee.
    flat_fee_multiple: float
        A flat fee applied to the output.  Not used in this equation for Yieldspace.
    governance_fee_multiple: float
        The multiple applied to the trade and flat fee to calculate the share paid to governance.
    gov_fees_accrued: float
        The amount of governance fees that haven't been collected yet, denominated in shares.
    longs_outstanding: float
        The amount of longs that are still open.
    shorts_outstanding: float
        The amount of shorts that are still open.
    long_average_maturity_time: float
        The average maturity time of long positions.
    short_average_maturity_time: float
        The average maturity time of short positions.
    long_base_volume: float
        The amount of base paid by outstanding longs.
    short_base_volume: float
        The amount of base paid to outstanding shorts.
    checkpoints: defaultdict[float, Checkpoint]
        Time delimited checkpoints
    checkpoint_duration: float
        Time between checkpoints, defaults to 1 day
    total_supply_longs: defaultdict[float, float]
        Checkpointed total supply for longs stored as {checkpoint_time: bond_amount}
    total_supply_shorts: defaultdict[float, float]
        Checkpointed total supply for shorts stored as {checkpoint_time: bond_amount}
    total_supply_withdraw_shares: float
        Total amount of withdraw shares outstanding
    withdraw_shares_ready_to_withdraw: float
        Shares that have been freed up to withdraw by withdraw_shares
    withdraw_capital: float
        The margin capital reclaimed by the withdraw process
    withdraw_interest: float
        The interest earned by the redemptions which put capital into the withdraw pool
    """

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        return setattr(self, key, value)

    lp_total_supply: float = 0.0
    share_reserves: float = 0.0
    bond_reserves: float = 0.0
    base_buffer: float = 0.0
    bond_buffer: float = 0.0
    variable_apr: float = 0.0
    share_price: float = 1.0
    init_share_price: float = 1.0
    curve_fee_multiple: float = 0.0
    flat_fee_multiple: float = 0.0
    governance_fee_multiple: float = 0.0
    gov_fees_accrued: float = 0.0
    longs_outstanding: float = 0.0
    shorts_outstanding: float = 0.0
    long_average_maturity_time: float = 0.0
    short_average_maturity_time: float = 0.0
    long_base_volume: float = 0.0
    short_base_volume: float = 0.0
    checkpoints: defaultdict[float, Checkpoint] = field(default_factory=lambda: defaultdict(Checkpoint))
    checkpoint_duration: float = field(default=1 / 365)
    total_supply_longs: defaultdict[float, float] = field(default_factory=lambda: defaultdict(float))
    total_supply_shorts: defaultdict[float, float] = field(default_factory=lambda: defaultdict(float))
    total_supply_withdraw_shares: float = 0.0
    withdraw_shares_ready_to_withdraw: float = 0.0
    withdraw_capital: float = 0.0
    withdraw_interest: float = 0.0

    def apply_delta(self, delta: hyperdrive_actions.MarketDeltas) -> None:
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
            self.checkpoints[mint_time].long_base_volume += delta_checkpoint
        for mint_time, delta_checkpoint in delta.short_checkpoints.items():
            self.checkpoints[mint_time].short_base_volume += delta_checkpoint
        for mint_time, delta_supply in delta.total_supply_longs.items():
            self.total_supply_longs[mint_time] += delta_supply
        for mint_time, delta_supply in delta.total_supply_shorts.items():
            self.total_supply_shorts[mint_time] += delta_supply

    def copy(self) -> MarketState:
        """Returns a new copy of self"""
        return MarketState(**copy.deepcopy(self.__dict__))


class Market(
    base_market.Market[
        MarketState,
        hyperdrive_actions.MarketDeltas,
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
        market_state: MarketState,
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
    def time_stretch_constant(self) -> float:
        r"""Returns the market time stretch constant"""
        return self.position_duration.time_stretch

    @property
    def annualized_position_duration(self) -> float:
        r"""Returns the position duration in years"""
        return self.position_duration.days / 365

    @property
    def fixed_apr(self) -> float:
        """Returns the current market apr"""
        # calc_apr_from_spot_price will throw an error if share_reserves <= zero
        # TODO: Negative values should never happen, but do because of rounding errors.
        #       Write checks to remedy this in the market.
        # issue #146

        if self.market_state.share_reserves <= 0:  # market is empty; negative value likely due to rounding error
            return np.nan
        return price_utils.calc_apr_from_spot_price(price=self.spot_price, time_remaining=self.position_duration)

    @property
    def spot_price(self) -> float:
        """Returns the current market price of the share reserves"""
        # calc_spot_price_from_reserves will throw an error if share_reserves is zero
        if self.market_state.share_reserves == 0:  # market is empty
            return np.nan
        return self.pricing_model.calc_spot_price_from_reserves(
            market_state=self.market_state,
            time_remaining=self.position_duration,
        )

    def check_action(self, agent_action: hyperdrive_actions.MarketAction) -> None:
        r"""Ensure that the agent action is an allowed action for this market

        Parameters
        ----------
        action_type : MarketActionType
            See MarketActionType for all acceptable actions that can be performed on this market

        Returns
        -------
        None
        """
        if (
            agent_action.action_type
            in [
                hyperdrive_actions.MarketActionType.CLOSE_LONG,
                hyperdrive_actions.MarketActionType.CLOSE_SHORT,
            ]
            and agent_action.mint_time is None
        ):
            raise ValueError("ERROR: agent_action.mint_time must be provided when closing a short or long")

    def perform_action(
        self, action_details: tuple[int, hyperdrive_actions.MarketAction]
    ) -> tuple[int, wallet.Wallet, hyperdrive_actions.MarketDeltas]:
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
        self.check_action(agent_action)
        # for each position, specify how to forumulate trade and then execute
        market_deltas = hyperdrive_actions.MarketDeltas()
        agent_deltas = wallet.Wallet(address=0)
        # TODO: Related to #57. When we handle failed transactions, remove this try-catch.  We
        # should handle these in the simulator, not in the market.  The market should throw errors.
        try:
            if agent_action.action_type == hyperdrive_actions.MarketActionType.OPEN_LONG:  # buy to open long
                market_deltas, agent_deltas = self.open_long(
                    agent_wallet=agent_action.wallet,
                    base_amount=agent_action.trade_amount,  # in base: that's the thing in your wallet you want to sell
                )
            elif agent_action.action_type == hyperdrive_actions.MarketActionType.CLOSE_LONG:  # sell to close long
                # TODO: python 3.10 includes TypeGuard which properly avoids issues when using Optional type
                mint_time = float(agent_action.mint_time or 0)
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
                mint_time = float(agent_action.mint_time or 0)
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
                raise ValueError(f'ERROR: Unknown trade type "{agent_action.action_type}".')
        except AssertionError as err:
            logging.debug("TRADE FAILED %s\npre_trade_market = %s\nerror = %s", agent_action, self.market_state, err)
        logging.debug(
            "%s\n%s\nagent_deltas = %s\npre_trade_market = %s",
            agent_action,
            market_deltas,
            agent_deltas,
            self.market_state,
        )
        return agent_id, agent_deltas, market_deltas

    def initialize(
        self,
        wallet_address: int,
        contribution: float,
        target_apr: float,
    ) -> tuple[hyperdrive_actions.MarketDeltas, wallet.Wallet]:
        """Market Deltas so that an LP can initialize the market"""
        if self.market_state.share_reserves > 0 or self.market_state.bond_reserves > 0:
            raise AssertionError("The market appears to already be initialized.")
        share_reserves = contribution / self.market_state.share_price
        bond_reserves = self.pricing_model.calc_initial_bond_reserves(
            target_apr=target_apr,
            time_remaining=self.position_duration,
            market_state=MarketState(
                share_reserves=share_reserves,
                init_share_price=self.market_state.init_share_price,
                share_price=self.market_state.share_price,
            ),
        )
        lp_tokens = self.market_state.share_price * share_reserves + bond_reserves
        # TODO: add lp_tokens to bond reserves per https://github.com/element-fi/hyperdrive/pull/140
        # bond_reserves += lp_tokens
        market_deltas = hyperdrive_actions.MarketDeltas(
            d_base_asset=contribution, d_bond_asset=bond_reserves, d_lp_total_supply=lp_tokens
        )
        agent_deltas = wallet.Wallet(
            address=wallet_address,
            balance=-types.Quantity(amount=contribution, unit=types.TokenType.BASE),
            lp_tokens=lp_tokens,
        )
        self.update_market(market_deltas)
        return market_deltas, agent_deltas

    def open_short(
        self, agent_wallet: wallet.Wallet, bond_amount: float, max_deposit: float = 2 ^ 32
    ) -> tuple[hyperdrive_actions.MarketDeltas, wallet.Wallet]:
        """Calculates the deltas from opening a short and then updates the agent wallet & market state"""
        # create/update the checkpoint
        self.apply_checkpoint(self.latest_checkpoint_time, self.market_state.share_price)
        # calc market and agent deltas
        market_deltas, agent_deltas = hyperdrive_actions.calc_open_short(
            agent_wallet.address,
            bond_amount,
            self,
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
        agent_wallet: wallet.Wallet,
        open_share_price: float,
        bond_amount: float,
        mint_time: float,
    ) -> tuple[hyperdrive_actions.MarketDeltas, wallet.Wallet]:
        """Calculate the deltas from closing a short and then update the agent wallet & market state"""
        # create/update the checkpoint
        self.apply_checkpoint(mint_time, self.market_state.share_price)
        # calc market and agent deltas
        market_deltas, agent_deltas = hyperdrive_actions.calc_close_short(
            wallet_address=agent_wallet.address,
            bond_amount=bond_amount,
            market=self,
            mint_time=mint_time,
            open_share_price=open_share_price,
        )
        # apply deltas
        self.market_state.apply_delta(market_deltas)
        agent_wallet.update(agent_deltas)
        return market_deltas, agent_deltas

    def open_long(
        self,
        agent_wallet: wallet.Wallet,
        base_amount: float,
    ) -> tuple[hyperdrive_actions.MarketDeltas, wallet.Wallet]:
        """Calculate the deltas from opening a long and then update the agent wallet & market state"""
        # create/update the checkpoint
        self.apply_checkpoint(self.latest_checkpoint_time, self.market_state.share_price)
        # calc market and agent deltas
        market_deltas, agent_deltas = hyperdrive_actions.calc_open_long(
            wallet_address=agent_wallet.address,
            base_amount=base_amount,
            market=self,
        )
        # update long_share_price
        self.update_long_share_price(abs(market_deltas.d_bond_asset))
        # apply deltas
        self.market_state.apply_delta(market_deltas)
        agent_wallet.update(agent_deltas)
        return market_deltas, agent_deltas

    def update_long_share_price(self, bond_proceeds: float) -> None:
        """Upates the weighted average share price for longs at the latest checkpoint."""
        long_share_price = self.market_state.checkpoints[self.latest_checkpoint_time].long_share_price
        total_supply = self.market_state.total_supply_longs[self.latest_checkpoint_time]
        updated_long_share_price = hyperdrive_actions.update_weighted_average(
            long_share_price, total_supply, self.market_state.share_price, bond_proceeds, True
        )
        self.market_state.checkpoints[self.latest_checkpoint_time].long_share_price = updated_long_share_price

    def close_long(
        self, agent_wallet: wallet.Wallet, bond_amount: float, mint_time: float
    ) -> tuple[hyperdrive_actions.MarketDeltas, wallet.Wallet]:
        """Calculate the deltas from closing a long and then update the agent wallet & market state"""
        # create/update the checkpoint
        self.apply_checkpoint(mint_time, self.market_state.share_price)
        # calc market and agent deltas
        market_deltas, agent_deltas = hyperdrive_actions.calc_close_long(
            wallet_address=agent_wallet.address,
            bond_amount=bond_amount,
            market=self,
            mint_time=mint_time,
        )
        # apply deltas
        self.market_state.apply_delta(market_deltas)
        agent_wallet.update(agent_deltas)
        return market_deltas, agent_deltas

    def add_liquidity(
        self,
        agent_wallet: wallet.Wallet,
        bond_amount: float,
    ) -> tuple[hyperdrive_actions.MarketDeltas, wallet.Wallet]:
        """Computes new deltas for bond & share reserves after liquidity is added"""
        self.apply_checkpoint(self.latest_checkpoint_time, self.market_state.share_price)
        market_deltas, agent_deltas = hyperdrive_actions.calc_add_liquidity(
            wallet_address=agent_wallet.address,
            base_in=bond_amount,
            market=self,
        )
        self.market_state.apply_delta(market_deltas)
        agent_wallet.update(agent_deltas)
        return market_deltas, agent_deltas

    def remove_liquidity(
        self,
        agent_wallet: wallet.Wallet,
        lp_shares: float,
    ) -> tuple[hyperdrive_actions.MarketDeltas, wallet.Wallet]:
        """Computes new deltas for bond & share reserves after liquidity is removed"""
        self.apply_checkpoint(self.latest_checkpoint_time, self.market_state.share_price)

        market_deltas, agent_deltas = hyperdrive_actions.calc_remove_liquidity(
            wallet_address=agent_wallet.address,
            lp_shares=lp_shares,
            market=self,
        )
        self.market_state.apply_delta(market_deltas)
        agent_wallet.update(agent_deltas)
        return market_deltas, agent_deltas

    def checkpoint(self, checkpoint_time: float) -> None:
        """allows anyone to mint a new checkpoint."""
        # if the checkpoint has already been set, return early.
        if self.market_state.checkpoints[checkpoint_time].share_price != 0:
            return
        # if the checkpoint time isn't divisible by the checkpoint duration
        # or is in the future, it's an invalid checkpoint and we should
        # revert.
        latest_checkpoint = self.latest_checkpoint_time
        if (checkpoint_time * 365) % (
            365 * self.market_state.checkpoint_duration
        ) > 0 or latest_checkpoint < checkpoint_time:
            raise errors.InvalidCheckpointTime()
        # if the checkpoint time is the latest checkpoint, we use the current
        # share price. otherwise, we use a linear search to find the closest
        # share price and use that to perform the checkpoint.
        if checkpoint_time == latest_checkpoint:
            self.apply_checkpoint(latest_checkpoint, self.market_state.share_price)
        else:
            _time = checkpoint_time
            while True:
                closest_share_price = self.market_state.checkpoints[_time].share_price
                if _time == latest_checkpoint:
                    closest_share_price = self.market_state.share_price
                if closest_share_price != 0:
                    self.apply_checkpoint(checkpoint_time, closest_share_price)
                    break
                _time += self.market_state.checkpoint_duration

    @property
    def latest_checkpoint_time(self) -> float:
        """Gets the most recent checkpoint time."""
        # NOTE: modulus doesn't work well with floats, checkpoints are days right now so multiply by
        # 365 so we can get integer values.
        latest_checkpoint = int(
            int(self.block_time.time * 365)
            - (int(self.block_time.time * 365) % int(self.market_state.checkpoint_duration * 365))
        )
        # divide the result by 365 again to get years
        return latest_checkpoint / 365

    def apply_checkpoint(self, checkpoint_time: float, share_price: float) -> float:
        r"""Creates a new checkpoint if necessary and closes matured positions.

        Parameters
        ----------
        checkpoint_time: float
            The block time for the checkpoint to be created or cleared.
        share_price: float
            The share price of the market at the checkpoint time.

        Returns
        -------
        float
            The share price for the checkpoint after mature positions have been closed.
        """
        # Return early if the checkpoint has already been updated.
        if self.market_state.checkpoints[checkpoint_time].share_price != 0 or checkpoint_time > self.block_time.time:
            return self.market_state.checkpoints[checkpoint_time].share_price
        # Create the share price checkpoint.
        self.market_state.checkpoints[checkpoint_time].share_price = share_price
        mint_time = checkpoint_time - self.annualized_position_duration
        # Close out any matured long positions and pay out the long withdrawal pool for longs that
        # have matured.
        matured_longs_amount = self.market_state.total_supply_longs[mint_time]
        if matured_longs_amount > 0:
            market_deltas, _ = hyperdrive_actions.calc_close_long(
                wallet.Wallet(0).address, matured_longs_amount, self, mint_time, False
            )
            self.market_state.apply_delta(market_deltas)
        # Close out any matured short positions and pay out the short withdrawal pool for shorts
        # that have matured.
        matured_shorts_amount = self.market_state.total_supply_shorts[mint_time]
        if matured_shorts_amount > 0:
            open_share_price = self.market_state.checkpoints[mint_time].share_price
            market_deltas, _ = hyperdrive_actions.calc_close_short(
                wallet.Wallet(0).address, matured_shorts_amount, self, mint_time, open_share_price
            )
            self.market_state.apply_delta(market_deltas)
        return self.market_state.checkpoints[mint_time].share_price

    def redeem_withdraw_shares(
        self,
        agent_wallet: wallet.Wallet,
        shares: float,
        min_output: float,
        as_underlying: bool,
    ) -> float:
        r"""Redeems withdrawal shares if enough margin has been freed to do so.

        Parameters
        ----------
        agent_wallet: wallet.Wallet
            The agent's wallet.
        shares: float
            The withdrawal shares to redeem.
        min_output: float
            The minimum amount of base the LP expects to receive.
        as_underlying: bool
            If true, the user is paid in underlying, if false the contract transfers in yield source
            directly. Note - for some paths one choice may be disabled or blocked.

        Returns
        -------
        float
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
        self, _shares: float, _min_output: float, as_underlying: bool
    ) -> tuple[hyperdrive_actions.MarketDeltas, wallet.Wallet]:
        r"""Calculates the market and wallet deltas for redeemable withdrawal shares, if enough margin
        has been freed to do so.

        Parameters
        ----------
        shares: float
            The withdrawal shares to redeem.
        min_output: float
            The minimum amount of base the LP expects to receive.
        as_underlying: bool
            If true, the user is paid in underlying, if false the contract transfers in yield source
            directly. Note - for some paths one choice may be disabled or blocked.

        Returns
        -------
        tuple[hyperdrive_actions.MarketDeltas, wallet.Wallet]

        """
        shares = Decimal(_shares)
        min_output = Decimal(_min_output)
        market_deltas = hyperdrive_actions.MarketDeltas()
        # TODO don't use a wallet. issue #315
        wallet_deltas = wallet.Wallet(address=0)
        # We burn the shares from the user
        wallet_deltas.withdraw_shares -= _shares
        # The user gets a refund on their margin equal to the face value of their withdraw shares
        # times the percent of the withdraw pool which has been lost.
        recovered_margin = (
            shares
            * Decimal(self.market_state.withdraw_capital)
            / Decimal(self.market_state.withdraw_shares_ready_to_withdraw)
        )
        # The user gets interest equal to their percent of the withdraw pool times the withdraw pool
        # interest
        recovered_interest = (
            shares
            * Decimal(self.market_state.withdraw_interest)
            / Decimal(self.market_state.withdraw_shares_ready_to_withdraw)
        )
        # Update the pool state
        # Note - Will revert here if not enough margin has been reclaimed by checkpoints or by
        #  position closes
        market_deltas.withdraw_shares_ready_to_withdraw -= float(shares)
        market_deltas.withdraw_capital -= float(recovered_margin)
        market_deltas.withdraw_interest -= float(recovered_interest)
        # Withdraw for the user
        base_proceeds = self._withdraw(float(recovered_margin + recovered_interest), as_underlying)
        # TODO: figure out how to keep track of hyperdrive's base asset amount.  market_deltas has
        # a d_base_asset, but that is used to update the share_reserves :/.
        # market_deltas.d_base_asset -= base_proceeds
        wallet_deltas.balance.amount += base_proceeds
        # Enforce min user outputs
        if min_output > Decimal(base_proceeds):
            raise errors.OutputLimit
        return market_deltas, wallet_deltas

    def _withdraw(self, shares: float, as_underlying: bool) -> float:
        r"""Calculates the amount of base to withdraw for a given amount of shares.

        Parameters
        ----------
        shares: float
            The withdrawal shares to redeem.
        as_underlying: bool
            If true, the user is paid in underlying, if false the contract transfers in yield source
            directly. Note - for some paths one choice may be disabled or blocked.

        Returns
        -------
        float
          The withdraw_value and share_price as a tuple.
        """
        # This yield source doesn't accept the underlying since it's just base.
        if not as_underlying:
            raise errors.UnsupportedOption
        # TODO: add step to accrue interest
        # Get the amount of base to transfer.
        amount_withdrawn = shares * self.market_state.share_price
        return amount_withdrawn

    def calc_free_margin(
        self, freed_capital: float, max_capital: float, interest: float
    ) -> hyperdrive_actions.MarketDeltas:
        r"""Moves capital into the withdraw pool and marks shares ready for withdraw.

        Parameters
        ----------
        freed_capital: float
            The amount of capital to add to the withdraw pool, must not be more than the max capital.
        max_capital: float
            The margin which the LP used to back the position which is being closed.
        interest: float
            The interest earned by this margin position, fixed interest for shorts and variable for longs.

        Returns
        -------
        hyperdrive_actions.MarketDeltas
            Market deltas that include the capital, interest and shares added to the withdraw pool.
        """
        # If we don't have capital to free then simply return zero
        withdraw_share_supply = self.market_state.total_supply_withdraw_shares
        withdraw_shares_ready_to_withdraw = self.market_state.withdraw_shares_ready_to_withdraw
        withdraw_pool_deltas = hyperdrive_actions.MarketDeltas()
        if withdraw_share_supply <= withdraw_shares_ready_to_withdraw:
            return withdraw_pool_deltas
        # If we have more capital freed than needed we adjust down all values
        if max_capital + withdraw_shares_ready_to_withdraw > withdraw_share_supply:
            # in this case we want max_capital * adjustment + withdraw_shares_ready_to_withdraw = withdraw_share_supply
            # so adjustment = (withdraw_share_supply - withdraw_shares_ready_to_withdraw) / max_capital
            # we adjust max_capital and do corresponding reduction in freed_capital and interest
            adjustment = withdraw_share_supply - withdraw_shares_ready_to_withdraw / max_capital
            freed_capital *= adjustment
            max_capital *= adjustment
            interest *= adjustment
            withdraw_pool_deltas.withdraw_shares_ready_to_withdraw = max_capital
            withdraw_pool_deltas.withdraw_capital = freed_capital
            withdraw_pool_deltas.withdraw_interest = interest
        # Finally return the amount used by this action and the caller can update reserves.
        return withdraw_pool_deltas


@dataclass
class CheckpointFP:
    """
    Hyperdrive positions are bucketed into checkpoints, which allows us to avoid poking in any
    period that has LP or trading activity. The checkpoints contain the starting share price from
    the checkpoint as well as aggregate volume values.
    """

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        return setattr(self, key, value)

    share_price: FixedPoint = FixedPoint(0)
    long_share_price: FixedPoint = FixedPoint(0)
    long_base_volume: FixedPoint = FixedPoint(0)
    short_base_volume: FixedPoint = FixedPoint(0)


@types.freezable(frozen=False, no_new_attribs=False)
@dataclass
class MarketStateFP(base_market.BaseMarketStateFP):
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
    checkpoints: defaultdict[int, Checkpoint]
        Time delimited checkpoints
    checkpoint_duration: FixedPoint
        Time between checkpoints, defaults to 1 day
    total_supply_longs: defaultdict[int, FixedPoint]
        Checkpointed total supply for longs stored as {checkpoint_time: bond_amount}
    total_supply_shorts: defaultdict[int, FixedPoint]
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
    checkpoints: defaultdict[int, CheckpointFP] = field(default_factory=lambda: defaultdict(CheckpointFP))
    checkpoint_duration: FixedPoint = FixedPoint(1 / 365)
    total_supply_longs: defaultdict[int, FixedPoint] = field(default_factory=lambda: defaultdict(lambda: FixedPoint(0)))
    total_supply_shorts: defaultdict[int, FixedPoint] = field(
        default_factory=lambda: defaultdict(lambda: FixedPoint(0))
    )
    total_supply_withdraw_shares: FixedPoint = FixedPoint(0)
    withdraw_shares_ready_to_withdraw: FixedPoint = FixedPoint(0)
    withdraw_capital: FixedPoint = FixedPoint(0)
    withdraw_interest: FixedPoint = FixedPoint(0)

    def apply_delta(self, delta: hyperdrive_actions.MarketDeltasFP) -> None:
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
            self.checkpoints[mint_time].long_base_volume += delta_checkpoint
        for mint_time, delta_checkpoint in delta.short_checkpoints.items():
            self.checkpoints[mint_time].short_base_volume += delta_checkpoint
        for mint_time, delta_supply in delta.total_supply_longs.items():
            self.total_supply_longs[mint_time] += delta_supply
        for mint_time, delta_supply in delta.total_supply_shorts.items():
            self.total_supply_shorts[mint_time] += delta_supply

    def copy(self) -> MarketStateFP:
        """Returns a new copy of self"""
        return MarketStateFP(**copy.deepcopy(self.__dict__))


class MarketFP(
    base_market.MarketFP[
        MarketStateFP,
        hyperdrive_actions.MarketDeltasFP,
        hyperdrive_pm.HyperdrivePricingModelFP,
    ]
):
    r"""Market state simulator

    Holds state variables for market simulation and executes trades.
    The Market class executes trades by updating market variables according to the given pricing model.
    It also has some helper variables for assessing pricing model values given market conditions.
    """

    def __init__(
        self,
        pricing_model: hyperdrive_pm.HyperdrivePricingModelFP,
        market_state: MarketStateFP,
        position_duration: time.StretchedTimeFP,
        block_time: time.BlockTimeFP,
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
        # calc_apr_from_spot_price will throw an error if share_reserves <= zero
        if self.market_state.share_reserves < FixedPoint(0):
            raise OverflowError(f"Share reserves should be >= 0, not {self.market_state.share_reserves}")
        elif self.market_state.share_price == FixedPoint(0):
            return FixedPoint("nan")
        return price_utils.calc_apr_from_spot_price_fp(price=self.spot_price, time_remaining=self.position_duration)

    @property
    def spot_price(self) -> FixedPoint:
        """Returns the current market price of the share reserves"""
        # calc_spot_price_from_reserves will throw an error if share_reserves is zero
        if self.market_state.share_reserves == FixedPoint(0):  # market is empty
            return FixedPoint("nan")
        return self.pricing_model.calc_spot_price_from_reserves(
            market_state=self.market_state,
            time_remaining=self.position_duration,
        )

    @property
    def latest_checkpoint_time(self) -> FixedPoint:
        """Gets the most recent checkpoint time."""
        # FIXME: Delete below once I verify that we don't need to convert to days anymore
        # block_time_days = self.block_time.time * FixedPoint("365.0")
        # checkpoint_duration_days = self.market_state.checkpoint_duration * FixedPoint("365.0")
        # return (block_time_days - (block_time_days % checkpoint_duration_days)) / FixedPoint("365.0")
        return self.block_time.time - (self.block_time.time % self.market_state.checkpoint_duration)

    def check_action(self, agent_action: hyperdrive_actions.MarketActionFP) -> None:
        r"""Ensure that the agent action is an allowed action for this market

        Parameters
        ----------
        action_type : MarketActionType
            See MarketActionType for all acceptable actions that can be performed on this market

        Returns
        -------
        None
        """
        if (
            agent_action.action_type
            in [
                hyperdrive_actions.MarketActionType.CLOSE_LONG,
                hyperdrive_actions.MarketActionType.CLOSE_SHORT,
            ]
            and agent_action.mint_time is None
        ):
            raise ValueError("ERROR: agent_action.mint_time must be provided when closing a short or long")

    def perform_action(
        self, action_details: tuple[int, hyperdrive_actions.MarketActionFP]
    ) -> tuple[int, wallet.WalletFP, hyperdrive_actions.MarketDeltasFP]:
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
        self.check_action(agent_action)
        # for each position, specify how to forumulate trade and then execute
        market_deltas = hyperdrive_actions.MarketDeltasFP()
        agent_deltas = wallet.WalletFP(address=0)
        # TODO: Related to #57. When we handle failed transactions, remove this try-catch.  We
        # should handle these in the simulator, not in the market.  The market should throw errors.
        try:
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
                open_share_price = agent_action.wallet.shorts[int(mint_time)].open_share_price
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
                raise ValueError(f'ERROR: Unknown trade type "{agent_action.action_type}".')
        except AssertionError as err:
            logging.debug("TRADE FAILED %s\npre_trade_market = %s\nerror = %s", agent_action, self.market_state, err)
        logging.debug(
            "%s\n%s\nagent_deltas = %s\npre_trade_market = %s",
            agent_action,
            market_deltas,
            agent_deltas,
            self.market_state,
        )
        return agent_id, agent_deltas, market_deltas

    def initialize(
        self,
        wallet_address: int,
        contribution: FixedPoint,
        target_apr: FixedPoint,
    ) -> tuple[hyperdrive_actions.MarketDeltasFP, wallet.WalletFP]:
        """Market Deltas so that an LP can initialize the market"""
        if self.market_state.share_reserves > FixedPoint(0) or self.market_state.bond_reserves > FixedPoint(0):
            raise AssertionError("The market appears to already be initialized.")
        share_reserves = contribution / self.market_state.share_price
        bond_reserves = self.pricing_model.calc_initial_bond_reserves(
            target_apr=target_apr,
            time_remaining=self.position_duration,
            market_state=MarketStateFP(
                share_reserves=share_reserves,
                init_share_price=self.market_state.init_share_price,
                share_price=self.market_state.share_price,
            ),
        )
        lp_tokens = self.market_state.share_price * share_reserves + bond_reserves
        # TODO: add lp_tokens to bond reserves per https://github.com/element-fi/hyperdrive/pull/140
        # bond_reserves += lp_tokens
        market_deltas = hyperdrive_actions.MarketDeltasFP(
            d_base_asset=contribution, d_bond_asset=bond_reserves, d_lp_total_supply=lp_tokens
        )
        agent_deltas = wallet.WalletFP(
            address=wallet_address,
            balance=-types.QuantityFP(amount=contribution, unit=types.TokenType.BASE),
            lp_tokens=lp_tokens,
        )
        self.update_market(market_deltas)
        return market_deltas, agent_deltas

    def open_short(
        self,
        agent_wallet: wallet.WalletFP,
        bond_amount: FixedPoint,
        max_deposit: FixedPoint = FixedPoint(2**32 * 10**18),  # FIXME: This isn't over the max right?
    ) -> tuple[hyperdrive_actions.MarketDeltasFP, wallet.WalletFP]:
        """Calculates the deltas from opening a short and then updates the agent wallet & market state"""
        # create/update the checkpoint
        self.apply_checkpoint(self.latest_checkpoint_time, self.market_state.share_price)
        # calc market and agent deltas
        market_deltas, agent_deltas = hyperdrive_actions.calc_open_short_fp(
            agent_wallet.address,
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
        agent_wallet: wallet.WalletFP,
        open_share_price: FixedPoint,
        bond_amount: FixedPoint,
        mint_time: FixedPoint,
    ) -> tuple[hyperdrive_actions.MarketDeltasFP, wallet.WalletFP]:
        """Calculate the deltas from closing a short and then update the agent wallet & market state"""
        # create/update the checkpoint
        self.apply_checkpoint(mint_time, self.market_state.share_price)
        # calc market and agent deltas
        market_deltas, agent_deltas = hyperdrive_actions.calc_close_short_fp(
            agent_wallet.address,
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
        agent_wallet: wallet.WalletFP,
        base_amount: FixedPoint,
    ) -> tuple[hyperdrive_actions.MarketDeltasFP, wallet.WalletFP]:
        """Calculate the deltas from opening a long and then update the agent wallet & market state"""
        # create/update the checkpoint
        self.apply_checkpoint(self.latest_checkpoint_time, self.market_state.share_price)
        # calc market and agent deltas
        market_deltas, agent_deltas = hyperdrive_actions.calc_open_long_fp(
            agent_wallet.address,
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
        long_share_price = self.market_state.checkpoints[int(self.latest_checkpoint_time)].long_share_price
        total_supply = self.market_state.total_supply_longs[int(self.latest_checkpoint_time)]
        updated_long_share_price = hyperdrive_actions.update_weighted_average_fp(
            long_share_price, total_supply, self.market_state.share_price, bond_proceeds, True
        )
        self.market_state.checkpoints[int(self.latest_checkpoint_time)].long_share_price = updated_long_share_price

    def close_long(
        self, agent_wallet: wallet.WalletFP, bond_amount: FixedPoint, mint_time: FixedPoint
    ) -> tuple[hyperdrive_actions.MarketDeltasFP, wallet.WalletFP]:
        """Calculate the deltas from closing a long and then update the agent wallet & market state"""
        # create/update the checkpoint
        self.apply_checkpoint(mint_time, self.market_state.share_price)
        # calc market and agent deltas
        market_deltas, agent_deltas = hyperdrive_actions.calc_close_long_fp(
            agent_wallet.address,
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
        agent_wallet: wallet.WalletFP,
        bond_amount: FixedPoint,
    ) -> tuple[hyperdrive_actions.MarketDeltasFP, wallet.WalletFP]:
        """Computes new deltas for bond & share reserves after liquidity is added"""
        self.apply_checkpoint(self.latest_checkpoint_time, self.market_state.share_price)
        market_deltas, agent_deltas = hyperdrive_actions.calc_add_liquidity_fp(
            agent_wallet.address,
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
        agent_wallet: wallet.WalletFP,
        lp_shares: FixedPoint,
    ) -> tuple[hyperdrive_actions.MarketDeltasFP, wallet.WalletFP]:
        """Computes new deltas for bond & share reserves after liquidity is removed"""
        self.apply_checkpoint(self.latest_checkpoint_time, self.market_state.share_price)

        market_deltas, agent_deltas = hyperdrive_actions.calc_remove_liquidity_fp(
            agent_wallet.address,
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
        # if the checkpoint has already been set, return early.
        if self.market_state.checkpoints[int(checkpoint_time)].share_price != 0:
            return
        # if the checkpoint time isn't divisible by the checkpoint duration
        # or is in the future, it's an invalid checkpoint and we should
        # revert.
        latest_checkpoint = self.latest_checkpoint_time
        if (checkpoint_time * FixedPoint("365.0")) % (
            FixedPoint("365.0") * self.market_state.checkpoint_duration
        ) > FixedPoint(0) or latest_checkpoint < checkpoint_time:
            raise errors.InvalidCheckpointTime()
        # if the checkpoint time is the latest checkpoint, we use the current
        # share price. otherwise, we use a linear search to find the closest
        # share price and use that to perform the checkpoint.
        if checkpoint_time == latest_checkpoint:
            self.apply_checkpoint(latest_checkpoint, self.market_state.share_price)
        else:
            _time = checkpoint_time
            while True:
                closest_share_price = self.market_state.checkpoints[int(_time)].share_price
                if _time == latest_checkpoint:
                    closest_share_price = self.market_state.share_price
                if closest_share_price != 0:
                    self.apply_checkpoint(checkpoint_time, closest_share_price)
                    break
                _time += self.market_state.checkpoint_duration

    def apply_checkpoint(self, checkpoint_time: FixedPoint, share_price: FixedPoint) -> FixedPoint:
        r"""Creates a new checkpoint if necessary and closes matured positions.

        Parameters
        ----------
        checkpoint_time: FixedPoint
            The block time for the checkpoint to be created or cleared.
        share_price: FixedPoint
            The share price of the market at the checkpoint time.

        Returns
        -------
        FixedPoint
            The share price for the checkpoint after mature positions have been closed.
        """
        # Return early if the checkpoint has already been updated.
        if (
            self.market_state.checkpoints[int(checkpoint_time)].share_price != 0
            or checkpoint_time > self.block_time.time
        ):
            return self.market_state.checkpoints[int(checkpoint_time)].share_price
        # Create the share price checkpoint.
        self.market_state.checkpoints[int(checkpoint_time)].share_price = share_price
        mint_time = checkpoint_time - self.annualized_position_duration
        # Close out any matured long positions and pay out the long withdrawal pool for longs that
        # have matured.
        matured_longs_amount = self.market_state.total_supply_longs[int(mint_time)]
        if matured_longs_amount > FixedPoint(0):
            market_deltas, _ = hyperdrive_actions.calc_close_long_fp(
                wallet.Wallet(0).address,
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
        matured_shorts_amount = self.market_state.total_supply_shorts[mint_time]
        if matured_shorts_amount > FixedPoint(0):
            open_share_price = self.market_state.checkpoints[mint_time].share_price
            market_deltas, _ = hyperdrive_actions.calc_close_short_fp(
                wallet.Wallet(0).address,
                matured_shorts_amount,
                self.market_state,
                self.position_duration,
                self.pricing_model,
                self.block_time.time,
                mint_time,
                open_share_price,
            )
            self.market_state.apply_delta(market_deltas)
        return self.market_state.checkpoints[mint_time].share_price

    def redeem_withdraw_shares(
        self,
        agent_wallet: wallet.WalletFP,
        shares: FixedPoint,
        min_output: FixedPoint,
        as_underlying: bool,
    ) -> FixedPoint:
        r"""Redeems withdrawal shares if enough margin has been freed to do so.

        Parameters
        ----------
        agent_wallet: wallet.Wallet
            The agent's wallet.
        shares: FixedPoint
            The withdrawal shares to redeem.
        min_output: FixedPoint
            The minimum amount of base the LP expects to receive.
        as_underlying: bool
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
    ) -> tuple[hyperdrive_actions.MarketDeltasFP, wallet.WalletFP]:
        r"""Calculates the market and wallet deltas for redeemable withdrawal shares, if enough margin
        has been freed to do so.

        Parameters
        ----------
        shares: FixedPoint
            The withdrawal shares to redeem.
        min_output: FixedPoint
            The minimum amount of base the LP expects to receive.
        as_underlying: bool
            If true, the user is paid in underlying, if false the contract transfers in yield source
            directly. Note - for some paths one choice may be disabled or blocked.

        Returns
        -------
        tuple[hyperdrive_actions.MarketDeltas, wallet.Wallet]

        """
        market_deltas = hyperdrive_actions.MarketDeltasFP()
        # TODO don't use a wallet. issue #315
        wallet_deltas = wallet.WalletFP(address=0)
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

        Parameters
        ----------
        shares: FixedPoint
            The withdrawal shares to redeem.
        as_underlying: bool
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

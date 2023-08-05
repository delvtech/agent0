"""Market simulators store state information when interfacing AMM pricing models with users."""
from __future__ import annotations

import copy
from dataclasses import dataclass, field

import elfpy
from elfpy import types
from elfpy.markets.base import BaseMarketState
from fixedpointmath import FixedPoint


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
    # dataclasses can have many attributes
    # pylint: disable=too-many-instance-attributes

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        return setattr(self, key, value)

    lp_total_supply: FixedPoint = FixedPoint(0)
    share_reserves: FixedPoint = FixedPoint(0)
    bond_reserves: FixedPoint = FixedPoint(0)
    base_buffer: FixedPoint = FixedPoint(0)
    bond_buffer: FixedPoint = FixedPoint(0)
    minimum_share_reserves: FixedPoint = FixedPoint(1)
    variable_apr: FixedPoint = FixedPoint(0)
    share_price: FixedPoint = FixedPoint(1.0)
    init_share_price: FixedPoint = FixedPoint(1.0)
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
    checkpoint_duration: FixedPoint = FixedPoint("1.0").div_up(FixedPoint("365.0"))
    checkpoint_duration_days: FixedPoint = FixedPoint("1.0")
    total_supply_longs: dict[FixedPoint, FixedPoint] = field(default_factory=dict)
    total_supply_shorts: dict[FixedPoint, FixedPoint] = field(default_factory=dict)
    total_supply_withdraw_shares: FixedPoint = FixedPoint(0)
    withdraw_shares_ready_to_withdraw: FixedPoint = FixedPoint(0)
    withdraw_capital: FixedPoint = FixedPoint(0)
    withdraw_interest: FixedPoint = FixedPoint(0)

    def apply_delta(self, delta: HyperdriveMarketState) -> None:
        r"""Applies a delta to the market state."""
        # assets & prices
        self.share_reserves += delta.share_reserves
        self.bond_reserves += delta.bond_reserves
        self.base_buffer += delta.base_buffer
        self.bond_buffer += delta.bond_buffer
        self.lp_total_supply += delta.lp_total_supply
        self.share_price += delta.share_price
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

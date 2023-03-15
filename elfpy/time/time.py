"""Helper functions for converting time units"""

from dataclasses import dataclass
from decimal import Decimal

import numpy as np

import elfpy.types as types


@dataclass
class BlockTime:
    r"""Global time."""

    time: float = 0  # time in years
    block_number: int = 0
    step_size: float = 1 / 365  # defaults to 1 day

    @property
    def time_in_seconds(self) -> float:
        """1 year = 31,556,952 seconds"""
        return self.time * 31_556_952

    def tick(self, delta_years: float) -> None:
        """ticks the time by delta_time amount"""
        self.time += delta_years

    def step(self) -> None:
        """ticks the time by step_size"""
        self.time += self.step_size

    def set_time(self, time: float) -> None:
        """Sets the time"""
        self.time = time

    def set_step_size(self, step_size: float) -> None:
        """Sets the step_size for tick"""
        self.step_size = step_size


@types.freezable(frozen=True, no_new_attribs=True)
@dataclass
class StretchedTime:
    r"""Stores time in units of days, as well as normalized & stretched variants

    .. todo:: Improve this constructor so that StretchedTime can be constructed from years.
    """
    days: Decimal
    time_stretch: Decimal
    normalizing_constant: Decimal

    @property
    def stretched_time(self):
        r"""Returns days / normalizing_constant / time_stretch"""
        return days_to_time_remaining(self.days, self.time_stretch, normalizing_constant=self.normalizing_constant)

    @property
    def normalized_time(self):
        r"""Format time as normalized days"""
        return norm_days(
            self.days,
            self.normalizing_constant,
        )


def get_years_remaining(market_time: Decimal, mint_time: Decimal, position_duration_years: Decimal) -> Decimal:
    r"""Get the time remaining in years on a token

    Parameters
    ----------
    market_time : Decimal
        Time that has elapsed in the given market, in years
    mint_time : Decimal
        Time at which the token in question was minted, relative to market_time,
        in yearss. Should be less than market_time.
    position_duration_years: Decimal
        Total duration of the token's term, in years

    Returns
    -------
    Decimal
        Time left until token maturity, in years
    """
    if mint_time > market_time:
        raise ValueError(f"elfpy.utils.time.get_years_remaining: ERROR: {mint_time=} must be less than {market_time=}.")
    years_elapsed = market_time - mint_time
    # if we are closing after the position duration has completed, then just set time_remaining to zero
    return (
        position_duration_years - years_elapsed if position_duration_years - years_elapsed > Decimal(0) else Decimal(0)
    )


def norm_days(days: Decimal, normalizing_constant: Decimal = Decimal(365)) -> Decimal:
    r"""Returns days normalized, with a default assumption of a year-long scale

    Parameters
    ----------
    days : Decimal
        Amount of days to normalize
    normalizing_constant : Decimal
        Amount of days to use as a normalization factor. Defaults to 365

    Returns
    -------
    Decimal
        Amount of days provided, converted to fractions of a year
    """
    return days / normalizing_constant


def days_to_time_remaining(
    days_remaining: Decimal, time_stretch: Decimal = Decimal(1), normalizing_constant: Decimal = Decimal(365)
) -> Decimal:
    r"""Converts remaining pool length in days to normalized and stretched time

    Parameters
    ----------
    days_remaining : Decimal
        Time left until term maturity, in days
    time_stretch : Decimal
        Amount of time units (in terms of a normalizing constant) to use for stretching time, for calculations
        Defaults to 1
    normalizing_constant : Decimal
        Amount of days to use as a normalization factor
        Defaults to 365

    Returns
    -------
    Decimal
        Time remaining until term maturity, in normalized and stretched time
    """
    normed_days_remaining = norm_days(days_remaining, normalizing_constant)
    return normed_days_remaining / time_stretch


def time_to_days_remaining(time_remaining: float, time_stretch: float = 1, normalizing_constant: float = 365) -> float:
    r"""Converts normalized and stretched time remaining in pool to days

    Parameters
    ----------
    time_remaining : float
        Time left until term maturity, in normalized and stretched time
    time_stretch : float
        Amount of time units (in terms of a normalizing constant) to use for stretching time, for calculations
        Defaults to 1
    normalizing_constant : float
        Amount of days to use as a normalization factor. Defaults to 365

    Returns
    -------
    float
        Time remaining until term maturity, in days
    """
    normed_days_remaining = time_remaining * time_stretch
    return normed_days_remaining * normalizing_constant

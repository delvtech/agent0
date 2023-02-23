"""Helper functions for converting time units"""

from datetime import datetime, timedelta
from dataclasses import dataclass

import pytz
import numpy as np

import elfpy.types as types


@types.freezable(frozen=True, no_new_attribs=True)
@dataclass
class StretchedTime:
    r"""Stores time in units of days, as well as normalized & stretched variants

    .. todo:: Improve this constructor so that StretchedTime can be constructed from years.
    """
    days: float
    time_stretch: float
    normalizing_constant: float

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

    def __str__(self):
        output_string = (
            "StretchedTime(\n"
            f"\t{self.days=},\n"
            f"\t{self.normalized_time=},\n"
            f"\t{self.stretched_time=},\n"
            f"\t{self.time_stretch=},\n"
            f"\t{self.normalizing_constant=},\n"
            ")"
        )
        return output_string


def current_datetime() -> datetime:
    r"""Returns the current time

    Returns
    -------
    datetime
        Current UTC time
    """
    return datetime.now(pytz.timezone("Etc/GMT-0"))


def block_number_to_datetime(start_time: datetime, block_number: float, time_between_blocks: float) -> datetime:
    r"""Converts the current block number to a datetime based on the start datetime of the simulation

    Parameters
    ----------
    start_time : datetime
        Timestamp at which the simulation started
    block_number : int
        Number of blocks since the simulation started
    time_between_blocks : float
        Number of seconds between blocks

    Returns
    -------
    datetime
        Timestamp at which the provided block number was (or will be) validated
    """
    delta_time = timedelta(seconds=block_number * time_between_blocks)
    return start_time + delta_time


def year_as_datetime(start_time: datetime, years: float) -> datetime:
    r"""Returns a year (e.g. the current market time) in datetime format

    Parameters
    ----------
    start_time : datetime
        Timestamp at which the simulation started
    years : float
        years since start_time to convert into datetime

    Returns
    -------
    datetime
        Timestamp for the provided start_time plus the provided year
    """

    days = years * 365
    delta_time = timedelta(days=days)
    return start_time + delta_time


def get_years_remaining(market_time: float, mint_time: float, position_duration_years: float) -> float:
    r"""Get the time remaining in years on a token

    Parameters
    ----------
    market_time : float
        Time that has elapsed in the given market, in years
    mint_time : float
        Time at which the token in question was minted, relative to market_time,
        in yearss. Should be less than market_time.
    position_duration_years: float
        Total duration of the token's term, in years

    Returns
    -------
    float
        Time left until token maturity, in years
    """
    if mint_time > market_time:
        raise ValueError(f"elfpy.utils.time.get_years_remaining: ERROR: {mint_time=} must be less than {market_time=}.")
    years_elapsed = market_time - mint_time
    # if we are closing after the position duration has completed, then just set time_remaining to zero
    time_remaining = np.maximum(position_duration_years - years_elapsed, 0)
    return time_remaining


def norm_days(days: float, normalizing_constant: float = 365) -> float:
    r"""Returns days normalized, with a default assumption of a year-long scale

    Parameters
    ----------
    days : float
        Amount of days to normalize
    normalizing_constant : float
        Amount of days to use as a normalization factor. Defaults to 365

    Returns
    -------
    float
        Amount of days provided, converted to fractions of a year
    """
    return days / normalizing_constant


def stretch_time(time: float, time_stretch: float = 1.0) -> float:
    r"""Returns stretched time values

    Parameters
    ----------
    time : float
        Time that needs to be stretched for calculations, in terms of the normalizing constant
    time_stretch : float
        Amount of time units (in terms of a normalizing constant) to use for stretching time, for calculations
        Defaults to 1

    Returns
    -------
    float
        Stretched time, using the provided parameters
    """
    return time / time_stretch


def unnorm_days(normed_days: float, normalizing_constant: float = 365) -> float:
    r"""Returns days from a value between 0 and 1

    Parameters
    ----------
    normed_days : float
        Normalized amount of days, according to a normalizing constant
    normalizing_constant : float
        Amount of days to use as a normalization factor. Defaults to 365

    Returns
    -------
    float
        Amount of days, calculated from the provided parameters
    """
    return normed_days * normalizing_constant


def unstretch_time(stretched_time: float, time_stretch: float = 1) -> float:
    r"""Returns unstretched time value, which should be between 0 and 1

    Parameters
    ----------
    stretched_time : float
        Time that has been stretched using the time_stretch factor
    time_stretch : float
        Amount of time units (in terms of a normalizing constant) to use for stretching time, for calculations
        Defaults to 1

    Returns
    -------
    float
        Time that was provided, unstretched but still based on the normalization factor
    """
    return stretched_time * time_stretch


def days_to_time_remaining(days_remaining: float, time_stretch: float = 1, normalizing_constant: float = 365) -> float:
    r"""Converts remaining pool length in days to normalized and stretched time

    Parameters
    ----------
    days_remaining : float
        Time left until term maturity, in days
    time_stretch : float
        Amount of time units (in terms of a normalizing constant) to use for stretching time, for calculations
        Defaults to 1
    normalizing_constant : float
        Amount of days to use as a normalization factor
        Defaults to 365

    Returns
    -------
    float
        Time remaining until term maturity, in normalized and stretched time
    """
    normed_days_remaining = norm_days(days_remaining, normalizing_constant)
    time_remaining = stretch_time(normed_days_remaining, time_stretch)
    return time_remaining


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
    normed_days_remaining = unstretch_time(time_remaining, time_stretch)
    days_remaining = unnorm_days(normed_days_remaining, normalizing_constant)
    return days_remaining

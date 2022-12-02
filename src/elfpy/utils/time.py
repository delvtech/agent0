"""
Helper functions for converting time units
"""


from datetime import datetime, timedelta
import pytz

import numpy as np


def current_datetime() -> datetime:
    """Returns the current time"""
    return datetime.now(pytz.timezone("Etc/GMT-0"))


def block_number_to_datetime(start_time: datetime, block_number: float, time_between_blocks: float) -> datetime:
    """Converts the current block number to a datetime based on the start datetime of the simulation"""
    delta_time = timedelta(seconds=block_number * time_between_blocks)
    return start_time + delta_time


def yearfrac_as_datetime(start_time: datetime, yearfrac: float) -> datetime:
    """Returns a yearfrac (e.g. the current market time) in datetime format"""
    dayfrac = yearfrac * 365
    delta_time = timedelta(days=dayfrac)
    return start_time + delta_time


def get_yearfrac_remaining(market_time: float, mint_time: float, token_duration: float) -> float:
    """Get the year fraction remaining on a token"""
    yearfrac_elapsed = market_time - mint_time
    time_remaining = np.maximum(token_duration - yearfrac_elapsed, 0)
    return time_remaining


def norm_days(days: float, normalizing_constant: float = 365) -> float:
    """Returns days normalized between 0 and 1, with a default assumption of a year-long scale"""
    return days / normalizing_constant


def stretch_time(time: float, time_stretch: float = 1.0) -> float:
    """Returns stretched time values"""
    return time / time_stretch


def unnorm_days(normed_days: float, normalizing_constant: float = 365) -> float:
    """Returns days from a value between 0 and 1"""
    return normed_days * normalizing_constant


def unstretch_time(stretched_time: float, time_stretch: float = 1) -> float:
    """Returns unstretched time value, which should be between 0 and 1"""
    return stretched_time * time_stretch


def days_to_time_remaining(days_remaining: float, time_stretch: float = 1, normalizing_constant: float = 365) -> float:
    """Converts remaining pool length in days to normalized and stretched time"""
    normed_days_remaining = norm_days(days_remaining, normalizing_constant)
    time_remaining = stretch_time(normed_days_remaining, time_stretch)
    return time_remaining


def time_to_days_remaining(time_remaining: float, time_stretch: float = 1, normalizing_constant: float = 365) -> float:
    """Converts normalized and stretched time remaining in pool to days"""
    normed_days_remaining = unstretch_time(time_remaining, time_stretch)
    days_remaining = unnorm_days(normed_days_remaining, normalizing_constant)
    return days_remaining

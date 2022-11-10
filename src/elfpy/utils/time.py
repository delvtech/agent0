"""
Helper functions for converting time units
"""


import datetime
import pytz

import numpy as np


def current_datetime():
    """Returns the current time"""
    return datetime.datetime.now(pytz.timezone('Etc/GMT-0'))


def block_number_to_datetime(start_time, block_number, time_between_blocks):
    """Converts the current block number to a datetime based on the start datetime of the simulation"""
    delta_time = datetime.timedelta(seconds=block_number * time_between_blocks)
    return start_time + delta_time


def yearfrac_as_datetime(start_time, yearfrac):
    """Returns a yearfrac (e.g. the current market time) in datetime format"""
    dayfrac = yearfrac * 365
    delta_time = datetime.timedelta(days=dayfrac)
    return start_time + delta_time


def get_yearfrac_remaining(market_time, mint_time, token_duration):
    """Get the year fraction remaining on a token"""
    yearfrac_elapsed = market_time - mint_time
    time_remaining = np.maximum(token_duration - yearfrac_elapsed, 0)
    return time_remaining

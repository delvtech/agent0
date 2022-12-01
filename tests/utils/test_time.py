"""
Testing for time utilities found in src/elfpy/utils/time.py
"""

# pylint: disable=too-many-lines
# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-locals
# pylint: disable=attribute-defined-outside-init

import unittest
import numpy as np

from elfpy.utils import time as time_utils


class TestTimeUtils(unittest.TestCase):
    """Unit tests for the parse_simulation_config function"""

    def test_current_datetime():
        """
        Test the current_datetime function
        """
        return datetime.datetime.now(pytz.timezone("Etc/GMT-0"))


    # def block_number_to_datetime(start_time, block_number, time_between_blocks):
    #     """
    #     Converts the current block number to a datetime based on the start datetime of the simulation

    #     Arguments
    #     ---------
    #     start_time : datetime
    #         Timestamp at which the simulation started
    #     block_number : int
    #         Number of blocks since the simulation started
    #     time_between_blocks : float
    #         Number of seconds between blocks

    #     Returns
    #     -------
    #     datetime
    #         Timestamp at which the provided block number was (or will be) validated
    #     """
    #     delta_time = datetime.timedelta(seconds=block_number * time_between_blocks)
    #     return start_time + delta_time


    # def yearfrac_as_datetime(start_time, yearfrac):
    #     """
    #     Returns a yearfrac (e.g. the current market time) in datetime format

    #     Arguments
    #     ---------
    #     start_time : datetime
    #         Timestamp at which the simulation started
    #     yearfrac : float
    #         Fraction of a year since start_time to convert into datetime

    #     Returns
    #     -------
    #     datetime
    #         Timestamp for the provided start_time plus the provided yearfrac
    #     """
    #     dayfrac = yearfrac * 365
    #     delta_time = datetime.timedelta(days=dayfrac)
    #     return start_time + delta_time


    # def get_yearfrac_remaining(market_time, mint_time, token_duration):
    #     """
    #     Get the year fraction remaining on a token

    #     Arguments
    #     ---------
    #     market_time : datetime
    #         Time that has elapsed in the given market
    #     mint_time : datetime
    #         Time at which the token in question was minted
    #     token_duration : float
    #         Total duration of the token's term, in fractions of a year

    #     Returns
    #     -------
    #     float
    #         Time left until token maturity, in fractions of a year
    #     """
    #     yearfrac_elapsed = market_time - mint_time
    #     time_remaining = np.maximum(token_duration - yearfrac_elapsed, 0)
    #     return time_remaining


    # def norm_days(days, normalizing_constant=365):
    #     """
    #     Returns days normalized between 0 and 1, with a default assumption of a year-long scale

    #     Arguments
    #     ---------
    #     days : float
    #         Amount of days to normalize
    #     normalizing_constant : float
    #         Amount of days to use as a normalization factor. Defaults to 365

    #     Returns
    #     -------
    #         Amount of days provided, converted to fractions of a year
    #     """
    #     return days / normalizing_constant


    # def stretch_time(time, time_stretch=1):
    #     """
    #     Returns stretched time values

    #     Arguments
    #     ---------
    #     time : float
    #         Time that needs to be stretched for calculations, in terms of the normalizing constant
    #     time_stretch : float
    #         Amount of time units (in terms of a normalizing constant) to use for stretching time, for calculations
    #         Defaults to 1

    #     Returns
    #     -------
    #     float
    #         Stretched time, using the provided parameters
    #     """
    #     return time / time_stretch


    # def unnorm_days(normed_days, normalizing_constant=365):
    #     """
    #     Returns days from a value between 0 and 1

    #     Arguments
    #     ---------
    #     normed_days : float
    #         Normalized amount of days, according to a normalizing constant
    #     normalizing_constant : float
    #         Amount of days to use as a normalization factor. Defaults to 365

    #     Returns
    #     -------
    #     float
    #         Amount of days, calculated from the provided parameters
    #     """
    #     return normed_days * normalizing_constant


    # def unstretch_time(stretched_time, time_stretch=1):
    #     """
    #     Returns unstretched time value, which should be between 0 and 1

    #     Arguments
    #     ---------
    #     stretched_time : float
    #         Time that has been stretched using the time_stretch factor
    #     time_stretch : float
    #         Amount of time units (in terms of a normalizing constant) to use for stretching time, for calculations
    #         Defaults to 1

    #     Returns
    #     -------
    #     float
    #         Time that was provided, unstretched but still based on the normalization factor
    #     """
    #     return stretched_time * time_stretch


    # def days_to_time_remaining(days_remaining, time_stretch=1, normalizing_constant=365):
    #     """
    #     Converts remaining pool length in days to normalized and stretched time
       
    #     Arguments
    #     ---------
    #     days_remaining : float
    #         Time left until term maturity, in days
    #     time_stretch : float
    #         Amount of time units (in terms of a normalizing constant) to use for stretching time, for calculations
    #         Defaults to 1
    #     normalizing_constant : float
    #         Amount of days to use as a normalization factor. Defaults to 365

    #     Returns
    #     -------
    #     float
    #         Time remaining until term maturity, in normalized and stretched time

    #     """
    #     normed_days_remaining = norm_days(days_remaining, normalizing_constant)
    #     time_remaining = stretch_time(normed_days_remaining, time_stretch)
    #     return time_remaining


    # def time_to_days_remaining(time_remaining, time_stretch=1, normalizing_constant=365):
    #     """
    #     Converts normalized and stretched time remaining in pool to days
       
    #     Arguments
    #     ---------
    #     time_remaining : float
    #         Time left until term maturity, in normalized and stretched time
    #     time_stretch : float
    #         Amount of time units (in terms of a normalizing constant) to use for stretching time, for calculations
    #         Defaults to 1
    #     normalizing_constant : float
    #         Amount of days to use as a normalization factor. Defaults to 365

    #     Returns
    #     -------
    #     float
    #         Time remaining until term maturity, in days
    #     """
    #     normed_days_remaining = unstretch_time(time_remaining, time_stretch)
    #     days_remaining = unnorm_days(normed_days_remaining, normalizing_constant)
    #     return days_remaining
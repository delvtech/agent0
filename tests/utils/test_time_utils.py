"""Testing for time utilities found in elfpy/utils/time.py"""
from __future__ import annotations  # types are strings by default in 3.11

import datetime
import unittest
import pytz
import numpy as np

import elfpy.time_utils as time_utils


class TestTimeUtils(unittest.TestCase):
    """Unit tests for the parse_simulation_config function"""

    def test_current_datetime(self):
        """Test the current_datetime function"""

        now = datetime.datetime.now(pytz.timezone("Etc/GMT-0"))
        test_time = time_utils.current_datetime()

        assert (
            now < test_time < (now + datetime.timedelta(milliseconds=100))
        ), f"Unexpected time value {test_time} should be close to {now}"

    def test_block_number_to_datetime(self):
        """Test the block_number_to_datetime function"""

        start_time = datetime.datetime.strptime("28/03/1990 05:30:42", "%d/%m/%Y %H:%M:%S")

        test_cases = [
            # test 1: block number 0 (at start time)
            {
                "start_time": start_time,  # arbitrarily chosen date
                "block_number": 0,  # first block, should be at start_time
                "time_between_blocks": 12,  # time in seconds
                "expected_result": start_time,
            },
            # test 2: block number 2628000 (1 year after start)
            {
                "start_time": start_time,  # arbitrarily chosen date
                "block_number": 365 * 24 * 60 * 60 / 12,  # block after 1 year
                "time_between_blocks": 12,  # time in seconds
                "expected_result": start_time + datetime.timedelta(days=365),
            },
            # test 3: block number 69420
            {
                "start_time": start_time,  # arbitrarily chosen date
                "block_number": 69420,
                "time_between_blocks": 12,  # time in seconds
                "expected_result": start_time + datetime.timedelta(seconds=69420 * 12),
            },
        ]

        for test_case in test_cases:
            block_time = time_utils.block_number_to_datetime(
                test_case["start_time"], test_case["block_number"], test_case["time_between_blocks"]
            )
            assert block_time == test_case["expected_result"], f"unexpected time value {block_time}"

    def test_year_as_datetime(self):
        """Unit tests for the year_as_datetime function"""

        # Choose an arbitrary date as start_time
        start_time = datetime.datetime.strptime("28/03/1990 05:30:42", "%d/%m/%Y %H:%M:%S")

        test_cases = [
            # test 1: year = 6 months
            {
                "start_time": start_time,  # arbitrarily chosen date
                "year": 0.50,  # 6 months
                "expected_result": "26/09/1990 17:30:42",
            }
        ]

        for test_case in test_cases:
            year_time = time_utils.year_as_datetime(test_case["start_time"], test_case["year"])

            assert (
                datetime.datetime.strftime(year_time, "%d/%m/%Y %H:%M:%S") == test_case["expected_result"]
            ), f"unexpected time value {year_time}"

    def test_get_year_remaining(self):
        """Unit tests for the get_year_remaining function"""

        test_cases = [
            # test 1: 6mo duration, minted at term start
            {
                "market_time": 0,  # same time as market initialization
                "mint_time": 0,  # minted at time of market initialization
                "num_position_days": 0.50,  # 6 months duration
                "expected_result": 0.50,  # the entire duration remaining
                "is_error_case": False,
            },
            # test 2: 6mo duration, 3mo elapsed since mint
            {
                "market_time": 0.50,  # 0.50 years = 6 months elapsed since market initialization
                "mint_time": 0.25,  # minted at 0.25 years = 3 months after market initialization
                "num_position_days": 0.50,  # 6 months duration
                "expected_result": 0.25,  # 3 months remaining
                "is_error_case": False,
            },
            # test 3: 6mo duration, 9mo elapsed since mint
            {
                "market_time": 0.75,  # 0.75 years = 9 months elapsed since market initialization
                "mint_time": 0,  # minted at time of market initialization
                "num_position_days": 0.50,  # 6 months duration
                "expected_result": 0,  # bond has matured. No time remaining (not negative)
                "is_error_case": False,
            },
            # test 4: ERROR CASE: 6mo duration, 9mo elapsed since mint
            {
                "market_time": 0.50,  # 0.50 years = 6 months elapsed since market initialization
                "mint_time": 0.75,  # minted at 0.75 = 9 months elapsed since market initialization
                "num_position_days": 1.00,  # 1 year duration
                "expected_result": ValueError,  # bond was minted in the future
                "is_error_case": True,
            },
        ]

        for test_case in test_cases:
            if test_case["is_error_case"]:
                with self.assertRaises(test_case["expected_result"]):
                    time_remaining = time_utils.get_years_remaining(
                        test_case["market_time"], test_case["mint_time"], test_case["num_position_days"]
                    )
            else:
                time_remaining = time_utils.get_years_remaining(
                    test_case["market_time"], test_case["mint_time"], test_case["num_position_days"]
                )
                np.testing.assert_almost_equal(
                    time_remaining, test_case["expected_result"], err_msg=f"unexpected time remaining {time_remaining}"
                )

    def test_norm_days(self):
        """Unit tests for the norm_days function"""

        test_cases = [
            # test 1
            {"days": 0, "normalizing_constant": 365, "expected_result": 0},  # 1 year scale
            # test 2
            {"days": 182.5, "normalizing_constant": 365, "expected_result": 0.5},  # 6 months  # 1 year scale
            # test 3
            {"days": 360, "normalizing_constant": 180, "expected_result": 2},  # twice the scale  # arbitrary scale
        ]

        for test_case in test_cases:
            norm_days = time_utils.norm_days(test_case["days"], test_case["normalizing_constant"])

            np.testing.assert_almost_equal(
                norm_days, test_case["expected_result"], err_msg=f"unexpected normalized days {norm_days}"
            )

    def test_unnorm_days(self):
        """Unit tests for the unnorm_days function"""

        test_cases = [
            # test 1
            {"normed_days": 0, "normalizing_constant": 365, "expected_result": 0},  # 1 year scale
            # test 2
            {
                "normed_days": 0.5,  # half the scale
                "normalizing_constant": 365,  # 1 year scale
                "expected_result": 182.5,
            },
            # test 3
            {
                "normed_days": 2,  # twice the scale
                "normalizing_constant": 180,  # arbitrary scale
                "expected_result": 360,
            },
        ]

        for test_case in test_cases:
            unnormed_days = time_utils.unnorm_days(test_case["normed_days"], test_case["normalizing_constant"])

            np.testing.assert_almost_equal(
                unnormed_days, test_case["expected_result"], err_msg=f"unexpected amount of days {unnormed_days}"
            )

    def test_days_to_time_remaining(self):
        """Unit tests for the days_to_time_remaining function"""

        test_cases = [
            # test 1: 6mo remaining; 1 year scale; stretched to 20 years
            {
                "days_remaining": 182.5,  # 6 months remaining
                "time_stretch": 20,  # 20 years stretch
                "normalizing_constant": 365,  # 1 year scale
                "expected_result": 0.025,  #
            },
            # test 2: 9mo remaining; 1 year scale; stretched to 20 years
            {
                "days_remaining": 273.75,  # 9 months remaining
                "time_stretch": 20,  # 20 years stretch
                "normalizing_constant": 365,  # 1 year scale
                "expected_result": 0.0375,  #
            },
            # test 3: 3mo remaining; 180-day scale; stretched to 5 years
            {
                "days_remaining": 91.25,  # 3 months remaining
                "time_stretch": 5,  # 5 years stretch
                "normalizing_constant": 180,  # 1 year scale
                "expected_result": 0.1013888889,  #
            },
        ]

        for test_case in test_cases:
            time_remaining = time_utils.days_to_time_remaining(
                test_case["days_remaining"], test_case["time_stretch"], test_case["normalizing_constant"]
            )

            np.testing.assert_almost_equal(
                time_remaining, test_case["expected_result"], err_msg=f"unexpected time remaining {time_remaining}"
            )

    def test_time_to_days_remaining(self):
        """Unit tests for the time_to_days_remaining function"""

        test_cases = [
            # test 1: 0.025 stretched time remaining; 1 year scale; stretched to 20 years
            {
                "time_remaining": 0.025,
                "time_stretch": 20,  # 20 years stretch
                "normalizing_constant": 365,  # 1 year scale
                "expected_result": 182.5,  #
            },
            # test 2: 0.0375 stretched time remaining; 1 year scale; stretched to 20 years
            {
                "time_remaining": 0.0375,
                "time_stretch": 20,  # 20 years stretch
                "normalizing_constant": 365,  # 1 year scale
                "expected_result": 273.75,  # 9 months remaining
            },
            # test 3: 0.10 stretched time remaining; 180-day scale; stretched to 5 years
            {
                "time_remaining": 0.10,  # 3 months remaining
                "time_stretch": 5,  # 5 years stretch
                "normalizing_constant": 180,  # 1 year scale
                "expected_result": 90,  #
            },
        ]

        for test_case in test_cases:
            days_remaining = time_utils.time_to_days_remaining(
                test_case["time_remaining"], test_case["time_stretch"], test_case["normalizing_constant"]
            )

            np.testing.assert_almost_equal(
                days_remaining, test_case["expected_result"], err_msg=f"unexpected time remaining {days_remaining}"
            )

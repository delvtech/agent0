"""Testing for time utilities found in elfpy/utils/time.py"""
from __future__ import annotations  # types are strings by default in 3.11

import unittest
import numpy as np

import elfpy.time as time


class TestTimeUtils(unittest.TestCase):
    """Unit tests for the parse_simulation_config function"""

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
                    time_remaining = time.get_years_remaining(
                        test_case["market_time"], test_case["mint_time"], test_case["num_position_days"]
                    )
            else:
                time_remaining = time.get_years_remaining(
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
            norm_days = time.norm_days(test_case["days"], test_case["normalizing_constant"])

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
            unnormed_days = time.unnorm_days(test_case["normed_days"], test_case["normalizing_constant"])

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
            time_remaining = time.days_to_time_remaining(
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
            days_remaining = time.time_to_days_remaining(
                test_case["time_remaining"], test_case["time_stretch"], test_case["normalizing_constant"]
            )

            np.testing.assert_almost_equal(
                days_remaining, test_case["expected_result"], err_msg=f"unexpected time remaining {days_remaining}"
            )

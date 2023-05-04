"""Testing for time utilities found in elfpy/utils/time.py"""
from __future__ import annotations  # types are strings by default in 3.11

import unittest

import elfpy.time as time
from elfpy.utils.math import FixedPoint


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
                    time_remaining = time.get_years_remaining_fp(
                        FixedPoint(test_case["market_time"]),
                        FixedPoint(test_case["mint_time"]),
                        FixedPoint(test_case["num_position_days"]),
                    )
            else:
                time_remaining = time.get_years_remaining_fp(
                    FixedPoint(test_case["market_time"]),
                    FixedPoint(test_case["mint_time"]),
                    FixedPoint(test_case["num_position_days"]),
                )
                self.assertAlmostEqual(
                    float(time_remaining),
                    test_case["expected_result"],
                    places=18,
                    msg=f"unexpected time remaining {time_remaining}",
                )

    def test_days_to_time_remaining(self):
        """Unit tests for the days_to_time_remaining function"""

        test_cases = [
            # test 1: 6mo remaining; 1 year scale; stretched to 20 years
            {
                "days_remaining": 182.5,  # 6 months remaining
                "time_stretch": 20.0,  # 20 years stretch
                "normalizing_constant": 365.0,  # 1 year scale
                "expected_result": 0.025,  #
            },
            # test 2: 9mo remaining; 1 year scale; stretched to 20 years
            {
                "days_remaining": 273.75,  # 9 months remaining
                "time_stretch": 20.0,  # 20 years stretch
                "normalizing_constant": 365.0,  # 1 year scale
                "expected_result": 0.0375,  #
            },
            # test 3: 3mo remaining; 180-day scale; stretched to 5 years
            {
                "days_remaining": 91.25,  # 3 months remaining
                "time_stretch": 5.0,  # 5 years stretch
                "normalizing_constant": 180.0,  # 1 year scale
                "expected_result": 0.1013888889,  #
            },
        ]

        for test_case in test_cases:
            time_remaining = time.days_to_time_remaining_fp(
                FixedPoint(test_case["days_remaining"]),
                FixedPoint(test_case["time_stretch"]),
                FixedPoint(test_case["normalizing_constant"]),
            )

            self.assertAlmostEqual(
                float(time_remaining),
                test_case["expected_result"],
                places=10,
                msg=f"unexpected time remaining {time_remaining}",
            )

    def test_block_time_init(self):
        """Test default values for block time"""
        test_time = time.BlockTimeFP()
        assert test_time.time == FixedPoint(0)
        assert test_time.block_number == FixedPoint(0)
        assert test_time.step_size == FixedPoint("1.0") / FixedPoint("365.0")

    def test_block_time_setters(self):
        """Test attribute setters for block time"""
        test_time = time.BlockTimeFP()
        # default step_size
        assert test_time.step_size == FixedPoint("1.0") / FixedPoint("365.0")
        # change it
        test_time.set_step_size(FixedPoint("0.5"))
        assert test_time.step_size == FixedPoint("0.5")
        # default time
        assert test_time.time == FixedPoint(0)
        # change it
        test_time.set_time(FixedPoint("4.0"))
        assert test_time.time == FixedPoint("4.0")

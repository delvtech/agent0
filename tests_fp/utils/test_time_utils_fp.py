"""Testing for time utilities found in elfpy/utils/time.py"""
from __future__ import annotations  # types are strings by default in 3.11

import unittest

import elfpy.time as time
from elfpy.math import FixedPoint


class TestTimeUtils(unittest.TestCase):
    """Unit tests for the parse_simulation_config function"""

    APPROX_EQ: FixedPoint = FixedPoint(1e-9)

    def test_get_year_remaining(self):
        """Unit tests for the get_year_remaining function"""

        test_cases = [
            # test 1: 6mo duration, minted at term start
            {
                "market_time": FixedPoint("0.0"),  # same time as market initialization
                "mint_time": FixedPoint("0.0"),  # minted at time of market initialization
                "num_position_days": FixedPoint("0.50"),  # 6 months duration
                "expected_result": FixedPoint("0.50"),  # the entire duration remaining
                "is_error_case": False,
            },
            # test 2: 6mo duration, 3mo elapsed since mint
            {
                "market_time": FixedPoint("0.50"),  # 0.50 years = 6 months elapsed since market initialization
                "mint_time": FixedPoint("0.25"),  # minted at 0.25 years = 3 months after market initialization
                "num_position_days": FixedPoint("0.50"),  # 6 months duration
                "expected_result": FixedPoint("0.25"),  # 3 months remaining
                "is_error_case": False,
            },
            # test 3: 6mo duration, 9mo elapsed since mint
            {
                "market_time": FixedPoint("0.75"),  # 0.75 years = 9 months elapsed since market initialization
                "mint_time": FixedPoint("0.0"),  # minted at time of market initialization
                "num_position_days": FixedPoint("0.50"),  # 6 months duration
                "expected_result": FixedPoint("0.0"),  # bond has matured. No time remaining (not negative)
                "is_error_case": False,
            },
            # test 4: ERROR CASE: 6mo duration, 9mo elapsed since mint
            {
                "market_time": FixedPoint("0.50"),  # 0.50 years = 6 months elapsed since market initialization
                "mint_time": FixedPoint("0.75"),  # minted at 0.75 = 9 months elapsed since market initialization
                "num_position_days": FixedPoint("1.00"),  # 1 year duration
                "expected_result": ValueError,  # bond was minted in the future
                "is_error_case": True,
            },
        ]

        for test_case in test_cases:
            if test_case["is_error_case"]:
                with self.assertRaises(test_case["expected_result"]):
                    time_remaining = time.get_years_remaining_fp(
                        test_case["market_time"], test_case["mint_time"], test_case["num_position_days"]
                    )
            else:
                time_remaining = time.get_years_remaining_fp(
                    test_case["market_time"], test_case["mint_time"], test_case["num_position_days"]
                )
                self.assertAlmostEqual(
                    time_remaining,
                    test_case["expected_result"],
                    delta=self.APPROX_EQ,
                    msg=f"unexpected time remaining {time_remaining}",
                )

    def test_days_to_time_remaining(self):
        """Unit tests for the days_to_time_remaining function"""

        test_cases = [
            # test 1: 6mo remaining; 1 year scale; stretched to 20 years
            {
                "days_remaining": FixedPoint("182.5"),  # 6 months remaining
                "time_stretch": FixedPoint("20.0"),  # 20 years stretch
                "normalizing_constant": FixedPoint("365"),  # 1 year scale
                "expected_result": FixedPoint("0.025"),  #
            },
            # test 2: 9mo remaining; 1 year scale; stretched to 20 years
            {
                "days_remaining": FixedPoint("273.75"),  # 9 months remaining
                "time_stretch": FixedPoint("20.0"),  # 20 years stretch
                "normalizing_constant": FixedPoint("365.0"),  # 1 year scale
                "expected_result": FixedPoint("0.0375"),  #
            },
            # test 3: 3mo remaining; 180-day scale; stretched to 5 years
            {
                "days_remaining": FixedPoint("91.25"),  # 3 months remaining
                "time_stretch": FixedPoint("5.0"),  # 5 years stretch
                "normalizing_constant": FixedPoint("180.0"),  # 1 year scale
                "expected_result": FixedPoint("0.1013888889"),  #
            },
        ]

        for test_case in test_cases:
            time_remaining = time.days_to_time_remaining_fp(
                test_case["days_remaining"], test_case["time_stretch"], test_case["normalizing_constant"]
            )
            self.assertAlmostEqual(
                time_remaining,
                test_case["expected_result"],
                delta=self.APPROX_EQ,
                msg=f"unexpected time remaining {time_remaining}",
            )

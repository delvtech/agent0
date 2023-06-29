"""Testing for time utilities found in elfpy/utils/time.py"""
from __future__ import annotations  # types are strings by default in 3.11

import unittest

from fixedpointmath import FixedPoint

import elfpy.time as time


class TestTimeUtils(unittest.TestCase):
    """Unit tests for the parse_simulation_config function"""

    APPROX_EQ: FixedPoint = FixedPoint(1e-10)

    def test_get_year_remaining(self):
        """Unit tests for the get_year_remaining function"""

        test_cases = [
            # test 1: 6mo duration, minted at term start
            {
                "market_time": FixedPoint(0),  # same time as market initialization
                "mint_time": FixedPoint(0),  # minted at time of market initialization
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
                "mint_time": FixedPoint(0),  # minted at time of market initialization
                "num_position_days": FixedPoint("0.50"),  # 6 months duration
                "expected_result": FixedPoint(0),  # bond has matured. No time remaining (not negative)
                "is_error_case": False,
            },
            # test 4: ERROR CASE: 6mo duration, 9mo elapsed since mint
            {
                "market_time": FixedPoint("0.50"),  # 0.50 years = 6 months elapsed since market initialization
                "mint_time": FixedPoint("0.75"),  # minted at 0.75 = 9 months elapsed since market initialization
                "num_position_days": FixedPoint("1.0"),  # 1 year duration
                "expected_result": ValueError,  # bond was minted in the future
                "is_error_case": True,
            },
        ]

        for test_case in test_cases:
            if test_case["is_error_case"]:
                with self.assertRaises(test_case["expected_result"]):
                    time_remaining = time.get_years_remaining(
                        test_case["market_time"],
                        test_case["mint_time"],
                        test_case["num_position_days"],
                    )
            else:
                time_remaining = time.get_years_remaining(
                    test_case["market_time"],
                    test_case["mint_time"],
                    test_case["num_position_days"],
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
                "normalizing_constant": FixedPoint("365.0"),  # 1 year scale
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
            time_remaining = time.days_to_time_remaining(
                test_case["days_remaining"],
                test_case["time_stretch"],
                test_case["normalizing_constant"],
            )

            self.assertAlmostEqual(
                time_remaining,
                test_case["expected_result"],
                delta=self.APPROX_EQ,
                msg=f"unexpected time remaining {time_remaining}",
            )

    def test_block_time_init(self):
        """Test default values for block time"""
        test_time = time.BlockTime()
        self.assertEqual(test_time.time, FixedPoint(0))
        self.assertEqual(test_time.block_number, FixedPoint(0))
        self.assertEqual(test_time.step_size, FixedPoint("1.0") / FixedPoint("365.0"))
        with self.assertRaises(ValueError):
            test_time = time.BlockTime(unit=time.TimeUnit.SECONDS)

    def test_block_time_setters(self):
        """Test attribute setters for block time"""
        test_time = time.BlockTime()
        # time
        self.assertEqual(test_time.time, FixedPoint(0))
        test_time.set_time(FixedPoint("4.0"), unit=time.TimeUnit.YEARS)
        self.assertEqual(test_time.time, FixedPoint("4.0"))
        with self.assertRaises(AttributeError):
            test_time.time = FixedPoint("2.0")
        with self.assertRaises(TypeError):
            test_time.set_time(2, unit=time.TimeUnit.YEARS)  # type: ignore
        # step_size
        self.assertEqual(test_time.step_size, FixedPoint("1.0") / FixedPoint("365.0"))
        test_time.set_step_size(FixedPoint("0.5"))
        self.assertEqual(test_time.step_size, FixedPoint("0.5"))
        with self.assertRaises(AttributeError):
            test_time.step_size = FixedPoint("0.25")
        with self.assertRaises(TypeError):
            test_time.set_step_size(0.25)  # type: ignore
        # block_number
        self.assertEqual(test_time.block_number, FixedPoint(0))
        test_time.set_block_number(FixedPoint("5.0"))
        self.assertEqual(test_time.block_number, FixedPoint("5.0"))
        with self.assertRaises(AttributeError):
            test_time.block_number = FixedPoint("3.0")
        with self.assertRaises(TypeError):
            test_time.set_step_size(3.0)  # type: ignore

    def test_time_tick(self):
        """Test the BlockTime tick function"""
        test_time = time.BlockTime()
        self.assertEqual(test_time.time, FixedPoint(0))
        test_time.tick(FixedPoint(5))
        self.assertEqual(test_time.time, FixedPoint(5))
        test_time.tick(FixedPoint(1))
        self.assertEqual(test_time.time, FixedPoint(6))

    def test_time_step(self):
        """Test the BlockTime step function"""
        test_time = time.BlockTime()
        self.assertEqual(test_time.time, FixedPoint(0))
        test_time.step()
        self.assertEqual(test_time.time, FixedPoint("1.0") / FixedPoint("365.0"))
        test_time.step()
        self.assertEqual(test_time.time, FixedPoint("2.0") / FixedPoint("365.0"))

    def test_time_conversion(self):
        """Test the BlockTime unit conversion function"""
        test_time = time.BlockTime()
        test_time.set_time(FixedPoint("1.0"), time.TimeUnit.YEARS)
        self.assertEqual(test_time.time_conversion(time.TimeUnit.SECONDS), FixedPoint("31_556_952.0"))
        self.assertEqual(test_time.time_conversion(time.TimeUnit.MINUTES), FixedPoint("525_600.0"))
        self.assertEqual(test_time.time_conversion(time.TimeUnit.HOURS), FixedPoint("8_760.0"))
        self.assertEqual(test_time.time_conversion(time.TimeUnit.DAYS), FixedPoint("365.0"))
        self.assertEqual(test_time.time_conversion(time.TimeUnit.YEARS), FixedPoint("1.0"))
        test_time.set_time(FixedPoint("2.0"), time.TimeUnit.YEARS)
        self.assertEqual(test_time.time_conversion(time.TimeUnit.SECONDS), FixedPoint(2 * 31_556_952))
        self.assertEqual(test_time.time_conversion(time.TimeUnit.MINUTES), FixedPoint(2 * 525_600))
        self.assertEqual(test_time.time_conversion(time.TimeUnit.HOURS), FixedPoint(2 * 8_760))
        self.assertEqual(test_time.time_conversion(time.TimeUnit.DAYS), FixedPoint(2 * 365))
        self.assertEqual(test_time.time_conversion(time.TimeUnit.YEARS), FixedPoint(2 * 1))

"""Testing for price utilities found in src/elfpy/utils/price.py"""
from __future__ import annotations  # types are strings by default in 3.11

import unittest
import numpy as np

from elfpy.types import StretchedTime
from elfpy.utils import price as price_utils


class BasePriceTest(unittest.TestCase):
    """Unit tests for price utilities"""

    # ### Spot Price and APR ###

    def run_calc_apr_from_spot_price_test(self):
        """Unit tests for the calc_apr_from_spot_price function"""

        test_cases = [
            # test 1: 0.95 price; 6mo remaining;
            {
                "price": 0.95,
                "time_remaining": StretchedTime(
                    days=182.5,  # 6 months = 0.5 years
                    time_stretch=1,
                    normalizing_constant=365,
                ),
                # APR = (1 - 0.95) / 0.95 / 0.5
                #     = 0.1052631579
                "expected_result": 0.1052631579,  # just over 10% APR
            },
            # test 2: 0.99 price; 6mo remaining;
            {
                "price": 0.99,
                "time_remaining": StretchedTime(
                    days=182.5,  # 6 months = 0.5 years
                    time_stretch=1,
                    normalizing_constant=365,
                ),
                # APR = (1 - 0.99) / 0.99 / 0.5
                #     = 0.0202020202
                "expected_result": 0.0202020202,  # just over 2% APR
            },
            # test 3: 1.00 price; 6mo remaining;
            {
                "price": 1.00,  # 0% APR
                "time_remaining": StretchedTime(
                    days=182.5,  # 6 months = 0.5 years
                    time_stretch=1,
                    normalizing_constant=365,
                ),
                # APR = (1 - 1) / 1 / 0.5
                #     = 0
                "expected_result": 0,  # 0% APR
            },
            # test 4: 0.95 price; 3mo remaining;
            {
                "price": 0.95,
                "time_remaining": StretchedTime(
                    days=91.25,  # 3 months = 0.25 years
                    time_stretch=1,
                    normalizing_constant=365,
                ),
                # APR = (1 - 0.95) / 0.95 / 0.25
                #     = 0.2105263158
                "expected_result": 0.2105263158,  # just over 21% APR
            },
            # test 5: 0.95 price; 12mo remaining;
            {
                "price": 0.95,
                "time_remaining": StretchedTime(
                    days=365,  # 12 months = 1 years
                    time_stretch=1,
                    normalizing_constant=365,
                ),
                # APR = (1 - 0.95) / 0.95 / 1
                #     = 0.05263157895
                "expected_result": 0.05263157895,  # just over 5% APR
            },
            # test 6: 0.10 price; 3mo remaining;
            {
                "price": 0.10,  # 0% APR
                "time_remaining": StretchedTime(
                    days=91.25,  # 3 months = 0.25 years
                    time_stretch=1,
                    normalizing_constant=365,
                ),
                # APR = (1 - 0.10) / 0.10 / 0.25
                #     = 0
                "expected_result": 36,  # 3600% APR
            },
            # test 7: ERROR CASE
            #   -0.50 (negative) price; 3mo remaining;
            #   the function asserts that price > 0, so this case should raise an AssertionError
            {
                "price": -0.50,  # 0% APR
                "time_remaining": StretchedTime(
                    days=91.25,  # 3 months = 0.25 years
                    time_stretch=1,
                    normalizing_constant=365,
                ),
                # APR = (1 - 0.10) / 0.10 / 0.25
                #     = 0
                "is_error_case": True,  # failure case
                "expected_result": AssertionError,
            },
            # test 8: ERROR CASE
            #   0.95 price; -3mo remaining (negative);
            #   the function asserts that normalized_time_remaining > 0, so this case \
            #   should raise an AssertionError
            {
                "price": 0.95,  # 0% APR
                "time_remaining": StretchedTime(
                    days=-91.25,  # -3 months = -0.25 years
                    time_stretch=1,
                    normalizing_constant=365,
                ),
                # APR = (1 - 0.10) / 0.10 / 0.25
                #     = 0
                "is_error_case": True,  # failure case
                "expected_result": AssertionError,
            },
            # test 9: STRANGE RESULT CASE
            #   1.50 price (>1.00); 3mo remaining;
            #   the AMM math shouldn't let price be greater than 1
            {
                "price": 1.50,  # 0% APR
                "time_remaining": StretchedTime(
                    days=91.25,  # 3 months = 0.25 years
                    time_stretch=1,
                    normalizing_constant=365,
                ),
                # APR = (1 - 1.50) / 1.50 / 0.25
                #     = -1.333333333
                "expected_result": -1.3333333333333333,  # strange result
            },
        ]

        for test_case in test_cases:

            # Check if this test case is supposed to fail
            if "is_error_case" in test_case and test_case["is_error_case"]:

                # Check that test case throws the expected error
                with self.assertRaises(test_case["expected_result"]):
                    apr = price_utils.calc_apr_from_spot_price(
                        price=test_case["price"], time_remaining=test_case["time_remaining"]
                    )

            # If test was not supposed to fail, continue normal execution
            else:
                apr = price_utils.calc_apr_from_spot_price(
                    price=test_case["price"], time_remaining=test_case["time_remaining"]
                )

                np.testing.assert_almost_equal(apr, test_case["expected_result"], err_msg="unexpected apr")

    def run_calc_spot_price_from_apr_test(self):
        """Unit tests for the calc_spot_price_from_apr function"""

        test_cases = [
            # test 1: 10% apr; 6mo remaining;
            {
                "apr": 0.10,  # 10% apr
                "time_remaining": StretchedTime(
                    days=182.5,  # 6 months = 0.5 years
                    time_stretch=1,
                    normalizing_constant=365,
                ),
                # price = 1 / (1 + 0.10 * 0.5)
                #     = 0.1052631579
                "expected_result": 0.9523809524,  # just over 0.95
            },
            # test 2: 2% apr; 6mo remaining;
            {
                "apr": 0.02,  # 2% apr
                "time_remaining": StretchedTime(
                    days=182.5,  # 6 months = 0.5 years
                    time_stretch=1,
                    normalizing_constant=365,
                ),
                # price = 1 / (1 + 0.02 * 0.5)
                #     = 0.9900990099
                "expected_result": 0.9900990099,  # just over 0.99
            },
            # test 3: 0% apr; 6mo remaining;
            {
                "apr": 0,  # 0% apr
                "time_remaining": StretchedTime(
                    days=182.5,  # 6 months = 0.5 years
                    time_stretch=1,
                    normalizing_constant=365,
                ),
                # price = 1 / (1 + 0 * 0.5)
                #     = 1
                "expected_result": 1,
            },
            # test 4: 21% apr; 3mo remaining;
            {
                "apr": 0.21,  # 21% apr
                "time_remaining": StretchedTime(
                    days=91.25,  # 3 months = 0.25 years
                    time_stretch=1,
                    normalizing_constant=365,
                ),
                # price = 1 / (1 + 0.21 * 0.25)
                #     = 0.2105263158
                "expected_result": 0.9501187648,  # just over 0.95
            },
            # test 5: 5% apr; 12mo remaining;
            {
                "apr": 0.05,  # 5% apr
                "time_remaining": StretchedTime(
                    days=365,  # 12 months = 1 years
                    time_stretch=1,
                    normalizing_constant=365,
                ),
                # price = 1 / (1 + 0.05 * 1)
                #     = 0.05263157895
                "expected_result": 0.9523809524,  # just over 0.95
            },
            # test 6: 3600% apr; 3mo remaining;
            {
                "apr": 36,  # 3600% apr
                "time_remaining": StretchedTime(
                    days=91.25,  # 3 months = 0.25 years
                    time_stretch=1,
                    normalizing_constant=365,
                ),
                # price = 1 / (1 + 36 * 0.25)
                #     = 0.1
                "expected_result": 0.10,
            },
            # test 7: 0% apr; 3mo remaining;
            {
                "apr": 0,  # 0% apr
                "time_remaining": StretchedTime(
                    days=91.25,  # 3 months = 0.25 years
                    time_stretch=1,
                    normalizing_constant=365,
                ),
                # price = 1 / (1 + 0 * 0.25)
                #     = 0
                "expected_result": 1.00,
            },
            # test 8: 5% apr; no time remaining;
            {
                "apr": 5,  # 500% apr
                "time_remaining": StretchedTime(
                    days=0,  # 0 months = 0 years
                    time_stretch=1,
                    normalizing_constant=365,
                ),
                # price = 1 / (1 + 5 * 0)
                #     = 0
                "expected_result": 1.00,
            },
        ]

        for test_case in test_cases:
            spot_price = price_utils.calc_spot_price_from_apr(
                apr=test_case["apr"], time_remaining=test_case["time_remaining"]
            )

            np.testing.assert_almost_equal(spot_price, test_case["expected_result"], err_msg="unexpected apr")


class TestPriceUtils(BasePriceTest):
    """Test calculations for each of the price utility functions"""

    def test_calc_apr_from_spot_price(self):
        """Execute the test"""
        self.run_calc_apr_from_spot_price_test()

    def test_calc_spot_price_from_apr(self):
        """Execute the test"""
        self.run_calc_spot_price_from_apr_test()

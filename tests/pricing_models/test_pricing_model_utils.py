"""Testing for the utility methods in the pricing models"""
import unittest
from typing import Union

import numpy as np

import elfpy.pricing_models.yieldspace as yieldspace_pm
import elfpy.pricing_models.hyperdrive as hyperdrive_pm
from elfpy.markets.hyperdrive.hyperdrive_market import MarketState
from elfpy.utils import sim_utils
import elfpy.time as time


class BasePricingModelUtilsTest(unittest.TestCase):
    """Unit tests for price utilities"""

    def run_calc_k_const_test(
        self, pricing_model: Union[hyperdrive_pm.HyperdrivePricingModel, yieldspace_pm.YieldspacePricingModel]
    ):
        """Unit tests for calc_k_const function

        .. todo:: fix comments to actually reflect test case values
        """

        test_cases = [
            # test 1: 500k share_reserves; 500k bond_reserves
            #   1 share price; 1 init_share_price; 3mo elapsed
            {
                "market_state": MarketState(
                    share_reserves=500000,  # z = 500000
                    bond_reserves=500000,  # y = 500000
                    share_price=1,  # c = 1
                    init_share_price=1,  # u = 1
                ),
                "time_elapsed": 0.25,  # t = 0.25
                # k = c/u * (u*y)**t + (2y+c*x)**t
                #     = 1/1 * (1*500000)**0.25 + (2*500000+1*500000)**0.25
                #     = 61.587834600530776
                "expected_result": 61.587834600530776,
            },
            # test 2: 500k share_reserves; 500k bond_reserves
            #   1 share price; 1 init_share_price; 12mo elapsed
            {
                "market_state": MarketState(
                    share_reserves=500000,  # x = 500000
                    bond_reserves=500000,  # y = 500000
                    share_price=1,  # c = 1
                    init_share_price=1,  # u = 1
                ),
                "time_elapsed": 1,  # t = 1
                # k = c/u * (u*y)**t + (2y+c*x)**t
                #     = 1/1 * (1*500000)**1 + (2*500000+1*500000)**1
                #     = 2000000
                "expected_result": 2000000,
            },
            # test 3: 5M share_reserves; 5M bond_reserves
            #   2 share price; 1.5 init_share_price; 6mo elapsed
            {
                "market_state": MarketState(
                    share_reserves=5000000,  # x = 5000000
                    bond_reserves=5000000,  # y = 5000000
                    share_price=2,  # c = 2
                    init_share_price=1.5,  # u = 1.5
                ),
                "time_elapsed": 0.50,  # t = 0.50
                # k = c/u * (u*y)**t + (2y+c*x)**t
                #     = 2/1.5 * (1.5*5000000)**0.50 + (2*5000000+2*5000000)**0.50
                #     = 8123.619671700687
                "expected_result": 8123.619671700687,
            },
            # test 4: 0M share_reserves; 5M bond_reserves
            #   2 share price; 1.5 init_share_price; 3mo elapsed
            {
                "market_state": MarketState(
                    share_reserves=0,  # x = 0
                    bond_reserves=5000000,  # y = 5000000
                    share_price=2,  # c = 2
                    init_share_price=1.5,  # u = 1.5
                ),
                "time_elapsed": 0.25,  # t = 0.25
                # k = c/u * (u*y)**t + (2y+c*x)**t
                #     = 2/1.5 * (1*5000000)**0.25 + (2*5000000+1*5000000)**0.25
                #     = 61.587834600530776
                "expected_result": 56.23413251903491,
            },
            # test 5: 0 share_reserves; 0 bond_reserves
            #   2 share price; 1.5 init_share_price; 3mo elapsed
            {
                "market_state": MarketState(
                    share_reserves=0,  # x = 0
                    bond_reserves=0,  # y = 0
                    share_price=2,  # c = 2
                    init_share_price=1.5,  # u = 1.5
                ),
                "time_elapsed": 0.25,  # t = 0.25
                # k = c/u * (u*y)**t + (2y+c*x)**t
                #     = 2/1.5 * (1*5000000)**0.25 + (2*5000000+1*5000000)**0.25
                #     = 61.587834600530776
                "expected_result": 0,
            },
            # test 6: ERROR CASE; 0 INIT SHARE PRICE
            #   5M share_reserves; 5M bond_reserves
            #   2 share price; 1.5 init_share_price; 6mo elapsed
            {
                "market_state": MarketState(
                    share_reserves=5000000,  # x = 5000000
                    bond_reserves=5000000,  # y = 5000000
                    share_price=2,  # c = 2
                    init_share_price=0,  # ERROR CASE; u = 0
                ),
                "time_elapsed": 0.50,  # t = 0.50
                # k = c/u * (u*y)**t + (2y+c*x)**t
                #     = 1/1 * (1*5000000)**0.50 + (2*5000000+1*5000000)**0.50
                #     = 61.587834600530776
                "is_error_case": True,  # failure case
                "expected_result": ZeroDivisionError,
            },
        ]

        for test_case in test_cases:
            # Check if this test case is supposed to fail
            if "is_error_case" in test_case and test_case["is_error_case"]:
                # Check that test case throws the expected error
                with self.assertRaises(test_case["expected_result"]):
                    k = float(
                        pricing_model._calc_k_const(  # pylint: disable=protected-access
                            market_state=test_case["market_state"],
                            time_remaining=time.StretchedTime(
                                days=time.time_to_days_remaining(1 - test_case["time_elapsed"]),
                                time_stretch=1,
                                normalizing_constant=365,
                            ),
                        )
                    )

            # If test was not supposed to fail, continue normal execution
            else:
                k = float(
                    pricing_model._calc_k_const(  # pylint: disable=protected-access
                        market_state=test_case["market_state"],
                        time_remaining=time.StretchedTime(
                            days=time.time_to_days_remaining(1 - test_case["time_elapsed"]),
                            time_stretch=1,
                            normalizing_constant=365,
                        ),
                    )
                )
                np.testing.assert_almost_equal(k, test_case["expected_result"], err_msg="unexpected k")


class TestPricingModelUtils(BasePricingModelUtilsTest):
    """Test calculations for each of the pricing model utility functions"""

    def test_calc_k_const(self):
        """Execute the test"""
        self.run_calc_k_const_test(sim_utils.get_pricing_model("hyperdrive"))
        self.run_calc_k_const_test(sim_utils.get_pricing_model("yieldspace"))

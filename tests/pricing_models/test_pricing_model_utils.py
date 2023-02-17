"""Testing for the utility methods in the pricing models"""
import unittest
import numpy as np

from elfpy.pricing_models.base import PricingModel
from elfpy.types import MarketState, StretchedTime
from elfpy.utils import sim_utils
from elfpy.utils.time import time_to_days_remaining


class BasePricingModelUtilsTest(unittest.TestCase):
    """Unit tests for price utilities"""

    def run_calc_liquidity_test(self, pricing_model: PricingModel):
        """Unit tests for the pricing model calc_liquidity function

        Example check for the test:
            test 1: 5M target_liquidity; 5% APR;
            6mo remaining; 22.186877016851916 time_stretch (targets 5% APR);
            1 init share price; 1 share price
                l = target_liquidity = 5_000_000
                r = target_apr = 0.05
                days = 182.5
                time_stretch = 3.09396 / (0.02789 * r * 100)
                t = days / 365
                T = t / time_stretch
                u = init_share_price = 1
                c = share_price = 1  # share price of the LP in the yield source; c = 1
                z = share_reserves = l / c
                y = bond_reserves = (z / 2) * (u * (1 + r * t) ** (1 / T) - c)
                p = ((2 * y + c * z) / (u * z)) ** (-T)  # spot price from reserves
                final_apr = (1 - p) / (p * t)
                total_liquidity = c * z
        """

        test_cases = [
            # test 1: 5M target_liquidity; 5% APR;
            #   6mo remaining; 22.186877016851916 time_stretch (targets 5% APR);
            #   1 init share price; 1 share price
            {
                "target_liquidity": 5_000_000,  # Targeting 5M liquidity
                "target_apr": 0.05,  # fixed rate APR you'd get from purchasing bonds; r = 0.05
                "time_remaining": StretchedTime(
                    days=182.5,  # 6 months remaining; t = 0.50,
                    time_stretch=22.186877016851916,
                    normalizing_constant=365,
                ),
                "init_share_price": 1,  # original share price pool started; u = 1
                "share_price": 1,  # share price of the LP in the yield source; c = 1
                "expected_share_reserves": 5_000_000,  # target_liquidity / share_price
                "expected_bond_reserves": 4_978_218.90560554,
            },
            # test 2: 5M target_liquidity; 2% APR;
            #   6mo remaining; 22.186877016851916 time_stretch (targets 5% APR);
            #   1 init share price; 1 share price
            {
                "target_liquidity": 5_000_000,  # Targeting 5M liquidity
                "target_apr": 0.02,  # fixed rate APR you'd get from purchasing bonds; r = 0.02
                "time_remaining": StretchedTime(
                    days=182.5,  # 6 months remaining; t = 0.50
                    time_stretch=55.467192542129794,
                    normalizing_constant=365,
                ),
                "init_share_price": 1,  # original share price pool started; u = 1
                "share_price": 1,  # share price of the LP in the yield source; c = 1
                "expected_share_reserves": 5_000_000.0,  # target_liquidity / share_price
                "expected_bond_reserves": 5_039_264.014565533,
            },
            # test 3: 5M target_liquidity; 8% APR;
            #   6mo remaining; 22.186877016851916 time_stretch (targets 5% APR);
            #   1 init share price; 1 share price
            {
                "target_liquidity": 5_000_000,  # Targeting 5M liquidity
                "target_apr": 0.08,  # fixed rate APR you'd get from purchasing bonds; r = 0.08
                "time_remaining": StretchedTime(
                    days=182.5,  # 6 months remaining; t = 0.50
                    time_stretch=13.866798135532449,
                    normalizing_constant=365,
                ),
                "init_share_price": 1,  # original share price pool started; u = 1
                "share_price": 1,  # share price of the LP in the yield source; c = 1
                "expected_share_reserves": 5_000_000.0,
                "expected_bond_reserves": 4_918_835.884062026,
            },
            # test 4:  10M target_liquidity; 3% APR
            #   3mo remaining; 36.97812836141986 time_stretch (targets 3% APR);
            #   1.5 init share price; 2 share price
            {
                "target_liquidity": 10_000_000,  # Targeting 10M liquidity
                "target_apr": 0.03,  # fixed rate APR you'd get from purchasing bonds; r = 0.03
                "time_remaining": StretchedTime(
                    days=91.25,  # 3 months remaining; t = 0.25
                    time_stretch=36.97812836141987,
                    normalizing_constant=365,
                ),
                "init_share_price": 1.5,  # original share price when pool started
                "share_price": 2,  # share price of the LP in the yield source
                "expected_share_reserves": 5_000_000.0,
                "expected_bond_reserves": 6_324_407.309278079,
            },
            # test 5:  10M target_liquidity; 5% APR
            #   9mo remaining; 36.97812836141986 time_stretch (targets 3% APR);
            #   1.5 init share price; 2 share price
            {
                "target_liquidity": 10_000_000,  # Targeting 10M liquidity
                "target_apr": 0.03,  # fixed rate APR you'd get from purchasing bonds; r = 0.03
                "time_remaining": StretchedTime(
                    days=273.75,  # 9 months remaining; t = 0.75
                    time_stretch=36.97812836141987,
                    normalizing_constant=365,
                ),
                "init_share_price": 1.3,  # original share price when pool started
                "share_price": 1.5,  # share price of the LP in the yield source
                "expected_share_reserves": 6666666.666666667,
                "expected_bond_reserves": 7979677.952016878,
            },
            # test 6: ERROR CASE: 0 TARGET LIQUIDITY -> ZeroDivisionError
            #   10M target_liquidity; 6% APR;
            #   3mo remaining; 36.97812836141986 time_stretch (targets 3% APR);
            #   1 init share price; 1 share price
            {
                "target_liquidity": 0,  # ERROR CASE; Targeting 0 liquidity
                "target_apr": 0.06,  # fixed rate APR you'd get from purchasing bonds; r = 0.06
                "time_remaining": StretchedTime(
                    days=91.25,  # 3 months remaining; t = 0.25
                    time_stretch=36.97812836141986,
                    normalizing_constant=365,
                ),
                "init_share_price": 1,  # original share price when pool started
                "share_price": 1,  # share price of the LP in the yield source
                "is_error_case": True,  # this test is supposed to fail
                "expected_result": ZeroDivisionError,
                "expected_share_reserves": ZeroDivisionError,  #
                "expected_bond_reserves": ZeroDivisionError,  #
            },
        ]
        # Loop through the test cases & pricing model
        for test_case in [test_cases[0]]:
            # Check if this test case is supposed to fail
            if "is_error_case" in test_case and test_case["is_error_case"]:
                # Check that test case throws the expected error
                with self.assertRaises(test_case["expected_result"]):
                    # share, bond
                    share_reserves, bond_reserves = pricing_model.calc_liquidity(
                        market_state=MarketState(
                            init_share_price=test_case["init_share_price"],
                            share_price=test_case["share_price"],
                        ),
                        target_liquidity=test_case["target_liquidity"],
                        target_apr=test_case["target_apr"],
                        position_duration=test_case["time_remaining"],
                    )
            # If test was not supposed to fail, continue normal execution
            else:
                share_reserves, bond_reserves = pricing_model.calc_liquidity(
                    market_state=MarketState(
                        init_share_price=test_case["init_share_price"],
                        share_price=test_case["share_price"],
                    ),
                    target_liquidity=test_case["target_liquidity"],
                    target_apr=test_case["target_apr"],
                    position_duration=test_case["time_remaining"],
                )
                np.testing.assert_almost_equal(
                    test_case["expected_share_reserves"],
                    share_reserves,
                    err_msg="unexpected share_reserves",
                )
                np.testing.assert_almost_equal(
                    test_case["expected_bond_reserves"],
                    bond_reserves,
                    err_msg="unexpected bond_reserves",
                )

    def run_calc_k_const_test(self, pricing_model: PricingModel):
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
                            time_remaining=StretchedTime(
                                days=time_to_days_remaining(1 - test_case["time_elapsed"]),
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
                        time_remaining=StretchedTime(
                            days=time_to_days_remaining(1 - test_case["time_elapsed"]),
                            time_stretch=1,
                            normalizing_constant=365,
                        ),
                    )
                )
                np.testing.assert_almost_equal(k, test_case["expected_result"], err_msg="unexpected k")

    def run_calc_bond_for_target_apr(self, pricing_model: PricingModel):
        """Unit tests for calc_bond_for_target_apr"""
        test_cases = [
            {
                "expected_result": 0,
                "target_apr": 0.0,
                "base": 0,
                "position_duration": 365,
                "share_price": 1,
                "is_error_case": False,
            },
            {
                "expected_result": 100,
                "target_apr": 0.0,
                "base": 100,
                "position_duration": 365,
                "share_price": 1,
                "is_error_case": False,
            },
            {
                "expected_result": 111.11111111111111,
                "target_apr": 0.1,
                "base": 100,
                "position_duration": 365,
                "share_price": 1,
                "is_error_case": False,
            },
            {
                "expected_result": 105.26315789473685,
                "target_apr": 0.1,
                "base": 100,
                "position_duration": 182.5,
                "share_price": 1,
                "is_error_case": False,
            },
            {
                "expected_result": 52.631578947368425,
                "target_apr": 0.1,
                "base": 100,
                "position_duration": 182.5,
                "share_price": 2,
                "is_error_case": False,
            },
            {
                "expected_result": AssertionError,
                "target_apr": 1.1,
                "base": 100,
                "position_duration": 365,
                "share_price": 1,
                "is_error_case": True,
            },
            {
                "expected_result": AssertionError,
                "target_apr": 0.9,
                "base": -100,
                "position_duration": 365,
                "share_price": 1,
                "is_error_case": True,
            },
            {
                "expected_result": AssertionError,
                "target_apr": 0.9,
                "base": 100,
                "position_duration": 500,
                "share_price": 1,
                "is_error_case": True,
            },
            {
                "expected_result": AssertionError,
                "target_apr": 0.9,
                "base": 100,
                "position_duration": 365,
                "share_price": -1,
                "is_error_case": True,
            },
        ]

        for test_case in test_cases:
            # Check if this test case is supposed to fail
            if "is_error_case" in test_case and test_case["is_error_case"]:
                # Check that test case throws the expected error
                with self.assertRaises(test_case["expected_result"]):
                    bond = float(
                        pricing_model.calc_bond_for_target_apr(
                            target_apr=test_case["target_apr"],
                            base=test_case["base"],
                            position_duration=StretchedTime(
                                days=test_case["position_duration"],
                                time_stretch=1,
                                normalizing_constant=test_case["position_duration"],
                            ),
                            share_price=test_case["share_price"],
                        )
                    )

            # If test was not supposed to fail, continue normal execution
            else:
                bond = float(
                    pricing_model.calc_bond_for_target_apr(
                        target_apr=test_case["target_apr"],
                        base=test_case["base"],
                        position_duration=StretchedTime(
                            days=test_case["position_duration"],
                            time_stretch=1,
                            normalizing_constant=test_case["position_duration"],
                        ),
                        share_price=test_case["share_price"],
                    )
                )
                np.testing.assert_almost_equal(bond, test_case["expected_result"], err_msg="unexpected bond")

    def run_calc_base_for_target_apr(self, pricing_model: PricingModel):
        """Unit tests for calc_base_for_target_apr"""
        test_cases = [
            {
                "expected_result": 0,
                "target_apr": 0.0,
                "bond": 0,
                "position_duration": 365,
                "share_price": 1,
                "is_error_case": False,
            },
            {
                "expected_result": 100,
                "target_apr": 0.0,
                "bond": 100,
                "position_duration": 365,
                "share_price": 1,
                "is_error_case": False,
            },
            {
                "expected_result": 90,
                "target_apr": 0.1,
                "bond": 100,
                "position_duration": 365,
                "share_price": 1,
                "is_error_case": False,
            },
            {
                "expected_result": 95,
                "target_apr": 0.1,
                "bond": 100,
                "position_duration": 182.5,
                "share_price": 1,
                "is_error_case": False,
            },
            {
                "expected_result": 190,
                "target_apr": 0.1,
                "bond": 100,
                "position_duration": 182.5,
                "share_price": 2,
                "is_error_case": False,
            },
            {
                "expected_result": AssertionError,
                "target_apr": 1.1,
                "bond": 100,
                "position_duration": 365,
                "share_price": 1,
                "is_error_case": True,
            },
            {
                "expected_result": AssertionError,
                "target_apr": 0.9,
                "bond": -100,
                "position_duration": 365,
                "share_price": 1,
                "is_error_case": True,
            },
            {
                "expected_result": AssertionError,
                "target_apr": 0.9,
                "bond": 100,
                "position_duration": 500,
                "share_price": 1,
                "is_error_case": True,
            },
            {
                "expected_result": AssertionError,
                "target_apr": 0.9,
                "bond": 100,
                "position_duration": 365,
                "share_price": -1,
                "is_error_case": True,
            },
        ]

        for test_case_number, test_case in enumerate(test_cases):
            # Check if this test case is supposed to fail
            if "is_error_case" in test_case and test_case["is_error_case"]:
                # Check that test case throws the expected error
                with self.assertRaises(test_case["expected_result"], msg=f"test case {test_case_number=}"):
                    bond = float(
                        pricing_model.calc_base_for_target_apr(
                            target_apr=test_case["target_apr"],
                            bond=test_case["bond"],
                            position_duration=StretchedTime(
                                days=test_case["position_duration"],
                                time_stretch=1,
                                normalizing_constant=test_case["position_duration"],
                            ),
                            share_price=test_case["share_price"],
                        )
                    )

            # If test was not supposed to fail, continue normal execution
            else:
                bond = float(
                    pricing_model.calc_base_for_target_apr(
                        target_apr=test_case["target_apr"],
                        bond=test_case["bond"],
                        position_duration=StretchedTime(
                            days=test_case["position_duration"],
                            time_stretch=1,
                            normalizing_constant=test_case["position_duration"],
                        ),
                        share_price=test_case["share_price"],
                    )
                )
                np.testing.assert_almost_equal(bond, test_case["expected_result"], err_msg="unexpected bond")


class TestPricingModelUtils(BasePricingModelUtilsTest):
    """Test calculations for each of the pricing model utility functions"""

    def test_calc_k_const(self):
        """Execute the test"""
        self.run_calc_k_const_test(sim_utils.get_pricing_model("hyperdrive"))
        self.run_calc_k_const_test(sim_utils.get_pricing_model("yieldspace"))

    def test_calc_liquidity(self):
        """Execute the test"""
        self.run_calc_liquidity_test(sim_utils.get_pricing_model("hyperdrive"))
        self.run_calc_liquidity_test(sim_utils.get_pricing_model("yieldspace"))

    def test_calc_bond_for_target_apr(self):
        """Execute the test"""
        # this calc is pricing model agnostic, picking hyperdrive
        self.run_calc_bond_for_target_apr(sim_utils.get_pricing_model("hyperdrive"))

    def test_calc_base_for_target_apr(self):
        """Execute the test"""
        # this calc is pricing model agnostic, picking hyperdrive
        self.run_calc_base_for_target_apr(sim_utils.get_pricing_model("hyperdrive"))

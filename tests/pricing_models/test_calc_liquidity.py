"""Tests for calculating liquidity within pricing models"""

import unittest
import numpy as np

from elfpy.pricing_models import ElementPricingModel, HyperdrivePricingModel


class LiquidityTestDefinitions(unittest.TestCase):
    """Unit tests for liquidity calculations"""

    def run_calc_total_liquidity_from_reserves_and_price_test(self, pricing_model):
        """
        Test cases for calc_total_liquidity_from_reserves_and_price
        The functions calculates total liquidity using the following formula:
        liquidity = base_asset_reserves + token_asset_reserves * spot_price
        """

        # Test cases
        # 1. 500k base asset, 500k pts, p = 0.95
        # liquidity = 500000 + 500000 * 0.95 = 975000
        # 2. 800k base asset, 200k pts, p = 0.98
        # liquidity = 800000 + 200000 * 0.98 = 996000
        # 3. 200k base asset, 800k pts, p = 0.92
        # liquidity = 200000 + 800000 * 0.92 = 936000
        # 4. 1M base asset, 0 pts, p = 1.00
        # liquidity = 1000000 + 0 * 1.00 = 1000000
        # 5. 0 base asset, 1M pts, p = 0.90
        # liquidity = 0 + 1000000 * 0.90 = 900000
        # 6. 500k base asset, 500k pts, p = 1.50
        # liquidity = 500000 + 500000 * 1.50 = 1250000
        # The AMM math wouldn't allow p > 1
        # 7. 999999 base asset, 1 pt, p = 0
        # liquidity = 950000 + 50000 * 0 = 950000
        # The AMM math wouldn't allow p = 0. In fact, for this ratio p should be almost 1.00

        test_cases = [
            # test 1
            {
                "base_asset_reserves": 500000,
                "token_asset_reserves": 500000,
                "spot_price": 0.95,
                "expected_result": 975000,
            },
            # test 2
            {
                "base_asset_reserves": 800000,
                "token_asset_reserves": 200000,
                "spot_price": 0.98,
                "expected_result": 996000,
            },
            # test 3
            {
                "base_asset_reserves": 200000,
                "token_asset_reserves": 800000,
                "spot_price": 0.92,
                "expected_result": 936000,
            },
            # test 4
            {"base_asset_reserves": 1000000, "token_asset_reserves": 0, "spot_price": 1.00, "expected_result": 1000000},
            # test 5
            {"base_asset_reserves": 0, "token_asset_reserves": 1000000, "spot_price": 0.90, "expected_result": 900000},
            # test 6. Price > 1.00. The AMM math wouldn't allow this though but the function doesn't check for it
            {
                "base_asset_reserves": 500000,
                "token_asset_reserves": 500000,
                "spot_price": 1.50,
                "expected_result": 1250000,
            },
            # test 7. 999999 base asset, 1 pt, p = 0
            {"base_asset_reserves": 999999, "token_asset_reserves": 1, "spot_price": 0, "expected_result": 999999},
        ]

        for test_case in test_cases:
            liquidity = pricing_model.calc_total_liquidity_from_reserves_and_price(
                test_case["base_asset_reserves"], test_case["token_asset_reserves"], test_case["spot_price"]
            )
            assert (
                liquidity == test_case["expected_result"]
            ), f"Calculated liquidity doesn't match the expected amount for these inputs: {test_case}"

    def run_calc_liquidity_test(self, pricing_model):
        """Unit tests for the calc_liquidity function"""

        test_cases = [
            # test 1: 5M target_liquidity; 1k market price; 5% APR;
            #   6mo remaining; 22.186877016851916 time_stretch (targets 5% APR);
            #   1 init share price; 1 share price
            {
                "target_liquidity_usd": 5000000,  # Targeting 5M USD liquidity
                "market_price": 1000,  # Market price of base asset
                "apr": 0.05,  # fixed rate APR you'd get from purchasing bonds; r = 0.05
                "days_remaining": 182.5,  # 6 months remaining; t = 0.50
                "time_stretch": 22.186877016851916,
                "init_share_price": 1,  # original share price pool started; u = 1
                "share_price": 1,  # share price of the LP in the yield source; c = 1
                "expected_base_asset_reserves": 2536.3203786253266,  #
                "expected_token_asset_reserves": 2525.2716119090405,  #
                "expected_total_liquidity": 5000,  # ~50:50 reserves ratio
            },
            # test 2: 5M target_liquidity; 1k market price; 2% APR;
            #   6mo remaining; 22.186877016851916 time_stretch (targets 5% APR);
            #   1 init share price; 1 share price
            {
                "target_liquidity_usd": 5000000,  # Targeting 5M USD liquidity
                "market_price": 1000,  # Market price of base asset
                "apr": 0.02,  # fixed rate APR you'd get from purchasing bonds; r = 0.02
                "days_remaining": 182.5,  # 6 months remaining; t = 0.50
                "time_stretch": 22.186877016851916,
                "init_share_price": 1,  # original share price pool started; u = 1
                "share_price": 1,  # share price of the LP in the yield source; c = 1
                "expected_base_asset_reserves": 3922.192745298014,  #
                "expected_token_asset_reserves": 1088.5853272490062,  #
                "expected_total_liquidity": 5000,  # base > token reserves
            },
            # test 3: 5M target_liquidity; 1k market price; 8% APR;
            #   6mo remaining; 22.186877016851916 time_stretch (targets 5% APR);
            #   1 init share price; 1 share price
            {
                "target_liquidity_usd": 5000000,  # Targeting 5M USD liquidity
                "market_price": 1000,  # Market price of base asset
                "apr": 0.08,  # fixed rate APR you'd get from purchasing bonds; r = 0.08
                "days_remaining": 182.5,  # 6 months remaining; t = 0.50
                "time_stretch": 22.186877016851916,
                "init_share_price": 1,  # original share price pool started; u = 1
                "share_price": 1,  # share price of the LP in the yield source; c = 1
                "expected_base_asset_reserves": 1534.0469740383746,  #
                "expected_token_asset_reserves": 3604.591147000091,  #
                "expected_total_liquidity": 5000,  # token > base reserves
            },
            # test 4: 10M target_liquidity; 500 market price; 3% APR;
            #   3mo remaining; 36.97812836141986 time_stretch (targets 3% APR);
            #   1.5 init share price; 2 share price
            {
                "target_liquidity_usd": 10000000,  # Targeting 10M USD liquidity
                "market_price": 500,  # Market price of base asset
                "apr": 0.03,  # fixed rate APR you'd get from purchasing bonds; r = 0.03
                "days_remaining": 91.25,  # 3 months remaining; t = 0.25
                "time_stretch": 36.97812836141986,
                "init_share_price": 1.5,  # original share price when pool started
                "share_price": 2,  # share price of the LP in the yield source
                "expected_base_asset_reserves": 12287.029415142337,  #
                "expected_token_asset_reserves": 7770.817864244096,  #
                "expected_total_liquidity": 20000,  # base > token reserves?
            },
            # test 5: 10M target_liquidity; 500 market price; 1% APR;
            #   3mo remaining; 36.97812836141986 time_stretch (targets 3% APR);
            #   1.5 init share price; 2 share price
            {
                "target_liquidity_usd": 10000000,  # Targeting 10M USD liquidity
                "market_price": 500,  # Market price of base asset
                "apr": 0.01,  # fixed rate APR you'd get from purchasing bonds; r = 0.01
                "days_remaining": 91.25,  # 3 months remaining; t = 0.25
                "time_stretch": 36.97812836141986,
                "init_share_price": 1.5,  # original share price when pool started
                "share_price": 2,  # share price of the LP in the yield source
                "expected_base_asset_reserves": 19186.027487682495,  #
                "expected_token_asset_reserves": 816.0074435982989,  #
                "expected_total_liquidity": 20000,  # base > token reserves?
            },
            # test 6: 10M target_liquidity; 500 market price; 6% APR;
            #   3mo remaining; 36.97812836141986 time_stretch (targets 3% APR);
            #   1.5 init share price; 2 share price
            {
                "target_liquidity_usd": 10000000,  # Targeting 10M USD liquidity
                "market_price": 500,  # Market price of base asset
                "apr": 0.06,  # fixed rate APR you'd get from purchasing bonds; r = 0.06
                "days_remaining": 91.25,  # 3 months remaining; t = 0.25
                "time_stretch": 36.97812836141986,
                "init_share_price": 1.5,  # original share price when pool started
                "share_price": 2,  # share price of the LP in the yield source
                "expected_base_asset_reserves": 5195.968749573127,  #
                "expected_token_asset_reserves": 15026.091719183272,  #
                "expected_total_liquidity": 20000,  # base > token reserves?
            },
            # test 7: ERROR CASE: 0 TARGET LIQUIDITY -> ZeroDivisionError
            #   10M target_liquidity; 500 market price; 6% APR;
            #   3mo remaining; 36.97812836141986 time_stretch (targets 3% APR);
            #   1.5 init share price; 2 share price
            {
                "target_liquidity_usd": 0,  # ERROR CASE; Targeting 0 USD liquidity
                "market_price": 500,  # Market price of base asset
                "apr": 0.06,  # fixed rate APR you'd get from purchasing bonds; r = 0.06
                "days_remaining": 91.25,  # 3 months remaining; t = 0.25
                "time_stretch": 36.97812836141986,
                "init_share_price": 1.5,  # original share price when pool started
                "share_price": 2,  # share price of the LP in the yield source
                "is_error_case": True,  # this test is supposed to fail
                "expected_result": ZeroDivisionError,
                "expected_base_asset_reserves": ZeroDivisionError,  #
                "expected_token_asset_reserves": ZeroDivisionError,  #
                "expected_total_liquidity": ZeroDivisionError,  #
            },
            # test 8: ERROR CASE: 0 MARKET PRICE -> ZeroDivisionError
            #   10M target_liquidity; 500 market price; 6% APR;
            #   3mo remaining; 36.97812836141986 time_stretch (targets 3% APR);
            #   1.5 init share price; 2 share price
            {
                "target_liquidity_usd": 10000000,  # Targeting 10M USD liquidity
                "market_price": 0,  # ERROR CASE; Market price of base asset
                "apr": 0.06,  # fixed rate APR you'd get from purchasing bonds; r = 0.06
                "days_remaining": 91.25,  # 3 months remaining; t = 0.25
                "time_stretch": 36.97812836141986,
                "init_share_price": 1.5,  # original share price when pool started
                "share_price": 2,  # share price of the LP in the yield source
                "is_error_case": True,  # this test is supposed to fail
                "expected_result": ZeroDivisionError,
                "expected_base_asset_reserves": ZeroDivisionError,  #
                "expected_token_asset_reserves": ZeroDivisionError,  #
                "expected_total_liquidity": ZeroDivisionError,  #
            },
            # test 9: STRANGE CASE: 0 APR -> NEGATIVE BASE LIQUIDITY?
            #   10M target_liquidity; 500 market price; 6% APR;
            #   3mo remaining; 36.97812836141986 time_stretch (targets 3% APR);
            #   1.5 init share price; 2 share price
            {
                "target_liquidity_usd": 1000000,  # Targeting 5M USD liquidity
                "market_price": 500,  # Market price of base asset
                "apr": 0.00,  # fixed rate APR you'd get from purchasing bonds; r = 0.06
                "days_remaining": 91.25,  # 3 months remaining; t = 0.25
                "time_stretch": 36.97812836141986,
                "init_share_price": 1.5,  # original share price when pool started
                "share_price": 2,  # share price of the LP in the yield source
                "is_error_case": False,  #
                "expected_base_asset_reserves": 2285.714285714286,  #
                "expected_token_asset_reserves": -285.7142857142857,  # NEGATIVE?
                "expected_total_liquidity": 2000,  # base > token reserves?
            },
            # test 10: ERROR CASE: 0 MARKET PRICE -> ZeroDivisionError
            #   10M target_liquidity; 500 market price; 6% APR;
            #   3mo remaining; 36.97812836141986 time_stretch (targets 3% APR);
            #   1.5 init share price; 2 share price
            {
                "target_liquidity_usd": 10000000,  # Targeting 10M USD liquidity
                "market_price": 500,  # Market price of base asset
                "apr": 0.06,  # fixed rate APR you'd get from purchasing bonds; r = 0.06
                "days_remaining": 0,  # ERROR CASE; 0 days remaining; t = 0
                "time_stretch": 36.97812836141986,
                "init_share_price": 1.5,  # original share price when pool started
                "share_price": 2,  # share price of the LP in the yield source
                "is_error_case": True,  # this test is supposed to fail
                "expected_result": ZeroDivisionError,
                "expected_base_asset_reserves": ZeroDivisionError,  #
                "expected_token_asset_reserves": ZeroDivisionError,  #
                "expected_total_liquidity": ZeroDivisionError,  #
            },
            # test 10: ERROR CASE: 0 TIME STRETCH -> ZeroDivisionError
            #   10M target_liquidity; 500 market price; 6% APR;
            #   3mo remaining; 0 time_stretch (targets 3% APR);
            #   1.5 init share price; 2 share price
            {
                "target_liquidity_usd": 10000000,  # Targeting 10M USD liquidity
                "market_price": 500,  # Market price of base asset
                "apr": 0.06,  # fixed rate APR you'd get from purchasing bonds; r = 0.06
                "days_remaining": 91.25,  # 3 months remaining; t = 0.25
                "time_stretch": 0,  # ERROR CASE
                "init_share_price": 1.5,  # original share price when pool started
                "share_price": 2,  # share price of the LP in the yield source
                "is_error_case": True,  # this test is supposed to fail
                "expected_result": ZeroDivisionError,
                "expected_base_asset_reserves": ZeroDivisionError,  #
                "expected_token_asset_reserves": ZeroDivisionError,  #
                "expected_total_liquidity": ZeroDivisionError,  #
            },
            # test 11: CURRENT SHARE PRICE < INIT SHARE PRICE
            #   10M target_liquidity; 500 market price; 6% APR;
            #   3mo remaining; 36.97812836141986 time_stretch (targets 3% APR);
            #   1.5 init share price; 1 share price
            {
                "target_liquidity_usd": 10000000,  # Targeting 10M USD liquidity
                "market_price": 500,  # Market price of base asset
                "apr": 0.06,  # fixed rate APR you'd get from purchasing bonds; r = 0.06
                "days_remaining": 91.25,  # 3 months remaining; t = 0.25
                "time_stretch": 36.97812836141986,  # Targets 3% APR
                "init_share_price": 1.5,  # original share price when pool started
                "share_price": 1.0,  # ERROR CASE; share_price below init_share_price
                "is_error_case": False,  #
                "expected_result": 0,
                "expected_base_asset_reserves": 2781.2982274103742,  #
                "expected_token_asset_reserves": 17476.982299178464,  #
                "expected_total_liquidity": 20000,  #
            },
            # test 12: INIT SHARE PRICE = 0; CURRENT SHARE PRICE < INIT SHARE PRICE
            #   10M target_liquidity; 500 market price; 6% APR;
            #   3mo remaining; 36.97812836141986 time_stretch (targets 3% APR);
            #   0 init share price; 0.5 share price
            {
                "target_liquidity_usd": 10000000,  # Targeting 10M USD liquidity
                "market_price": 500,  # Market price of base asset
                "apr": 0.06,  # fixed rate APR you'd get from purchasing bonds; r = 0.06
                "days_remaining": 91.25,  # 3 months remaining; t = 0.25
                "time_stretch": 36.97812836141986,  # Targets 3% APR
                "init_share_price": 0,  # ERROR CASE; original share price when pool started
                "share_price": 0.5,  # share_price below init_share_price
                "is_error_case": False,  #
                "expected_result": 0,
                "expected_base_asset_reserves": 39417.47572815535,  #
                "expected_token_asset_reserves": -19708.737864077673,  # NEGATIVE?
                "expected_total_liquidity": 20000,  #
            },
            # test 13: ERROR CASE; BOTH INIT AND CURRENT SHARE PRICE = 0
            #   10M target_liquidity; 500 market price; 6% APR;
            #   3mo remaining; 36.97812836141986 time_stretch (targets 3% APR);
            #   0 init share price; 0 share price
            {
                "target_liquidity_usd": 10000000,  # Targeting 10M USD liquidity
                "market_price": 500,  # Market price of base asset
                "apr": 0.06,  # fixed rate APR you'd get from purchasing bonds; r = 0.06
                "days_remaining": 91.25,  # 3 months remaining; t = 0.25
                "time_stretch": 36.97812836141986,  # Targets 3% APR
                "init_share_price": 0,  # ERROR CASE; original share price when pool started
                "share_price": 0,  # share_price below init_share_price
                "is_error_case": True,  # this test is supposed to fail
                "expected_result": ZeroDivisionError,
                "expected_base_asset_reserves": ZeroDivisionError,  #
                "expected_token_asset_reserves": ZeroDivisionError,  #
                "expected_total_liquidity": ZeroDivisionError,  #
            },
        ]

        for test_case in test_cases:

            # Check if this test case is supposed to fail
            if "is_error_case" in test_case and test_case["is_error_case"]:

                # Check that test case throws the expected error
                with self.assertRaises(test_case["expected_result"]):
                    base_asset_reserves, token_asset_reserves, total_liquidity = pricing_model.calc_liquidity(
                        test_case["target_liquidity_usd"],
                        test_case["market_price"],
                        test_case["apr"],
                        test_case["days_remaining"],
                        test_case["time_stretch"],
                        test_case["init_share_price"],
                        test_case["share_price"],
                    )

            # If test was not supposed to fail, continue normal execution
            else:
                base_asset_reserves, token_asset_reserves, total_liquidity = pricing_model.calc_liquidity(
                    test_case["target_liquidity_usd"],
                    test_case["market_price"],
                    test_case["apr"],
                    test_case["days_remaining"],
                    test_case["time_stretch"],
                    test_case["init_share_price"],
                    test_case["share_price"],
                )

                np.testing.assert_almost_equal(
                    base_asset_reserves,
                    test_case["expected_base_asset_reserves"],
                    err_msg="unexpected base_asset_reserves",
                )
                np.testing.assert_almost_equal(
                    token_asset_reserves,
                    test_case["expected_token_asset_reserves"],
                    err_msg="unexpected token_asset_reserves",
                )
                np.testing.assert_almost_equal(
                    total_liquidity, test_case["expected_total_liquidity"], err_msg="unexpected total_liquidity"
                )


class TestLiquidityCalc(LiquidityTestDefinitions):
    """Unit tests for liquidity calculations"""

    def test_calc_total_liquidity_from_reserves_and_price(self):
        """Run test for each pricing model"""
        for pricing_model in [ElementPricingModel, HyperdrivePricingModel]:
            self.run_calc_total_liquidity_from_reserves_and_price_test(pricing_model)

    def test_calc_liquidity(self):
        """Run test for each pricing model"""
        for pricing_model in [ElementPricingModel, HyperdrivePricingModel]:
            self.run_calc_liquidity_test(pricing_model)

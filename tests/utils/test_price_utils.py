"""
Testing for price utilities found in src/elfpy/utils/price.py
"""

# pylint: disable=too-many-lines
# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-locals
# pylint: disable=attribute-defined-outside-init

import unittest
import numpy as np

from elfpy.utils import price as price_utils


class TestPriceUtils(unittest.TestCase):
    """Unit tests for price utilities"""

    def test_calc_total_liquidity_from_reserves_and_price(self):
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
                "expected_result": 975000
            },
            # test 2
            {
                "base_asset_reserves": 800000,
                "token_asset_reserves": 200000,
                "spot_price": 0.98,
                "expected_result": 996000
            },
            # test 3
            {
                "base_asset_reserves": 200000,
                "token_asset_reserves": 800000,
                "spot_price": 0.92,
                "expected_result": 936000
            },
            # test 4
            {
                "base_asset_reserves": 1000000,
                "token_asset_reserves": 0,
                "spot_price": 1.00,
                "expected_result": 1000000
            },
            # test 5
            {
                "base_asset_reserves": 0,
                "token_asset_reserves": 1000000,
                "spot_price": 0.90,
                "expected_result": 900000
            },
            # test 6. Price > 1.00. The AMM math wouldn't allow this though but the function doesn't check for it
            {
                "base_asset_reserves": 500000,
                "token_asset_reserves": 500000,
                "spot_price": 1.50,
                "expected_result": 1250000
            },
            # test 7. 999999 base asset, 1 pt, p = 0
            {
                "base_asset_reserves": 999999,
                "token_asset_reserves": 1,
                "spot_price": 0,
                "expected_result": 999999
            }
        ]

        for test_case in test_cases:
            liquidity = price_utils.calc_total_liquidity_from_reserves_and_price(
                test_case["base_asset_reserves"],
                test_case["token_asset_reserves"],
                test_case["spot_price"]
            )
            assert liquidity == test_case["expected_result"], \
                f"Calculated liquidity doesn't match the expected amount for these inputs: {test_case}"


    def test_calc_base_asset_reserves(self):
        """Unit tests for the calc_base_asset_reserves function"""

        test_cases = [
            # test 1: 5% APR; 500k bond reserves; 6mo remaining;
            #   22.186877016851916 t_stretch (targets 5% APR);
            #   1 init share price; 1 share price
            #
            {
                "apr": 0.05, # fixed rate APR you'd get from purchasing bonds; r = 0.05
                "token_asset_reserves": 500000, # PT reserves; y = 500000
                "days_remaining": 182.5, # 6 months remaining; t = 0.50
                "time_stretch": 22.186877016851916, # 22.186877016851916 time_stretch; T = 0.02253584403
                "init_share_price": 1, # original share price pool started; u = 1
                "share_price": 1, # share price of the LP in the yield source; c = 1
                # from the inputs, we have:
                # c = 1
                # y = 500000
                # u = 1
                # r = 0.05
                # t = 0.50
                # T = 0.02253584403
                # x = 2*c*y/(u*(r*t + 1)**(1/T) - c)
                #   = 2*1*500000/(1*(0.05*0.50 + 1)**(1/0.02253584403) - 1)
                #   = 502187.63927495584
                "expected_result": 502187.63927495584 # ~50:50 reserves ratio
            },
            # test 2: 2% APR; 200k bond reserves; 6mo remaining;
            #   22.186877016851916 t_stretch (targets 5% APR);
            #   1 init share price; 1 share price
            {
                "apr": 0.02, # fixed rate APR you'd get from purchasing bonds; r = 0.05
                "token_asset_reserves": 200000, # PT reserves; y = 200000
                "days_remaining": 182.5, # 6 months remaining; t = 0.50
                "time_stretch": 22.186877016851916, # 22.186877016851916 time_stretch; T = 0.02253584403
                "init_share_price": 1, # original share price pool started; u = 1
                "share_price": 1, # share price of the LP in the yield source; c = 1
                # from the inputs, we have:
                # c = 1
                # y = 200000
                # u = 1
                # r = 0.02
                # t = 0.50
                # T = 0.02253584403
                # x = 2*c*y/(u*(r*t + 1)**(1/T) - c)
                #   = 2*1*200000/(1*(0.02*0.50 + 1)**(1/0.02253584403) - 1)
                #   = 720603.6398101918
                "expected_result": 720603.6398101918 # base > token reserves
            },
            # test 3: 8% APR; 800k bond reserves; 6mo remaining;
            #   22.186877016851916 t_stretch (targets 5% APR);
            #   1 init share price; 1 share price
            {
                "apr": 0.08, # fixed rate APR you'd get from purchasing bonds; r = 0.05
                "token_asset_reserves": 800000, # PT reserves; y = 800000
                "days_remaining": 182.5, # 6 months remaining; t = 0.50
                "time_stretch": 22.186877016851916, # 22.186877016851916 time_stretch; T = 0.02253584403
                "init_share_price": 1, # original share price pool started; u = 1
                "share_price": 1, # share price of the LP in the yield source; c = 1
                # from the inputs, we have:
                # c = 1
                # y = 800000
                # u = 1
                # r = 0.08
                # t = 0.50
                # T = 0.02253584403
                # x = 2*c*y/(u*(r*t + 1)**(1/T) - c)
                #   = 2*1*800000/(1*(0.08*0.50 + 1)**(1/0.02253584403) - 1)
                #   = 340465.1260523857
                "expected_result": 340465.1260523857 # token > base reserves
            },
            # test 4: 3% APR; 500k bond reserves; 3mo remaining;
            #   36.97812836141986 t_stretch (targets 3% APR);
            #   1.5 init share price; 2 share price
            {
                "apr": 0.03, # fixed rate APR you'd get from purchasing bonds; r = 0.03
                "token_asset_reserves": 500000, # PT reserves; y = 500000
                "days_remaining": 91.25, # 3 months remaining; t = 0.25
                "time_stretch": 36.97812836141986, # 36.97812836141986 time_stretch; T = 0.006760753209
                "init_share_price": 1.5, # original share price pool started; u = 1.5
                "share_price": 2, # share price of the LP in the yield source; c = 2
                # from the inputs, we have:
                # c = 2
                # y = 500000
                # u = 1.5
                # r = 0.03
                # t = 0.25
                # T = 0.006760753209
                # x = 2*c*y/(u*(r*t + 1)**(1/T) - c)
                #   = 2*2*500000/(1.5*(0.03*0.25 + 1)**(1/0.006760753209) - 1)
                #   = 790587.9168574204
                "expected_result": 790587.9168574204 # token > base reserves (too much? share_price sus)
            },
            # test 5: 1% APR; 200k bond reserves; 3mo remaining;
            #   36.97812836141986 t_stretch (targets 3% APR);
            #   1.5 init share price; 2 share price
            {
                "apr": 0.01, # fixed rate APR you'd get from purchasing bonds; r = 0.01
                "token_asset_reserves": 200000, # PT reserves; y = 200000
                "days_remaining": 91.25, # 3 months remaining; t = 0.25
                "time_stretch": 36.97812836141986, # 36.97812836141986 time_stretch; T = 0.006760753209
                "init_share_price": 1.5, # original share price pool started; u = 1.5
                "share_price": 2, # share price of the LP in the yield source; c = 2
                # from the inputs, we have:
                # c = 2
                # y = 500000
                # u = 1.5
                # r = 0.01
                # t = 0.25
                # T = 0.006760753209
                # x = 2*c*y/(u*(r*t + 1)**(1/T) - c)
                #   = 2*2*200000/(1.5*(0.01*0.25 + 1)**(1/0.006760753209) - 1)
                #   = 4702414.821874424
                "expected_result": 4702414.821874424 # base > token reserves (too much? share_price sus)
            },
            # test 6: 6% APR; 800k bond reserves; 3mo remaining;
            #   36.97812836141986 t_stretch (targets 3% APR);
            #   1.5 init share price; 2 share price
            {
                "apr": 0.06, # fixed rate APR you'd get from purchasing bonds; r = 0.06
                "token_asset_reserves": 800000, # PT reserves; y = 800000
                "days_remaining": 91.25, # 3 months remaining; t = 0.25
                "time_stretch": 36.97812836141986, # 36.97812836141986 time_stretch; T = 0.006760753209
                "init_share_price": 1.5, # original share price pool started; u = 1.5
                "share_price": 2, # share price of the LP in the yield source; c = 2
                # from the inputs, we have:
                # c = 2
                # y = 800000
                # u = 1.5
                # r = 0.06
                # t = 0.25
                # T = 0.006760753209
                # x = 2*c*y/(u*(r*t + 1)**(1/T) - c)
                #   = 2*2*800000/(1.5*(0.06*0.25 + 1)**(1/0.006760753209) - 1)
                #   = 276637.1374102353
                "expected_result": 276637.1374102353 # token > base reserves (is it enough? share_price sus)
            },
            # test 7: DIVISION BY ZERO ERROR
            #   5% APR; 500k bond reserves; 6mo remaining;
            #   22.186877016851916 t_stretch (targets 5% APR);
            #   1 init share price; 1.25 share price
            {
                "apr": 0.05, # fixed rate APR you'd get from purchasing bonds; r = 0.05
                "token_asset_reserves": 500000, # PT reserves; y = 500000
                "days_remaining": 182.5, # 6 months remaining; t = 0.50
                "time_stretch": 0, # 0 time_stretch; T = infinite (division by zero)
                "init_share_price": 1, # original share price pool started; u = 1
                "share_price": 1.25, # share price of the LP in the yield source; c = 1.25
                # from the inputs, we have:
                # c = 1.25
                # y = 500000
                # u = 1
                # r = 0.05
                # t = 0.50
                # T = infinite
                # x = ZeroDivisionError
                "is_error_case": True, # this test is supposed to fail
                "expected_result": ZeroDivisionError # negative result? Error!
            },
            # test 8: STRANGE RESULTS CASE
            #   0.01% APR; 1000 bond reserves; 3mo remaining;
            #   22.186877016851916 t_stretch (targets 5% APR);
            #   1 init share price; 1.03 share price
            #
            #   This case is low fixed APR on a pool whose yield source has performed very well
            #   (share price increased a lot) which could happen, for example, if the source of
            #   the high yield dries up during the term. The result is negative base_asset_reserves
            #   which shouldn't happen
            {
                "apr": 0.0001, # fixed rate APR you'd get from purchasing bonds; r = 0.01
                "token_asset_reserves": 1000, # PT reserves; y = 1000
                "days_remaining": 91.25, # 3 months remaining; t = 0.25
                "time_stretch": 22.186877016851916, # 22.186877016851916 time_stretch; T = 0.01126792202
                "init_share_price": 1, # original share price pool started; u = 1
                "share_price": 1.01, # share price of the LP in the yield source; c = 1.25
                # from the inputs, we have:
                # c = 1.03
                # y = 1000
                # u = 1
                # r = 0.0001
                # t = 0.25
                # T = 0.01126792202
                # x = 2*c*y/(u*(r*t + 1)**(1/T) - c)
                #   = 2*1.01*1000/(1*(0.0001*0.25 + 1)**(1/0.01126792202) - 1.01)
                #   = -74157.0654965635 (negative)
                "expected_result": -259677.58637922065 # negative result? Strange, check math!
            }
        ]

        for test_case in test_cases:

            # Check if this test case is supposed to fail
            if 'is_error_case' in test_case:

                # Check that test case throws the expected error
                with self.assertRaises(test_case['expected_result']):
                    base_asset_reserves = price_utils.calc_base_asset_reserves(
                        test_case["apr"],
                        test_case["token_asset_reserves"],
                        test_case["days_remaining"],
                        test_case["time_stretch"],
                        test_case["init_share_price"],
                        test_case["share_price"]
                    )

            # If test was not supposed to fail, continue normal execution
            else:
                base_asset_reserves = price_utils.calc_base_asset_reserves(
                    test_case["apr"],
                    test_case["token_asset_reserves"],
                    test_case["days_remaining"],
                    test_case["time_stretch"],
                    test_case["init_share_price"],
                    test_case["share_price"]
                )
                # assert base_asset_reserves >= 0, \
                #     f'the provided parameters resulted in negative base_asset_reserves {base_asset_reserves}'

                np.testing.assert_almost_equal(
                    base_asset_reserves,
                    test_case["expected_result"],
                    err_msg="unexpected base_asset_reserves",
                )


    def test_calc_liquidity(self):
        """Unit tests for the calc_liquidity function"""

        test_cases = [
            # test 1: 5M target_liquidity; 1k market price; 5% APR;
            #   6mo remaining; 22.186877016851916 time_stretch (targets 5% APR);
            #   1 init share price; 1 share price
            {
                "target_liquidity_usd": 5000000, # Targeting 5M USD liquidity
                "market_price": 1000, # Market price of base asset
                "apr": 0.05, # fixed rate APR you'd get from purchasing bonds; r = 0.05
                "days_remaining": 182.5, # 6 months remaining; t = 0.50
                "time_stretch": 22.186877016851916,
                "init_share_price": 1, # original share price pool started; u = 1
                "share_price": 1, # share price of the LP in the yield source; c = 1
                "expected_base_asset_reserves": 2536.3203786253266, #
                "expected_token_asset_reserves": 2525.2716119090405, #
                "expected_total_liquidity": 5000.0 # ~50:50 reserves ratio
            },
            # test 2: 5M target_liquidity; 1k market price; 2% APR;
            #   6mo remaining; 22.186877016851916 time_stretch (targets 5% APR);
            #   1 init share price; 1 share price
            {
                "target_liquidity_usd": 5000000, # Targeting 5M USD liquidity
                "market_price": 1000, # Market price of base asset
                "apr": 0.02, # fixed rate APR you'd get from purchasing bonds; r = 0.02
                "days_remaining": 182.5, # 6 months remaining; t = 0.50
                "time_stretch": 22.186877016851916,
                "init_share_price": 1, # original share price pool started; u = 1
                "share_price": 1, # share price of the LP in the yield source; c = 1
                "expected_base_asset_reserves": 3922.192745298014, #
                "expected_token_asset_reserves": 1088.5853272490062, #
                "expected_total_liquidity": 5000.0 # base > token reserves
            },
            # test 3: 5M target_liquidity; 1k market price; 8% APR;
            #   6mo remaining; 22.186877016851916 time_stretch (targets 5% APR);
            #   1 init share price; 1 share price
            {
                "target_liquidity_usd": 5000000, # Targeting 5M USD liquidity
                "market_price": 1000, # Market price of base asset
                "apr": 0.08, # fixed rate APR you'd get from purchasing bonds; r = 0.08
                "days_remaining": 182.5, # 6 months remaining; t = 0.50
                "time_stretch": 22.186877016851916,
                "init_share_price": 1, # original share price pool started; u = 1
                "share_price": 1, # share price of the LP in the yield source; c = 1
                "expected_base_asset_reserves": 1534.0469740383746, #
                "expected_token_asset_reserves": 3604.591147000091, #
                "expected_total_liquidity": 5000.0 # token > base reserves
            },
            # test 4: 10M target_liquidity; 500 market price; 3% APR;
            #   3mo remaining; 36.97812836141986 time_stretch (targets 3% APR);
            #   1.5 init share price; 2 share price
            {
                "target_liquidity_usd": 10000000, # Targeting 5M USD liquidity
                "market_price": 500, # Market price of base asset
                "apr": 0.03, # fixed rate APR you'd get from purchasing bonds; r = 0.03
                "days_remaining": 91.25, # 3 months remaining; t = 0.25
                "time_stretch": 36.97812836141986,
                "init_share_price": 1.5, # original share price when pool started
                "share_price": 2, # share price of the LP in the yield source
                "expected_base_asset_reserves": 12287.029415142337, #
                "expected_token_asset_reserves": 7770.817864244096, #
                "expected_total_liquidity": 20000.0 # base > token reserves?
            },
            # test 5: 10M target_liquidity; 500 market price; 1% APR;
            #   3mo remaining; 36.97812836141986 time_stretch (targets 3% APR);
            #   1.5 init share price; 2 share price
            {
                "target_liquidity_usd": 10000000, # Targeting 5M USD liquidity
                "market_price": 500, # Market price of base asset
                "apr": 0.01, # fixed rate APR you'd get from purchasing bonds; r = 0.01
                "days_remaining": 91.25, # 3 months remaining; t = 0.25
                "time_stretch": 36.97812836141986,
                "init_share_price": 1.5, # original share price when pool started
                "share_price": 2, # share price of the LP in the yield source
                "expected_base_asset_reserves": 19186.027487682495, #
                "expected_token_asset_reserves": 816.0074435982989, #
                "expected_total_liquidity": 20000.0 # base > token reserves?
            },
            # test 6: 10M target_liquidity; 500 market price; 6% APR;
            #   3mo remaining; 36.97812836141986 time_stretch (targets 3% APR);
            #   1.5 init share price; 2 share price
            {
                "target_liquidity_usd": 10000000, # Targeting 5M USD liquidity
                "market_price": 500, # Market price of base asset
                "apr": 0.06, # fixed rate APR you'd get from purchasing bonds; r = 0.06
                "days_remaining": 91.25, # 3 months remaining; t = 0.25
                "time_stretch": 36.97812836141986,
                "init_share_price": 1.5, # original share price when pool started
                "share_price": 2, # share price of the LP in the yield source
                "expected_base_asset_reserves": 5195.968749573127, #
                "expected_token_asset_reserves": 15026.091719183272, #
                "expected_total_liquidity": 20000.0 # base > token reserves?
            }
        ]

        for test_case in test_cases:
            base_asset_reserves, token_asset_reserves, total_liquidity = price_utils.calc_liquidity(
                test_case["target_liquidity_usd"],
                test_case["market_price"],
                test_case["apr"],
                test_case["days_remaining"],
                test_case["time_stretch"],
                test_case["init_share_price"],
                test_case["share_price"]
            )

            np.testing.assert_almost_equal(
                base_asset_reserves,
                test_case["expected_base_asset_reserves"],
                err_msg="unexpected base_asset_reserves"
            )
            np.testing.assert_almost_equal(
                token_asset_reserves,
                test_case["expected_token_asset_reserves"],
                err_msg="unexpected token_asset_reserves"
            )
            np.testing.assert_almost_equal(
                total_liquidity,
                test_case["expected_total_liquidity"],
                err_msg="unexpected total_liquidity"
            )


    # ### Spot Price and APR ###


    def test_calc_apr_from_spot_price(self):
        """Unit tests for the calc_apr_from_spot_price function"""

        test_cases = [
            # test 1: 0.95 price; 6mo remaining;
            {
                "price": 0.95,
                "normalized_days_remaining": 0.5, # 6 months = 0.5 years
                # APR = (1 - 0.95) / 0.95 / 0.5
                #     = 0.1052631579
                "expected_result": 0.1052631579 # just over 10% APR
            },
            # test 2: 0.99 price; 6mo remaining;
            {
                "price": 0.99,
                "normalized_days_remaining": 0.5, # 6 months = 0.5 years
                # APR = (1 - 0.99) / 0.99 / 0.5
                #     = 0.0202020202
                "expected_result": 0.0202020202 # just over 2% APR
            },
            # test 3: 1.00 price; 6mo remaining;
            {
                "price": 1.00, # 0% APR
                "normalized_days_remaining": 0.5, # 6 months = 0.5 years
                # APR = (1 - 1) / 1 / 0.5
                #     = 0
                "expected_result": 0 # 0% APR
            },
            # test 4: 0.95 price; 3mo remaining;
            {
                "price": 0.95,
                "normalized_days_remaining": 0.25, # 3 months = 0.25 years
                # APR = (1 - 0.95) / 0.95 / 0.25
                #     = 0.2105263158
                "expected_result": 0.2105263158 # just over 21% APR
            },
            # test 5: 0.95 price; 12mo remaining;
            {
                "price": 0.95,
                "normalized_days_remaining": 1, # 12 months = 1 year
                # APR = (1 - 0.95) / 0.95 / 1
                #     = 0.05263157895
                "expected_result": 0.05263157895 # just over 5% APR
            },
            # test 6: 0.10 price; 3mo remaining;
            {
                "price": 0.10, # 0% APR
                "normalized_days_remaining": 0.25, # 3 months = 0.25 years
                # APR = (1 - 0.10) / 0.10 / 0.25
                #     = 0
                "expected_result": 36 # 3600% APR
            },
            # test 7: ERROR CASE
            #   -0.50 (negative) price; 3mo remaining;
            #   the function asserts that price > 0, so this case should raise an AssertionError
            {
                "price": -0.50, # 0% APR
                "normalized_days_remaining": 0.25, # 3 months = 0.25 years
                # APR = (1 - 0.10) / 0.10 / 0.25
                #     = 0
                "is_error_case": True, # failure case
                "expected_result": AssertionError
            },
            # test 8: ERROR CASE
            #   0.95 price; -3mo remaining (negative);
            #   the function asserts that normalized_days_remaining > 0, so this case \
            #   should raise an AssertionError
            {
                "price": 0.95, # 0% APR
                "normalized_days_remaining": -0.25, # -3 months = -0.25 years
                # APR = (1 - 0.10) / 0.10 / 0.25
                #     = 0
                "is_error_case": True, # failure case
                "expected_result": AssertionError
            },
            # test 9: STRANGE RESULT CASE
            #   1.50 price (>1.00); 3mo remaining;
            #   the AMM math shouldn't let price be greater than 1
            {
                "price": 1.50, # 0% APR
                "normalized_days_remaining": 0.25, # 3 months = 0.25 years
                # APR = (1 - 1.50) / 1.50 / 0.25
                #     = -1.333333333
                "expected_result": -1.3333333333333333, # strange result
            }
        ]

        for test_case in test_cases:

            # Check if this test case is supposed to fail
            if 'is_error_case' in test_case:

                # Check that test case throws the expected error
                with self.assertRaises(test_case['expected_result']):
                    apr = price_utils.calc_apr_from_spot_price(
                    test_case["price"],
                    test_case["normalized_days_remaining"]
                )

            # If test was not supposed to fail, continue normal execution
            else:
                apr = price_utils.calc_apr_from_spot_price(
                    test_case["price"],
                    test_case["normalized_days_remaining"]
                )

                np.testing.assert_almost_equal(
                    apr,
                    test_case["expected_result"],
                    err_msg="unexpected apr"
                )


    def test_calc_spot_price_from_apr(self):
        """Unit tests for the calc_spot_price_from_apr function"""

        test_cases = [
            # test 1: 10% apr; 6mo remaining;
            {
                "apr_decimal": 0.10, # 10% apr
                "normalized_days_remaining": 0.5, # 6 months = 0.5 years
                # price = 1 / (1 + 0.10 * 0.5)
                #     = 0.1052631579
                "expected_result": 0.9523809524 # just over 0.95
            },
            # test 2: 2% apr; 6mo remaining;
            {
                "apr_decimal": 0.02, # 2% apr
                "normalized_days_remaining": 0.5, # 6 months = 0.5 years
                # price = 1 / (1 + 0.02 * 0.5)
                #     = 0.9900990099
                "expected_result": 0.9900990099 # just over 0.99
            },
            # test 3: 0% apr; 6mo remaining;
            {
                "apr_decimal": 0, # 0% apr
                "normalized_days_remaining": 0.5, # 6 months = 0.5 years
                # price = 1 / (1 + 0 * 0.5)
                #     = 1
                "expected_result": 1
            },
            # test 4: 21% apr; 3mo remaining;
            {
                "apr_decimal": 0.21, # 21% apr
                "normalized_days_remaining": 0.25, # 3 months = 0.25 years
                # price = 1 / (1 + 0.21 * 0.25)
                #     = 0.2105263158
                "expected_result": 0.9501187648 # just over 0.95
            },
            # test 5: 5% apr; 12mo remaining;
            {
                "apr_decimal": 0.05, # 5% apr
                "normalized_days_remaining": 1, # 12 months = 1 year
                # price = 1 / (1 + 0.05 * 1)
                #     = 0.05263157895
                "expected_result": 0.9523809524 # just over 0.95
            },
            # test 6: 0.10 price; 3mo remaining;
            {
                "apr_decimal": 36, # 3600% apr
                "normalized_days_remaining": 0.25, # 3 months = 0.25 years
                # price = 1 / (1 + 0 * 0.5)
                #     = 0
                "expected_result": 0.10
            }
        ]

        for test_case in test_cases:
            spot_price = price_utils.calc_spot_price_from_apr(
                test_case["apr_decimal"],
                test_case["normalized_days_remaining"]
            )

            np.testing.assert_almost_equal(
                spot_price,
                test_case["expected_result"],
                err_msg="unexpected apr"
            )


    # ### YieldSpace ###


    def test_calc_k_const(self):
        """Unit tests for calc_k_const function"""

        test_cases = [
            # test 1: 500k share_reserves; 500k bond_reserves
            #   1 share price; 1 init_share_price; 3mo elapsed
            {
                "share_reserves": 500000, # x = 500000
                "bond_reserves": 500000, # y = 500000
                "share_price": 1, # c = 1
                "init_share_price": 1, # u = 1
                "time_elapsed": 0.25, # t = 0.25
                # k = c/u * (u*y)**t + (2y+c*x)**t
                #     = 1/1 * (1*500000)**0.25 + (2*500000+1*500000)**0.25
                #     = 61.587834600530776
                "expected_result": 61.587834600530776
            },
            # test 2: 500k share_reserves; 500k bond_reserves
            #   1 share price; 1 init_share_price; 12mo elapsed
            {
                "share_reserves": 500000, # x = 500000
                "bond_reserves": 500000, # y = 500000
                "share_price": 1, # c = 1
                "init_share_price": 1, # u = 1
                "time_elapsed": 1, # t = 1
                # k = c/u * (u*y)**t + (2y+c*x)**t
                #     = 1/1 * (1*500000)**1 + (2*500000+1*500000)**1
                #     = 2000000
                "expected_result": 2000000
            },
            # test 3: 5M share_reserves; 5M bond_reserves
            #   2 share price; 1.5 init_share_price; 6mo elapsed
            {
                "share_reserves": 5000000, # x = 5000000
                "bond_reserves": 5000000, # y = 5000000
                "share_price": 2, # c = 2
                "init_share_price": 1.5, # u = 1.5
                "time_elapsed": 0.50, # t = 0.50
                # k = c/u * (u*y)**t + (2y+c*x)**t
                #     = 1/1 * (1*5000000)**0.50 + (2*5000000+1*5000000)**0.50
                #     = 61.587834600530776
                "expected_result": 8123.619671700687
            },
            # test 1: 5M share_reserves; 5M bond_reserves
            #   2 share price; 1.5 init_share_price; 3mo elapsed
            {
                "share_reserves": 5000000, # x = 5000000
                "bond_reserves": 5000000, # y = 5000000
                "share_price": 2, # c = 2
                "init_share_price": 1.5, # u = 1.5
                "time_elapsed": 0.25, # t = 0.25
                # k = c/u * (u*y)**t + (2y+c*x)**t
                #     = 2/1.5 * (1*5000000)**0.25 + (2*5000000+1*5000000)**0.25
                #     = 61.587834600530776
                "expected_result": 136.64970645711588
            },
        ]

        for test_case in test_cases:
            k = price_utils.calc_k_const(
                test_case["share_reserves"],
                test_case["bond_reserves"],
                test_case["share_price"],
                test_case["init_share_price"],
                test_case["time_elapsed"],
            )

            np.testing.assert_almost_equal(
                k,
                test_case["expected_result"],
                err_msg="unexpected k"
            )

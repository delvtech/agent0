"""
Testing for the parsing the Market, AMM and Simulator configs from a TOML file
"""

# pylint: disable=too-many-lines
# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-locals
# pylint: disable=attribute-defined-outside-init

from typing import Union

from dataclasses import dataclass, fields, MISSING
import unittest
import numpy as np

from elfpy.utils import price as price_utils, time as time_utils
from elfpy.pricing_models import ElementPricingModel, HyperdrivePricingModel



class TestPriceUtils(unittest.TestCase):
    """Unit tests for the parse_simulation_config function"""

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
            # Liquidity = 0 + 1000000 * 0.90 = 900000

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
            }
        ]

        for test_case in test_cases:
            liquidity = price_utils.calc_total_liquidity_from_reserves_and_price(
                test_case["base_asset_reserves"],
                test_case["token_asset_reserves"],
                test_case["spot_price"]
            )
            assert liquidity == test_case["expected_result"], f"Calculated liquidity doesn't match the expected amount for these inputs: {test_case}"

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
            }
        ]

        for test_case in test_cases:
            base_asset_reserves = price_utils.calc_base_asset_reserves(
                test_case["apr"],
                test_case["token_asset_reserves"],
                test_case["days_remaining"],
                test_case["time_stretch"],
                test_case["init_share_price"],
                test_case["share_price"]
            )

            np.testing.assert_almost_equal(
                base_asset_reserves,
                test_case["expected_result"],
                err_msg="unexpected base_asset_reserves",
            )


    def test_calc_liquidity(self):

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
                "apr": 0.02, # fixed rate APR you'd get from purchasing bonds; r = 0.05
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
                "apr": 0.08, # fixed rate APR you'd get from purchasing bonds; r = 0.05
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
                "apr": 0.01, # fixed rate APR you'd get from purchasing bonds; r = 0.03
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
                "apr": 0.06, # fixed rate APR you'd get from purchasing bonds; r = 0.03
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


    # def calc_apr_from_spot_price(price, normalized_days_remaining):
    #     """Returns the APR (decimal) given the current (positive) base asset price and the remaining pool duration"""
    #     assert price > 0, (
    #         "pricing_models.calc_apr_from_spot_price: ERROR: calc_apr_from_spot_price:"
    #         f"Price argument should be greater or equal to zero, not {price}"
    #     )
    #     assert (
    #         normalized_days_remaining > 0
    #     ), f"normalized_days_remaining argument should be greater than zero, not {normalized_days_remaining}"
    #     return (1 - price) / price / normalized_days_remaining  # price = 1 / (1 + r * t)


    # def calc_spot_price_from_apr(apr_decimal, normalized_days_remaining):
    #     """Returns the current spot price based on the current APR (decimal) and the remaining pool duration"""
    #     return 1 / (1 + apr_decimal * normalized_days_remaining)  # price = 1 / (1 + r * t)


    # ### YieldSpace ###


    # def calc_k_const(share_reserves, bond_reserves, share_price, init_share_price, time_elapsed):
    #     """Returns the 'k' constant variable for trade mathematics"""
    #     scale = share_price / init_share_price
    #     total_reserves = bond_reserves + share_price * share_reserves
    #     return scale * (init_share_price * share_reserves) ** (time_elapsed) + (bond_reserves + total_reserves) ** (
    #         time_elapsed
    #     )

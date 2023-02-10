# base.calc_spot_price_from_reserves
# utils.price.calc_spot_price_from_apr

import unittest

import numpy as np

from elfpy.pricing_models.base import PricingModel
import elfpy.utils.price as price_utils
from elfpy.types import MarketState, StretchedTime


class TestSpotPriceCalculations(unittest.TestCase):
    """Test spot price calculation in base pricing model & price utils"""

    def test_calc_spot_price_from_reserves(self):
        """Test base pricing model calculation

        .. todo:: write failure tests
        """
        test_cases = [
            # test 1: 500k share_reserves; 500k bond_reserves
            #   1 share price; 1 init_share_price
            #   90d elapsed; time_stretch=1; norm=365
            {
                "market_state": MarketState(
                    share_reserves=500000,  # z
                    bond_reserves=500000,  # y
                    share_price=1,  # c
                    init_share_price=1,  # u
                ),
                "time_remaining": StretchedTime(
                    days=90,
                    time_stretch=1,
                    normalizing_constant=365,
                ),
                # tau = days / normalizing_constant / time_stretch
                # s = y + c*z
                # p = ((2y + cz)/(u*z))^(-tau)
                # p = ((2 * 500000 + 1 * 500000) / (1 * 500000))**(-(90 / 1 / 365))
                "expected_result": 0.7626998539403097,
            },
            # test 2: 250k share_reserves; 500k bond_reserves
            #   2 share price; 1.5 init_share_price
            #   90d elapsed; time_stretch=1; norm=365
            {
                "market_state": MarketState(
                    share_reserves=250000,  # z
                    bond_reserves=500000,  # y
                    share_price=2,  # c
                    init_share_price=1.5,  # u
                ),
                "time_remaining": StretchedTime(
                    days=90,
                    time_stretch=1,
                    normalizing_constant=365,
                ),
                # tau = days / normalizing_constant / time_stretch
                # s = y + c*z
                # p = ((2y + cz)/(u*z))^(-tau)
                # p = ((2 * 500000 + 2 * 250000) / (1.5 * 250000))**(-(90 / 1 / 365))
                "expected_result": 0.7104718111828882,
            },
            # test 3: 250k share_reserves; 300k bond_reserves
            #   2 share price; 1.5 init_share_price
            #   180d elapsed; time_stretch=0.7; norm=365
            {
                "market_state": MarketState(
                    share_reserves=250000,  # z
                    bond_reserves=300000,  # y
                    share_price=2,  # c
                    init_share_price=1.5,  # u
                ),
                "time_remaining": StretchedTime(
                    days=180,
                    time_stretch=0.7,
                    normalizing_constant=365,
                ),
                # tau = days / normalizing_constant / time_stretch
                # s = y + c*z
                # p = ((2y + cz)/(u*z))^(-tau)
                # p = ((2 * 300000 + 2 * 250000) / (1.5 * 250000))**(-(180 / 0.7 / 365))
                "expected_result": 0.4685364947185249,
            },
        ]
        pricing_model = PricingModel()
        for test_number, test_case in enumerate(test_cases):
            spot_price = pricing_model.calc_spot_price_from_reserves(
                market_state=test_case["market_state"],
                time_remaining=test_case["time_remaining"],
            )
            np.testing.assert_almost_equal(
                spot_price,
                test_case["expected_result"],
                err_msg=f"{test_number=} failed, {spot_price=}, {test_case['expected_result']}",
            )

    def test_calc_spot_price_from_apr(self):
        test_cases = [
            # test 1: r = 0.05; d=90
            {
                "apr": 0.05,
                "time_remaining": StretchedTime(
                    days=90, time_stretch=1, normalizing_constant=365  # not used  # not used
                ),
                # t = time_remaining / 365
                # p = 1 / (1 + r * t)
                # p = 1 / (1 + 0.05 * (90 / 365))
                "expected_result": 0.9878213802435724,
            },
            # test 2: r = 0.025; d=90
            {
                "apr": 0.025,
                "time_remaining": StretchedTime(
                    days=90,
                    time_stretch=1,  # not used
                    normalizing_constant=90,  # not used
                ),
                # t = time_remaining / 365
                # p = 1 / (1 + r * t)
                # p = 1 / (1 + 0.025 * (90 / 365))
                "expected_result": 0.9938733832539143,
            },
            # test 3: r = 0.025; d=180
            {
                "apr": 0.025,
                "time_remaining": StretchedTime(
                    days=180,
                    time_stretch=0.5,  # not used
                    normalizing_constant=270,  # not used
                ),
                # t = time_remaining / 365
                # p = 1 / (1 + r * t)
                # p = 1 / (1 + 0.025 * (180 / 365))
                "expected_result": 0.9878213802435724,
            },
            # test 3: r = 0.1; d=365
            {
                "apr": 0.1,
                "time_remaining": StretchedTime(
                    days=365,
                    time_stretch=1.0,  # not used
                    normalizing_constant=365,  # not used
                ),
                # t = time_remaining / 365
                # p = 1 / (1 + r * t)
                # p = 1 / (1 + 0.1 * (365 / 365))
                "expected_result": 0.9090909090909091,
            },
        ]
        for test_number, test_case in enumerate(test_cases):
            spot_price = price_utils.calc_spot_price_from_apr(
                apr=test_case["apr"],
                time_remaining=test_case["time_remaining"],
            )
            np.testing.assert_almost_equal(
                spot_price,
                test_case["expected_result"],
                err_msg=f"{test_number=} failed, {spot_price=}, {test_case['expected_result']}",
            )

    def test_calc_spot_price_consistency(self):
        test_cases = [
            # test 1: 500k share_reserves; 500k bond_reserves
            #   1 share price; 1 init_share_price
            #   90d elapsed; time_stretch=1; norm=365
            {
                "market_state": MarketState(
                    share_reserves=500000,  # z
                    bond_reserves=500000,  # y
                    share_price=1,  # c
                    init_share_price=1,  # u
                ),
                "time_remaining": StretchedTime(
                    days=90,
                    time_stretch=1,
                    normalizing_constant=365,
                ),
            },
            # test 2: 250k share_reserves; 500k bond_reserves
            #   2 share price; 1.5 init_share_price
            #   90d elapsed; time_stretch=1; norm=365
            {
                "market_state": MarketState(
                    share_reserves=250000,  # z
                    bond_reserves=500000,  # y
                    share_price=2,  # c
                    init_share_price=1.5,  # u
                ),
                "time_remaining": StretchedTime(
                    days=90,
                    time_stretch=1,
                    normalizing_constant=365,
                ),
            },
            # test 3: 250k share_reserves; 300k bond_reserves
            #   2 share price; 1.5 init_share_price
            #   180d elapsed; time_stretch=0.7; norm=365
            {
                "market_state": MarketState(
                    share_reserves=250000,  # z
                    bond_reserves=300000,  # y
                    share_price=2,  # c
                    init_share_price=1.5,  # u
                ),
                "time_remaining": StretchedTime(
                    days=180,
                    time_stretch=0.7,
                    normalizing_constant=365,
                ),
            },
        ]
        pricing_model = PricingModel()
        for test_number, test_case in enumerate(test_cases):
            pm_spot_price = pricing_model.calc_spot_price_from_reserves(
                market_state=test_case["market_state"],
                time_remaining=test_case["time_remaining"],
            )
            pm_apr = pricing_model.calc_apr_from_reserves(
                market_state=test_case["market_state"],
                time_remaining=test_case["time_remaining"],
            )
            util_spot_price = price_utils.calc_spot_price_from_apr(
                apr=pm_apr,
                time_remaining=test_case["time_remaining"],
            )
            np.testing.assert_almost_equal(
                pm_spot_price,
                util_spot_price,
                err_msg=f"{test_number=} failed, {pm_spot_price=}, {util_spot_price=}",
            )

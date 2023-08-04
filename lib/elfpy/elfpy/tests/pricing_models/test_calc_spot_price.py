"""Testing for spot price calculations in Pricing Models and Price utils"""
import unittest

from fixedpointmath import FixedPoint

import lib.elfpy.elfpy.time as time
import lib.elfpy.elfpy.utils.price as price_utils
from lib.elfpy.elfpy.markets.base import BasePricingModel
from lib.elfpy.elfpy.markets.hyperdrive import HyperdriveMarketState


class TestSpotPriceCalculations(unittest.TestCase):
    """Test spot price calculation in base pricing model & price utils"""

    APPROX_EQ: FixedPoint = FixedPoint(1e-16)

    def test_calc_spot_price_from_reserves(self):
        """Test base pricing model calculation

        .. todo:: write failure tests
        """
        test_cases = [
            # test 1: 500k share_reserves; 500k bond_reserves
            #   1 share price; 1 init_share_price
            #   90d elapsed; time_stretch=1; norm=365
            {
                "market_state": HyperdriveMarketState(
                    share_reserves=FixedPoint("500000.0"),  # z
                    bond_reserves=FixedPoint("500000.0"),  # y
                    share_price=FixedPoint("1.0"),  # c
                    init_share_price=FixedPoint("1.0"),  # u
                ),
                "time_remaining": time.StretchedTime(
                    days=FixedPoint("90.0"),
                    time_stretch=FixedPoint("1.0"),
                    normalizing_constant=FixedPoint("365.0"),
                ),
                # tau = days / normalizing_constant / time_stretch
                # s = y + c*z
                # p = ((2y + cz)/(u*z))^(-tau)
                # p = ((2 * 500000 + 1 * 500000) / (1 * 500000))**(-(90 / 1 / 365))
                "expected_result": FixedPoint("0.7626998539403097"),
            },
            # test 2: 250k share_reserves; 500k bond_reserves
            #   2 share price; 1.5 init_share_price
            #   90d elapsed; time_stretch=1; norm=365
            {
                "market_state": HyperdriveMarketState(
                    share_reserves=FixedPoint("250000.0"),  # z
                    bond_reserves=FixedPoint("500000.0"),  # y
                    share_price=FixedPoint("2.0"),  # c
                    init_share_price=FixedPoint("1.5"),  # u
                ),
                "time_remaining": time.StretchedTime(
                    days=FixedPoint("90.0"),
                    time_stretch=FixedPoint("1.0"),
                    normalizing_constant=FixedPoint("365.0"),
                ),
                # tau = days / normalizing_constant / time_stretch
                # s = y + c*z
                # p = ((2y + cz)/(u*z))^(-tau)
                # p = ((2 * 500000 + 2 * 250000) / (1.5 * 250000))**(-(90 / 1 / 365))
                "expected_result": FixedPoint("0.7104718111828882"),
            },
            # test 3: 250k share_reserves; 300k bond_reserves
            #   2 share price; 1.5 init_share_price
            #   180d elapsed; time_stretch=0.7; norm=365
            {
                "market_state": HyperdriveMarketState(
                    share_reserves=FixedPoint("250000.0"),  # z
                    bond_reserves=FixedPoint("300000.0"),  # y
                    share_price=FixedPoint("2.0"),  # c
                    init_share_price=FixedPoint("1.5"),  # u
                ),
                "time_remaining": time.StretchedTime(
                    days=FixedPoint("180.0"),
                    time_stretch=FixedPoint("0.7"),
                    normalizing_constant=FixedPoint("365.0"),
                ),
                # tau = days / normalizing_constant / time_stretch
                # s = y + c*z
                # p = ((2y + cz)/(u*z))^(-tau)
                # p = ((2 * 300000 + 2 * 250000) / (1.5 * 250000))**(-(180 / 0.7 / 365))
                "expected_result": FixedPoint("0.4685364947185249"),
            },
        ]
        pricing_model = BasePricingModel()
        for test_number, test_case in enumerate(test_cases):
            # TODO: convert these tests to use total supply, not the approximation
            # approximation of total supply
            test_case["market_state"].lp_total_supply = (
                test_case["market_state"].bond_reserves
                + test_case["market_state"].share_price * test_case["market_state"].share_reserves
            )
            spot_price = pricing_model.calc_spot_price_from_reserves(
                market_state=test_case["market_state"],
                time_remaining=test_case["time_remaining"],
            )
            self.assertAlmostEqual(
                spot_price,
                test_case["expected_result"],
                delta=self.APPROX_EQ,
                msg=f"{test_number=} failed, {spot_price=}, {test_case['expected_result']}",
            )

    def test_calc_spot_price_from_apr(self):
        """Test the price utils function for calculating spot price"""
        test_cases = [
            # test 1: r = 0.05; d=90
            {
                "apr": FixedPoint("0.05"),
                "time_remaining": time.StretchedTime(
                    days=FixedPoint("90.0"),
                    time_stretch=FixedPoint("1.0"),  # not used
                    normalizing_constant=FixedPoint("365.0"),  # not used
                ),
                # t = time_remaining / 365
                # p = 1 / (1 + r * t)
                # p = 1 / (1 + 0.05 * (90 / 365))
                "expected_result": FixedPoint("0.9878213802435724"),
            },
            # test 2: r = 0.025; d=90
            {
                "apr": FixedPoint("0.025"),
                "time_remaining": time.StretchedTime(
                    days=FixedPoint("90.0"),
                    time_stretch=FixedPoint("1.0"),  # not used
                    normalizing_constant=FixedPoint("90.0"),  # not used
                ),
                # t = time_remaining / 365
                # p = 1 / (1 + r * t)
                # p = 1 / (1 + 0.025 * (90 / 365))
                "expected_result": FixedPoint("0.9938733832539143"),
            },
            # test 3: r = 0.025; d=180
            {
                "apr": FixedPoint("0.025"),
                "time_remaining": time.StretchedTime(
                    days=FixedPoint("180.0"),
                    time_stretch=FixedPoint("0.5"),  # not used
                    normalizing_constant=FixedPoint("270.0"),  # not used
                ),
                # t = time_remaining / 365
                # p = 1 / (1 + r * t)
                # p = 1 / (1 + 0.025 * (180 / 365))
                "expected_result": FixedPoint("0.9878213802435724"),
            },
            # test 3: r = 0.1; d=365
            {
                "apr": FixedPoint("0.1"),
                "time_remaining": time.StretchedTime(
                    days=FixedPoint("365.0"),
                    time_stretch=FixedPoint("1.0"),  # not used
                    normalizing_constant=FixedPoint("365.0"),  # not used
                ),
                # t = time_remaining / 365
                # p = 1 / (1 + r * t)
                # p = 1 / (1 + 0.1 * (365 / 365))
                "expected_result": FixedPoint("0.9090909090909091"),
            },
        ]
        for test_number, test_case in enumerate(test_cases):
            spot_price = price_utils.calc_spot_price_from_apr(
                apr=test_case["apr"],
                time_remaining=test_case["time_remaining"],
            )
            self.assertAlmostEqual(
                spot_price,
                test_case["expected_result"],
                delta=self.APPROX_EQ,
                msg=f"{test_number=} failed, {spot_price=}, {test_case['expected_result']}",
            )

    def test_calc_spot_price_consistency(self):
        """Test consistency of spot price calculations

        compute spot price from reserves using pricing model
        compute apr from reserves using pricing model
        compute spot price from apr using price utils
        compare spot price calculations
        """
        test_cases = [
            # test 1: 500k share_reserves; 500k bond_reserves
            #   1 share price; 1 init_share_price
            #   90d elapsed; time_stretch=1; norm=365
            {
                "market_state": HyperdriveMarketState(
                    share_reserves=FixedPoint("500000.0"),  # z
                    bond_reserves=FixedPoint("500000.0"),  # y
                    share_price=FixedPoint("1.0"),  # c
                    init_share_price=FixedPoint("1.0"),  # u
                ),
                "time_remaining": time.StretchedTime(
                    days=FixedPoint("90.0"),
                    time_stretch=FixedPoint("1.0"),
                    normalizing_constant=FixedPoint("365.0"),
                ),
            },
            # test 2: 250k share_reserves; 500k bond_reserves
            #   2 share price; 1.5 init_share_price
            #   90d elapsed; time_stretch=1; norm=365
            {
                "market_state": HyperdriveMarketState(
                    share_reserves=FixedPoint("250000.0"),  # z
                    bond_reserves=FixedPoint("500000.0"),  # y
                    share_price=FixedPoint("2.0"),  # c
                    init_share_price=FixedPoint("1.5"),  # u
                ),
                "time_remaining": time.StretchedTime(
                    days=FixedPoint("90.0"),
                    time_stretch=FixedPoint("1.0"),
                    normalizing_constant=FixedPoint("365.0"),
                ),
            },
            # test 3: 250k share_reserves; 300k bond_reserves
            #   2 share price; 1.5 init_share_price
            #   180d elapsed; time_stretch=0.7; norm=365
            {
                "market_state": HyperdriveMarketState(
                    share_reserves=FixedPoint("250000.0"),  # z
                    bond_reserves=FixedPoint("300000.0"),  # y
                    share_price=FixedPoint("2.0"),  # c
                    init_share_price=FixedPoint("1.5"),  # u
                ),
                "time_remaining": time.StretchedTime(
                    days=FixedPoint("180.0"),
                    time_stretch=FixedPoint("0.7"),
                    normalizing_constant=FixedPoint("365.0"),
                ),
            },
        ]
        pricing_model = BasePricingModel()
        for test_number, test_case in enumerate(test_cases):
            # TODO: convert these tests to use total supply, not the approximation
            # approximation of total supply
            test_case["market_state"].lp_total_supply = (
                test_case["market_state"].bond_reserves
                + test_case["market_state"].share_price * test_case["market_state"].share_reserves
            )
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
            self.assertAlmostEqual(
                pm_spot_price,
                util_spot_price,
                delta=self.APPROX_EQ,
                msg=f"{test_number=} failed, {pm_spot_price=}, {util_spot_price=}",
            )

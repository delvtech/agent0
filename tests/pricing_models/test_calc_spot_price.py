# base.calc_spot_price_from_reserves
# utils.price.calc_spot_price_from_apr

import unittest
from elfpy.pricing_models.base import PricingModel
import elfpy.utils.price as price_utils
from elfpy.types import MarketState, StretchedTime


class TestSpotPriceCalculations(unittest.TestCase):
    def test_calc_spot_price_from_reserves(self):

        # def calc_spot_price_from_reserves(
        # self,
        # market_state: MarketState,
        # time_remaining: StretchedTime,
        # ) -> float:

        test_cases = [
            # test 1: 500k share_reserves; 500k bond_reserves
            #   1 share price; 1 init_share_price
            #   90d elapsed; time_stretch=1; norm=365
            {
                "market_state": MarketState(
                    share_reserves=500000,  # z = 500000
                    bond_reserves=500000,  # y = 500000
                    share_price=1,  # c = 1
                    init_share_price=1,  # u = 1
                ),
                "time_remaining": StretchedTime(
                    days=90,
                    time_stretch=1,
                    normalizing_constant=365,
                ),
                # tau = days / normalizing_constant / time_stretch
                # s = y + c*z
                # p = ((2y + cz)/(u*z))^(-tau)
                # p = ((2 * 500000 + 1 * 500000) / (1 * 500000))**((-(90 / 1 / 365))
                "expected_result": 0.7626998539403097,
            },
        ]

    def test_calc_spot_price_from_apr(self):
        # (price: float, time_remaining: StretchedTime)
        pass

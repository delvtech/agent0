"""
Testing for the calc_out_given_in of the pricing models.
"""

# pylint: disable=too-many-lines
# pylint: disable=line-too-long
# pylint: disable=duplicate-code

import decimal
import unittest
import numpy as np
from test_dataclasses import (
    TestCaseCalcOutGivenInSuccess,
    TestResultCalcOutGivenInSuccess,
    TestResultCalcOutGivenInSuccessByModel,
    TestCaseCalcOutGivenInFailure,
)

from elfpy.pricing_models.base import PricingModel
from elfpy.pricing_models.hyperdrive import HyperdrivePricingModel
from elfpy.pricing_models.yieldspace import YieldSpacePricingModel
from elfpy.types import MarketState, Quantity, StretchedTime, TokenType


class TestCalcOutGivenIn(unittest.TestCase):
    """Unit tests for the calc_out_given_in function"""

    # TODO: Add tests for the full TradeResult object.
    def test_calc_out_given_in_success(self):
        """Success tests for calc_out_given_in"""
        pricing_models: list[PricingModel] = [YieldSpacePricingModel(), HyperdrivePricingModel()]

        # Test cases where token_out = TokenType.PT indicating that bonds are being
        # purchased for base.
        #
        # 1. in_ = 100; 1% fee; 100k share reserves; 100k bond reserves;
        #    1 share price; 1 init share price; t_stretch targeting 5% APY;
        #    6 mo remaining
        # 2. in_ = 100; 20% fee; 100k share reserves; 100k bond reserves;
        #    1 share price; 1 init share price; t_stretch targeting 5% APY;
        #    6 mo remaining
        # 3. in_ = 10k; 1% fee; 100k share reserves; 100k bond reserves;
        #    1 share price; 1 init share price; t_stretch targeting 5% APY;
        #    6 mo remaining
        # 4. in_ = 80k; 1% fee; 100k share reserves; 100k bond reserves;
        #    1 share price; 1 init share price; t_stretch targeting 5% APY;
        #    6 mo remaining
        # 5. in_ = 200; 1% fee; 100k share reserves; 100k bond reserves;
        #    2 share price; 1.5 init share price; t_stretch targeting 5% APY;
        #    6 mo remaining
        # 6. in_ = 200; 1% fee; 100k share reserves; 1M bond reserves;
        #    2 share price; 1.5 init share price; t_stretch targeting 5% APY;
        #    6 mo remaining
        # 7. in_ = 200; 1% fee; 100k share reserves; 1M bond reserves;
        #    2 share price; 1.5 init share price; t_stretch targeting 5% APY;
        #    3 mo remaining
        # 8. in_ = 200; 1% fee; 100k share reserves; 1M bond reserves;
        #    2 share price; 1.5 init share price; t_stretch targeting 10% APY;
        #    3 mo remaining
        pt_out_test_cases = [
            # Low slippage trade - in_ is 0.1% of share reserves.
            (
                TestCaseCalcOutGivenInSuccess(
                    in_=Quantity(amount=100, unit=TokenType.BASE),
                    market_state=MarketState(
                        share_reserves=100_000,
                        bond_reserves=100_000,
                        share_price=1,
                        init_share_price=1,
                    ),
                    fee_percent=0.01,
                    days_remaining=182.5,
                    time_stretch_apy=0.05,
                ),
                # From the input, we have the following values:
                #
                #   t_stretch = 22.1868770168519182502689135891
                #
                #   tau = d / (365 * t_stretch)
                #     = 182.5 / (365 * 22.1868770168519182502689135891)
                #     = 0.0225358440315970471499308329778
                #
                #   1 - tau = 0.977464155968402952850069167022
                #
                #   k = (c / mu) * (mu * z) **(1 - tau) + (2 * y + c * z)**(1 - tau)
                #     = 100000**0.9774641559684029528500691670222 + (2*100000 +
                #           100000*1)**0.9774641559684029528500691670222
                #     = 302929.51067963685
                #
                #   p = ((2 * y + c * z) / (mu * z)) ** tau
                #     = ((2 * 100_000 + 1 * 100_000) / (1 * 100_000)) ** 0.0225358440315970471499308329778
                #     = 1.0250671833648672
                TestResultCalcOutGivenInSuccessByModel(
                    yieldspace=TestResultCalcOutGivenInSuccess(
                        # without_fee_or_slippage = p * in_
                        #                         = 1.0250671833648672 * 100
                        #                         = 102.50671833648673
                        without_fee_or_slippage=102.50671833648673,
                        # We want to solve for the amount of bonds out given the
                        # amount of shares coming in, so we set up the problem as:
                        #
                        #   k = (c / mu) * (mu * (z + d_z)) ** (1 - tau) + (2 * y + c * z - d_y') ** (1 - tau)
                        #     = 100_100 ** (1 - tau) + (300_000 - d_y') ** (1 - tau)
                        #
                        # Solving for d_y, we get the following calculation:
                        #
                        #   d_y' = 300_000 - (k - 100_100 ** (1 - tau) ** (1 / (1 - tau))
                        #       = 102.50516899477225
                        #
                        # Note that this is slightly smaller than the without slippage value
                        without_fee=102.50516899477225,
                        # fee = 0.01 * (p - 1) * 100 = 0.02506718336486724
                        fee=0.02506718336486724,
                        # with_fee = d_y' - fee
                        #          = 102.50516899477225 - 0.02506718336486724
                        #          = 102.48010181140738
                        with_fee=102.48010181140738,
                    ),
                    hyperdrive=TestResultCalcOutGivenInSuccess(
                        # spot_price = (1 / p) * c * delta_z * t + c * delta_z * (1 - t)
                        # spot_price = (1 / 0.9517182274304707) * 1 * 100.0 * 0.5 + 1 * 100.0 * 0.5
                        without_fee_or_slippage=102.53655815229496,
                        # yield space equation (for hyperdrive multiply d_z by t):
                        # k = (c / mu) * (mu * (z + d_z))**(1 - tau) + (2y + cz - d_y')**(1 - tau)
                        # dy' = 2y + c*z - (k - (c / mu) * (mu * (z + d_z))**(1 - tau))**(1 / (1 - tau))
                        #
                        # note: use delta_z * t to phase the curve part out, and add delta_z * (1 - t)
                        # to phase the flat part in over the length of the term:
                        #
                        # dy' = 2*y + c*z - (k - (c / u) * (u * (z + delta_z*t))**(1 - tau_full))**(1 / (1 - tau_full))
                        #       + c * delta_z * (1 - t)
                        # dy' = 199900.0 + 100050.0 - (229443.78725685307 - 1.0 * (1 * (100050.0 + 100.0*0.5))**(0.9549283119368059))**(1.0471990279267966)
                        #       + 1 * 100.0 * 0.5
                        without_fee=102.5357591957436,
                        # fee = ((1 / p) - 1) * phi * c * d_z
                        # fee = (1.050731163045899 - 1) * 0.01 * 1 * 100.0
                        fee=0.025365581522949543,
                        with_fee=102.51039361422065,
                    ),
                ),
            ),
            # High fee percentage - 20%.
            (
                TestCaseCalcOutGivenInSuccess(
                    in_=Quantity(amount=100, unit=TokenType.BASE),
                    market_state=MarketState(
                        share_reserves=100_000,
                        bond_reserves=100_000,
                        share_price=1,
                        init_share_price=1,
                    ),
                    fee_percent=0.2,
                    days_remaining=182.5,
                    time_stretch_apy=0.05,
                ),
                # The trading constants are the same as the "Low slippage trade"
                # case. The only values that should change are `fee` and
                # `with_fee` since the fee percentage changed.
                TestResultCalcOutGivenInSuccessByModel(
                    yieldspace=TestResultCalcOutGivenInSuccess(
                        without_fee_or_slippage=102.50671833648673,
                        without_fee=102.50516899477225,
                        # fee = 0.2 * (p - 1) * 100 = 0.5013436672973448
                        fee=0.5013436672973448,
                        # with_fee = d_y' - fee
                        #          = 102.50516899477225 - 0.5013436672973448
                        #          = 102.0038253274749
                        with_fee=102.0038253274749,
                    ),
                    hyperdrive=TestResultCalcOutGivenInSuccess(
                        # spot_price = (1 / p) * c * delta_z * t + c * delta_z * (1 - t)
                        # spot_price = (1 / 0.9517182274304707) * 1 * 100.0 * 0.5 + 1 * 100.0 * 0.5
                        without_fee_or_slippage=102.53655815229496,
                        # yield space equation (for hyperdrive multiply d_z by t):
                        # k = (c / mu) * (mu * (z + d_z))**(1 - tau) + (2y + cz - d_y')**(1 - tau)
                        # dy' = 2y + c*z - (k - (c / mu) * (mu * (z + d_z))**(1 - tau))**(1 / (1 - tau))
                        #
                        # note: use delta_z * t to phase the curve part out, and add delta_z * (1 - t)
                        # to phase the flat part in over the length of the term:
                        #
                        # dy' = 2*y + c*z - (k - (c / u) * (u * (z + delta_z*t))**(1 - tau_full))**(1 / (1 - tau_full))
                        #       + c * delta_z * (1 - t)
                        # dy' = 199900.0 + 100050.0 - (229443.78725685307 - 1.0 * (1 * (100050.0 + 100.0*0.5))**(0.9549283119368059))**(1.0471990279267966)
                        #       + 1 * 100.0 * 0.5
                        without_fee=102.5357591957436,
                        # fee = ((1 / p) - 1) * phi * c * d_z
                        # fee = (1.050731163045899 - 1) * 0.2 * 1 * 100.0
                        fee=0.5073116304589909,
                        with_fee=102.02844756528461,
                    ),
                ),
            ),
            # Medium slippage trade - in_ is 10% of share reserves.
            (
                TestCaseCalcOutGivenInSuccess(
                    in_=Quantity(amount=10_000, unit=TokenType.BASE),
                    market_state=MarketState(
                        share_reserves=100_000,
                        bond_reserves=100_000,
                        share_price=1,
                        init_share_price=1,
                    ),
                    fee_percent=0.01,
                    days_remaining=182.5,
                    time_stretch_apy=0.05,
                ),
                # The trading constants are the same as the "Low slippage trade"
                # case.
                TestResultCalcOutGivenInSuccessByModel(
                    yieldspace=TestResultCalcOutGivenInSuccess(
                        # without_fee_or_slippage = p * in_
                        #                         = 1.0250671833648672 * 10_000
                        #                         = 10250.671833648672
                        without_fee_or_slippage=10250.671833648672,
                        # We want to solve for the amount of bonds out given the
                        # amount of shares coming in, so we set up the problem as:
                        #
                        #   k = (c / mu) * (mu * (z + d_z)) ** (1 - tau) + (2 * y + c * z - d_y') ** (1 - tau)
                        #     = 110_000 ** (1 - tau) + (300_000 - d_y') ** (1 - tau)
                        #
                        # Solving for d_y, we get the following calculation:
                        #
                        #   d_y' = 300_000 - (k - 110_000 ** (1 - tau) ** (1 / (1 - tau))
                        #       = 10235.514826394327
                        #
                        # Note that this is slightly smaller than the without slippage value
                        without_fee=10235.514826394327,
                        # fee = 0.01 * (p - 1) * 10_000 = 2.506718336486724
                        fee=2.506718336486724,
                        # with_fee = d_y' - fee
                        #          = 10235.514826394327 - 2.506718336486724
                        #          = 10233.00810805784
                        with_fee=10233.00810805784,
                    ),
                    hyperdrive=TestResultCalcOutGivenInSuccess(
                        # spot_price = (1 / p) * c * delta_z * t + c * delta_z * (1 - t)
                        # spot_price = (1 / 0.9545075460138804) * 1 * 10000.0 * 0.5 + 1 * 10000.0 * 0.5
                        without_fee_or_slippage=10238.303270498493,
                        # yield space equation (for hyperdrive multiply d_z by t):
                        # k = (c / mu) * (mu * (z + d_z))**(1 - tau) + (2y + cz - d_y')**(1 - tau)
                        # dy' = 2y + c*z - (k - (c / mu) * (mu * (z + d_z))**(1 - tau))**(1 / (1 - tau))
                        #
                        # note: use delta_z * t to phase the curve part out, and add delta_z * (1 - t)
                        # to phase the flat part in over the length of the term:
                        #
                        # dy' = 2*y + c*z - (k - (c / u) * (u * (z + delta_z*t))**(1 - tau_full))**(1 / (1 - tau_full))
                        #       + c * delta_z * (1 - t)
                        # dy' = 190000.0 + 105000.0 - (229575.5303140286 - 1.0 * (1 * (105000.0 + 10000.0*0.5))**(0.9549283119368059))**(1.0471990279267966)
                        #       + 1 * 10000.0 * 0.5
                        without_fee=10230.669780368684,
                        # fee = ((1 / p) - 1) * phi * c * d_z
                        # fee = (1.0476606540996984 - 1) * 0.01 * 1 * 10000.0
                        fee=2.383032704984922,
                        with_fee=10228.286747663698,
                    ),
                ),
            ),
            # High slippage trade - in_ is 80% of share reserves.
            (
                TestCaseCalcOutGivenInSuccess(
                    in_=Quantity(amount=80_000, unit=TokenType.BASE),
                    market_state=MarketState(
                        share_reserves=100_000,
                        bond_reserves=100_000,
                        share_price=1,
                        init_share_price=1,
                    ),
                    fee_percent=0.01,
                    days_remaining=182.5,
                    time_stretch_apy=0.05,
                ),
                # The trading constants are the same as the "Low slippage trade"
                # case. The only values that should change are `fee` and
                # `with_fee` since the fee percentage changed.
                TestResultCalcOutGivenInSuccessByModel(
                    yieldspace=TestResultCalcOutGivenInSuccess(
                        # without_fee_or_slippage = p * in_
                        #                         = 1.0250671833648672 * 80_000
                        #                         = 82005.37466918938
                        without_fee_or_slippage=82005.37466918938,
                        # We want to solve for the amount of bonds out given the
                        # amount of shares coming in, so we set up the problem as:
                        #
                        #   k = (c / mu) * (mu * (z + d_z)) ** (1 - tau) + (2 * y + c * z - d_y') ** (1 - tau)
                        #     = 180_000 ** (1 - tau) + (300_000 - d_y') ** (1 - tau)
                        #
                        # Solving for d_y, we get the following calculation:
                        #
                        #   d_y' = 300_000 - (k - 180_000 ** (1 - tau) ** (1 / (1 - tau))
                        #       = 81138.27602200207
                        #
                        # Note that this is slightly smaller than the without slippage value
                        without_fee=81138.27602200207,
                        # fee = 0.01 * (p - 1) * 80_000 = 20.053746691893792
                        fee=20.053746691893792,
                        # with_fee = d_y' - fee
                        #          = 81138.27602200207 - 20.053746691893792
                        #          = 81118.22227531018
                        with_fee=81118.22227531018,
                    ),
                    hyperdrive=TestResultCalcOutGivenInSuccess(
                        # spot_price = (1 / p) * c * delta_z * t + c * delta_z * (1 - t)
                        # spot_price = (1 / 0.9724844998246822) * 1 * 80000.0 * 0.5 + 1 * 80000.0 * 0.5
                        without_fee_or_slippage=81131.76097635605,
                        # yield space equation (for hyperdrive multiply d_z by t):
                        # k = (c / mu) * (mu * (z + d_z))**(1 - tau) + (2y + cz - d_y')**(1 - tau)
                        # dy' = 2y + c*z - (k - (c / mu) * (mu * (z + d_z))**(1 - tau))**(1 / (1 - tau))
                        #
                        # note: use delta_z * t to phase the curve part out, and add delta_z * (1 - t)
                        # to phase the flat part in over the length of the term:
                        #
                        # dy' = 2*y + c*z - (k - (c / u) * (u * (z + delta_z*t))**(1 - tau_full))**(1 / (1 - tau_full))
                        #       + c * delta_z * (1 - t)
                        # dy' = 120000.0 + 140000.0 - (230291.34947619453 - 1.0 * (1 * (140000.0 + 80000.0*0.5))**(0.9549283119368059))**(1.0471990279267966)
                        #       + 1 * 80000.0 * 0.5
                        without_fee=80737.60201076139,
                        # fee = ((1 / p) - 1) * phi * c * d_z
                        # fee = (1.0282940244089014 - 1) * 0.01 * 1 * 80000.0
                        fee=11.317609763560556,
                        with_fee=80726.28440099783,
                    ),
                ),
            ),
            # Non-trivial initial share price and share price.
            (
                TestCaseCalcOutGivenInSuccess(
                    # Base in of 200 is 100 shares at the current share price.
                    in_=Quantity(amount=200, unit=TokenType.BASE),
                    market_state=MarketState(
                        share_reserves=100_000,
                        bond_reserves=100_000,
                        share_price=2,
                        init_share_price=1.5,
                    ),
                    fee_percent=0.01,
                    days_remaining=182.5,
                    time_stretch_apy=0.05,
                ),
                # From the input, we have the following values:
                #
                #   t_stretch = 22.1868770168519182502689135891
                #
                #   tau = d / (365 * t_stretch)
                #     = 182.5 / (365 * 22.1868770168519182502689135891)
                #     = 0.0225358440315970471499308329778
                #
                #   1 - tau = 0.977464155968402952850069167022
                #
                #   k = (c / mu) * (mu * z) **(1 - tau) + (2 * y + c * z)**(1 - tau)
                #     = (2 / 1.50) * (1.5 * 100000) ** 0.9774641559684029528500691670222 + (2 * 100000 +
                #           2 * 100000) ** 0.9774641559684029528500691670222
                #     = 451988.7122137336
                #
                #   p = ((2 * y + c * z) / (mu * z)) ** tau
                #     = ((2 * 100_000 + 2 * 100_000) / (1.5 * 100_000)) ** 0.0225358440315970471499308329778
                #     = 1.0223499142867662
                TestResultCalcOutGivenInSuccessByModel(
                    yieldspace=TestResultCalcOutGivenInSuccess(
                        # without_fee_or_slippage = p * in_
                        #                         = 1.0223499142867662 * 200
                        #                         = 204.46998285735324
                        without_fee_or_slippage=204.46998285735324,
                        # We want to solve for the amount of bonds out given the
                        # amount of shares coming in, so we set up the problem as:
                        #
                        #   k = (c / mu) * (mu * (z + d_z)) ** (1 - tau) + (2 * y + c * z - d_y') ** (1 - tau)
                        #     = (2 / 1.5) * 150_150 ** (1 - tau) + (400_000 - d_y') ** (1 - tau)
                        #
                        # Solving for d_y, we get the following calculation:
                        #
                        #   d_y' = 400_000 - (k - (2 / 1.5) * 150_150 ** (1 - tau) ** (1 / (1 - tau))
                        #       = 204.46650180319557
                        #
                        # Note that this is slightly smaller than the without slippage value
                        without_fee=204.46650180319557,
                        # fee = 0.01 * (p - 1) * 200 = 0.044699828573532496
                        fee=0.044699828573532496,
                        # with_fee = d_y' - fee
                        #          = 204.46650180319557 - 0.044699828573532496
                        #          = 204.42180197462204
                        with_fee=204.42180197462204,
                    ),
                    hyperdrive=TestResultCalcOutGivenInSuccess(
                        # spot_price = (1 / p) * c * delta_z * t + c * delta_z * (1 - t)
                        # spot_price = (1 / 0.9567876240571412) * 2 * 100.0 * 0.5 + 2 * 100.0 * 0.5
                        without_fee_or_slippage=204.51640205792188,
                        # yield space equation (for hyperdrive multiply d_z by t):
                        # k = (c / mu) * (mu * (z + d_z))**(1 - tau) + (2y + cz - d_y')**(1 - tau)
                        # dy' = 2y + c*z - (k - (c / mu) * (mu * (z + d_z))**(1 - tau))**(1 / (1 - tau))
                        #
                        # note: use delta_z * t to phase the curve part out, and add delta_z * (1 - t)
                        # to phase the flat part in over the length of the term:
                        #
                        # dy' = 2*y + c*z - (k - (c / u) * (u * (z + delta_z*t))**(1 - tau_full))**(1 / (1 - tau_full))
                        #       + c * delta_z * (1 - t)
                        # dy' = 199800.0 + 200100.0 - (340529.31114464573 - 1.3333333333333333 * (1.5 * (100050.0 + 100.0*0.5))**(0.9549283119368059))**(1.0471990279267966)
                        #       + 2 * 100.0 * 0.5
                        without_fee=204.51460954395588,
                        # fee = ((1 / p) - 1) * phi * c * d_z
                        # fee = (1.045164020579219 - 1) * 0.01 * 2 * 100.0
                        fee=0.04516402057921898,
                        with_fee=204.46944552337666,
                    ),
                ),
            ),
            # Very unbalanced reserves.
            (
                TestCaseCalcOutGivenInSuccess(
                    in_=Quantity(amount=200, unit=TokenType.BASE),
                    market_state=MarketState(
                        share_reserves=100_000,
                        bond_reserves=1_000_000,
                        share_price=2,
                        init_share_price=1.5,
                    ),
                    fee_percent=0.01,
                    days_remaining=182.5,
                    time_stretch_apy=0.05,
                ),
                # From the input, we have the following values:
                #
                #   t_stretch = 22.1868770168519182502689135891
                #
                #   tau = d / (365 * t_stretch)
                #     = 182.5 / (365 * 22.1868770168519182502689135891)
                #     = 0.0225358440315970471499308329778
                #
                #   1 - tau = 0.977464155968402952850069167022
                #
                #   k = (c / mu) * (mu * z) **(1 - tau) + (2 * y + c * z)**(1 - tau)
                #     = (2 / 1.50) * (1.5 * 100000) ** 0.9774641559684029528500691670222 + (2 * 100000 +
                #           2 * 1_000_000) ** 0.9774641559684029528500691670222
                #     = 1_735_927.3223407117
                #
                #   p = ((2 * y + c * z) / (mu * z)) ** tau
                #     = ((2 * 100_000 + 2 * 1_000_000) / (1.5 * 100_000)) ** 0.0225358440315970471499308329778
                #     = 1.0623907066406753
                TestResultCalcOutGivenInSuccessByModel(
                    yieldspace=TestResultCalcOutGivenInSuccess(
                        # without_fee_or_slippage = p * in_
                        #                         = 1.0623907066406753 * 200
                        #                         = 212.47814132813505
                        without_fee_or_slippage=212.47814132813505,
                        # We want to solve for the amount of bonds out given the
                        # amount of shares coming in, so we set up the problem as:
                        #
                        #   k = (c / mu) * (mu * (z + d_z)) ** (1 - tau) + (2 * y + c * z - d_y') ** (1 - tau)
                        #     = (2 / 1.5) * 150_150 ** (1 - tau) + (2_200_000 - d_y') ** (1 - tau)
                        #
                        # Solving for d_y, we get the following calculation:
                        #
                        #   d_y' = 2_200_000 - (k - (2 / 1.5) * 150_150 ** (1 - tau) ** (1 / (1 - tau))
                        #       = 212.47551672440022
                        #
                        # Note that this is slightly smaller than the without slippage value
                        without_fee=212.47551672440022,
                        # fee = 0.01 * (p - 1) * 200 = 0.1247814132813505
                        fee=0.1247814132813505,
                        # with_fee = d_y' - fee
                        #          = 212.47551672440022 - 0.1247814132813505
                        #          = 212.35073531111888
                        with_fee=212.35073531111888,
                    ),
                    hyperdrive=TestResultCalcOutGivenInSuccess(
                        # spot_price = (1 / p) * c * delta_z * t + c * delta_z * (1 - t)
                        # spot_price = (1 / 0.8860171912017127) * 2 * 100.0 * 0.5 + 2 * 100.0 * 0.5
                        without_fee_or_slippage=212.86462722508705,
                        # yield space equation (for hyperdrive multiply d_z by t):
                        # k = (c / mu) * (mu * (z + d_z))**(1 - tau) + (2y + cz - d_y')**(1 - tau)
                        # dy' = 2y + c*z - (k - (c / mu) * (mu * (z + d_z))**(1 - tau))**(1 / (1 - tau))
                        #
                        # note: use delta_z * t to phase the curve part out, and add delta_z * (1 - t)
                        # to phase the flat part in over the length of the term:
                        #
                        # dy' = 2*y + c*z - (k - (c / u) * (u * (z + delta_z*t))**(1 - tau_full))**(1 / (1 - tau_full))
                        #       + c * delta_z * (1 - t)
                        # dy' = 1999800.0 + 200100.0 - (1255977.392544668 - 1.3333333333333333 * (1.5 * (100050.0 + 100.0*0.5))**(0.9549283119368059))**(1.0471990279267966)
                        #       + 2 * 100.0 * 0.5
                        without_fee=212.86322583956644,
                        # fee = ((1 / p) - 1) * phi * c * d_z
                        # fee = (1.1286462722508706 - 1) * 0.01 * 2 * 100.0
                        fee=0.12864627225087055,
                        with_fee=212.73457956731556,
                    ),
                ),
            ),
            # A term of a quarter year.
            (
                TestCaseCalcOutGivenInSuccess(
                    in_=Quantity(amount=200, unit=TokenType.BASE),
                    market_state=MarketState(
                        share_reserves=100_000,
                        bond_reserves=1_000_000,
                        share_price=2,
                        init_share_price=1.5,
                    ),
                    fee_percent=0.01,
                    days_remaining=91.25,
                    time_stretch_apy=0.05,
                ),
                # From the input, we have the following values:
                #
                #   t_stretch = 22.1868770168519182502689135891
                #
                #   tau = d / (365 * t_stretch)
                #     = 91.25 / (365 * 22.1868770168519182502689135891)
                #     = 0.011267922015798522
                #
                #   1 - tau = 0.9887320779842015
                #
                #   k = (c / mu) * (mu * z) **(1 - tau) + (2 * y + c * z)**(1 - tau)
                #     = (2 / 1.50) * (1.5 * 100000) ** 0.9887320779842015 + (2 * 100000 +
                #           2 * 1_000_000) ** 0.9887320779842015
                #     = 2_041_060.1949973335
                #
                #   p = ((2 * y + c * z) / (mu * z)) ** tau
                #     = ((2 * 100_000 + 2 * 1_000_000) / (1.5 * 100_000)) ** 0.011267922015798522
                #     = 1.0307233899745727
                TestResultCalcOutGivenInSuccessByModel(
                    yieldspace=TestResultCalcOutGivenInSuccess(
                        # without_fee_or_slippage = p * in_
                        #                         = 1.0307233899745727 * 200
                        #                         = 206.14467799491453
                        without_fee_or_slippage=206.14467799491453,
                        # We want to solve for the amount of bonds out given the
                        # amount of shares coming in, so we set up the problem as:
                        #
                        #   k = (c / mu) * (mu * (z + d_z)) ** (1 - tau) + (2 * y + c * z - d_y') ** (1 - tau)
                        #     = (2 / 1.5) * 150_150 ** (1 - tau) + (2_200_000 - d_y') ** (1 - tau)
                        #
                        # Solving for d_y, we get the following calculation:
                        #
                        #   d_y' = 2_200_000 - (k - (2 / 1.5) * 150_150 ** (1 - tau) ** (1 / (1 - tau))
                        #       = 206.14340814948082
                        #
                        # Note that this is slightly smaller than the without slippage value
                        without_fee=206.14340814948082,
                        # fee = 0.01 * (p - 1) * 200 = 0.06144677994914538
                        fee=0.06144677994914538,
                        # with_fee = d_y' - fee
                        #          = 206.14340814948082 - 0.06144677994914538
                        #          = 206.08196136953168
                        with_fee=206.08196136953168,
                    ),
                    hyperdrive=TestResultCalcOutGivenInSuccess(
                        # spot_price = (1 / p) * c * delta_z * t + c * delta_z * (1 - t)
                        # spot_price = (1 / 0.8860280762544887) * 2 * 100.0 * 0.25 + 2 * 100.0 * 0.75
                        without_fee_or_slippage=206.4316203289689,
                        # yield space equation (for hyperdrive multiply d_z by t):
                        # k = (c / mu) * (mu * (z + d_z))**(1 - tau) + (2y + cz - d_y')**(1 - tau)
                        # dy' = 2y + c*z - (k - (c / mu) * (mu * (z + d_z))**(1 - tau))**(1 / (1 - tau))
                        #
                        # note: use delta_z * t to phase the curve part out, and add delta_z * (1 - t)
                        # to phase the flat part in over the length of the term:
                        #
                        # dy' = 2*y + c*z - (k - (c / u) * (u * (z + delta_z*t))**(1 - tau_full))**(1 / (1 - tau_full))
                        #       + c * delta_z * (1 - t)
                        # dy' = 1999700.0 + 200150.0 - (1255980.5727267754 - 1.3333333333333333 * (1.5 * (100075.0 + 100.0*0.25))**(0.9549283119368059))**(1.0471990279267966)
                        #       + 2 * 100.0 * 0.75
                        without_fee=206.43127003777772,
                        # fee = ((1 / p) - 1) * phi * c * d_z
                        # fee = (1.1286324065793778 - 1) * 0.01 * 2 * 100.0
                        fee=0.0643162032896889,
                        with_fee=206.36695383448804,
                    ),
                ),
            ),
            # A time stretch targeting 10% APY.
            (
                TestCaseCalcOutGivenInSuccess(
                    in_=Quantity(amount=200, unit=TokenType.BASE),
                    market_state=MarketState(
                        share_reserves=100_000,
                        bond_reserves=1_000_000,
                        share_price=2,
                        init_share_price=1.5,
                    ),
                    fee_percent=0.01,
                    days_remaining=91.25,
                    time_stretch_apy=0.10,
                ),
                # From the input, we have the following values:
                #
                #   t_stretch = 11.093438508425956
                #
                #   tau = d / (365 * t_stretch)
                #     = 91.25 / (365 * 11.093438508425956)
                #     = 0.022535844031597054
                #
                #   1 - tau = 0.977464155968403
                #
                #   k = (c / mu) * (mu * z) **(1 - tau) + (2 * y + c * z)**(1 - tau)
                #     = (2 / 1.50) * (1.5 * 100000) ** 0.977464155968403 + (2 * 100000 +
                #           2 * 1_000_000) ** 0.977464155968403
                #     = 1_735_927.3223407117
                #
                #   p = ((2 * y + c * z) / (mu * z)) ** tau
                #     = ((2 * 100_000 + 2 * 1_000_000) / (1.5 * 100_000)) ** 0.022535844031597054
                #     = 1.0623907066406753
                TestResultCalcOutGivenInSuccessByModel(
                    yieldspace=TestResultCalcOutGivenInSuccess(
                        # without_fee_or_slippage = p * in_
                        #                         = 1.0623907066406753 * 200
                        #                         = 212.47814132813505
                        without_fee_or_slippage=212.47814132813505,
                        # We want to solve for the amount of bonds out given the
                        # amount of shares coming in, so we set up the problem as:
                        #
                        #   k = (c / mu) * (mu * (z + d_z)) ** (1 - tau) + (2 * y + c * z - d_y') ** (1 - tau)
                        #     = (2 / 1.5) * 150_150 ** (1 - tau) + (2_200_000 - d_y') ** (1 - tau)
                        #
                        # Solving for d_y, we get the following calculation:
                        #
                        #   d_y' = 2_200_000 - (k - (2 / 1.5) * 150_150 ** (1 - tau) ** (1 / (1 - tau))
                        #       = 212.47551672440022
                        #
                        # Note that this is slightly smaller than the without slippage value
                        without_fee=212.47551672440022,
                        # fee = 0.01 * (p - 1) * 200 = 0.1247814132813505
                        fee=0.1247814132813505,
                        # with_fee = d_y' - fee
                        #          = 212.47551672440022 - 0.1247814132813505
                        #          = 212.35073531111888
                        with_fee=212.35073531111888,
                    ),
                    hyperdrive=TestResultCalcOutGivenInSuccess(
                        # spot_price = (1 / p) * c * delta_z * t + c * delta_z * (1 - t)
                        # spot_price = (1 / 0.7850457519112299) * 2 * 100.0 * 0.25 + 2 * 100.0 * 0.75
                        without_fee_or_slippage=213.6905554590579,
                        # yield space equation (for hyperdrive multiply d_z by t):
                        # k = (c / mu) * (mu * (z + d_z))**(1 - tau) + (2y + cz - d_y')**(1 - tau)
                        # dy' = 2y + c*z - (k - (c / mu) * (mu * (z + d_z))**(1 - tau))**(1 / (1 - tau))
                        #
                        # note: use delta_z * t to phase the curve part out, and add delta_z * (1 - t)
                        # to phase the flat part in over the length of the term:
                        #
                        # dy' = 2*y + c*z - (k - (c / u) * (u * (z + delta_z*t))**(1 - tau_full))**(1 / (1 - tau_full))
                        #       + c * delta_z * (1 - t)
                        # dy' = 1999700.0 + 200150.0 - (658100.1250781124 - 1.3333333333333333 * (1.5 * (100075.0 + 100.0*0.25))**(0.9098566238736118))**(1.0990742648469305)
                        #       + 2 * 100.0 * 0.75
                        without_fee=213.68975529121235,
                        # fee = ((1 / p) - 1) * phi * c * d_z
                        # fee = (1.273811109181158 - 1) * 0.01 * 2 * 100.0
                        fee=0.13690555459057896,
                        with_fee=213.55284973662177,
                    ),
                ),
            ),
        ]

        # Test cases where token_out = TokenType.BASE indicating that bonds are being
        # sold for base.
        #
        # 1. in_ = 100; 1% fee; 100k share reserves; 100k bond reserves;
        #    1 share price; 1 init share price; t_stretch targeting 5% APY;
        #    6 mo remaining
        # 2. in_ = 100; 20% fee; 100k share reserves; 100k bond reserves;
        #    1 share price; 1 init share price; t_stretch targeting 5% APY;
        #    6 mo remaining
        # 3. in_ = 10k; 1% fee; 100k share reserves; 100k bond reserves;
        #    1 share price; 1 init share price; t_stretch targeting 5% APY;
        #    6 mo remaining
        # 4. in_ = 80k; 1% fee; 100k share reserves; 100k bond reserves;
        #    1 share price; 1 init share price; t_stretch targeting 5% APY;
        #    6 mo remaining
        # 5. in_ = 100; 1% fee; 100k share reserves; 100k bond reserves;
        #    2 share price; 1.5 init share price; t_stretch targeting 5% APY;
        #    6 mo remaining
        # 6. in_ = 100; 1% fee; 100k share reserves; 1M bond reserves;
        #    2 share price; 1.5 init share price; t_stretch targeting 5% APY;
        #    6 mo remaining
        # 7. in_ = 100; 1% fee; 100k share reserves; 1M bond reserves;
        #    2 share price; 1.5 init share price; t_stretch targeting 5% APY;
        #    3 mo remaining
        # 8. in_ = 100; 1% fee; 100k share reserves; 1M bond reserves;
        #    2 share price; 1.5 init share price; t_stretch targeting 10% APY;
        #    3 mo remaining
        base_out_test_cases = [
            # Low slippage trade - in_ is 0.1% of share reserves.
            (
                TestCaseCalcOutGivenInSuccess(
                    in_=Quantity(amount=100, unit=TokenType.PT),
                    market_state=MarketState(
                        share_reserves=100_000,
                        bond_reserves=100_000,
                        share_price=1,
                        init_share_price=1,
                    ),
                    fee_percent=0.01,
                    days_remaining=182.5,
                    time_stretch_apy=0.05,
                ),
                # From the input, we have the following values:
                #
                #   t_stretch = 22.1868770168519182502689135891
                #
                #   tau = d / (365 * t_stretch)
                #     = 182.5 / (365 * 22.1868770168519182502689135891)
                #     = 0.022535844031597044
                #
                #   1 - tau = 0.977464155968403
                #
                #   k = (c / mu) * (mu * z) **(1 - tau) + (2 * y + c * z)**(1 - tau)
                #     = 100000**0.9774641559684029528500691670222 + (2*100000 +
                #           100000*1)**0.9774641559684029528500691670222
                #     = 302929.51067963685
                #
                #   p = ((2 * y + c * z) / (mu * z)) ** tau
                #     = ((2 * 100_000 + 1 * 100_000) / (1 * 100_000)) ** 0.022535844031597044
                #     = 1.0250671833648672
                TestResultCalcOutGivenInSuccessByModel(
                    yieldspace=TestResultCalcOutGivenInSuccess(
                        # without_fee_or_slippage = (1 / p) * in_
                        #                         = (1 / 1.0250671833648672) * 100
                        #                         = 97.55458141947516
                        without_fee_or_slippage=97.55458141947516,
                        # We want to solve for the amount of shares out given the
                        # amount of bonds coming in, so we set up the problem as:
                        #
                        #   k = (c / mu) * (mu * (z - d_z')) ** (1 - tau) + (2 * y + c * z + d_y) ** (1 - tau)
                        #     = (100_000 - d_z') ** (1 - tau) + 300_100 ** (1 - tau)
                        #
                        # Solving for d_z, we get the following calculation:
                        #
                        #   d_z' = 100_000 - (k - 300_100 ** (1 - tau)) ** (1 / (1 - tau))
                        #       = 97.55314236719278
                        #
                        # The output is d_x' = c * d_z'. Since c = 1, d_x' = d_z'. Note
                        # that this is slightly smaller than the without slippage
                        # value.
                        without_fee=97.55314236719278,
                        # fee = 0.01 * (1 - (1 / p)) * 100 = 0.024454185805248493
                        fee=0.024454185805248493,
                        # with_fee = d_x' - fee
                        #          = 97.55314236719278 - 0.024454185805248493
                        #          = 97.52868818138752
                        with_fee=97.52868818138752,
                    ),
                    hyperdrive=TestResultCalcOutGivenInSuccess(
                        # spot_price = p * delta_y * t + delta_y * (1 - t)
                        # spot_price = 0.9516610350825238 * 100 * 0.5 + 100 * 0.5
                        without_fee_or_slippage=97.58305175412619,
                        # yield space equation (for hyperdrive multiply d_z by t):
                        # k = (c / mu) * (mu * (z + d_z))**(1 - tau) + (2y + cz - d_y')**(1 - tau)
                        # dy' = 2y + c*z - (k - (c / mu) * (mu * (z + d_z))**(1 - tau))**(1 / (1 - tau))
                        #
                        # note: use delta_z * t to phase the curve part out, and add delta_z * (1 - t)
                        # to phase the flat part in over the length of the term:
                        #
                        # dy' = 2*y + c*z - (k - (c / u) * (u * (z + delta_z*t))**(1 - tau_full))**(1 / (1 - tau_full))
                        #       + c * delta_z * (1 - t)
                        # dy' = 200100.0 + 99950.0 - (229441.04155954163 - 1.0 * (1 * (99950.0 + 100.0*0.5))**(0.9549283119368059))**(1.0471990279267966)
                        #       + 1 * 100.0 * 0.5
                        without_fee=97.58236250383197,
                        # fee = ((1 / p) - 1) * phi * c * d_z
                        # fee = (1.0507943092503356 - 1) * 0.01 * 1 * 100.0
                        fee=0.02416948245873818,
                        with_fee=97.55819302137324,
                    ),
                ),
            ),
            # High fee percentage - 20%.
            (
                TestCaseCalcOutGivenInSuccess(
                    in_=Quantity(amount=100, unit=TokenType.PT),
                    market_state=MarketState(
                        share_reserves=100_000,
                        bond_reserves=100_000,
                        share_price=1,
                        init_share_price=1,
                    ),
                    fee_percent=0.2,
                    days_remaining=182.5,
                    time_stretch_apy=0.05,
                ),
                # The trading constants are the same as the "Low slippage trade"
                # case. The only values that should change are `fee` and
                # `with_fee` since the fee percentage changed.
                TestResultCalcOutGivenInSuccessByModel(
                    yieldspace=TestResultCalcOutGivenInSuccess(
                        without_fee_or_slippage=97.55458141947516,
                        without_fee=97.55314236719278,
                        # fee = 0.2 * (1 - (1 / p)) * 100 = 0.48908371610497
                        fee=0.48908371610497,
                        # with_fee = d_x' - fee
                        #          = 97.55314236719278 - 0.48908371610497
                        #          = 97.0640586510878
                        with_fee=97.0640586510878,
                    ),
                    hyperdrive=TestResultCalcOutGivenInSuccess(
                        # spot_price = p * delta_y * t + delta_y * (1 - t)
                        # spot_price = 0.9516610350825238 * 100 * 0.5 + 100 * 0.5
                        without_fee_or_slippage=97.58305175412619,
                        # yield space equation (for hyperdrive multiply d_z by t):
                        # k = (c / mu) * (mu * (z + d_z))**(1 - tau) + (2y + cz - d_y')**(1 - tau)
                        # dy' = 2y + c*z - (k - (c / mu) * (mu * (z + d_z))**(1 - tau))**(1 / (1 - tau))
                        #
                        # note: use delta_z * t to phase the curve part out, and add delta_z * (1 - t)
                        # to phase the flat part in over the length of the term:
                        #
                        # dy' = 2*y + c*z - (k - (c / u) * (u * (z + delta_z*t))**(1 - tau_full))**(1 / (1 - tau_full))
                        #       + c * delta_z * (1 - t)
                        # dy' = 200100.0 + 99950.0 - (229441.04155954163 - 1.0 * (1 * (99950.0 + 100.0*0.5))**(0.9549283119368059))**(1.0471990279267966)
                        #       + 1 * 100.0 * 0.5
                        without_fee=97.58236250383197,
                        # fee = ((1 / p) - 1) * phi * c * d_z
                        # fee = (1.0507943092503356 - 1) * 0.2 * 1 * 100.0
                        fee=0.4833896491747636,
                        with_fee=97.0989728546572,
                    ),
                ),
            ),
            # Medium slippage trade - in_ is 10% of share reserves.
            (
                TestCaseCalcOutGivenInSuccess(
                    in_=Quantity(amount=10_000, unit=TokenType.PT),
                    market_state=MarketState(
                        share_reserves=100_000,
                        bond_reserves=100_000,
                        share_price=1,
                        init_share_price=1,
                    ),
                    fee_percent=0.01,
                    days_remaining=182.5,
                    time_stretch_apy=0.05,
                ),
                # The trading constants are the same as the "Low slippage trade"
                # case.
                TestResultCalcOutGivenInSuccessByModel(
                    yieldspace=TestResultCalcOutGivenInSuccess(
                        # without_fee_or_slippage = (1 / p) * in_
                        #                         = (1 / 1.0250671833648672) * 10_000
                        #                         = 9755.458141947514
                        without_fee_or_slippage=9755.458141947514,
                        # We want to solve for the amount of shares out given the
                        # amount of bonds coming in, so we set up the problem as:
                        #
                        #   k = (c / mu) * (mu * (z - d_z')) ** (1 - tau) + (2 * y + c * z + d_y) ** (1 - tau)
                        #     = (100_000 - d_z') ** (1 - tau) + 310_000 ** (1 - tau)
                        #
                        # Solving for d_z, we get the following calculation:
                        #
                        #   d_z' = 100_000 - (k - 310_000 ** (1 - tau)) ** (1 / (1 - tau))
                        #       = 9740.77011591768
                        #
                        # The output is d_x' = c * d_z'. Since c = 1, d_x' = d_z'. Note
                        # that this is slightly smaller than the without slippage
                        # value.
                        without_fee=9740.77011591768,
                        # fee = 0.01 * (1 - (1 / p)) * 10_000 = 2.4454185805248496
                        fee=2.4454185805248496,
                        # with_fee = d_x' - fee
                        #          = 9740.77011591768 - 2.4454185805248496
                        #          = 9738.324697337155
                        with_fee=9738.324697337155,
                    ),
                    hyperdrive=TestResultCalcOutGivenInSuccess(
                        # spot_price = p * delta_y * t + delta_y * (1 - t)
                        # spot_price = 0.9487848776296056 * 10000 * 0.5 + 10000 * 0.5
                        without_fee_or_slippage=9743.924388148029,
                        # yield space equation (for hyperdrive multiply d_z by t):
                        # k = (c / mu) * (mu * (z + d_z))**(1 - tau) + (2y + cz - d_y')**(1 - tau)
                        # dy' = 2y + c*z - (k - (c / mu) * (mu * (z + d_z))**(1 - tau))**(1 / (1 - tau))
                        #
                        # note: use delta_z * t to phase the curve part out, and add delta_z * (1 - t)
                        # to phase the flat part in over the length of the term:
                        #
                        # dy' = 2*y + c*z - (k - (c / u) * (u * (z + delta_z*t))**(1 - tau_full))**(1 / (1 - tau_full))
                        #       + c * delta_z * (1 - t)
                        # dy' = 210000.0 + 95000.0 - (229300.86075687787 - 1.0 * (1 * (95000.0 + 10000.0*0.5))**(0.9549283119368059))**(1.0471990279267966)
                        #       + 1 * 10000.0 * 0.5
                        without_fee=9736.764362542177,
                        # fee = ((1 / p) - 1) * phi * c * d_z
                        # fee = (1.0539796992742418 - 1) * 0.01 * 1 * 10000.0
                        fee=2.5607561185197247,
                        with_fee=9734.203606423658,
                    ),
                ),
            ),
            # High slippage trade - in_ is 80% of share reserves.
            (
                TestCaseCalcOutGivenInSuccess(
                    in_=Quantity(amount=80_000, unit=TokenType.PT),
                    market_state=MarketState(
                        share_reserves=100_000,
                        bond_reserves=100_000,
                        share_price=1,
                        init_share_price=1,
                    ),
                    fee_percent=0.01,
                    days_remaining=182.5,
                    time_stretch_apy=0.05,
                ),
                # The trading constants are the same as the "Low slippage trade"
                # case.
                TestResultCalcOutGivenInSuccessByModel(
                    yieldspace=TestResultCalcOutGivenInSuccess(
                        # without_fee_or_slippage = (1 / p) * in_
                        #                         = (1 / 1.0250671833648672) * 80_000
                        #                         = 78043.66513558012
                        without_fee_or_slippage=78043.66513558012,
                        # We want to solve for the amount of shares out given the
                        # amount of bonds coming in, so we set up the problem as:
                        #
                        #   k = (c / mu) * (mu * (z - d_z')) ** (1 - tau) + (2 * y + c * z + d_y) ** (1 - tau)
                        #     = (100_000 - d_z') ** (1 - tau) + 380_000 ** (1 - tau)
                        #
                        # Solving for d_z, we get the following calculation:
                        #
                        #   d_z' = 100_000 - (k - 380_000 ** (1 - tau)) ** (1 / (1 - tau))
                        #       = 76850.14470187116
                        #
                        # The output is d_x' = c * d_z'. Since c = 1, d_x' = d_z'. Note
                        # that this is slightly smaller than the without slippage
                        # value.
                        without_fee=76850.14470187116,
                        # fee = 0.01 * (1 - (1 / p)) * 80_000 = 19.563348644198797
                        fee=19.563348644198797,
                        # with_fee = d_x' - fee
                        #          = 76850.14470187116 - 19.563348644198797
                        #          = 76830.58135322697
                        with_fee=76830.58135322697,
                    ),
                    hyperdrive=TestResultCalcOutGivenInSuccess(
                        # spot_price = p * delta_y * t + delta_y * (1 - t)
                        # spot_price = 0.9247966553572445 * 80000 * 0.5 + 80000 * 0.5
                        without_fee_or_slippage=76991.86621428978,
                        # yield space equation (for hyperdrive multiply d_z by t):
                        # k = (c / mu) * (mu * (z + d_z))**(1 - tau) + (2y + cz - d_y')**(1 - tau)
                        # dy' = 2y + c*z - (k - (c / mu) * (mu * (z + d_z))**(1 - tau))**(1 / (1 - tau))
                        #
                        # note: use delta_z * t to phase the curve part out, and add delta_z * (1 - t)
                        # to phase the flat part in over the length of the term:
                        #
                        # dy' = 2*y + c*z - (k - (c / u) * (u * (z + delta_z*t))**(1 - tau_full))**(1 / (1 - tau_full))
                        #       + c * delta_z * (1 - t)
                        # dy' = 280000.0 + 60000.0 - (228040.6635311023 - 1.0 * (1 * (60000.0 + 80000.0*0.5))**(0.9549283119368059))**(1.0471990279267966)
                        #       + 1 * 80000.0 * 0.5
                        without_fee=76247.60327471803,
                        # fee = ((1 / p) - 1) * phi * c * d_z
                        # fee = (1.081318789603218 - 1) * 0.01 * 1 * 80000.0
                        fee=30.081337857102145,
                        with_fee=76217.52193686093,
                    ),
                ),
            ),
            # Non-trivial initial share price and share price.
            (
                TestCaseCalcOutGivenInSuccess(
                    in_=Quantity(amount=100, unit=TokenType.PT),
                    market_state=MarketState(
                        share_reserves=100_000,
                        bond_reserves=100_000,
                        share_price=2,
                        init_share_price=1.5,
                    ),
                    fee_percent=0.01,
                    days_remaining=182.5,
                    time_stretch_apy=0.05,
                ),
                # The trading constants for time are the same as the "Low
                # slippage trade" case.
                #
                # From the new values, we have:
                #
                #   k = (c / mu) * (mu * z) ** (1 - tau) + (2 * y + c * z) ** (1 - tau)
                #     = (2 / 1.5) * (1.5 * 100000) ** 0.977464155968403 + (2 * 100000 + 2 * 100000) ** 0.977464155968403
                #     = 451_988.7122137336
                #
                #   p = ((2 * y + c * z) / (mu * z)) ** tau
                #     = ((2 * 100_000 + 2 * 100_000) / (1.5 * 100_000)) ** 0.022535844031597044
                #     = 1.0223499142867662
                TestResultCalcOutGivenInSuccessByModel(
                    yieldspace=TestResultCalcOutGivenInSuccess(
                        # without_fee_or_slippage = (1 / p) * in_
                        #                         = (1 / 1.0223499142867662) * 100
                        #                         = 97.813868424652
                        without_fee_or_slippage=97.813868424652,
                        # We want to solve for the amount of shares out given the
                        # amount of bonds coming in, so we set up the problem as:
                        #
                        #   k = (c / mu) * (mu * (z - d_z')) ** (1 - tau) + (2 * y + c * z + d_y) ** (1 - tau)
                        #     = (2 / 1.5) * (1.5 * (100_000 - d_z')) ** (1 - tau) + 400_100 ** (1 - tau)
                        #
                        # Solving for d_z, we get the following calculation:
                        #
                        #   d_z' = 100_000 - (1 / 1.5) * ((1.5 / 2) * (k - 400_100 ** (1 - tau))) ** (1 / (1 - tau))
                        #       = 48.906526897713775
                        #
                        # The output is d_x' = c * d_z' = 2 * 48.906526897713775 = 97.81305379542755.
                        # Note that this is slightly smaller than the without slippage
                        # value.
                        without_fee=97.81305379542755,
                        # fee = 0.01 * (1 - (1 / p)) * 100 = 0.024454185805248493
                        fee=0.02186131575348005,
                        # with_fee = d_x' - fee
                        #          = 97.81305379542755 - 0.02186131575348005
                        #          = 97.79119247967407
                        with_fee=97.79119247967407,
                    ),
                    hyperdrive=TestResultCalcOutGivenInSuccess(
                        # spot_price = p * delta_y * t + delta_y * (1 - t)
                        # spot_price = 0.9567391137793314 * 100 * 0.5 + 100 * 0.5
                        without_fee_or_slippage=97.83695568896657,
                        # yield space equation (for hyperdrive multiply d_z by t):
                        # k = (c / mu) * (mu * (z + d_z))**(1 - tau) + (2y + cz - d_y')**(1 - tau)
                        # dy' = 2y + c*z - (k - (c / mu) * (mu * (z + d_z))**(1 - tau))**(1 / (1 - tau))
                        #
                        # note: use delta_z * t to phase the curve part out, and add delta_z * (1 - t)
                        # to phase the flat part in over the length of the term:
                        #
                        # dy' = 2*y + c*z - (k - (c / u) * (u * (z + delta_z*t))**(1 - tau_full))**(1 / (1 - tau_full))
                        #       + c * delta_z * (1 - t)
                        # dy' = 200100.0 + 199950.0 - (340525.6919141115 - 1.3333333333333333 * (1.5 * (99975.0 + 50.0*0.5))**(0.9549283119368059))**(1.0471990279267966)
                        #       + 2 * 50.0 * 0.5
                        without_fee=97.83656302187592,
                        # fee = ((1 / p) - 1) * phi * c * d_z
                        # fee = (1.0452170143329653 - 1) * 0.01 * 2 * 50.0
                        fee=0.021630443110334296,
                        with_fee=97.81493257876558,
                    ),
                ),
            ),
            # Very unbalanced reserves.
            (
                TestCaseCalcOutGivenInSuccess(
                    in_=Quantity(amount=100, unit=TokenType.PT),
                    market_state=MarketState(
                        share_reserves=100_000,
                        bond_reserves=1_000_000,
                        share_price=2,
                        init_share_price=1.5,
                    ),
                    fee_percent=0.01,
                    days_remaining=182.5,
                    time_stretch_apy=0.05,
                ),
                # The trading constants for time are the same as the "Low
                # slippage trade" case.
                #
                # From the new values, we have:
                #
                #   k = (c / mu) * (mu * z) **(1 - tau) + (2 * y + c * z)**(1 - tau)
                #     = (2 / 1.5) * (1.5 * 100_000) ** 0.977464155968403 + (2 * 100_000 +
                #           2 * 1_000_000) ** 0.977464155968403
                #     = 1735927.3223407117
                #
                #   p = ((2 * y + c * z) / (mu * z)) ** tau
                #     = ((2 * 1_000_000 + 2 * 100_000) / (1.5 * 100_000)) ** 0.022535844031597044
                #     = 1.062390706640675
                TestResultCalcOutGivenInSuccessByModel(
                    yieldspace=TestResultCalcOutGivenInSuccess(
                        # without_fee_or_slippage = (1 / p) * in_
                        #                         = (1 / 1.0623907066406753) * 100
                        #                         = 94.1273294042681
                        without_fee_or_slippage=94.1273294042681,
                        # We want to solve for the amount of shares out given the
                        # amount of bonds coming in, so we set up the problem as:
                        #
                        #   k = (c / mu) * (mu * (z - d_z')) ** (1 - tau) + (2 * y + c * z + d_y) ** (1 - tau)
                        #     = (2 / 1.5) * (1.5 * (100_000 - d_z')) ** (1 - tau) + 2_200_100 ** (1 - tau)
                        #
                        # Solving for d_z, we get the following calculation:
                        #
                        #   d_z' = 100_000 - (1 / 1.5) * ((1.5 / 2) * (k - 2_200_100 ** (1 - tau))) ** (1 / (1 - tau))
                        #       = 47.06339097737509
                        #
                        # The output is d_x' = c * d_z' = 2 * 47.06339097737509 = 94.12678195475019.
                        # Note that this is slightly smaller than the without slippage
                        # value.
                        without_fee=94.12678195475019,
                        # fee = 0.01 * (1 - (1 / p)) * 100 = 0.05872670595731877
                        fee=0.05872670595731899,
                        # with_fee = d_x' - fee
                        #          = 94.12678195475019 - 0.05872670595731899
                        #          = 94.06805524879287
                        with_fee=94.06805524879287,
                    ),
                    hyperdrive=TestResultCalcOutGivenInSuccess(
                        # spot_price = p * delta_y * t + delta_y * (1 - t)
                        # spot_price = 0.8859845220046657 * 100 * 0.5 + 100 * 0.5
                        without_fee_or_slippage=94.29922610023328,
                        # yield space equation (for hyperdrive multiply d_z by t):
                        # k = (c / mu) * (mu * (z + d_z))**(1 - tau) + (2y + cz - d_y')**(1 - tau)
                        # dy' = 2y + c*z - (k - (c / mu) * (mu * (z + d_z))**(1 - tau))**(1 / (1 - tau))
                        #
                        # note: use delta_z * t to phase the curve part out, and add delta_z * (1 - t)
                        # to phase the flat part in over the length of the term:
                        #
                        # dy' = 2*y + c*z - (k - (c / u) * (u * (z + delta_z*t))**(1 - tau_full))**(1 / (1 - tau_full))
                        #       + c * delta_z * (1 - t)
                        # dy' = 2000100.0 + 199950.0 - (1255967.849960625 - 1.3333333333333333 * (1.5 * (99975.0 + 50.0*0.5))**(0.9549283119368059))**(1.0471990279267966)
                        #       + 2 * 50.0 * 0.5
                        without_fee=94.29898221750045,
                        # fee = ((1 / p) - 1) * phi * c * d_z
                        # fee = (1.1286878891939987 - 1) * 0.01 * 2 * 50.0
                        fee=0.05700773899766715,
                        with_fee=94.24197447850278,
                    ),
                ),
            ),
            # A term of a quarter year.
            (
                TestCaseCalcOutGivenInSuccess(
                    in_=Quantity(amount=100, unit=TokenType.PT),
                    market_state=MarketState(
                        share_reserves=100_000,
                        bond_reserves=1_000_000,
                        share_price=2,
                        init_share_price=1.5,
                    ),
                    fee_percent=0.01,
                    days_remaining=91.25,
                    time_stretch_apy=0.05,
                ),
                # From the input, we have the following values:
                #
                #   t_stretch = 22.1868770168519182502689135891
                #
                #   tau = d / (365 * t_stretch)
                #     = 91.25 / (365 * 22.1868770168519182502689135891)
                #     = 0.011267922015798522
                #
                #   1 - tau = 0.9887320779842015
                #
                #   k = (c / mu) * (mu * z) **(1 - tau) + (2 * y + c * z)**(1 - tau)
                #     = (2 / 1.5) * (1.5 * 100_000) ** 0.9887320779842015 +
                #           (2 * 1_000_000 + 2 * 100_000) ** 0.9887320779842015
                #     = 2_041_060.1949973335
                #
                #   p = ((2 * y + c * z) / (mu * z)) ** tau
                #     = ((2 * 100_000 + 2 * 1_000_000) / (1.5 * 100_000)) ** 0.011267922015798522
                #     = 1.0307233899745727
                TestResultCalcOutGivenInSuccessByModel(
                    yieldspace=TestResultCalcOutGivenInSuccess(
                        # without_fee_or_slippage = (1 / p) * in_
                        #                         = (1 / 1.0307233899745727) * 100
                        #                         = 97.0192400528205
                        without_fee_or_slippage=97.0192400528205,
                        # We want to solve for the amount of shares out given the
                        # amount of bonds coming in, so we set up the problem as:
                        #
                        #   k = (c / mu) * (mu * (z - d_z')) ** (1 - tau) + (2 * y + c * z + d_y) ** (1 - tau)
                        #     = (2 / 1.5) * (1.5 * (100_000 - d_z')) ** (1 - tau) + 2_200_100 ** (1 - tau)
                        #
                        # Solving for d_z, we get the following calculation:
                        #
                        #   d_z' = 100_000 - (1 / 1.5) * ((1.5 / 2) * (k - 2_200_100 ** (1 - tau))) ** (1 / (1 - tau))
                        #       = 48.50947500564507
                        #
                        # The output is d_x' = c * d_z' = 2 * 48.50947500564507 = 97.01895001129014.
                        # Note that this is slightly smaller than the without slippage
                        # value.
                        without_fee=97.01895001129014,
                        # fee = 0.01 * (1 - (1 / p)) * 100 = 0.0298075994717949
                        fee=0.0298075994717949,
                        # with_fee = d_x' - fee
                        #          = 97.01895001129014 - 0.0298075994717949
                        #          = 96.98914241181835
                        with_fee=96.98914241181835,
                    ),
                    hyperdrive=TestResultCalcOutGivenInSuccess(
                        # spot_price = p * delta_y * t + delta_y * (1 - t)
                        # spot_price = 0.8859790750896572 * 100 * 0.25 + 100 * 0.75
                        without_fee_or_slippage=97.14947687724143,
                        # yield space equation (for hyperdrive multiply d_z by t):
                        # k = (c / mu) * (mu * (z + d_z))**(1 - tau) + (2y + cz - d_y')**(1 - tau)
                        # dy' = 2y + c*z - (k - (c / mu) * (mu * (z + d_z))**(1 - tau))**(1 / (1 - tau))
                        #
                        # note: use delta_z * t to phase the curve part out, and add delta_z * (1 - t)
                        # to phase the flat part in over the length of the term:
                        #
                        # dy' = 2*y + c*z - (k - (c / u) * (u * (z + delta_z*t))**(1 - tau_full))**(1 / (1 - tau_full))
                        #       + c * delta_z * (1 - t)
                        # dy' = 2000150.0 + 199925.0 - (1255966.2592326764 - 1.3333333333333333 * (1.5 * (99962.5 + 50.0*0.25))**(0.9549283119368059))**(1.0471990279267966)
                        #       + 2 * 50.0 * 0.75
                        without_fee=97.14941590232775,
                        # fee = ((1 / p) - 1) * phi * c * d_z
                        # fee = (1.1286948282596905 - 1) * 0.01 * 2 * 50.0
                        fee=0.028505231227585665,
                        with_fee=97.12091067110016,
                    ),
                ),
            ),
            # A time stretch targetting 10% APY.
            (
                TestCaseCalcOutGivenInSuccess(
                    in_=Quantity(amount=100, unit=TokenType.PT),
                    market_state=MarketState(
                        share_reserves=100_000,
                        bond_reserves=1_000_000,
                        share_price=2,
                        init_share_price=1.5,
                    ),
                    fee_percent=0.01,
                    days_remaining=91.25,
                    time_stretch_apy=0.10,
                ),
                # From the input, we have the following values:
                #
                #   t_stretch = 11.093438508425956
                #
                #   tau = d / (365 * t_stretch)
                #     = 91.25 / (365 * 11.093438508425956)
                #     = 0.022535844031597054
                #
                #   1 - tau = 0.977464155968403
                #
                #   k = (c / mu) * (mu * z) **(1 - tau) + (2 * y + c * z)**(1 - tau)
                #     = (2 / 1.5) * (1.5 * 100_000) ** 0.977464155968403 +
                #           (2 * 1_000_000 + 2 * 100_000) ** 0.977464155968403
                #     = 1_735_927.3223407117
                #
                #   p = ((2 * y + c * z) / (mu * z)) ** tau
                #     = ((2 * 100_000 + 2 * 1_000_000) / (1.5 * 100_000)) ** 0.022535844031597054
                #     = 1.0623907066406753
                TestResultCalcOutGivenInSuccessByModel(
                    yieldspace=TestResultCalcOutGivenInSuccess(
                        # without_fee_or_slippage = (1 / p) * in_
                        #                         = (1 / 1.0623907066406753) * 100
                        #                         = 94.1273294042681
                        without_fee_or_slippage=94.1273294042681,
                        # We want to solve for the amount of shares out given the
                        # amount of bonds coming in, so we set up the problem as:
                        #
                        #   k = (c / mu) * (mu * (z - d_z')) ** (1 - tau) + (2 * y + c * z + d_y) ** (1 - tau)
                        #     = (2 / 1.5) * (1.5 * (100_000 - d_z)) ** (1 - tau) + 2_200_100 ** (1 - tau)
                        #
                        # Solving for d_z, we get the following calculation:
                        #
                        #   d_z' = 100_000 - (1 / 1.5) * ((1.5 / 2) * (k - 2_200_100 ** (1 - tau))) ** (1 / (1 - tau))
                        #       = 47.06339097737509
                        #
                        # The output is d_x' = c * d_z' = 2 * 47.06339097737509 = 94.12678195475019.
                        # Note that this is slightly smaller than the without slippage
                        # value.
                        without_fee=94.12678195475019,
                        # fee = 0.01 * (1 - (1 / p)) * 100 = 0.05872670595731899
                        fee=0.05872670595731899,
                        # with_fee = d_x' - fee
                        #          = 94.12678195475019 - 0.05872670595731899
                        #          = 94.06805524879287
                        with_fee=94.06805524879287,
                    ),
                    hyperdrive=TestResultCalcOutGivenInSuccess(
                        # spot_price = p * delta_y * t + delta_y * (1 - t)
                        # spot_price = 0.7849589214967245 * 100 * 0.25 + 100 * 0.75
                        without_fee_or_slippage=94.62397303741811,
                        # yield space equation (for hyperdrive multiply d_z by t):
                        # k = (c / mu) * (mu * (z + d_z))**(1 - tau) + (2y + cz - d_y')**(1 - tau)
                        # dy' = 2y + c*z - (k - (c / mu) * (mu * (z + d_z))**(1 - tau))**(1 / (1 - tau))
                        #
                        # note: use delta_z * t to phase the curve part out, and add delta_z * (1 - t)
                        # to phase the flat part in over the length of the term:
                        #
                        # dy' = 2*y + c*z - (k - (c / u) * (u * (z + delta_z*t))**(1 - tau_full))**(1 / (1 - tau_full))
                        #       + c * delta_z * (1 - t)
                        # dy' = 2000150.0 + 199925.0 - (658085.0939516554 - 1.3333333333333333 * (1.5 * (99962.5 + 50.0*0.25))**(0.9098566238736118))**(1.0990742648469305)
                        #       + 2 * 50.0 * 0.75
                        without_fee=94.62387616650085,
                        # fee = ((1 / p) - 1) * phi * c * d_z
                        # fee = (1.273952015340172 - 1) * 0.01 * 2 * 50.0
                        fee=0.05376026962581887,
                        with_fee=94.57011589687504,
                    ),
                ),
            ),
        ]

        # Iterate over all of the test cases and verify that the pricing model
        # produces the expected outputs for each test case.
        test_cases = pt_out_test_cases + base_out_test_cases

        for (
            test_number,
            (
                test_case,
                results_by_model,
            ),
        ) in enumerate(test_cases):
            for pricing_model in pricing_models:
                model_name = pricing_model.model_name()
                model_type = pricing_model.model_type()
                if model_type == "yieldspace":
                    break
                time_stretch = pricing_model.calc_time_stretch(test_case.time_stretch_apy)

                expected_result = results_by_model[model_type]

                # Ensure we get the expected results from the pricing model.
                trade_result = pricing_model.calc_out_given_in(
                    in_=test_case.in_,
                    market_state=test_case.market_state,
                    fee_percent=test_case.fee_percent,
                    time_remaining=StretchedTime(days=test_case.days_remaining, time_stretch=time_stretch),
                )
                np.testing.assert_almost_equal(
                    trade_result.breakdown.without_fee_or_slippage,
                    expected_result.without_fee_or_slippage,
                    err_msg=f"test {test_number + 1} unexpected without_fee_or_slippage",
                )
                np.testing.assert_almost_equal(
                    trade_result.breakdown.without_fee,
                    expected_result.without_fee,
                    err_msg=f"test {test_number + 1} unexpected without_fee",
                )
                model_name = pricing_model.model_name()
                if model_type in {"yieldspace", "hyperdrive"}:
                    np.testing.assert_almost_equal(
                        trade_result.breakdown.fee,
                        expected_result.fee,
                        err_msg=f"test {test_number + 1} unexpected fee",
                    )
                    np.testing.assert_almost_equal(
                        trade_result.breakdown.with_fee,
                        expected_result.with_fee,
                        err_msg=f"test {test_number + 1} unexpected with_fee",
                    )
                else:
                    raise AssertionError(f'Expected model_name to be "YieldSpace", not {model_name}')

    def test_calc_out_given_in_precision(self):
        """
        This test ensures that the pricing model can handle very extreme inputs
        such as extremely small inputs with extremely large reserves.
        """
        pricing_models: list[PricingModel] = [YieldSpacePricingModel(), HyperdrivePricingModel()]

        for pricing_model in pricing_models:
            for trade_amount in [1 / 10**x for x in range(0, 19)]:
                # in is in base, out is in bonds
                trade_quantity = Quantity(amount=trade_amount, unit=TokenType.BASE)
                market_state = MarketState(
                    share_reserves=1,
                    bond_reserves=20_000_000_000,
                    share_price=1,
                    init_share_price=1,
                )
                fee_percent = 0.1
                time_remaining = StretchedTime(days=365, time_stretch=pricing_model.calc_time_stretch(0.05))
                trade_result = pricing_model.calc_out_given_in(
                    in_=trade_quantity,
                    market_state=market_state,
                    fee_percent=fee_percent,
                    time_remaining=time_remaining,
                )
                self.assertGreater(trade_result.breakdown.with_fee, 0.0)

                # in is in bonds, out is in base
                trade_quantity = Quantity(amount=trade_amount, unit=TokenType.PT)
                market_state = MarketState(
                    share_reserves=10_000_000_000,
                    bond_reserves=1,
                    share_price=2,
                    init_share_price=1.2,
                )
                fee_percent = 0.1
                time_remaining = StretchedTime(days=365, time_stretch=pricing_model.calc_time_stretch(0.05))
                trade_result = pricing_model.calc_out_given_in(
                    in_=trade_quantity,
                    market_state=market_state,
                    fee_percent=fee_percent,
                    time_remaining=time_remaining,
                )
                self.assertGreater(trade_result.breakdown.with_fee, 0.0)

    # TODO: This should be refactored to be a test for check_input_assertions and check_output_assertions
    def test_calc_out_given_in_failure(self):
        """Failure tests for calc_out_given_in"""
        pricing_models: list[PricingModel] = [YieldSpacePricingModel(), HyperdrivePricingModel()]

        # Failure test cases.
        test_cases = [
            TestCaseCalcOutGivenInFailure(
                # amount negative
                in_=Quantity(amount=-1, unit=TokenType.PT),
                market_state=MarketState(
                    share_reserves=100_000,
                    bond_reserves=1_000_000,
                    share_price=1,
                    init_share_price=1,
                ),
                fee_percent=0.01,
                time_remaining=StretchedTime(days=91.25, time_stretch=1),
                exception_type=AssertionError,
            ),
            # amount 0
            TestCaseCalcOutGivenInFailure(
                in_=Quantity(amount=0, unit=TokenType.PT),
                market_state=MarketState(
                    share_reserves=100_000,
                    bond_reserves=1_000_000,
                    share_price=1,
                    init_share_price=1,
                ),
                fee_percent=0.01,
                time_remaining=StretchedTime(days=91.25, time_stretch=1),
                exception_type=AssertionError,
            ),
            TestCaseCalcOutGivenInFailure(
                in_=Quantity(amount=100, unit=TokenType.PT),
                market_state=MarketState(
                    # share reserves negative
                    share_reserves=-1,
                    bond_reserves=1_000_000,
                    share_price=1,
                    init_share_price=1,
                ),
                fee_percent=0.01,
                time_remaining=StretchedTime(days=91.25, time_stretch=1),
                exception_type=AssertionError,
            ),
            TestCaseCalcOutGivenInFailure(
                in_=Quantity(amount=100, unit=TokenType.PT),
                market_state=MarketState(
                    share_reserves=100_000,
                    # bond reserves negative
                    bond_reserves=-1,
                    share_price=1,
                    init_share_price=1,
                ),
                fee_percent=0.01,
                time_remaining=StretchedTime(days=91.25, time_stretch=1),
                exception_type=AssertionError,
            ),
            TestCaseCalcOutGivenInFailure(
                in_=Quantity(amount=100, unit=TokenType.PT),
                market_state=MarketState(
                    share_reserves=100_000,
                    bond_reserves=1_000_000,
                    share_price=1,
                    init_share_price=1,
                ),
                # fee negative
                fee_percent=-1,
                time_remaining=StretchedTime(days=91.25, time_stretch=1),
                exception_type=AssertionError,
            ),
            TestCaseCalcOutGivenInFailure(
                in_=Quantity(amount=100, unit=TokenType.PT),
                market_state=MarketState(
                    share_reserves=100_000,
                    bond_reserves=1_000_000,
                    share_price=1,
                    init_share_price=1,
                ),
                # fee above 1
                fee_percent=1.1,
                time_remaining=StretchedTime(days=91.25, time_stretch=1),
                exception_type=AssertionError,
            ),
            TestCaseCalcOutGivenInFailure(
                in_=Quantity(amount=100, unit=TokenType.PT),
                market_state=MarketState(
                    share_reserves=100_000,
                    bond_reserves=1_000_000,
                    share_price=1,
                    init_share_price=1,
                ),
                fee_percent=0.01,
                # days remaining negative
                time_remaining=StretchedTime(days=-91.25, time_stretch=1),
                exception_type=AssertionError,
            ),
            TestCaseCalcOutGivenInFailure(
                in_=Quantity(amount=100, unit=TokenType.PT),
                market_state=MarketState(
                    share_reserves=100_000,
                    bond_reserves=1_000_000,
                    share_price=1,
                    init_share_price=1,
                ),
                fee_percent=0.01,
                # days remaining == 365, will get divide by zero error
                time_remaining=StretchedTime(days=365, time_stretch=1),
                exception_type=AssertionError,
            ),
            TestCaseCalcOutGivenInFailure(
                in_=Quantity(amount=100, unit=TokenType.PT),
                market_state=MarketState(
                    share_reserves=100_000,
                    bond_reserves=1_000_000,
                    share_price=1,
                    init_share_price=1,
                ),
                fee_percent=0.01,
                # days remaining > 365
                time_remaining=StretchedTime(days=500, time_stretch=1),
                exception_type=AssertionError,
            ),
            TestCaseCalcOutGivenInFailure(
                # amount very high, can't make trade
                in_=Quantity(amount=10_000_000, unit=TokenType.PT),
                market_state=MarketState(
                    share_reserves=100_000,
                    bond_reserves=1_000_000,
                    share_price=1,
                    init_share_price=1,
                ),
                fee_percent=0.01,
                time_remaining=StretchedTime(days=91.25, time_stretch=1),
                exception_type=(AssertionError, decimal.InvalidOperation),
            ),
            TestCaseCalcOutGivenInFailure(
                in_=Quantity(amount=100, unit=TokenType.PT),
                market_state=MarketState(
                    share_reserves=100_000,
                    bond_reserves=1_000_000,
                    share_price=2,
                    # init_share_price 0
                    init_share_price=0,
                ),
                fee_percent=0.01,
                time_remaining=StretchedTime(days=91.25, time_stretch=1),
                exception_type=AssertionError,
            ),
            TestCaseCalcOutGivenInFailure(
                in_=Quantity(amount=100, unit=TokenType.PT),
                market_state=MarketState(
                    share_reserves=100_000,
                    bond_reserves=1_000_000,
                    # share_price < init_share_price
                    share_price=1,
                    init_share_price=1.5,
                ),
                fee_percent=0.01,
                time_remaining=StretchedTime(days=91.25, time_stretch=1),
                exception_type=AssertionError,
            ),
            TestCaseCalcOutGivenInFailure(
                in_=Quantity(amount=100, unit=TokenType.PT),
                market_state=MarketState(
                    share_reserves=100_000,
                    bond_reserves=1_000_000,
                    # share_price 0
                    share_price=0,
                    init_share_price=1.5,
                ),
                fee_percent=0.01,
                time_remaining=StretchedTime(days=91.25, time_stretch=1),
                exception_type=AssertionError,
            ),
            TestCaseCalcOutGivenInFailure(
                # amount < 1 wei
                in_=Quantity(amount=0.5e-18, unit=TokenType.PT),
                market_state=MarketState(
                    share_reserves=100_000,
                    bond_reserves=1_000_000,
                    share_price=1,
                    init_share_price=1,
                ),
                fee_percent=0.01,
                time_remaining=StretchedTime(days=91.25, time_stretch=1),
                exception_type=AssertionError,
            ),
            TestCaseCalcOutGivenInFailure(
                in_=Quantity(amount=100, unit=TokenType.PT),
                market_state=MarketState(
                    # share_reserves < 1 wei
                    share_reserves=0.5e-18,
                    bond_reserves=1_000_000,
                    share_price=1,
                    init_share_price=1,
                ),
                fee_percent=0.01,
                time_remaining=StretchedTime(days=91.25, time_stretch=1),
                exception_type=AssertionError,
            ),
            TestCaseCalcOutGivenInFailure(
                in_=Quantity(amount=100, unit=TokenType.PT),
                market_state=MarketState(
                    share_reserves=100_000,
                    # bond reserves < 1 wei
                    bond_reserves=0.5e-18,
                    share_price=1,
                    init_share_price=1,
                ),
                fee_percent=0.01,
                time_remaining=StretchedTime(days=91.25, time_stretch=1),
                exception_type=AssertionError,
            ),
            TestCaseCalcOutGivenInFailure(
                in_=Quantity(amount=100, unit=TokenType.PT),
                market_state=MarketState(
                    # reserves waaaay unbalanced
                    share_reserves=30_000_000_000,
                    bond_reserves=1,
                    share_price=1,
                    init_share_price=1,
                ),
                fee_percent=0.01,
                time_remaining=StretchedTime(days=91.25, time_stretch=1),
                exception_type=AssertionError,
            ),
        ]

        # Verify that the pricing model raises the expected exception type for
        # each test case.
        for test_case in test_cases:
            for pricing_model in pricing_models:
                with self.assertRaises(test_case.exception_type):
                    pricing_model.check_input_assertions(
                        quantity=test_case.in_,
                        market_state=test_case.market_state,
                        fee_percent=test_case.fee_percent,
                        time_remaining=test_case.time_remaining,
                    )
                    trade_result = pricing_model.calc_out_given_in(
                        in_=test_case.in_,
                        market_state=test_case.market_state,
                        fee_percent=test_case.fee_percent,
                        time_remaining=test_case.time_remaining,
                    )
                    pricing_model.check_output_assertions(trade_result=trade_result)

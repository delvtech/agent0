"""
Testing for the calc_in_given_out of the pricing models.
"""

# pylint: disable=too-many-lines
# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-locals
# pylint: disable=attribute-defined-outside-init
# pylint: disable=duplicate-code

from typing import Optional

from dataclasses import dataclass
import unittest
import numpy as np

from elfpy.utils import time as time_utils
from elfpy.pricing_models.base import PricingModel
from elfpy.pricing_models.element import ElementPricingModel
from elfpy.pricing_models.yieldspace import YieldSpacePricingModel


@dataclass
class TestCaseCalcInGivenOutSuccess:
    """Dataclass for calc_in_given_out test cases"""

    out: float
    share_reserves: float
    bond_reserves: float
    token_in: str
    fee_percent: float
    days_remaining: float
    time_stretch_apy: float
    share_price: float
    init_share_price: float

    __test__ = False  # pytest: don't test this class


@dataclass
class TestResultCalcInGivenOutSuccess:
    """Dataclass for calc_in_given_out test results"""

    without_fee_or_slippage: float
    without_fee: float
    element_fee: Optional[float]
    element_with_fee: Optional[float]
    hyperdrive_fee: float
    hyperdrive_with_fee: float

    __test__ = False  # pytest: don't test this class


@dataclass
class TestCaseCalcInGivenOutFailure:
    """Dataclass for calc_in_given_out test cases"""

    out: float
    share_reserves: float
    bond_reserves: float
    token_in: str
    fee_percent: float
    time_remaining: float
    share_price: float
    init_share_price: float

    __test__ = False  # pytest: don't test this class


class TestCalcInGivenOut(unittest.TestCase):
    """Unit tests for the calc_in_given_out function"""

    # pylint: disable=line-too-long

    def test_calc_in_given_out_success(self):
        """Success tests for calc_in_given_out"""
        pricing_models = [ElementPricingModel(), YieldSpacePricingModel()]

        # Test cases where token_in = "base" indicating that bonds are being
        # purchased for base.
        #
        # 1. in_ = 100; 10% fee; 100k share reserves; 100k bond reserves;
        #    1 share price; 1 init share price; t_stretch targeting 5% APY;
        #    6 mo remaining
        # 2. in_ = 100; 20% fee; 100k share reserves; 100k bond reserves;
        #    1 share price; 1 init share price; t_stretch targeting 5% APY;
        #    6 mo remaining
        # 3. in_ = 10k; 10% fee; 100k share reserves; 100k bond reserves;
        #    1 share price; 1 init share price; t_stretch targeting 5% APY;
        #    6 mo remaining
        # 4. in_ = 80k; 10% fee; 100k share reserves; 100k bond reserves;
        #    1 share price; 1 init share price; t_stretch targeting 5% APY;
        #    6 mo remaining
        # 5. in_ = 200; 10% fee; 100k share reserves; 100k bond reserves;
        #    2 share price; 1.5 init share price; t_stretch targeting 5% APY;
        #    6 mo remaining
        # 6. in_ = 200; 10% fee; 100k share reserves; 1M bond reserves;
        #    2 share price; 1.5 init share price; t_stretch targeting 5% APY;
        #    6 mo remaining
        # 7. in_ = 200; 10% fee; 100k share reserves; 1M bond reserves;
        #    2 share price; 1.5 init share price; t_stretch targeting 5% APY;
        #    3 mo remaining
        # 8. in_ = 200; 10% fee; 100k share reserves; 1M bond reserves;
        #    2 share price; 1.5 init share price; t_stretch targeting 10% APY;
        #    3 mo remaining
        base_in_test_cases = [
            (  ## test one, basic starting point
                TestCaseCalcInGivenOutSuccess(
                    out=100,  # how many tokens you expect to get
                    share_reserves=100_000,  # base reserves (in share terms) base = share * share_price
                    bond_reserves=100_000,  # PT reserves
                    token_in="base",  # what token you're putting in
                    fee_percent=0.1,  # fee percent (normally 10%)
                    days_remaining=182.5,  # 6 months remaining
                    time_stretch_apy=0.05,  # APY of 5% used to calculate time_stretch
                    share_price=1,  # share price of the LP in the yield source
                    init_share_price=1,  # original share price pool started
                ),
                # From the input, we have the following values:
                # T = 22.1868770168519182502689135891
                # t = 0.0225358440315970471499308329778
                # 1 - t = 0.977464155968402952850069167022
                # k = c/u*(u*z)**(1-t) + (2*y + c*z)**(1-t)
                #   = 100000**0.9774641559684029528500691670222 + (2*100000 + 100000*1)**0.9774641559684029528500691670222
                #   = 302929.51067963685
                (
                    TestResultCalcInGivenOutSuccess(
                        # p = ((2y+cz)/uz)**t
                        #   = 1.0250671833648672
                        # without_fee_or_slippage = 1/p * out = 97.55458141947516
                        without_fee_or_slippage=97.55458141947516,
                        # d_z' = 1/u * (u/c*(k - (2*y + c*z - d_y)**(1-t)))**(1/(1-t)) - z
                        # d_z' = 1/1 * (1/1*(302929.51067963685 - (2*100000 + 100000 - 100)**(1-0.0225358440315970471499308329778)))**(1/(1-0.0225358440315970471499308329778)) - 100000
                        #         = 97.55601990513969
                        without_fee=97.55601990513969,
                        # element_fee = 0.1 * (out - d_z')
                        #     = 0.1 * (100 - 97.55601990513969)
                        #     = 0.2443980094860308
                        element_fee=0.2443980094860308,
                        # element_with_fee = d_z' + element_fee
                        #                  = 97.55601990513969 + 0.2443980094860308
                        element_with_fee=97.80041791462573,
                        # fee is 10% of discount before slippage = (100-97.55458141947516)*0.1 = 0.24454185805248443
                        hyperdrive_fee=0.24454185805248443,
                        # with_fee = d_z' + fee = 97.55601990513969 + 0.24454185805248443 = 97.80056176319217
                        hyperdrive_with_fee=97.80056176319218,
                    )
                ),
            ),  # end of test one
            (  ## test two, double the fee
                TestCaseCalcInGivenOutSuccess(
                    out=100,  # how many tokens you expect to get
                    share_reserves=100_000,  # base reserves (in share terms) base = share * share_price
                    bond_reserves=100_000,  # PT reserves
                    token_in="base",  # what token you're putting in
                    fee_percent=0.2,  # fee percent (normally 10%)
                    days_remaining=182.5,  # 6 months remaining
                    time_stretch_apy=0.05,  # APY of 5% used to calculate time_stretch
                    share_price=1,  # share price of the LP in the yield source
                    init_share_price=1,  # original share price pool started
                ),
                # From the input, we have the following values:
                # T = 22.1868770168519182502689135891
                # t = 0.0225358440315970471499308329778
                # 1 - t = 0.977464155968402952850069167022
                # k = c/u*(u*z)**(1-t) + (2*y + c*z)**(1-t)
                #   = 100000**0.9774641559684029528500691670222 + (2*100000 + 100000*1)**0.9774641559684029528500691670222
                #   = 302929.51067963685
                (
                    TestResultCalcInGivenOutSuccess(
                        # p = ((2y+cz)/uz)**t
                        #   = 1.0250671833648672
                        # without_fee_or_slippage = 1/p * out = 97.55458141947516
                        without_fee_or_slippage=97.55458141947516,
                        # d_z' = 1/u * (u/c*(k - (2*y + c*z - d_y)**(1-t)))**(1/(1-t)) - z
                        # d_z' = 1/1 * (1/1*(302929.51067963685 - (2*100000 + 100000 - 100)**(1-0.0225358440315970471499308329778)))**(1/(1-0.0225358440315970471499308329778)) - 100000
                        #         = 97.55601990513969
                        without_fee=97.55601990513969,
                        # element_fee = 0.2 * (out - d_z')
                        #     = 0.2 * (100 - 97.55601990513969)
                        #     = 0.4887960189720616
                        element_fee=0.4887960189720616,
                        # element_with_fee = d_z' + element_fee
                        #                  = 97.55601990513969 + 0.4887960189720616
                        element_with_fee=98.04481592411176,
                        # fee is 20% of discount before slippage = (100-97.55458141947516)*0.2 = 0.48908371610496887
                        hyperdrive_fee=0.48908371610496887,
                        # with_fee = d_z' + fee = 97.55601990513969 + 0.4887960189720616 = 98.04481592411175
                        hyperdrive_with_fee=98.04510362124466,
                    )
                ),
            ),  # end of test two
            (  ## test three, 10k out
                TestCaseCalcInGivenOutSuccess(
                    out=10_000,  # how many tokens you expect to get
                    share_reserves=100_000,  # base reserves (in share terms) base = share * share_price
                    bond_reserves=100_000,  # PT reserves
                    token_in="base",  # what token you're putting in
                    fee_percent=0.1,  # fee percent (normally 10%)
                    days_remaining=182.5,  # 6 months remaining
                    time_stretch_apy=0.05,  # APY of 5% used to calculate time_stretch
                    share_price=1,  # share price of the LP in the yield source
                    init_share_price=1,  # original share price pool started
                ),
                # From the input, we have the following values:
                # T = 22.1868770168519182502689135891
                # t = 0.0225358440315970471499308329778
                # 1 - t = 0.977464155968402952850069167022
                # k = c/u*(u*z)**(1-t) + (2*y + c*z)**(1-t)
                #   = 100000**0.9774641559684029528500691670222 + (2*100000 + 100000*1)**0.9774641559684029528500691670222
                #   = 302929.51067963685
                (
                    TestResultCalcInGivenOutSuccess(
                        # p = ((2y+cz)/uz)**t
                        #   = 1.0250671833648672
                        # without_fee_or_slippage = 1/p * out = 97.55458141947516
                        without_fee_or_slippage=9755.458141947514,
                        # d_z' = 1/u * (u/c*(k - (2*y + c*z - d_y)**(1-t)))**(1/(1-t)) - z
                        # d_z' = 1/1 * (1/1*(302929.51067963685 - (2*100000 + 100000 - 10000)**(1-0.0225358440315970471499308329778)))**(1/(1-0.0225358440315970471499308329778)) - 100000
                        #         = 9769.577831379836
                        without_fee=9769.577831379836,
                        # element_fee = 0.1 * (out - d_z')
                        #     = 0.1 * (10000 - 9769.577831379836)
                        #     = 23.04221686201636
                        element_fee=23.04221686201636,
                        # element_with_fee = d_z' + element_fee
                        #                  = 9769.577831379836 + 23.04221686201636
                        #                  = 9792.620048241854
                        element_with_fee=9792.620048241854,
                        # fee is 10% of discount before slippage = (10000-9755.458141947514)*0.1 = 24.454185805248564
                        hyperdrive_fee=24.454185805248564,
                        # with_fee = d_z' + fee = 9769.577831379836 +  24.454185805248564 = 97.80056176319217
                        hyperdrive_with_fee=9794.032017185085,
                    )
                ),
            ),  # end of test three
            (  ## test four, 80k out
                TestCaseCalcInGivenOutSuccess(
                    out=80_000,  # how many tokens you expect to get
                    share_reserves=100_000,  # base reserves (in share terms) base = share * share_price
                    bond_reserves=100_000,  # PT reserves
                    token_in="base",  # what token you're putting in
                    fee_percent=0.1,  # fee percent (normally 10%)
                    days_remaining=182.5,  # 6 months remaining
                    time_stretch_apy=0.05,  # APY of 5% used to calculate time_stretch
                    share_price=1,  # share price of the LP in the yield source
                    init_share_price=1,  # original share price pool started
                ),
                # From the input, we have the following values:
                # T = 22.1868770168519182502689135891
                # t = 0.0225358440315970471499308329778
                # 1 - t = 0.977464155968402952850069167022
                # k = c/u*(u*z)**(1-t) + (2*y + c*z)**(1-t)
                #   = 100000**0.9774641559684029528500691670222 + (2*100000 + 100000*1)**0.9774641559684029528500691670222
                #   = 302929.51067963685
                (
                    TestResultCalcInGivenOutSuccess(
                        # p = ((2y+cz)/uz)**t
                        #   = 1.0250671833648672
                        # without_fee_or_slippage = 1/p * out = 97.55458141947516
                        without_fee_or_slippage=78043.66513558012,
                        # d_z' = 1/u * (u/c*(k - (2*y + c*z - d_y)**(1-t)))**(1/(1-t)) - z
                        # d_z' = 1/1 * (1/1*(302929.51067963685 - (2*100000 + 100000 - 80000)**(1-0.0225358440315970471499308329778)))**(1/(1-0.0225358440315970471499308329778)) - 100000
                        #         = 78866.87433323538
                        without_fee=78866.87433323538,
                        # element_fee = 0.1 * (out - d_z')
                        #     = 0.1 * (80000 - 78866.87433323538)
                        #     = 113.31256667646231
                        element_fee=113.31256667646231,
                        # element_with_fee = d_z' + element_fee
                        #                  = 78866.87433323538 + 113.31256667646231
                        #                  = 78980.18689991185
                        element_with_fee=78980.18689991185,
                        # fee is 10% of discount before slippage = (80000-78043.66513558012)*0.1 = 195.6334864419885
                        hyperdrive_fee=195.6334864419885,
                        # with_fee = d_z' + fee = 78866.87433323538 +  195.6334864419885 = 79062.50781967737
                        hyperdrive_with_fee=79062.50781967737,
                    )
                ),
            ),  # end of test four
            (  ## test five, change share price
                TestCaseCalcInGivenOutSuccess(
                    out=200,  # how many tokens you expect to get
                    share_reserves=100_000,  # base reserves (in share terms) base = share * share_price
                    bond_reserves=100_000,  # PT reserves
                    token_in="base",  # what token you're putting in
                    fee_percent=0.1,  # fee percent (normally 10%)
                    days_remaining=182.5,  # 6 months remaining
                    time_stretch_apy=0.05,  # APY of 5% used to calculate time_stretch
                    share_price=2,  # share price of the LP in the yield source
                    init_share_price=1.5,  # original share price pool started
                ),
                # From the input, we have the following values:
                # T = 22.1868770168519182502689135891
                # t = 0.0225358440315970471499308329778
                # 1 - t = 0.977464155968402952850069167022
                # k = c/u*(u*z)**(1-t) + (2*y + c*z)**(1-t)
                #   = 2/1.5*((1.5*100000)**0.9774641559684029528500691670222) + (2*100000 + 2*100000)**0.9774641559684029528500691670222
                #   = 451988.7122137336
                (
                    TestResultCalcInGivenOutSuccess(
                        # p = ((2y+cz)/uz)**t
                        #   = ((2*100000 + 2*100000)/(1.5*100000))**0.0225358440315970471499308329778
                        #   = 1.0223499142867662
                        # without_fee_or_slippage = 1/p * out = 195.627736849304
                        without_fee_or_slippage=195.627736849304,
                        # d_z = 1/u * (u/c*(k - (2*y + c*z - d_y)**(1-t)))**(1/(1-t)) - z
                        # d_z = 2*(1/1.5 * (1.5/2*(451988.7122137336 - (2*100000 + 2*100000 - 200)**(1-0.0225358440315970471499308329778)))**(1/(1-0.0225358440315970471499308329778)) - 100000)
                        #        = 195.63099467812572
                        without_fee=195.63099467812572,
                        element_fee=None,
                        element_with_fee=None,
                        # fee is 10% of discount before slippage = (200-195.627736849304)*0.1 = 0.4372263150696
                        hyperdrive_fee=0.4372263150696,
                        # with_fee = without_fee + fee = 195.63099467812572 + 0.4372263150696 = 196.06822099319533
                        hyperdrive_with_fee=196.06822099319533,
                    )
                ),
            ),  # end of test five
            (  ## test six, up bond reserves to 1,000,000
                TestCaseCalcInGivenOutSuccess(
                    out=200,  # how many tokens you expect to get
                    share_reserves=100_000,  # base reserves (in share terms) base = share * share_price
                    bond_reserves=1_000_000,  # PT reserves
                    token_in="base",  # what token you're putting in
                    fee_percent=0.1,  # fee percent (normally 10%)
                    days_remaining=182.5,  # 6 months remaining
                    time_stretch_apy=0.05,  # APY of 5% used to calculate time_stretch
                    share_price=2,  # share price of the LP in the yield source
                    init_share_price=1.5,  # original share price pool started
                ),
                # From the input, we have the following values:
                # T = 22.1868770168519182502689135891
                # t = 0.0225358440315970471499308329778
                # 1 - t = 0.977464155968402952850069167022
                # k = c/u*(u*z)**(1-t) + (2*y + c*z)**(1-t)
                #   = 2/1.5*((1.5*100000)**0.9774641559684029528500691670222) + (2*1000000 + 2*100000)**0.9774641559684029528500691670222
                #   = 1735927.3223407117
                (
                    TestResultCalcInGivenOutSuccess(
                        # p = ((2y+cz)/uz)**t
                        #   = ((2*1000000 + 2*100000)/(1.5*100000))**0.0225358440315970471499308329778
                        #   = 1.062390706640675
                        # without_fee_or_slippage = 1/p * out = 188.25465880853625
                        without_fee_or_slippage=188.25465880853625,
                        # d_z' = 1/u * (u/c*(k - (2*y + c*z - d_y)**(1-t)))**(1/(1-t)) - z
                        # d_z' = 2*(1/1.5 * (1.5/2*(1735927.3223407117 - (2*1000000 + 2*100000 - 200)**(1-0.0225358440315970471499308329778)))**(1/(1-0.0225358440315970471499308329778)) - 100000)
                        #         = 188.2568477257446
                        without_fee=188.2568477257446,
                        element_fee=None,
                        element_with_fee=None,
                        # fee is 10% of discount before slippage = (200-188.25465880853625)*0.1 = 1.1745341191463752
                        hyperdrive_fee=1.1745341191463752,
                        # with_fee = d_z' + fee = 188.2568477257446 +  1.1745341191463752 = 189.43138184489098
                        hyperdrive_with_fee=189.43138184489098,
                    )
                ),
            ),  # end of test six
            (  ## test seven, halve the days remaining
                TestCaseCalcInGivenOutSuccess(
                    out=200,  # how many tokens you expect to get
                    share_reserves=100_000,  # base reserves (in share terms) base = share * share_price
                    bond_reserves=1_000_000,  # PT reserves
                    token_in="base",  # what token you're putting in
                    fee_percent=0.1,  # fee percent (normally 10%)
                    days_remaining=91.25,  # 3 months remaining
                    time_stretch_apy=0.05,  # APY of 5% used to calculate time_stretch
                    share_price=2,  # share price of the LP in the yield source
                    init_share_price=1.5,  # original share price pool started
                ),
                # From the input, we have the following values:
                # T = 22.1868770168519182502689135891
                # t = 91.25/365/22.1868770168519182502689135891 = 0.011267922015798524
                # 1 - t = 0.9887320779842015
                # k = c/u*(u*z)**(1-t) + (2*y + c*z)**(1-t)
                #   = 2/1.5*((1.5*100000)**0.9887320779842015) + (2*1000000 + 2*100000)**0.9887320779842015
                #   = 2041060.1949973335
                (
                    TestResultCalcInGivenOutSuccess(
                        # p = ((2y+cz)/uz)**t
                        #   = ((2*1000000 + 2*100000)/(1.5*100000))**0.011267922015798524
                        #   = 1.0307233899745727
                        # without_fee_or_slippage = 1/p * out = 194.038480105641
                        without_fee_or_slippage=194.038480105641,
                        # d_z' = 1/u * (u/c*(k - (2*y + c*z - d_y)**(1-t)))**(1/(1-t)) - z
                        # d_z' = 2*(1/1.5 * (1.5/2*(2041060.1949973335 - (2*1000000 + 2*100000 - 200)**(1-0.011267922015798524)))**(1/(1-0.011267922015798524)) - 100000)
                        #         = 194.0396397759323
                        without_fee=194.0396397759323,
                        element_fee=None,
                        element_with_fee=None,
                        # fee is 10% of discount before slippage = (200-194.038480105641)*0.1 = 0.5961519894358986
                        hyperdrive_fee=0.5961519894358986,
                        # with_fee = d_z' + fee = 194.0396397759323 + 0.5961519894358986 = 194.6357917653682
                        hyperdrive_with_fee=194.6357917653682,
                    )
                ),
            ),  # end of test seven
            (  ## test eight, halve the APY
                TestCaseCalcInGivenOutSuccess(
                    out=200,  # how many tokens you expect to get
                    share_reserves=100_000,  # base reserves (in share terms) base = share * share_price
                    bond_reserves=1_000_000,  # PT reserves
                    token_in="base",  # what token you're putting in
                    fee_percent=0.1,  # fee percent (normally 10%)
                    days_remaining=91.25,  # 3 months remaining
                    time_stretch_apy=0.025,  # APY of 5% used to calculate time_stretch
                    share_price=2,  # share price of the LP in the yield source
                    init_share_price=1.5,  # original share price pool started
                ),
                # From the input, we have the following values:
                # T = 3.09396 / 0.02789 / 2.5 = 44.37375403370383
                # t = 91.25/365/44.37375403370383 = 0.005633961007899263
                # 1 - t = 0.9943660389921007
                # k = c/u*(u*z)**(1-t) + (2*y + c*z)**(1-t)
                #   = 2/1.5*((1.5*100000)**0.9943660389921007) + (2*1000000 + 2*100000)**0.9943660389921007
                #   = 2213245.968723062
                (
                    TestResultCalcInGivenOutSuccess(
                        # p = ((2y+cz)/uz)**t
                        #   = ((2*1000000 + 2*100000)/(1.5*100000))**0.005633961007899263
                        #   = 1.015245482617171
                        # without_fee_or_slippage = 1/p * out = 196.99669038115388
                        without_fee_or_slippage=196.99669038115388,
                        # d_z' = 1/u * (u/c*(k - (2*y + c*z - d_y)**(1-t)))**(1/(1-t)) - z
                        # d_z' = 2*(1/1.5 * (1.5/2*(2213245.968723062 - (2*1000000 + 2*100000 - 200)**(1-0.005633961007899263)))**(1/(1-0.005633961007899263)) - 100000)
                        #         = 196.9972872567596
                        without_fee=196.9972872567596,
                        element_fee=None,
                        element_with_fee=None,
                        # fee is 10% of discount before slippage = (200-196.99669038115388)*0.1 = 0.3003309618846117
                        hyperdrive_fee=0.3003309618846117,
                        # with_fee = d_z' + fee = 196.9972872567596 + 0.3003309618846117 = 197.2976182186442
                        hyperdrive_with_fee=197.2976182186442,
                    )
                ),
            ),  # end of test eight
        ]
        pt_in_test_cases = [
            (  ## test one, basic starting point
                TestCaseCalcInGivenOutSuccess(
                    out=100,  # how many tokens you expect to get
                    share_reserves=100_000,  # base reserves (in share terms) base = share * share_price
                    bond_reserves=100_000,  # PT reserves
                    token_in="pt",  # what token you're putting in
                    fee_percent=0.1,  # fee percent (normally 10%)
                    days_remaining=182.5,  # 6 months remaining
                    time_stretch_apy=0.05,  # APY of 5% used to calculate time_stretch
                    share_price=1,  # share price of the LP in the yield source
                    init_share_price=1,  # original share price pool started
                ),
                # From the input, we have the following values:
                # T = 22.1868770168519182502689135891
                # t = 0.0225358440315970471499308329778
                # 1 - t = 0.977464155968402952850069167022
                # k = c/u*(u*z)**(1-t) + (2*y + c*z)**(1-t)
                #   = 100000**0.9774641559684029528500691670222 + (2*100000 + 100000*1)**0.9774641559684029528500691670222
                #   = 302929.51067963685
                (
                    TestResultCalcInGivenOutSuccess(
                        # p = ((2y+cz)/uz)**t
                        #   = 1.0250671833648672
                        # without_fee_or_slippage = p * out = 102.50671833648673
                        without_fee_or_slippage=102.50671833648673,
                        # d_y' = (k - c/u*(u*z - u*d_z)**(1-t))**(1/(1-t)) - y
                        #         = (302929.51067963685 - 1/1*(1*100000 - 1*100)**0.977464155968402952850069167022)**(1/0.977464155968402952850069167022) - (2*100_000 + 1*100_000)
                        #         = 102.50826839753427
                        without_fee=102.50826839753427,
                        # element_fee = 0.1 * (out - d_z')
                        #     = 0.1 * (102.50826839753427 - 100)
                        #     = 0.2508268397534266
                        element_fee=0.2508268397534266,
                        # element_with_fee = d_z' + element_fee
                        #                  = 102.50826839753427 + 0.2508268397534266
                        #                  = 102.7590952372877
                        element_with_fee=102.7590952372877,
                        # fee is 10% of discount before slippage = (102.50671833648673-100)*0.1 = 0.2506718336486728
                        hyperdrive_fee=0.2506718336486728,
                        # with_fee = d_y' + fee = 102.50826839753427 + 0.2506718336486728 = 102.75894023118293
                        hyperdrive_with_fee=102.75894023118293,
                    )
                ),
            ),  # end of test one
            (  ## test two, double the fee
                TestCaseCalcInGivenOutSuccess(
                    out=100,  # how many tokens you expect to get
                    share_reserves=100_000,  # base reserves (in share terms) base = share * share_price
                    bond_reserves=100_000,  # PT reserves
                    token_in="pt",  # what token you're putting in
                    fee_percent=0.2,  # fee percent (normally 10%)
                    days_remaining=182.5,  # 6 months remaining
                    time_stretch_apy=0.05,  # APY of 5% used to calculate time_stretch
                    share_price=1,  # share price of the LP in the yield source
                    init_share_price=1,  # original share price pool started
                ),
                # From the input, we have the following values:
                # T = 22.1868770168519182502689135891
                # t = 0.0225358440315970471499308329778
                # 1 - t = 0.977464155968402952850069167022
                # k = c/u*(u*z)**(1-t) + (2*y + c*z)**(1-t)
                #   = 100000**0.9774641559684029528500691670222 + (2*100000 + 100000*1)**0.9774641559684029528500691670222
                #   = 302929.51067963685
                (
                    TestResultCalcInGivenOutSuccess(
                        # p = ((2y+cz)/uz)**t
                        #   = 1.0250671833648672
                        # without_fee_or_slippage = p * out = 102.50671833648673
                        without_fee_or_slippage=102.50671833648673,
                        # d_y' = (k - c/u*(u*z - u*d_z)**(1-t))**(1/(1-t)) - y
                        #         = (302929.51067963685 - 1/1*(1*100000 - 1*100)**0.977464155968402952850069167022)**(1/0.977464155968402952850069167022) - (2*100_000 + 1*100_000)
                        #         = 102.50826839753427
                        without_fee=102.50826839753427,
                        # element_fee = 0.2 * (out - d_z')
                        #     = 0.2 * (102.50826839753427 - 100)
                        #     = 0.5016536795068532
                        element_fee=0.5016536795068532,
                        # element_with_fee = d_z' + element_fee
                        #                  = 102.50826839753427 + 0.5016536795068532
                        #                  = 103.00992207704113
                        element_with_fee=103.00992207704113,
                        # fee is 20% of discount before slippage = (102.50671833648673-100)*0.2 = 0.5013436672973456
                        hyperdrive_fee=0.5013436672973456,
                        # with_fee = d_y' + fee = 102.50826839753427 + 0.5013436672973456 = 103.00961206483161
                        hyperdrive_with_fee=103.00961206483161,
                    )
                ),
            ),  # end of test two
            (  ## test three, 10k out
                TestCaseCalcInGivenOutSuccess(
                    out=10_000,  # how many tokens you expect to get
                    share_reserves=100_000,  # base reserves (in share terms) base = share * share_price
                    bond_reserves=100_000,  # PT reserves
                    token_in="pt",  # what token you're putting in
                    fee_percent=0.1,  # fee percent (normally 10%)
                    days_remaining=182.5,  # 6 months remaining
                    time_stretch_apy=0.05,  # APY of 5% used to calculate time_stretch
                    share_price=1,  # share price of the LP in the yield source
                    init_share_price=1,  # original share price pool started
                ),
                # From the input, we have the following values:
                # T = 22.1868770168519182502689135891
                # t = 0.0225358440315970471499308329778
                # 1 - t = 0.977464155968402952850069167022
                # k = c/u*(u*z)**(1-t) + (2*y + c*z)**(1-t)
                #   = 100000**0.9774641559684029528500691670222 + (2*100000 + 100000*1)**0.9774641559684029528500691670222
                #   = 302929.51067963685
                (
                    TestResultCalcInGivenOutSuccess(
                        # p = ((2y+cz)/uz)**t
                        #   = 1.0250671833648672
                        # without_fee_or_slippage = p * out = 10250.671833648673
                        without_fee_or_slippage=10250.671833648673,
                        # d_y' = (k - c/u*(u*z - u*d_z)**(1-t))**(1/(1-t)) - y
                        #         = (302929.51067963685 - 1/1*(1*100000 - 1*10000)**0.977464155968402952850069167022)**(1/0.977464155968402952850069167022) - (2*100_000 + 1*100_000)
                        #         = 10266.550575620378
                        without_fee=10266.550575620378,
                        # element_fee = 0.1 * (out - d_z')
                        #     = 0.1 * (10266.550575620378 - 10000)
                        #     = 26.65505756203784
                        element_fee=26.65505756203784,
                        # element_with_fee = d_z' + element_fee
                        #                  = 10266.550575620378 + 26.65505756203784
                        #                  = 10293.205633182417
                        element_with_fee=10293.205633182417,
                        # fee is 10% of discount before slippage = (10250.671833648673-10000)*0.1 = 25.06718336486738
                        hyperdrive_fee=25.06718336486738,
                        # with_fee = d_y' + fee = 10266.550575620378 + 25.06718336486738 = 10291.617758985245
                        hyperdrive_with_fee=10291.617758985245,
                    )
                ),
            ),  # end of test three
            (  ## test four, 80k out
                TestCaseCalcInGivenOutSuccess(
                    out=80_000,  # how many tokens you expect to get
                    share_reserves=100_000,  # base reserves (in share terms) base = share * share_price
                    bond_reserves=100_000,  # PT reserves
                    token_in="pt",  # what token you're putting in
                    fee_percent=0.1,  # fee percent (normally 10%)
                    days_remaining=182.5,  # 6 months remaining
                    time_stretch_apy=0.05,  # APY of 5% used to calculate time_stretch
                    share_price=1,  # share price of the LP in the yield source
                    init_share_price=1,  # original share price pool started
                ),
                # From the input, we have the following values:
                # T = 22.1868770168519182502689135891
                # t = 0.0225358440315970471499308329778
                # 1 - t = 0.977464155968402952850069167022
                # k = c/u*(u*z)**(1-t) + (2*y + c*z)**(1-t)
                #   = 100000**0.9774641559684029528500691670222 + (2*100000 + 100000*1)**0.9774641559684029528500691670222
                #   = 302929.51067963685
                (
                    TestResultCalcInGivenOutSuccess(
                        # p = ((2y+cz)/uz)**t
                        #   = 1.0250671833648672
                        # without_fee_or_slippage = p * out = 82005.37466918938
                        without_fee_or_slippage=82005.37466918938,
                        # d_y' = (k - c/u*(u*z - u*d_z)**(1-t))**(1/(1-t)) - y
                        #         = (302929.51067963685 - 1/1*(1*100000 - 1*80000)**0.977464155968402952850069167022)**(1/0.977464155968402952850069167022) - (2*100_000 + 1*100_000)
                        #         = 83360.61360923108
                        without_fee=83360.61360923108,
                        # element_fee = 0.1 * (out - d_z')
                        #     = 0.1 * (83360.61360923108 - 80000)
                        #     = 336.0613609231077
                        element_fee=336.0613609231077,
                        # element_with_fee = d_z' + element_fee
                        #                  = 83360.61360923108 + 336.0613609231077
                        #                  = 83696.67497015418
                        element_with_fee=83696.67497015418,
                        # fee is 10% of discount before slippage = (82005.37466918938-80000)*0.1 = 200.53746691893758
                        hyperdrive_fee=200.53746691893758,
                        # with_fee = d_y' + fee = 83360.61360923108 + 200.53746691893758 = 83561.15107615001
                        hyperdrive_with_fee=83561.15107615001,
                    )
                ),
            ),  # end of test four
            (  ## test five, change share price
                TestCaseCalcInGivenOutSuccess(
                    out=200,  # how many tokens you expect to get
                    share_reserves=100_000,  # base reserves (in share terms) base = share * share_price
                    bond_reserves=100_000,  # PT reserves
                    token_in="pt",  # what token you're putting in
                    fee_percent=0.1,  # fee percent (normally 10%)
                    days_remaining=182.5,  # 6 months remaining
                    time_stretch_apy=0.05,  # APY of 5% used to calculate time_stretch
                    share_price=2,  # share price of the LP in the yield source
                    init_share_price=1.5,  # original share price pool started
                ),
                # From the input, we have the following values:
                # T = 22.1868770168519182502689135891
                # t = 0.0225358440315970471499308329778
                # 1 - t = 0.977464155968402952850069167022
                # k = c/u*(u*z)**(1-t) + (2*y + c*z)**(1-t)
                #   = 2/1.5*(1.5*100000)**0.9774641559684029528500691670222 + (2*100000 + 2*100000)**0.9774641559684029528500691670222
                #   = 451988.7122137336
                (
                    TestResultCalcInGivenOutSuccess(
                        # p = ((2y+cz)/uz)**t
                        #   = ((2*100000 + 2*100000)/(1.5*100000))**0.0225358440315970471499308329778
                        #   = 1.0223499142867662
                        # without_fee_or_slippage = p * out = 204.46998285735324
                        without_fee_or_slippage=204.46998285735324,
                        # d_y' = (k - c/u*(u*z - u*d_z)**(1-t))**(1/(1-t)) - y
                        #         = (451988.7122137336 - 2/1.5*(1.5*100000 - 1.5*100)**0.977464155968402952850069167022)**(1/0.977464155968402952850069167022) - (2*100_000 + 2*100_000)
                        #         = 204.4734651519102
                        without_fee=204.4734651519102,
                        element_fee=None,
                        element_with_fee=None,
                        # fee is 10% of discount before slippage = (204.46998285735324-200)*0.1 = 0.44699828573532446
                        hyperdrive_fee=0.44699828573532446,
                        # with_fee = d_z' + fee = 204.4734651519102 + 0.44699828573532446 = 204.92046343764554
                        hyperdrive_with_fee=204.92046343764554,
                    )
                ),
            ),  # end of test five
            (  ## test six, up bond reserves to 1,000,000
                TestCaseCalcInGivenOutSuccess(
                    out=200,  # how many tokens you expect to get
                    share_reserves=100_000,  # base reserves (in share terms) base = share * share_price
                    bond_reserves=1_000_000,  # PT reserves
                    token_in="pt",  # what token you're putting in
                    fee_percent=0.1,  # fee percent (normally 10%)
                    days_remaining=182.5,  # 6 months remaining
                    time_stretch_apy=0.05,  # APY of 5% used to calculate time_stretch
                    share_price=2,  # share price of the LP in the yield source
                    init_share_price=1.5,  # original share price pool started
                ),
                # From the input, we have the following values:
                # T = 22.1868770168519182502689135891
                # t = 0.0225358440315970471499308329778
                # 1 - t = 0.977464155968402952850069167022
                # k = c/u*(u*z)**(1-t) + (2*y + c*z)**(1-t)
                #   = 2/1.5*(1.5*100000)**0.9774641559684029528500691670222 + (2*1000000 + 2*100000)**0.9774641559684029528500691670222
                #   = 1735927.3223407117
                (
                    TestResultCalcInGivenOutSuccess(
                        # p = ((2y+cz)/uz)**t
                        #   = ((2*1000000 + 2*100000)/(1.5*100000))**0.0225358440315970471499308329778
                        #   = 1.062390706640675
                        # without_fee_or_slippage = p * out = 212.478141328135
                        without_fee_or_slippage=212.478141328135,
                        # d_y' = (k - c/u*(u*z - u*d_z)**(1-t))**(1/(1-t)) - y
                        #         = (1735927.3223407117 - 2/1.5*(1.5*100000 - 1.5*100)**0.977464155968402952850069167022)**(1/0.977464155968402952850069167022) - (2*100_0000 + 2*100_000)
                        #         = 212.48076756019145
                        without_fee=212.48076756019145,
                        element_fee=None,
                        element_with_fee=None,
                        # fee is 10% of discount before slippage = (212.478141328135-200)*0.1 = 1.2478141328134997
                        hyperdrive_fee=1.2478141328134997,
                        # with_fee = d_z' + fee = 212.48076756019145 + 1.2478141328134997 = 213.72858169300494
                        hyperdrive_with_fee=213.72858169300494,
                    )
                ),
            ),  # end of test six
            (  ## test seven, halve the days remaining
                TestCaseCalcInGivenOutSuccess(
                    out=200,  # how many tokens you expect to get
                    share_reserves=100_000,  # base reserves (in share terms) base = share * share_price
                    bond_reserves=1_000_000,  # PT reserves
                    token_in="pt",  # what token you're putting in
                    fee_percent=0.1,  # fee percent (normally 10%)
                    days_remaining=91.25,  # 3 months remaining
                    time_stretch_apy=0.05,  # APY of 5% used to calculate time_stretch
                    share_price=2,  # share price of the LP in the yield source
                    init_share_price=1.5,  # original share price pool started
                ),
                # From the input, we have the following values:
                # T = 22.1868770168519182502689135891
                # t = 91.25/365/22.1868770168519182502689135891 = 0.011267922015798524
                # 1 - t = 0.9887320779842015
                # k = c/u*(u*z)**(1-t) + (2*y + c*z)**(1-t)
                #   = 2/1.5*(1.5*100000)**0.9887320779842015 + (2*1000000 + 2*100000)**0.9887320779842015
                #   = 2041060.1949973335
                (
                    TestResultCalcInGivenOutSuccess(
                        # p = ((2y+cz)/uz)**t
                        #   = ((2*1000000 + 2*100000)/(1.5*100000))**0.011267922015798524
                        #   = 1.0307233899745727
                        # without_fee_or_slippage = p * out = 202.22264109508274
                        without_fee_or_slippage=206.14467799491453,
                        # d_y' = (k - c/u*(u*z - u*d_z)**(1-t))**(1/(1-t)) - y
                        #         = (2041060.1949973335 - 2/1.5*(1.5*100000 - 1.5*100)**0.9887320779842015)**(1/0.9887320779842015) - (2*100_0000 + 2*100_000)
                        #         = 206.1459486191161
                        without_fee=206.1459486191161,
                        element_fee=None,
                        element_with_fee=None,
                        # fee is 10% of discount before slippage = (206.14467799491453-200)*0.1 = 0.6144677994914531
                        hyperdrive_fee=0.6144677994914531,
                        # with_fee = d_z' + fee = 206.1459486191161 + 0.6144677994914531 = 206.76041641860755
                        hyperdrive_with_fee=206.76041641860755,
                    )
                ),
            ),  # end of test seven
            (  ## test eight, halve the APY
                TestCaseCalcInGivenOutSuccess(
                    out=200,  # how many tokens you expect to get
                    share_reserves=100_000,  # base reserves (in share terms) base = share * share_price
                    bond_reserves=1_000_000,  # PT reserves
                    token_in="pt",  # what token you're putting in
                    fee_percent=0.1,  # fee percent (normally 10%)
                    days_remaining=91.25,  # 3 months remaining
                    time_stretch_apy=0.025,  # APY of 5% used to calculate time_stretch
                    share_price=2,  # share price of the LP in the yield source
                    init_share_price=1.5,  # original share price pool started
                ),
                # From the input, we have the following values:
                # T = 3.09396 / 0.02789 / 2.5 = 44.37375403370383
                # t = 91.25/365/44.37375403370383 = 0.005633961007899263
                # 1 - t = 0.9943660389921007
                # k = c/u*(u*z)**(1-t) + (2*y + c*z)**(1-t)
                #   = 2/1.5*(1.5*100000)**0.9943660389921007 + (2*1000000 + 2*100000)**0.9943660389921007
                #   = 2213245.968723062
                (
                    TestResultCalcInGivenOutSuccess(
                        # p = ((2y+cz)/uz)**t
                        #   = ((2*1000000 + 2*100000)/(1.5*100000))**0.005633961007899263
                        #   = 1.015245482617171
                        # without_fee_or_slippage = p * out = 203.0490965234342
                        without_fee_or_slippage=203.0490965234342,
                        # d_y' = (k - c/u*(u*z - u*d_z)**(1-t))**(1/(1-t)) - y
                        #         = (2213245.968723062 - 2/1.5*(1.5*100000 - 1.5*100)**0.9943660389921007)**(1/0.9943660389921007) - (2*100_0000 + 2*100_000)
                        #         = 203.04972148826346
                        without_fee=203.04972148826346,
                        element_fee=None,
                        element_with_fee=None,
                        # fee is 10% of discount before slippage = (203.0490965234342-200)*0.1 = 0.30490965234342016
                        hyperdrive_fee=0.30490965234342016,
                        # with_fee = d_z' + fee = 203.04972148826346 + 0.30490965234342016 = 203.35463114060687
                        hyperdrive_with_fee=203.35463114060687,
                    )
                ),
            ),  # end of test eight
        ]
        test_cases = base_in_test_cases + pt_in_test_cases
        # test_cases = [pt_in_test_cases[6]]
        for (
            test_case,
            expected_result,
        ) in test_cases:
            for pricing_model in pricing_models:
                model_name = pricing_model.model_name()
                if model_name == "Element" and (
                    expected_result.element_fee is None or expected_result.element_with_fee is None
                ):
                    continue
                time_stretch = pricing_model.calc_time_stretch(test_case.time_stretch_apy)
                time_remaining = time_utils.stretch_time(
                    time_utils.days_to_time_remaining(test_case.days_remaining), time_stretch
                )

                # Ensure we get the expected results from the pricing model.
                (without_fee_or_slippage, with_fee, without_fee, fee) = pricing_model.calc_in_given_out(
                    test_case.out,
                    test_case.share_reserves,
                    test_case.bond_reserves,
                    test_case.token_in,
                    test_case.fee_percent,
                    time_remaining,
                    test_case.init_share_price,
                    test_case.share_price,
                )
                np.testing.assert_almost_equal(
                    without_fee_or_slippage,
                    expected_result.without_fee_or_slippage,
                    err_msg="unexpected without_fee_or_slippage",
                )
                np.testing.assert_almost_equal(
                    without_fee,
                    expected_result.without_fee,
                    err_msg="unexpected without_fee",
                )
                if (
                    model_name == "Element"
                    and not expected_result.element_fee is None
                    and not expected_result.element_with_fee is None
                ):
                    np.testing.assert_almost_equal(
                        expected_result.element_fee,
                        fee,
                        err_msg="unexpected element fee",
                    )
                    np.testing.assert_almost_equal(
                        expected_result.element_with_fee,
                        with_fee,
                        err_msg="unexpected element with_fee",
                    )
                elif model_name == "YieldSpace":
                    np.testing.assert_almost_equal(
                        expected_result.hyperdrive_fee,
                        fee,
                        err_msg="unexpected hyperdrive fee",
                    )
                    np.testing.assert_almost_equal(
                        expected_result.hyperdrive_with_fee,
                        with_fee,
                        err_msg="unexpected hyperdrive with_fee",
                    )
                else:
                    raise AssertionError(f'Expected model_name to be "Element" or "YieldSpace", not {model_name}')

    def test_calc_in_given_out_failure(self):
        """Failure tests for calc_in_given_out"""
        pricing_models: list[PricingModel] = [ElementPricingModel(), YieldSpacePricingModel()]

        # Failure test cases.
        test_cases = [
            TestCaseCalcInGivenOutFailure(
                out=-1,
                share_reserves=100_000,
                bond_reserves=1_000_000,
                token_in="base",
                fee_percent=0.01,
                time_remaining=0.25,
                share_price=1,
                init_share_price=1,
            ),
            TestCaseCalcInGivenOutFailure(
                out=0,
                share_reserves=100_000,
                bond_reserves=1_000_000,
                token_in="base",
                fee_percent=0.01,
                time_remaining=0.25,
                share_price=1,
                init_share_price=1,
            ),
            TestCaseCalcInGivenOutFailure(
                out=100,
                share_reserves=-1,
                bond_reserves=1_000_000,
                token_in="base",
                fee_percent=0.01,
                time_remaining=0.25,
                share_price=1,
                init_share_price=1,
            ),
            TestCaseCalcInGivenOutFailure(
                out=100,
                share_reserves=0,
                bond_reserves=1_000_000,
                token_in="base",
                fee_percent=0.01,
                time_remaining=0.25,
                share_price=1,
                init_share_price=1,
            ),
            TestCaseCalcInGivenOutFailure(
                out=100,
                share_reserves=100_000,
                bond_reserves=-1,
                token_in="base",
                fee_percent=0.01,
                time_remaining=0.25,
                share_price=1,
                init_share_price=1,
            ),
            TestCaseCalcInGivenOutFailure(
                out=100,
                share_reserves=100_000,
                bond_reserves=1_000_000,
                token_in="base",
                fee_percent=-1,
                time_remaining=0.25,
                share_price=1,
                init_share_price=1,
            ),
            TestCaseCalcInGivenOutFailure(
                out=100,
                share_reserves=100_000,
                bond_reserves=1_000_000,
                token_in="base",
                fee_percent=1.1,
                time_remaining=0.25,
                share_price=1,
                init_share_price=1,
            ),
            TestCaseCalcInGivenOutFailure(
                out=100,
                share_reserves=100_000,
                bond_reserves=1_000_000,
                token_in="base",
                fee_percent=0.01,
                time_remaining=-1,
                share_price=1,
                init_share_price=1,
            ),
            TestCaseCalcInGivenOutFailure(
                out=100,
                share_reserves=100_000,
                bond_reserves=1_000_000,
                token_in="base",
                fee_percent=0.01,
                time_remaining=1,
                share_price=1,
                init_share_price=1,
            ),
            TestCaseCalcInGivenOutFailure(
                out=100,
                share_reserves=100_000,
                bond_reserves=1_000_000,
                token_in="base",
                fee_percent=0.01,
                time_remaining=1.1,
                share_price=1,
                init_share_price=1,
            ),
            TestCaseCalcInGivenOutFailure(
                out=100,
                share_reserves=100_000,
                bond_reserves=1_000_000,
                token_in="fyt",
                fee_percent=0.01,
                time_remaining=0.25,
                share_price=1,
                init_share_price=1,
            ),
            TestCaseCalcInGivenOutFailure(
                out=10_000_000,
                share_reserves=100_000,
                bond_reserves=1_000_000,
                token_in="pt",
                fee_percent=0.01,
                time_remaining=0.25,
                share_price=1,
                init_share_price=1,
            ),
            TestCaseCalcInGivenOutFailure(
                out=100,
                share_reserves=100_000,
                bond_reserves=1_000_000,
                token_in="base",
                fee_percent=0.01,
                time_remaining=0.25,
                share_price=2,
                init_share_price=0,
            ),
            TestCaseCalcInGivenOutFailure(
                out=100,
                share_reserves=100_000,
                bond_reserves=1_000_000,
                token_in="base",
                fee_percent=0.01,
                time_remaining=0.25,
                share_price=1,
                init_share_price=1.5,
            ),
            TestCaseCalcInGivenOutFailure(
                out=100,
                share_reserves=100_000,
                bond_reserves=1_000_000,
                token_in="base",
                fee_percent=0.01,
                time_remaining=0.25,
                share_price=0,
                init_share_price=1.5,
            ),
        ]

        # Iterate over all of the test cases and verify that the pricing model
        # raises an AssertionError for each test case.
        for test_case in test_cases:
            for pricing_model in pricing_models:
                with self.assertRaises(AssertionError):
                    pricing_model.calc_in_given_out(
                        out=test_case.out,
                        share_reserves=test_case.share_reserves,
                        bond_reserves=test_case.bond_reserves,
                        token_in=test_case.token_in,
                        fee_percent=test_case.fee_percent,
                        time_remaining=test_case.time_remaining,
                        init_share_price=test_case.init_share_price,
                        share_price=test_case.share_price,
                    )

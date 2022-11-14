"""
Testing for the Hyperdrive Pricing Model
"""

# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-locals
# pylint: disable=attribute-defined-outside-init

import unittest
import itertools
import numpy as np
import pandas as pd

from elfpy.utils.time import stretch_time
from elfpy.pricing_models import HyperdrivePricingModel


class TestCaseCalcInGivenOut:
    __test__ = False  # pytest: don't test this class

    def __init__(
        self,
        out,
        share_reserves,
        bond_reserves,
        token_in,
        fee_percent,
        days_remaining,
        time_stretch_apy,
        share_price,
        init_share_price,
    ):
        self.out = out
        self.share_reserves = share_reserves
        self.bond_reserves = bond_reserves
        self.token_in = token_in
        self.fee_percent = fee_percent
        self.days_remaining = days_remaining
        self.time_stretch_apy = time_stretch_apy
        self.share_price = share_price
        self.init_share_price = init_share_price


class TestCaseCalcOutGivenIn:
    __test__ = False  # pytest: don't test this class

    def __init__(
        self,
        in_,
        share_reserves,
        bond_reserves,
        token_out,
        fee_percent,
        days_remaining,
        time_stretch_apy,
        share_price,
        init_share_price,
    ):
        self.in_ = in_
        self.share_reserves = share_reserves
        self.bond_reserves = bond_reserves
        self.token_out = token_out
        self.fee_percent = fee_percent
        self.days_remaining = days_remaining
        self.time_stretch_apy = time_stretch_apy
        self.share_price = share_price
        self.init_share_price = init_share_price


class TradeResult:
    __test__ = False  # pytest: don't test this class

    def __init__(self, without_fee_or_slippage, with_fee, without_fee, fee):
        self.without_fee_or_slippage = without_fee_or_slippage
        self.with_fee = with_fee
        self.without_fee = without_fee
        self.fee = fee


def compare_trade_results(actual, expected):
    np.testing.assert_almost_equal(
        actual.without_fee_or_slippage, expected.without_fee_or_slippage, err_msg="unexpected without_fee_or_slippage"
    )
    np.testing.assert_almost_equal(actual.with_fee, expected.with_fee, err_msg="unexpected without_fee")
    np.testing.assert_almost_equal(actual.without_fee, expected.without_fee, err_msg="unexpected fee")
    np.testing.assert_almost_equal(actual.fee, expected.fee, err_msg="unexpected with_fee")


class TestHyperdrivePricingModel(unittest.TestCase):
    def test_calc_in_given_out(self):
        pricing_model = HyperdrivePricingModel(False)
        test_cases = [
            (   # test one, basic starting point
                TestCaseCalcInGivenOut( 
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
                # τ = 0.0225358440315970471499308329778
                # 1 - τ = 0.977464155968402952850069167022
                # k = c/u*(u*z)**(1-τ) + (2*y + c*z)**(1-τ)
                # k = 100000**0.9774641559684029528500691670222 + (2*100000 + 100000*1)**0.9774641559684029528500691670222
                # k = 302929.51067963685
                (
                    TradeResult(
                        # p = ((2y+cz)/uz)**τ
                        #   = 1.0250671833648672
                        # without_fee_or_slippage = 1/p * out = 97.55458141947516
                        without_fee_or_slippage = 97.55458141947516
                        # fee is 10% of discount before slippage = (100-97.55601990513969)*0.1 = 2.4454185805248443*0.1 = 0.24454185805248443
                        ,
                        fee = 0.24454185805248443
                        # deltaZ = 1/u * (u/c*(k - (2*y + c*z - deltaY)**(1-τ)))**(1/(1-τ)) - z
                        # deltaZ = 1/1 * (1/1*(302929.51067963685 - (2*100000 + 100000 - 100)**(1-0.0225358440315970471499308329778)))**(1/(1-0.0225358440315970471499308329778)) - 100000
                        #        = 97.55601990513969
                        ,
                        without_fee = 97.55601990513969
                        # with_fee = without_fee + fee = 97.55601990513969 + 0.24454185805248443 = 97.80056176319217
                        ,
                        with_fee = 97.80056176319218,
                    )
                ),
            ),  # end of test one
            (   # test two, double the fee
                TestCaseCalcInGivenOut( 
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
                # τ = 0.0225358440315970471499308329778
                # 1 - τ = 0.977464155968402952850069167022
                # k = c/u*(u*z)**(1-τ) + (2*y + c*z)**(1-τ)
                # k = 100000**0.9774641559684029528500691670222 + (2*100000 + 100000*1)**0.9774641559684029528500691670222
                # k = 302929.51067963685
                (
                    TradeResult(
                        # p = ((2y+cz)/uz)**τ
                        #   = 1.0250671833648672
                        # without_fee_or_slippage = 1/p * out = 97.55458141947516
                        without_fee_or_slippage = 97.55458141947516
                        # fee is 10% of discount before slippage = (100-97.55458141947516)*0.2 = 2.4454185805248443*0.2 = 0.4887960189720616
                        ,
                        fee = 0.48908371610496887
                        # deltaZ = 1/u * (u/c*(k - (2*y + c*z - deltaY)**(1-τ)))**(1/(1-τ)) - z
                        # deltaZ = 1/1 * (1/1*(302929.51067963685 - (2*100000 + 100000 - 100)**(1-0.0225358440315970471499308329778)))**(1/(1-0.0225358440315970471499308329778)) - 100000
                        #        = 97.55601990513969
                        ,
                        without_fee = 97.55601990513969
                        # with_fee = without_fee + fee = 97.55601990513969 + 0.4887960189720616 = 98.04481592411175
                        ,
                        with_fee = 98.04510362124466,
                    )
                ),
            ),  # end of test two
            (   # test three, 10k out
                TestCaseCalcInGivenOut( 
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
                # τ = 0.0225358440315970471499308329778
                # 1 - τ = 0.977464155968402952850069167022
                # k = c/u*(u*z)**(1-τ) + (2*y + c*z)**(1-τ)
                # k = 100000**0.9774641559684029528500691670222 + (2*100000 + 100000*1)**0.9774641559684029528500691670222
                # k = 302929.51067963685
                (
                    TradeResult(
                        # p = ((2y+cz)/uz)**τ
                        #   = 1.0250671833648672
                        # without_fee_or_slippage = 1/p * out = 97.55458141947516
                        without_fee_or_slippage = 9755.458141947514
                        # fee is 10% of discount before slippage = (10000-9755.458141947514)*0.1 = 24.454185805248564
                        ,
                        fee = 24.454185805248564
                        # deltaZ = 1/u * (u/c*(k - (2*y + c*z - deltaY)**(1-τ)))**(1/(1-τ)) - z
                        # deltaZ = 1/1 * (1/1*(302929.51067963685 - (2*100000 + 100000 - 10000)**(1-0.0225358440315970471499308329778)))**(1/(1-0.0225358440315970471499308329778)) - 100000
                        #        = 9769.577831379836
                        ,
                        without_fee = 9769.577831379836
                        # with_fee = without_fee + fee = 9769.577831379836 +  24.454185805248564 = 97.80056176319217
                        ,
                        with_fee = 9794.032017185085,
                    )
                ),
            ),  # end of test three
            (   # test four, 80k out
                TestCaseCalcInGivenOut( 
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
                # τ = 0.0225358440315970471499308329778
                # 1 - τ = 0.977464155968402952850069167022
                # k = c/u*(u*z)**(1-τ) + (2*y + c*z)**(1-τ)
                # k = 100000**0.9774641559684029528500691670222 + (2*100000 + 100000*1)**0.9774641559684029528500691670222
                # k = 302929.51067963685
                (
                    TradeResult(
                        # p = ((2y+cz)/uz)**τ
                        #   = 1.0250671833648672
                        # without_fee_or_slippage = 1/p * out = 97.55458141947516
                        without_fee_or_slippage = 78043.66513558012
                        # fee is 10% of discount before slippage = (80000-78043.66513558012)*0.1 = 195.6334864419885
                        ,
                        fee = 195.6334864419885
                        # deltaZ = 1/u * (u/c*(k - (2*y + c*z - deltaY)**(1-τ)))**(1/(1-τ)) - z
                        # deltaZ = 1/1 * (1/1*(302929.51067963685 - (2*100000 + 100000 - 80000)**(1-0.0225358440315970471499308329778)))**(1/(1-0.0225358440315970471499308329778)) - 100000
                        #        = 78866.87433323538
                        ,
                        without_fee = 78866.87433323538
                        # with_fee = without_fee + fee = 78866.87433323538 +  195.6334864419885 = 79062.50781967737
                        ,
                        with_fee = 79062.50781967737,
                    )
                ),
            ),  # end of test four
            (   # test five, change share price
                TestCaseCalcInGivenOut( 
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
                # τ = 0.0225358440315970471499308329778
                # 1 - τ = 0.977464155968402952850069167022
                # k = c/u*(u*z)**(1-τ) + (2*y + c*z)**(1-τ)
                # k = 2/1.5*((1.5*100000)**0.9774641559684029528500691670222) + (2*100000 + 2*100000)**0.9774641559684029528500691670222
                # k = 451988.7122137336
                (
                    TradeResult(
                        # p = ((2y+cz)/uz)**τ
                        #   = ((2*100000 + 2*100000)/(1.5*100000))**0.0225358440315970471499308329778
                        #   = 1.0223499142867662
                        # without_fee_or_slippage = 1/p * out = 195.627736849304
                        without_fee_or_slippage = 195.627736849304 ,
                        # fee is 10% of discount before slippage = (200-195.627736849304)*0.1 = 0.4372263150696
                        fee = 0.4372263150696 ,
                        # deltaZ = 1/u * (u/c*(k - (2*y + c*z - deltaY)**(1-τ)))**(1/(1-τ)) - z
                        # deltaZ = 2*(1/1.5 * (1.5/2*(451988.7122137336 - (2*100000 + 2*100000 - 200)**(1-0.0225358440315970471499308329778)))**(1/(1-0.0225358440315970471499308329778)) - 100000)
                        #        = 195.63099467812572
                        without_fee = 195.63099467812572 ,
                        # with_fee = without_fee + fee = 195.63099467812572 +  0.4372263150696 = 196.06822099319533
                        with_fee = 196.06822099319533
                    )
                ),
            ),  # end of test five
            (   # test six, up bond reserves to 1,000,000
                TestCaseCalcInGivenOut( 
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
                # τ = 0.0225358440315970471499308329778
                # 1 - τ = 0.977464155968402952850069167022
                # k = c/u*(u*z)**(1-τ) + (2*y + c*z)**(1-τ)
                # k = 2/1.5*((1.5*100000)**0.9774641559684029528500691670222) + (2*1000000 + 2*100000)**0.9774641559684029528500691670222
                # k = 1735927.3223407117
                (
                    TradeResult(
                        # p = ((2y+cz)/uz)**τ
                        #   = ((2*1000000 + 2*100000)/(1.5*100000))**0.0225358440315970471499308329778
                        #   = 1.062390706640675
                        # without_fee_or_slippage = 1/p * out = 188.25465880853625
                        without_fee_or_slippage = 188.25465880853625 ,
                        # fee is 10% of discount before slippage = (200-188.25465880853625)*0.1 = 1.1745341191463752
                        fee = 1.1745341191463752 ,
                        # deltaZ = 1/u * (u/c*(k - (2*y + c*z - deltaY)**(1-τ)))**(1/(1-τ)) - z
                        # deltaZ = 2*(1/1.5 * (1.5/2*(1735927.3223407117 - (2*1000000 + 2*100000 - 200)**(1-0.0225358440315970471499308329778)))**(1/(1-0.0225358440315970471499308329778)) - 100000)
                        #        = 188.2568477257446
                        without_fee = 188.2568477257446 ,
                        # with_fee = without_fee + fee = 188.2568477257446 +  1.1745341191463752 = 188.2568477257446 +  1.1745341191463752
                        with_fee = 189.43138184489098
                    )
                ),
            ),  # end of test six
            (   # test seven, halve the days remaining
                TestCaseCalcInGivenOut( 
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
                # τ = 91.25/365/22.1868770168519182502689135891 = 0.011267922015798524
                # 1 - τ = 0.9887320779842015
                # k = c/u*(u*z)**(1-τ) + (2*y + c*z)**(1-τ)
                # k = 2/1.5*((1.5*100000)**0.9887320779842015) + (2*1000000 + 2*100000)**0.9887320779842015
                # k = 2041060.1949973335
                (
                    TradeResult(
                        # p = ((2y+cz)/uz)**τ
                        #   = ((2*1000000 + 2*100000)/(1.5*100000))**0.011267922015798524
                        #   = 1.0307233899745727
                        # without_fee_or_slippage = 1/p * out = 194.038480105641
                        without_fee_or_slippage = 194.038480105641 ,
                        # fee is 10% of discount before slippage = (200-194.038480105641)*0.1 = 0.5961519894358986
                        fee = 0.5961519894358986 ,
                        # deltaZ = 1/u * (u/c*(k - (2*y + c*z - deltaY)**(1-τ)))**(1/(1-τ)) - z
                        # deltaZ = 2*(1/1.5 * (1.5/2*(2041060.1949973335 - (2*1000000 + 2*100000 - 200)**(1-0.011267922015798524)))**(1/(1-0.011267922015798524)) - 100000)
                        #        = 194.0396397759323
                        without_fee = 194.0396397759323 ,
                        # with_fee = without_fee + fee = 194.0396397759323 +  0.5961519894358986 = 194.6357917653682
                        with_fee = 194.6357917653682
                    )
                ),
            ),  # end of test six
        ]
        for (test_case, expected) in test_cases:
            time_stretch = pricing_model.calc_time_stretch(test_case.time_stretch_apy)
            time_remaining = stretch_time(pricing_model.days_to_time_remaining(test_case.days_remaining), time_stretch)

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
            actual = TradeResult(without_fee_or_slippage, with_fee, without_fee, fee)
            compare_trade_results(actual, expected)
        return test_cases

    # FIXME:
    #
    # - [x] token_out = "pt"
    # - [ ] token_out = "base"
    # - [ ] asserts
    def test_calc_out_given_in(self):
        pricing_model = HyperdrivePricingModel(False)

        # Test cases where token_out = "pt".
        pt_out_test_cases = [
            # Low slippage trade - in_ is 0.1% of share reserves.
            (
                TestCaseCalcOutGivenIn(
                    in_=100,
                    share_reserves=100_000,
                    bond_reserves=100_000,
                    token_out="pt",
                    fee_percent=0.01,
                    days_remaining=182.5,
                    time_stretch_apy=0.05,
                    share_price=1,
                    init_share_price=1,
                ),
                # From the input, we have the following values:
                # - T = 0.02253584403159705
                # - p = 1.0250671833648672
                # - k = 302_929.51067963685
                (
                    # Using the spot price, the expected output without slippage or fees is given by:
                    #   1.0250671833648672 * 100 = 102.50671833648673
                    102.50671833648673,
                    # Combining the without_fee and the fee, we calculate with_fee as:
                    #   with_fee = 102.50516899477225 - 0.02506718336486724
                    102.48010181140738,
                    # We set up the problem as:
                    #   100_100 ** (1 - T) + (300_000 - d_y) ** (1 - T) = k
                    #
                    # Solving for d_y, we get the following calculation:
                    #   d_y = 300_000 - (k - 100_100 ** (1 - T)) ** (1 / (1 - T)) = 102.50516899477225
                    #
                    # Note that this is slightly smaller than the without slippage value
                    102.50516899477225,
                    # Since we are buying bonds, in_ is an amount of base and we calculate the fee using the spot price as:
                    #   fee = 0.01 * (p - 1) * 100 = 0.02506718336486724
                    0.02506718336486724,
                ),
            ),
            # High fee percentage - 20%.
            (
                TestCaseCalcOutGivenIn(
                    in_=100,
                    share_reserves=100_000,
                    bond_reserves=100_000,
                    token_out="pt",
                    fee_percent=0.2,
                    days_remaining=182.5,
                    time_stretch_apy=0.05,
                    share_price=1,
                    init_share_price=1,
                ),
                # From the input, we have the following values:
                # - T = 0.02253584403159705
                # - p = 1.0250671833648672
                # - k = 302_929.51067963685
                (
                    # Using the spot price, the expected output without slippage or fees is given by:
                    #   1.0250671833648672 * 100 = 102.50671833648673
                    102.50671833648673,
                    # Combining the without_fee and the fee, we calculate with_fee as:
                    #   with_fee = 102.50516899477225 - 0.5013436672973448 = 102.0038253274749
                    102.0038253274749,
                    # We set up the problem as:
                    #   100_100 ** (1 - T) + (300_000 - d_y) ** (1 - T) = k
                    #
                    # Solving for d_y, we get the following calculation:
                    #   d_y = 300_000 - (k - 100_100 ** (1 - T)) ** (1 / (1 - T)) = 102.50516899477225
                    #
                    # Note that this is slightly smaller than the without slippage value
                    102.50516899477225,
                    # Since we are buying bonds, in_ is an amount of base and we calculate the fee using the spot price as:
                    #   fee = 0.2 * (p - 1) * 100 = 0.5013436672973448
                    0.5013436672973448,
                ),
            ),
            # Medium slippage trade - in_ is 10% of share reserves.
            (
                TestCaseCalcOutGivenIn(
                    in_=10_000,
                    share_reserves=100_000,
                    bond_reserves=100_000,
                    token_out="pt",
                    fee_percent=0.01,
                    days_remaining=182.5,
                    time_stretch_apy=0.05,
                    share_price=1,
                    init_share_price=1,
                ),
                # From the input, we have the following values:
                # - T = 0.02253584403159705
                # - p = 1.0250671833648672
                # - k = 302_929.51067963685
                (
                    # Using the spot price, the expected output without slippage or fees is given by:
                    #   1.0250671833648672 * 10_000 = 10250.671833648672
                    10250.671833648672,
                    # Combining the without_fee and the fee, we calculate with_fee as:
                    #   with_fee = 10235.514826394327 - 2.506718336486724 = 10233.00810805784
                    10233.00810805784,
                    # We set up the problem as:
                    #   110_000 ** (1 - T) + (300_000 - d_y) ** (1 - T) = k
                    #
                    # Solving for d_y, we get the following calculation:
                    #   d_y = 300_000 - (k - 110_000 ** (1 - T)) ** (1 / (1 - T)) = 10235.514826394327
                    #
                    # Note that this is smaller than the without slippage value
                    10235.514826394327,
                    # Since we are buying bonds, in_ is an amount of base and we calculate the fee using the spot price as:
                    #   fee = 0.01 * (p - 1) * 10_000 = 2.506718336486724
                    2.506718336486724,
                ),
            ),
            # TODO: The slippage should arguably be much higher. This is something
            # we should consider more when thinking about the use of a time stretch
            # parameter.
            #
            # High slippage trade - in_ is 80% of share reserves.
            (
                TestCaseCalcOutGivenIn(
                    in_=80_000,
                    share_reserves=100_000,
                    bond_reserves=100_000,
                    token_out="pt",
                    fee_percent=0.01,
                    days_remaining=182.5,
                    time_stretch_apy=0.05,
                    share_price=1,
                    init_share_price=1,
                ),
                # From the input, we have the following values:
                # - T = 0.02253584403159705
                # - p = 1.0250671833648672
                # - k = 302_929.51067963685
                (
                    # Using the spot price, the expected output without slippage or fees is given by:
                    #   1.0250671833648672 * 80_000 = 82005.37466918938
                    82005.37466918938,
                    # Combining the without_fee and the fee, we calculate with_fee as:
                    #   with_fee = 81138.27602200207 - 20.053746691893792 = 81118.22227531018
                    81118.22227531018,
                    # We set up the problem as:
                    #   180_000 ** (1 - T) + (300_000 - d_y) ** (1 - T) = k
                    #
                    # Solving for d_y, we get the following calculation:
                    #   d_y = 300_000 - (k - 180_000 ** (1 - T)) ** (1 / (1 - T)) = 81138.27602200207
                    #
                    # Note that this is smaller than the without slippage value
                    81138.27602200207,
                    # Since we are buying bonds, in_ is an amount of base and we calculate the fee using the spot price as:
                    #   fee = 0.01 * (p - 1) * 80_000 = 20.053746691893792
                    20.053746691893792,
                ),
            ),
            # Non-trivial initial share price and share price.
            (
                TestCaseCalcOutGivenIn(
                    # Base in of 200 is 100 shares at the current share price.
                    in_=200,
                    share_reserves=100_000,
                    bond_reserves=100_000,
                    token_out="pt",
                    fee_percent=0.01,
                    days_remaining=182.5,
                    time_stretch_apy=0.05,
                    share_price=2,
                    init_share_price=1.5,
                ),
                # From the input, we have the following values:
                # - T = 0.02253584403159705
                # - p = 1.0223499142867662
                # - k = 451_988.7122137336
                (
                    # Using the spot price, the expected output without slippage or fees is given by:
                    #   1.0223499142867662 * 200 = 204.46998285735324
                    204.46998285735324,
                    # Combining the without_fee and the fee, we calculate with_fee as:
                    #   with_fee = 204.46650180319557 - 0.044699828573532496 = 204.42180197462204
                    204.42180197462204,
                    # We set up the problem as:
                    #   (2 / 1.5) * (1.5 * 100_100) ** (1 - T) + (400_000 - d_y) ** (1 - T) = k
                    #
                    # Solving for d_y, we get the following calculation:
                    #   d_y = 400_000 - (k - (2 / 1.5) * (1.5 * 100_100) ** (1 - T)) ** (1 / (1 - T)) = 204.46650180319557
                    #
                    # Note that this is slightly smaller than the without slippage value
                    204.46650180319557,
                    # Since we are buying bonds, in_ is an amount of base and we calculate the fee using the spot price as:
                    #   fee = 0.01 * (p - 1) * 200 = 0.044699828573532496
                    0.044699828573532496,
                ),
            ),
            # Very unbalanced reserves.
            (
                TestCaseCalcOutGivenIn(
                    in_=200,
                    share_reserves=100_000,
                    bond_reserves=1_000_000,
                    token_out="pt",
                    fee_percent=0.01,
                    days_remaining=182.5,
                    time_stretch_apy=0.05,
                    share_price=2,
                    init_share_price=1.5,
                ),
                # From the input, we have the following values:
                # - T = 0.02253584403159705
                # - p = 1.0623907066406753
                # - k = 1_735_927.3223407117
                (
                    # Using the spot price, the expected output without slippage or fees is given by:
                    #   1.0623907066406753 * 200 = 212.47814132813505
                    212.47814132813505,
                    # Combining the without_fee and the fee, we calculate with_fee as:
                    #   with_fee = 212.47551672440022 - 0.1247814132813505 = 212.35073531111888
                    212.35073531111888,
                    # We set up the problem as:
                    #   (2 / 1.5) * (1.5 * 100_100) ** (1 - T) + (2_200_000 - d_y) ** (1 - T) = k
                    #
                    # Solving for d_y, we get the following calculation:
                    #   d_y = 2_200_000 - (k - (2 / 1.5) * (1.5 * 100_100) ** (1 - T)) ** (1 / (1 - T)) = 212.47551672440022
                    #
                    # Note that this is slightly smaller than the without slippage value
                    212.47551672440022,
                    # Since we are buying bonds, in_ is an amount of base and we calculate the fee using the spot price as:
                    #   fee = 0.01 * (p - 1) * 200 = 0.1247814132813505
                    0.1247814132813505,
                ),
            ),
            # A term of a quarter year.
            (
                TestCaseCalcOutGivenIn(
                    in_=200,
                    share_reserves=100_000,
                    bond_reserves=1_000_000,
                    token_out="pt",
                    fee_percent=0.01,
                    days_remaining=91.25,
                    time_stretch_apy=0.05,
                    share_price=2,
                    init_share_price=1.5,
                ),
                # From the input, we have the following values:
                # - T = 0.011267922015798525
                # - p = 1.0307233899745727
                # - k = 2_041_060.1949973335
                (
                    # Using the spot price, the expected output without slippage or fees is given by:
                    #   1.0307233899745727 * 200 = 206.14467799491453
                    206.14467799491453,
                    # Combining the without_fee and the fee, we calculate with_fee as:
                    #   with_fee = 206.14340814948082 - 0.06144677994914538 = 206.08196136953168
                    206.08196136953168,
                    # We set up the problem as:
                    #   (2 / 1.5) * (1.5 * 100_100) ** (1 - T) + (2_200_000 - d_y) ** (1 - T) = k
                    #
                    # Solving for d_y, we get the following calculation:
                    #   d_y = 2_200_000 - (k - (2 / 1.5) * (1.5 * 100_100) ** (1 - T)) ** (1 / (1 - T)) = 206.14340814948082
                    #
                    # Note that this is slightly smaller than the without slippage value
                    206.14340814948082,
                    # Since we are buying bonds, in_ is an amount of base and we calculate the fee using the spot price as:
                    #   fee = 0.01 * (p - 1) * 200 = 0.06144677994914538
                    0.06144677994914538,
                ),
            ),
            # A time stretch targetting 10% APY.
            (
                TestCaseCalcOutGivenIn(
                    in_=200,
                    share_reserves=100_000,
                    bond_reserves=1_000_000,
                    token_out="pt",
                    fee_percent=0.01,
                    days_remaining=91.25,
                    time_stretch_apy=0.10,
                    share_price=2,
                    init_share_price=1.5,
                ),
                # From the input, we have the following values:
                # - T = 0.02253584403159705
                # - p = 1.0623907066406753
                # - k = 1_735_927.3223407117
                (
                    # Using the spot price, the expected output without slippage or fees is given by:
                    #   1.0623907066406753 * 200 = 212.47814132813505
                    212.47814132813505,
                    # Combining the without_fee and the fee, we calculate with_fee as:
                    #   with_fee = 212.47551672440022 - 0.1247814132813505 = 212.35073531111888
                    212.35073531111888,
                    # We set up the problem as:
                    #   (2 / 1.5) * (1.5 * 100_100) ** (1 - T) + (2_200_000 - d_y) ** (1 - T) = k
                    #
                    # Solving for d_y, we get the following calculation:
                    #   d_y = 2_200_000 - (k - (2 / 1.5) * (1.5 * 100_100) ** (1 - T)) ** (1 / (1 - T)) = 212.47551672440022
                    #
                    # Note that this is slightly smaller than the without slippage value
                    212.47551672440022,
                    # Since we are buying bonds, in_ is an amount of base and we calculate the fee using the spot price as:
                    #   fee = 0.01 * (p - 1) * 200 = 0.1247814132813505
                    0.1247814132813505,
                ),
            ),
        ]

        # Test cases where token_out = "base".
        base_out_test_cases = [
            # Low slippage trade - in_ is 0.1% of share reserves.
            (
                TestCaseCalcOutGivenIn(
                    in_=100,
                    share_reserves=100_000,
                    bond_reserves=100_000,
                    token_out="base",
                    fee_percent=0.01,
                    days_remaining=182.5,
                    time_stretch_apy=0.05,
                    share_price=1,
                    init_share_price=1,
                ),
                # From the input, we have the following values:
                # - T = 0.02253584403159705
                # - p = 1.0250671833648672
                # - k = 302_929.51067963685
                (
                    # Using the spot price, the expected output without slippage or fees is given by:
                    #   (1 / 1.0250671833648672) * 100 = 97.55458141947516
                    97.55458141947516,
                    # Combining the without_fee and the fee, we calculate with_fee as:
                    #   with_fee = 97.55314236719278 - 0.024454185805248493 = 97.52868818138752
                    97.52868818138752,
                    # We set up the problem as:
                    #   (100_000 - d_z) ** (1 - T) + 300_100 ** (1 - T) = k
                    #
                    # Solving for d_z, we get the following calculation:
                    #   d_z = 100_000 - (k - 300_100 ** (1 - T)) ** (1 / (1 - T)) = 97.55314236719278
                    #
                    # The output is d_x = c * d_z. Since c = 1, d_x = d_z.
                    # Note that this is slightly smaller than the without slippage value
                    97.55314236719278,
                    # Since we are buying bonds, in_ is an amount of base and we calculate the fee using the spot price as:
                    #   fee = 0.01 * (1 - (1 / p)) * 100 = 0.024454185805248493
                    0.024454185805248493,
                ),
            ),
            # High fee percentage - 20%.
            (
                TestCaseCalcOutGivenIn(
                    in_=100,
                    share_reserves=100_000,
                    bond_reserves=100_000,
                    token_out="base",
                    fee_percent=0.2,
                    days_remaining=182.5,
                    time_stretch_apy=0.05,
                    share_price=1,
                    init_share_price=1,
                ),
                # From the input, we have the following values:
                # - T = 0.02253584403159705
                # - p = 1.0250671833648672
                # - k = 302_929.51067963685
                (
                    # Using the spot price, the expected output without slippage or fees is given by:
                    #   (1 / 1.0250671833648672) * 100 = 97.55458141947516
                    97.55458141947516,
                    # Combining the without_fee and the fee, we calculate with_fee as:
                    #   with_fee = 97.55314236719278 - 0.48908371610497 = 97.0640586510878
                    97.0640586510878,
                    # We set up the problem as:
                    #   (100_000 - d_z) ** (1 - T) + 300_100 ** (1 - T) = k
                    #
                    # Solving for d_z, we get the following calculation:
                    #   d_z = 100_000 - (k - 300_100 ** (1 - T)) ** (1 / (1 - T)) = 97.55314236719278
                    #
                    # The output is d_x = c * d_z. Since c = 1, d_x = d_z.
                    # Note that this is slightly smaller than the without slippage value
                    97.55314236719278,
                    # Since we are buying bonds, in_ is an amount of base and we calculate the fee using the spot price as:
                    #   fee = 0.2 * (1 - (1 / p)) * 100 = 0.5013436672973448
                    0.48908371610497,
                ),
            ),
            # Medium slippage trade - in_ is 10% of share reserves.
            (
                TestCaseCalcOutGivenIn(
                    in_=10_000,
                    share_reserves=100_000,
                    bond_reserves=100_000,
                    token_out="base",
                    fee_percent=0.01,
                    days_remaining=182.5,
                    time_stretch_apy=0.05,
                    share_price=1,
                    init_share_price=1,
                ),
                # From the input, we have the following values:
                # - T = 0.02253584403159705
                # - p = 1.0250671833648672
                # - k = 302_929.51067963685
                (
                    # Using the spot price, the expected output without slippage or fees is given by:
                    #   (1 / 1.0250671833648672) * 10_000 = 9755.458141947514
                    9755.458141947514,
                    # Combining the without_fee and the fee, we calculate with_fee as:
                    #   with_fee = 9740.77011591768 - 2.4454185805248496 = 9738.324697337155
                    9738.324697337155,
                    # We set up the problem as:
                    #   (100_000 - d_z) ** (1 - T) + 310_000 ** (1 - T) = k
                    #
                    # Solving for d_z, we get the following calculation:
                    #   d_z = 100_000 - (k - 310_000 ** (1 - T)) ** (1 / (1 - T)) = 9740.77011591768
                    #
                    # The output is d_x = c * d_z. Since c = 1, d_x = d_z.
                    # Note that this is slightly smaller than the without slippage value
                    9740.77011591768,
                    # Since we are buying bonds, in_ is an amount of base and we calculate the fee using the spot price as:
                    #   fee = 0.01 * (1 - (1 / p)) * 10_000 = 2.4454185805248496
                    2.4454185805248496,
                ),
            ),
            # TODO: The slippage should arguably be much higher. This is something
            # we should consider more when thinking about the use of a time stretch
            # parameter.
            #
            # High slippage trade - in_ is 80% of share reserves.
            (
                TestCaseCalcOutGivenIn(
                    in_=80_000,
                    share_reserves=100_000,
                    bond_reserves=100_000,
                    token_out="base",
                    fee_percent=0.01,
                    days_remaining=182.5,
                    time_stretch_apy=0.05,
                    share_price=1,
                    init_share_price=1,
                ),
                # From the input, we have the following values:
                # - T = 0.02253584403159705
                # - p = 1.0250671833648672
                # - k = 302_929.51067963685
                (
                    # Using the spot price, the expected output without slippage or fees is given by:
                    #   (1 / 1.0250671833648672) * 80_000 = 78043.66513558012
                    78043.66513558012,
                    # Combining the without_fee and the fee, we calculate with_fee as:
                    #   with_fee = 76850.14470187116 - 19.563348644198797 = 76830.58135322697
                    76830.58135322697,
                    # We set up the problem as:
                    #   (100_000 - d_z) ** (1 - T) + 380_000 ** (1 - T) = k
                    #
                    # Solving for d_z, we get the following calculation:
                    #   d_z = 100_000 - (k - 380_000 ** (1 - T)) ** (1 / (1 - T)) = 76850.14470187116
                    #
                    # The output is d_x = c * d_z. Since c = 1, d_x = d_z.
                    # Note that this is slightly smaller than the without slippage value
                    76850.14470187116,
                    # Since we are buying bonds, in_ is an amount of base and we calculate the fee using the spot price as:
                    #   fee = 0.01 * (1 - (1 / p)) * 80_000 = 19.563348644198797
                    19.563348644198797,
                ),
            ),
            # Non-trivial initial share price and share price.
            (
                TestCaseCalcOutGivenIn(
                    in_=100,
                    share_reserves=100_000,
                    bond_reserves=100_000,
                    token_out="base",
                    fee_percent=0.01,
                    days_remaining=182.5,
                    time_stretch_apy=0.05,
                    share_price=2,
                    init_share_price=1.5,
                ),
                # From the input, we have the following values:
                # - T = 0.02253584403159705
                # - p = 1.0223499142867662
                # - k = 451_988.7122137336
                (
                    # Using the spot price, the expected output without slippage or fees is given by:
                    #   (1 / 1.0223499142867662) * 100 = 97.813868424652
                    97.813868424652,
                    # Combining the without_fee and the fee, we calculate with_fee as:
                    #   with_fee = 97.81305379542755 - 0.02186131575348005 = 97.79119247967407
                    97.79119247967407,
                    # We set up the problem as:
                    #   (2 / 1.5) * (1.5 * (100_000 - d_z)) ** (1 - T) + 400_100 ** (1 - T) = k
                    #
                    # Solving for d_z, we get the following calculation:
                    #   d_z = 100_000 - (1 / 1.5) * ((1.5 / 2) * (k - 400_100 ** (1 - T))) ** (1 / (1 - T)) = 48.906526897713775
                    #
                    # The output is d_x = c * d_z = 2 * 48.906526897713775 = 97.81305379542755.
                    # Note that this is slightly smaller than the without slippage value
                    97.81305379542755,
                    # Since we are buying bonds, in_ is an amount of base and we calculate the fee using the spot price as:
                    #   fee = 0.01 * (1 - (1 / p)) * 100 = 0.02186131575348005
                    0.02186131575348005,
                ),
            ),
            # Very unbalanced reserves.
            (
                TestCaseCalcOutGivenIn(
                    in_=100,
                    share_reserves=100_000,
                    bond_reserves=1_000_000,
                    token_out="base",
                    fee_percent=0.01,
                    days_remaining=182.5,
                    time_stretch_apy=0.05,
                    share_price=2,
                    init_share_price=1.5,
                ),
                # From the input, we have the following values:
                # - T = 0.02253584403159705
                # - p = 1.0623907066406753
                # - k = 1_735_927.3223407117
                (
                    # Using the spot price, the expected output without slippage or fees is given by:
                    #   (1 / 1.0623907066406753) * 100 = 94.1273294042681
                    94.1273294042681,
                    # Combining the without_fee and the fee, we calculate with_fee as:
                    #   with_fee = 94.12678195475019 - 0.05872670595731899 = 94.06805524879287
                    94.06805524879287,
                    # We set up the problem as:
                    #   (2 / 1.5) * (1.5 * (100_000 - d_z)) ** (1 - T) + 2_200_100 ** (1 - T) = k
                    #
                    # Solving for d_z, we get the following calculation:
                    #   d_z = 100_000 - (1 / 1.5) * ((1.5 / 2) * (k - 2_200_100 ** (1 - T))) ** (1 / (1 - T)) = 47.06339097737509
                    #
                    # The output is d_x = c * d_z = 2 * 47.06339097737509 = 94.12678195475019.
                    # Note that this is slightly smaller than the without slippage value
                    94.12678195475019,
                    # Since we are buying bonds, in_ is an amount of base and we calculate the fee using the spot price as:
                    #   fee = 0.01 * (1 - (1 / p)) * 100 = 0.05872670595731899
                    0.05872670595731899,
                ),
            ),
            # A term of a quarter year.
            (
                TestCaseCalcOutGivenIn(
                    in_=100,
                    share_reserves=100_000,
                    bond_reserves=1_000_000,
                    token_out="base",
                    fee_percent=0.01,
                    days_remaining=91.25,
                    time_stretch_apy=0.05,
                    share_price=2,
                    init_share_price=1.5,
                ),
                # From the input, we have the following values:
                # - T = 0.011267922015798525
                # - p = 1.0307233899745727
                # - k = 2_041_060.1949973335
                (
                    # Using the spot price, the expected output without slippage or fees is given by:
                    #   (1 / 1.0307233899745727) * 100 = 97.0192400528205
                    97.0192400528205,
                    # Combining the without_fee and the fee, we calculate with_fee as:
                    #   with_fee = 97.01895001129014 - 0.0298075994717949 = 96.98914241181835
                    96.98914241181835,
                    # We set up the problem as:
                    #   (2 / 1.5) * (1.5 * (100_000 - d_z)) ** (1 - T) + 2_200_100 ** (1 - T) = k
                    #
                    # Solving for d_z, we get the following calculation:
                    #   d_z = 100_000 - (1 / 1.5) * ((1.5 / 2) * (k - 2_200_100 ** (1 - T))) ** (1 / (1 - T)) = 48.50947500564507
                    #
                    # The output is d_x = c * d_z = 2 * 48.50947500564507 = 97.01895001129014.
                    # Note that this is slightly smaller than the without slippage value
                    97.01895001129014,
                    # Since we are buying bonds, in_ is an amount of base and we calculate the fee using the spot price as:
                    #   fee = 0.01 * (1 - (1 / p)) * 100 = 0.0298075994717949
                    0.0298075994717949,
                ),
            ),
            # A time stretch targetting 10% APY.
            (
                TestCaseCalcOutGivenIn(
                    in_=100,
                    share_reserves=100_000,
                    bond_reserves=1_000_000,
                    token_out="base",
                    fee_percent=0.01,
                    days_remaining=91.25,
                    time_stretch_apy=0.10,
                    share_price=2,
                    init_share_price=1.5,
                ),
                # From the input, we have the following values:
                # - T = 0.02253584403159705
                # - p = 1.0623907066406753
                # - k = 1_735_927.3223407117
                (
                    # Using the spot price, the expected output without slippage or fees is given by:
                    #   (1 / 1.0623907066406753) * 100 = 94.1273294042681
                    94.1273294042681,
                    # Combining the without_fee and the fee, we calculate with_fee as:
                    #   with_fee = 94.12678195475019 - 0.05872670595731899 = 94.06805524879287
                    94.06805524879287,
                    # We set up the problem as:
                    #   (2 / 1.5) * (1.5 * (100_000 - d_z)) ** (1 - T) + 2_200_100 ** (1 - T) = k
                    #
                    # Solving for d_z, we get the following calculation:
                    #   d_z = 100_000 - (1 / 1.5) * ((1.5 / 2) * (k - 2_200_100 ** (1 - T))) ** (1 / (1 - T)) = 47.06339097737509
                    #
                    # The output is d_x = c * d_z = 2 * 47.06339097737509 = 94.12678195475019.
                    # Note that this is slightly smaller than the without slippage value
                    94.12678195475019,
                    # Since we are buying bonds, in_ is an amount of base and we calculate the fee using the spot price as:
                    #   fee = 0.01 * (1 - (1 / p)) * 100 = 0.05872670595731899
                    0.05872670595731899,
                ),
            ),
        ]

        # Iterate over all of the test cases and verify that the pricing model
        # produces the expected outputs for each test case.
        test_cases = pt_out_test_cases + base_out_test_cases
        for (
            test_case,
            (expected_without_fee_or_slippage, expected_with_fee, expected_without_fee, expected_fee),
        ) in test_cases:
            time_stretch = pricing_model.calc_time_stretch(test_case.time_stretch_apy)
            time_remaining = stretch_time(pricing_model.days_to_time_remaining(test_case.days_remaining), time_stretch)

            # Ensure we get the expected results from the pricing model.
            (without_fee_or_slippage, with_fee, without_fee, fee) = pricing_model.calc_out_given_in(
                test_case.in_,
                test_case.share_reserves,
                test_case.bond_reserves,
                test_case.token_out,
                test_case.fee_percent,
                time_remaining,
                test_case.init_share_price,
                test_case.share_price,
            )
            assert without_fee_or_slippage == expected_without_fee_or_slippage, "unexpected without_fee_or_slippage"
            assert without_fee == expected_without_fee, "unexpected without_fee"
            assert fee == expected_fee, "unexpected fee"
            assert with_fee == expected_with_fee, "unexpected with_fee"
        return test_cases
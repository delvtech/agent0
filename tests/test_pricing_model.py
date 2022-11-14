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


class TestCaseCalcOutGivenInSuccess:
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


class TestCaseCalcOutGivenInFailure:
    __test__ = False  # pytest: don't test this class

    def __init__(
        self,
        in_,
        share_reserves,
        bond_reserves,
        token_out,
        fee_percent,
        time_remaining,
        share_price,
        init_share_price,
    ):
        self.in_ = in_
        self.share_reserves = share_reserves
        self.bond_reserves = bond_reserves
        self.token_out = token_out
        self.fee_percent = fee_percent
        self.time_remaining = time_remaining
        self.share_price = share_price
        self.init_share_price = init_share_price


class TradeResult:
    __test__ = False  # pytest: don't test this class

    def __init__(self, without_fee_or_slippage, with_fee, without_fee, fee):
        self.without_fee_or_slippage = without_fee_or_slippage
        self.with_fee = with_fee
        self.without_fee = without_fee
        self.fee = fee

    def compare_trade_results(self, other):
        np.testing.assert_almost_equal(
            self.without_fee_or_slippage, other.without_fee_or_slippage, err_msg="unexpected without_fee_or_slippage"
        )
        np.testing.assert_almost_equal(self.with_fee, other.with_fee, err_msg="unexpected without_fee")
        np.testing.assert_almost_equal(self.without_fee, other.without_fee, err_msg="unexpected fee")
        np.testing.assert_almost_equal(self.fee, other.fee, err_msg="unexpected with_fee")


class TestHyperdrivePricingModel(unittest.TestCase):
    def test_calc_in_given_out(self):
        pricing_model = HyperdrivePricingModel(False)
        test_cases = [
            (  # test one, basic starting point
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
                        without_fee_or_slippage=97.55458141947516
                        # fee is 10% of discount before slippage = (100-97.55601990513969)*0.1 = 2.4454185805248443*0.1 = 0.24454185805248443
                        ,
                        fee=0.24454185805248443
                        # deltaZ = 1/u * (u/c*(k - (2*y + c*z - deltaY)**(1-τ)))**(1/(1-τ)) - z
                        # deltaZ = 1/1 * (1/1*(302929.51067963685 - (2*100000 + 100000 - 100)**(1-0.0225358440315970471499308329778)))**(1/(1-0.0225358440315970471499308329778)) - 100000
                        #        = 97.55601990513969
                        ,
                        without_fee=97.55601990513969
                        # with_fee = without_fee + fee = 97.55601990513969 + 0.24454185805248443 = 97.80056176319217
                        ,
                        with_fee=97.80056176319218,
                    )
                ),
            ),  # end of test one
            (  # test two, double the fee
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
                        without_fee_or_slippage=97.55458141947516
                        # fee is 10% of discount before slippage = (100-97.55458141947516)*0.2 = 2.4454185805248443*0.2 = 0.4887960189720616
                        ,
                        fee=0.48908371610496887
                        # deltaZ = 1/u * (u/c*(k - (2*y + c*z - deltaY)**(1-τ)))**(1/(1-τ)) - z
                        # deltaZ = 1/1 * (1/1*(302929.51067963685 - (2*100000 + 100000 - 100)**(1-0.0225358440315970471499308329778)))**(1/(1-0.0225358440315970471499308329778)) - 100000
                        #        = 97.55601990513969
                        ,
                        without_fee=97.55601990513969
                        # with_fee = without_fee + fee = 97.55601990513969 + 0.4887960189720616 = 98.04481592411175
                        ,
                        with_fee=98.04510362124466,
                    )
                ),
            ),  # end of test two
            (  # test three, 10k out
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
                        without_fee_or_slippage=9755.458141947514
                        # fee is 10% of discount before slippage = (10000-9755.458141947514)*0.1 = 24.454185805248564
                        ,
                        fee=24.454185805248564
                        # deltaZ = 1/u * (u/c*(k - (2*y + c*z - deltaY)**(1-τ)))**(1/(1-τ)) - z
                        # deltaZ = 1/1 * (1/1*(302929.51067963685 - (2*100000 + 100000 - 10000)**(1-0.0225358440315970471499308329778)))**(1/(1-0.0225358440315970471499308329778)) - 100000
                        #        = 9769.577831379836
                        ,
                        without_fee=9769.577831379836
                        # with_fee = without_fee + fee = 9769.577831379836 +  24.454185805248564 = 97.80056176319217
                        ,
                        with_fee=9794.032017185085,
                    )
                ),
            ),  # end of test three
            (  # test four, 80k out
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
                        without_fee_or_slippage=78043.66513558012
                        # fee is 10% of discount before slippage = (80000-78043.66513558012)*0.1 = 195.6334864419885
                        ,
                        fee=195.6334864419885
                        # deltaZ = 1/u * (u/c*(k - (2*y + c*z - deltaY)**(1-τ)))**(1/(1-τ)) - z
                        # deltaZ = 1/1 * (1/1*(302929.51067963685 - (2*100000 + 100000 - 80000)**(1-0.0225358440315970471499308329778)))**(1/(1-0.0225358440315970471499308329778)) - 100000
                        #        = 78866.87433323538
                        ,
                        without_fee=78866.87433323538
                        # with_fee = without_fee + fee = 78866.87433323538 +  195.6334864419885 = 79062.50781967737
                        ,
                        with_fee=79062.50781967737,
                    )
                ),
            ),  # end of test four
            (  # test five, change share price
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
                        without_fee_or_slippage=195.627736849304,
                        # fee is 10% of discount before slippage = (200-195.627736849304)*0.1 = 0.4372263150696
                        fee=0.4372263150696,
                        # deltaZ = 1/u * (u/c*(k - (2*y + c*z - deltaY)**(1-τ)))**(1/(1-τ)) - z
                        # deltaZ = 2*(1/1.5 * (1.5/2*(451988.7122137336 - (2*100000 + 2*100000 - 200)**(1-0.0225358440315970471499308329778)))**(1/(1-0.0225358440315970471499308329778)) - 100000)
                        #        = 195.63099467812572
                        without_fee=195.63099467812572,
                        # with_fee = without_fee + fee = 195.63099467812572 +  0.4372263150696 = 196.06822099319533
                        with_fee=196.06822099319533,
                    )
                ),
            ),  # end of test five
            (  # test six, up bond reserves to 1,000,000
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
                        without_fee_or_slippage=188.25465880853625,
                        # fee is 10% of discount before slippage = (200-188.25465880853625)*0.1 = 1.1745341191463752
                        fee=1.1745341191463752,
                        # deltaZ = 1/u * (u/c*(k - (2*y + c*z - deltaY)**(1-τ)))**(1/(1-τ)) - z
                        # deltaZ = 2*(1/1.5 * (1.5/2*(1735927.3223407117 - (2*1000000 + 2*100000 - 200)**(1-0.0225358440315970471499308329778)))**(1/(1-0.0225358440315970471499308329778)) - 100000)
                        #        = 188.2568477257446
                        without_fee=188.2568477257446,
                        # with_fee = without_fee + fee = 188.2568477257446 +  1.1745341191463752 = 188.2568477257446 +  1.1745341191463752
                        with_fee=189.43138184489098,
                    )
                ),
            ),  # end of test six
            (  # test seven, halve the days remaining
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
                        without_fee_or_slippage=194.038480105641,
                        # fee is 10% of discount before slippage = (200-194.038480105641)*0.1 = 0.5961519894358986
                        fee=0.5961519894358986,
                        # deltaZ = 1/u * (u/c*(k - (2*y + c*z - deltaY)**(1-τ)))**(1/(1-τ)) - z
                        # deltaZ = 2*(1/1.5 * (1.5/2*(2041060.1949973335 - (2*1000000 + 2*100000 - 200)**(1-0.011267922015798524)))**(1/(1-0.011267922015798524)) - 100000)
                        #        = 194.0396397759323
                        without_fee=194.0396397759323,
                        # with_fee = without_fee + fee = 194.0396397759323 +  0.5961519894358986 = 194.6357917653682
                        with_fee=194.6357917653682,
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
            expected.compare_trade_results(TradeResult(without_fee_or_slippage, with_fee, without_fee, fee))

    def test_calc_out_given_in_success(self):
        pricing_model = HyperdrivePricingModel(False)

        # Test cases where token_out = "pt".
        pt_out_test_cases = [
            # Low slippage trade - in_ is 0.1% of share reserves.
            (
                TestCaseCalcOutGivenInSuccess(
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
                #
                #   t_stretch = 22.1868770168519182502689135891
                #
                #   τ = d / (365 * t_stretch)
                #     = 182.5 / (365 * 22.1868770168519182502689135891)
                #     = 0.0225358440315970471499308329778
                #
                #   1 - τ = 0.977464155968402952850069167022
                #
                #   k = (c / μ) * (μ * z) **(1 - τ) + (2 * y + c * z)**(1 - τ)
                #     = 100000**0.9774641559684029528500691670222 + (2*100000 + 100000*1)**0.9774641559684029528500691670222
                #     = 302929.51067963685
                #
                #   p = ((2 * y + c * z) / (μ * z)) ** τ
                #     = ((2 * 100_000 + 2 * 100_000) / (1.5 * 100_000)) ** 0.0225358440315970471499308329778
                #     = 1.0250671833648672
                TradeResult(
                    # without_fee_or_slippage = p * in_
                    #                         = 1.0250671833648672 * 100
                    #                         = 102.50671833648673
                    without_fee_or_slippage=102.50671833648673,
                    # fee = 0.01 * (p - 1) * 100 = 0.02506718336486724
                    fee=0.02506718336486724,
                    # We want to solve for the amount of bonds out given the
                    # amount of shares coming in, so we set up the problem as:
                    #
                    #   k = (c / μ) * (μ * (z + d_z)) ** (1 - τ) + (2 * y + c * z - d_y) ** (1 - τ)
                    #     = 100_100 ** (1 - T) + (300_000 - d_y) ** (1 - T)
                    #
                    # Solving for d_y, we get the following calculation:
                    #
                    #   d_y = 300_000 - (k - 100_100 ** (1 - T)) ** (1 / (1 - T))
                    #       = 102.50516899477225
                    #
                    # Note that this is slightly smaller than the without slippage value
                    without_fee=102.50516899477225,
                    # with_fee = d_y - fee
                    #          = 102.50516899477225 - 0.02506718336486724
                    #          = 102.48010181140738
                    with_fee=102.48010181140738,
                ),
            ),
            # High fee percentage - 20%.
            (
                TestCaseCalcOutGivenInSuccess(
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
                # The trading constants are the same as the previous case. The
                # only values that should change are `fee` and `with_fee` since
                # the fee percentage changed.
                TradeResult(
                    without_fee_or_slippage=102.50671833648673,
                    # fee = 0.2 * (p - 1) * 100 = 0.5013436672973448
                    fee=0.5013436672973448,
                    without_fee=102.50516899477225,
                    # with_fee = d_y - fee
                    #          = 102.50516899477225 - 0.5013436672973448
                    #          = 102.0038253274749
                    with_fee=102.0038253274749,
                ),
            ),
            # Medium slippage trade - in_ is 10% of share reserves.
            (
                TestCaseCalcOutGivenInSuccess(
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
                TradeResult(
                    # Using the spot price, the expected output without slippage or fees is given by:
                    #   1.0250671833648672 * 10_000 = 10250.671833648672
                    without_fee_or_slippage=10250.671833648672,
                    # Since we are buying bonds, in_ is an amount of base and we calculate the fee using the spot price as:
                    #   fee = 0.01 * (p - 1) * 10_000 = 2.506718336486724
                    fee=2.506718336486724,
                    # We set up the problem as:
                    #   110_000 ** (1 - T) + (300_000 - d_y) ** (1 - T) = k
                    #
                    # Solving for d_y, we get the following calculation:
                    #   d_y = 300_000 - (k - 110_000 ** (1 - T)) ** (1 / (1 - T)) = 10235.514826394327
                    #
                    # Note that this is smaller than the without slippage value
                    without_fee=10235.514826394327,
                    # Combining the without_fee and the fee, we calculate with_fee as:
                    #   with_fee = 10235.514826394327 - 2.506718336486724 = 10233.00810805784
                    with_fee=10233.00810805784,
                ),
            ),
            # TODO: The slippage should arguably be much higher. This is something
            # we should consider more when thinking about the use of a time stretch
            # parameter.
            #
            # High slippage trade - in_ is 80% of share reserves.
            (
                TestCaseCalcOutGivenInSuccess(
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
                TradeResult(
                    # Using the spot price, the expected output without slippage or fees is given by:
                    #   1.0250671833648672 * 80_000 = 82005.37466918938
                    without_fee_or_slippage=82005.37466918938,
                    # Since we are buying bonds, in_ is an amount of base and we calculate the fee using the spot price as:
                    #   fee = 0.01 * (p - 1) * 80_000 = 20.053746691893792
                    fee=20.053746691893792,
                    # We set up the problem as:
                    #   180_000 ** (1 - T) + (300_000 - d_y) ** (1 - T) = k
                    #
                    # Solving for d_y, we get the following calculation:
                    #   d_y = 300_000 - (k - 180_000 ** (1 - T)) ** (1 / (1 - T)) = 81138.27602200207
                    #
                    # Note that this is smaller than the without slippage value
                    without_fee=81138.27602200207,
                    # Combining the without_fee and the fee, we calculate with_fee as:
                    #   with_fee = 81138.27602200207 - 20.053746691893792 = 81118.22227531018
                    with_fee=81118.22227531018,
                ),
            ),
            # Non-trivial initial share price and share price.
            (
                TestCaseCalcOutGivenInSuccess(
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
                TradeResult(
                    # Using the spot price, the expected output without slippage or fees is given by:
                    #   1.0223499142867662 * 200 = 204.46998285735324
                    without_fee_or_slippage=204.46998285735324,
                    # Since we are buying bonds, in_ is an amount of base and we calculate the fee using the spot price as:
                    #   fee = 0.01 * (p - 1) * 200 = 0.044699828573532496
                    fee=0.044699828573532496,
                    # We set up the problem as:
                    #   (2 / 1.5) * (1.5 * 100_100) ** (1 - T) + (400_000 - d_y) ** (1 - T) = k
                    #
                    # Solving for d_y, we get the following calculation:
                    #   d_y = 400_000 - (k - (2 / 1.5) * (1.5 * 100_100) ** (1 - T)) ** (1 / (1 - T)) = 204.46650180319557
                    #
                    # Note that this is slightly smaller than the without slippage value
                    without_fee=204.46650180319557,
                    # Combining the without_fee and the fee, we calculate with_fee as:
                    #   with_fee = 204.46650180319557 - 0.044699828573532496 = 204.42180197462204
                    with_fee=204.42180197462204,
                ),
            ),
            # Very unbalanced reserves.
            (
                TestCaseCalcOutGivenInSuccess(
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
                TradeResult(
                    # Using the spot price, the expected output without slippage or fees is given by:
                    #   1.0623907066406753 * 200 = 212.47814132813505
                    without_fee_or_slippage=212.47814132813505,
                    # Since we are buying bonds, in_ is an amount of base and we calculate the fee using the spot price as:
                    #   fee = 0.01 * (p - 1) * 200 = 0.1247814132813505
                    fee=0.1247814132813505,
                    # We set up the problem as:
                    #   (2 / 1.5) * (1.5 * 100_100) ** (1 - T) + (2_200_000 - d_y) ** (1 - T) = k
                    #
                    # Solving for d_y, we get the following calculation:
                    #   d_y = 2_200_000 - (k - (2 / 1.5) * (1.5 * 100_100) ** (1 - T)) ** (1 / (1 - T)) = 212.47551672440022
                    #
                    # Note that this is slightly smaller than the without slippage value
                    without_fee=212.47551672440022,
                    # Combining the without_fee and the fee, we calculate with_fee as:
                    #   with_fee = 212.47551672440022 - 0.1247814132813505 = 212.35073531111888
                    with_fee=212.35073531111888,
                ),
            ),
            # A term of a quarter year.
            (
                TestCaseCalcOutGivenInSuccess(
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
                TradeResult(
                    # Using the spot price, the expected output without slippage or fees is given by:
                    #   1.0307233899745727 * 200 = 206.14467799491453
                    without_fee_or_slippage=206.14467799491453,
                    # Since we are buying bonds, in_ is an amount of base and we calculate the fee using the spot price as:
                    #   fee = 0.01 * (p - 1) * 200 = 0.06144677994914538
                    fee=0.06144677994914538,
                    # We set up the problem as:
                    #   (2 / 1.5) * (1.5 * 100_100) ** (1 - T) + (2_200_000 - d_y) ** (1 - T) = k
                    #
                    # Solving for d_y, we get the following calculation:
                    #   d_y = 2_200_000 - (k - (2 / 1.5) * (1.5 * 100_100) ** (1 - T)) ** (1 / (1 - T)) = 206.14340814948082
                    #
                    # Note that this is slightly smaller than the without slippage value
                    without_fee=206.14340814948082,
                    # Combining the without_fee and the fee, we calculate with_fee as:
                    #   with_fee = 206.14340814948082 - 0.06144677994914538 = 206.08196136953168
                    with_fee=206.08196136953168,
                ),
            ),
            # A time stretch targetting 10% APY.
            (
                TestCaseCalcOutGivenInSuccess(
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
                TradeResult(
                    # Using the spot price, the expected output without slippage or fees is given by:
                    #   1.0623907066406753 * 200 = 212.47814132813505
                    without_fee_or_slippage=212.47814132813505,
                    # Since we are buying bonds, in_ is an amount of base and we calculate the fee using the spot price as:
                    #   fee = 0.01 * (p - 1) * 200 = 0.1247814132813505
                    fee=0.1247814132813505,
                    # We set up the problem as:
                    #   (2 / 1.5) * (1.5 * 100_100) ** (1 - T) + (2_200_000 - d_y) ** (1 - T) = k
                    #
                    # Solving for d_y, we get the following calculation:
                    #   d_y = 2_200_000 - (k - (2 / 1.5) * (1.5 * 100_100) ** (1 - T)) ** (1 / (1 - T)) = 212.47551672440022
                    #
                    # Note that this is slightly smaller than the without slippage value
                    without_fee=212.47551672440022,
                    # Combining the without_fee and the fee, we calculate with_fee as:
                    #   with_fee = 212.47551672440022 - 0.1247814132813505 = 212.35073531111888
                    with_fee=212.35073531111888,
                ),
            ),
        ]

        # Test cases where token_out = "base".
        base_out_test_cases = [
            # Low slippage trade - in_ is 0.1% of share reserves.
            (
                TestCaseCalcOutGivenInSuccess(
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
                TradeResult(
                    # Using the spot price, the expected output without slippage or fees is given by:
                    #   (1 / 1.0250671833648672) * 100 = 97.55458141947516
                    without_fee_or_slippage=97.55458141947516,
                    # Since we are buying bonds, in_ is an amount of base and we calculate the fee using the spot price as:
                    #   fee = 0.01 * (1 - (1 / p)) * 100 = 0.024454185805248493
                    fee=0.024454185805248493,
                    # We set up the problem as:
                    #   (100_000 - d_z) ** (1 - T) + 300_100 ** (1 - T) = k
                    #
                    # Solving for d_z, we get the following calculation:
                    #   d_z = 100_000 - (k - 300_100 ** (1 - T)) ** (1 / (1 - T)) = 97.55314236719278
                    #
                    # The output is d_x = c * d_z. Since c = 1, d_x = d_z.
                    # Note that this is slightly smaller than the without slippage value
                    without_fee=97.55314236719278,
                    # Combining the without_fee and the fee, we calculate with_fee as:
                    #   with_fee = 97.55314236719278 - 0.024454185805248493 = 97.52868818138752
                    with_fee=97.52868818138752,
                ),
            ),
            # High fee percentage - 20%.
            (
                TestCaseCalcOutGivenInSuccess(
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
                TradeResult(
                    # Using the spot price, the expected output without slippage or fees is given by:
                    #   (1 / 1.0250671833648672) * 100 = 97.55458141947516
                    without_fee_or_slippage=97.55458141947516,
                    # Since we are buying bonds, in_ is an amount of base and we calculate the fee using the spot price as:
                    #   fee = 0.2 * (1 - (1 / p)) * 100 = 0.5013436672973448
                    fee=0.48908371610497,
                    # We set up the problem as:
                    #   (100_000 - d_z) ** (1 - T) + 300_100 ** (1 - T) = k
                    #
                    # Solving for d_z, we get the following calculation:
                    #   d_z = 100_000 - (k - 300_100 ** (1 - T)) ** (1 / (1 - T)) = 97.55314236719278
                    #
                    # The output is d_x = c * d_z. Since c = 1, d_x = d_z.
                    # Note that this is slightly smaller than the without slippage value
                    without_fee=97.55314236719278,
                    # Combining the without_fee and the fee, we calculate with_fee as:
                    #   with_fee = 97.55314236719278 - 0.48908371610497 = 97.0640586510878
                    with_fee=97.0640586510878,
                ),
            ),
            # Medium slippage trade - in_ is 10% of share reserves.
            (
                TestCaseCalcOutGivenInSuccess(
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
                TradeResult(
                    # Using the spot price, the expected output without slippage or fees is given by:
                    #   (1 / 1.0250671833648672) * 10_000 = 9755.458141947514
                    without_fee_or_slippage=9755.458141947514,
                    # Since we are buying bonds, in_ is an amount of base and we calculate the fee using the spot price as:
                    #   fee = 0.01 * (1 - (1 / p)) * 10_000 = 2.4454185805248496
                    fee=2.4454185805248496,
                    # We set up the problem as:
                    #   (100_000 - d_z) ** (1 - T) + 310_000 ** (1 - T) = k
                    #
                    # Solving for d_z, we get the following calculation:
                    #   d_z = 100_000 - (k - 310_000 ** (1 - T)) ** (1 / (1 - T)) = 9740.77011591768
                    #
                    # The output is d_x = c * d_z. Since c = 1, d_x = d_z.
                    # Note that this is slightly smaller than the without slippage value
                    without_fee=9740.77011591768,
                    # Combining the without_fee and the fee, we calculate with_fee as:
                    #   with_fee = 9740.77011591768 - 2.4454185805248496 = 9738.324697337155
                    with_fee=9738.324697337155,
                ),
            ),
            # TODO: The slippage should arguably be much higher. This is something
            # we should consider more when thinking about the use of a time stretch
            # parameter.
            #
            # High slippage trade - in_ is 80% of share reserves.
            (
                TestCaseCalcOutGivenInSuccess(
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
                TradeResult(
                    # Using the spot price, the expected output without slippage or fees is given by:
                    #   (1 / 1.0250671833648672) * 80_000 = 78043.66513558012
                    without_fee_or_slippage=78043.66513558012,
                    # Since we are buying bonds, in_ is an amount of base and we calculate the fee using the spot price as:
                    #   fee = 0.01 * (1 - (1 / p)) * 80_000 = 19.563348644198797
                    fee=19.563348644198797,
                    # We set up the problem as:
                    #   (100_000 - d_z) ** (1 - T) + 380_000 ** (1 - T) = k
                    #
                    # Solving for d_z, we get the following calculation:
                    #   d_z = 100_000 - (k - 380_000 ** (1 - T)) ** (1 / (1 - T)) = 76850.14470187116
                    #
                    # The output is d_x = c * d_z. Since c = 1, d_x = d_z.
                    # Note that this is slightly smaller than the without slippage value
                    without_fee=76850.14470187116,
                    # Combining the without_fee and the fee, we calculate with_fee as:
                    #   with_fee = 76850.14470187116 - 19.563348644198797 = 76830.58135322697
                    with_fee=76830.58135322697,
                ),
            ),
            # Non-trivial initial share price and share price.
            (
                TestCaseCalcOutGivenInSuccess(
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
                TradeResult(
                    # Using the spot price, the expected output without slippage or fees is given by:
                    #   (1 / 1.0223499142867662) * 100 = 97.813868424652
                    without_fee_or_slippage=97.813868424652,
                    # Since we are buying bonds, in_ is an amount of base and we calculate the fee using the spot price as:
                    #   fee = 0.01 * (1 - (1 / p)) * 100 = 0.02186131575348005
                    fee=0.02186131575348005,
                    # We set up the problem as:
                    #   (2 / 1.5) * (1.5 * (100_000 - d_z)) ** (1 - T) + 400_100 ** (1 - T) = k
                    #
                    # Solving for d_z, we get the following calculation:
                    #   d_z = 100_000 - (1 / 1.5) * ((1.5 / 2) * (k - 400_100 ** (1 - T))) ** (1 / (1 - T)) = 48.906526897713775
                    #
                    # The output is d_x = c * d_z = 2 * 48.906526897713775 = 97.81305379542755.
                    # Note that this is slightly smaller than the without slippage value
                    without_fee=97.81305379542755,
                    # Combining the without_fee and the fee, we calculate with_fee as:
                    #   with_fee = 97.81305379542755 - 0.02186131575348005 = 97.79119247967407
                    with_fee=97.79119247967407,
                ),
            ),
            # Very unbalanced reserves.
            (
                TestCaseCalcOutGivenInSuccess(
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
                TradeResult(
                    # Using the spot price, the expected output without slippage or fees is given by:
                    #   (1 / 1.0623907066406753) * 100 = 94.1273294042681
                    without_fee_or_slippage=94.1273294042681,
                    # Since we are buying bonds, in_ is an amount of base and we calculate the fee using the spot price as:
                    #   fee = 0.01 * (1 - (1 / p)) * 100 = 0.05872670595731899
                    fee=0.05872670595731899,
                    # We set up the problem as:
                    #   (2 / 1.5) * (1.5 * (100_000 - d_z)) ** (1 - T) + 2_200_100 ** (1 - T) = k
                    #
                    # Solving for d_z, we get the following calculation:
                    #   d_z = 100_000 - (1 / 1.5) * ((1.5 / 2) * (k - 2_200_100 ** (1 - T))) ** (1 / (1 - T)) = 47.06339097737509
                    #
                    # The output is d_x = c * d_z = 2 * 47.06339097737509 = 94.12678195475019.
                    # Note that this is slightly smaller than the without slippage value
                    without_fee=94.12678195475019,
                    # Combining the without_fee and the fee, we calculate with_fee as:
                    #   with_fee = 94.12678195475019 - 0.05872670595731899 = 94.06805524879287
                    with_fee=94.06805524879287,
                ),
            ),
            # A term of a quarter year.
            (
                TestCaseCalcOutGivenInSuccess(
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
                TradeResult(
                    # Using the spot price, the expected output without slippage or fees is given by:
                    #   (1 / 1.0307233899745727) * 100 = 97.0192400528205
                    without_fee_or_slippage=97.0192400528205,
                    # Since we are buying bonds, in_ is an amount of base and we calculate the fee using the spot price as:
                    #   fee = 0.01 * (1 - (1 / p)) * 100 = 0.0298075994717949
                    fee=0.0298075994717949,
                    # We set up the problem as:
                    #   (2 / 1.5) * (1.5 * (100_000 - d_z)) ** (1 - T) + 2_200_100 ** (1 - T) = k
                    #
                    # Solving for d_z, we get the following calculation:
                    #   d_z = 100_000 - (1 / 1.5) * ((1.5 / 2) * (k - 2_200_100 ** (1 - T))) ** (1 / (1 - T)) = 48.50947500564507
                    #
                    # The output is d_x = c * d_z = 2 * 48.50947500564507 = 97.01895001129014.
                    # Note that this is slightly smaller than the without slippage value
                    without_fee=97.01895001129014,
                    # Combining the without_fee and the fee, we calculate with_fee as:
                    #   with_fee = 97.01895001129014 - 0.0298075994717949 = 96.98914241181835
                    with_fee=96.98914241181835,
                ),
            ),
            # A time stretch targetting 10% APY.
            (
                TestCaseCalcOutGivenInSuccess(
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
                TradeResult(
                    # Using the spot price, the expected output without slippage or fees is given by:
                    #   (1 / 1.0623907066406753) * 100 = 94.1273294042681
                    without_fee_or_slippage=94.1273294042681,
                    # Since we are buying bonds, in_ is an amount of base and we calculate the fee using the spot price as:
                    #   fee = 0.01 * (1 - (1 / p)) * 100 = 0.05872670595731899
                    fee=0.05872670595731899,
                    # We set up the problem as:
                    #   (2 / 1.5) * (1.5 * (100_000 - d_z)) ** (1 - T) + 2_200_100 ** (1 - T) = k
                    #
                    # Solving for d_z, we get the following calculation:
                    #   d_z = 100_000 - (1 / 1.5) * ((1.5 / 2) * (k - 2_200_100 ** (1 - T))) ** (1 / (1 - T)) = 47.06339097737509
                    #
                    # The output is d_x = c * d_z = 2 * 47.06339097737509 = 94.12678195475019.
                    # Note that this is slightly smaller than the without slippage value
                    without_fee=94.12678195475019,
                    # Combining the without_fee and the fee, we calculate with_fee as:
                    #   with_fee = 94.12678195475019 - 0.05872670595731899 = 94.06805524879287
                    with_fee=94.06805524879287,
                ),
            ),
        ]

        # Iterate over all of the test cases and verify that the pricing model
        # produces the expected outputs for each test case.
        test_cases = pt_out_test_cases + base_out_test_cases
        for (
            test_case,
            expected,
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
            expected.compare_trade_results(TradeResult(without_fee_or_slippage, with_fee, without_fee, fee))

    def test_calc_out_given_in_failure(self):
        pricing_model = HyperdrivePricingModel(False)

        # Failure test cases.
        test_cases = [
            (
                TestCaseCalcOutGivenInFailure(
                    in_=-1,
                    share_reserves=100_000,
                    bond_reserves=1_000_000,
                    token_out="base",
                    fee_percent=0.01,
                    time_remaining=0.25,
                    share_price=2,
                    init_share_price=1.5,
                ),
                "pricing_models.calc_out_given_in: ERROR: expected in_ > 0, not -1!",
            ),
            (
                TestCaseCalcOutGivenInFailure(
                    in_=0,
                    share_reserves=100_000,
                    bond_reserves=1_000_000,
                    token_out="base",
                    fee_percent=0.01,
                    time_remaining=0.25,
                    share_price=2,
                    init_share_price=1.5,
                ),
                "pricing_models.calc_out_given_in: ERROR: expected in_ > 0, not 0!",
            ),
            (
                TestCaseCalcOutGivenInFailure(
                    in_=100,
                    share_reserves=-1,
                    bond_reserves=1_000_000,
                    token_out="base",
                    fee_percent=0.01,
                    time_remaining=0.25,
                    share_price=2,
                    init_share_price=1.5,
                ),
                "pricing_models.calc_out_given_in: ERROR: expected share_reserves > 0, not -1!",
            ),
            (
                TestCaseCalcOutGivenInFailure(
                    in_=100,
                    share_reserves=0,
                    bond_reserves=1_000_000,
                    token_out="base",
                    fee_percent=0.01,
                    time_remaining=0.25,
                    share_price=2,
                    init_share_price=1.5,
                ),
                "pricing_models.calc_out_given_in: ERROR: expected share_reserves > 0, not 0!",
            ),
            (
                TestCaseCalcOutGivenInFailure(
                    in_=100,
                    share_reserves=100_000,
                    bond_reserves=-1,
                    token_out="base",
                    fee_percent=0.01,
                    time_remaining=0.25,
                    share_price=2,
                    init_share_price=1.5,
                ),
                "pricing_models.calc_out_given_in: ERROR: expected bond_reserves > 0, not -1!",
            ),
            (
                TestCaseCalcOutGivenInFailure(
                    in_=100,
                    share_reserves=100_000,
                    bond_reserves=0,
                    token_out="base",
                    fee_percent=0.01,
                    time_remaining=0.25,
                    share_price=2,
                    init_share_price=1.5,
                ),
                "pricing_models.calc_out_given_in: ERROR: expected bond_reserves > 0, not 0!",
            ),
            (
                TestCaseCalcOutGivenInFailure(
                    in_=100,
                    share_reserves=100_000,
                    bond_reserves=1_000_000,
                    token_out="base",
                    fee_percent=-1,
                    time_remaining=0.25,
                    share_price=2,
                    init_share_price=1.5,
                ),
                "pricing_models.calc_out_given_in: ERROR: expected 1 >= fee_percent >= 0, not -1!",
            ),
            (
                TestCaseCalcOutGivenInFailure(
                    in_=100,
                    share_reserves=100_000,
                    bond_reserves=1_000_000,
                    token_out="base",
                    fee_percent=1.1,
                    time_remaining=0.25,
                    share_price=2,
                    init_share_price=1.5,
                ),
                "pricing_models.calc_out_given_in: ERROR: expected 1 >= fee_percent >= 0, not 1.1!",
            ),
            (
                TestCaseCalcOutGivenInFailure(
                    in_=100,
                    share_reserves=100_000,
                    bond_reserves=1_000_000,
                    token_out="base",
                    fee_percent=0.01,
                    time_remaining=-1,
                    share_price=2,
                    init_share_price=1.5,
                ),
                "pricing_models.calc_out_given_in: ERROR: expected 1 > time_remaining >= 0, not -1!",
            ),
            (
                TestCaseCalcOutGivenInFailure(
                    in_=100,
                    share_reserves=100_000,
                    bond_reserves=1_000_000,
                    token_out="base",
                    fee_percent=0.01,
                    time_remaining=1,
                    share_price=2,
                    init_share_price=1.5,
                ),
                "pricing_models.calc_out_given_in: ERROR: expected 1 > time_remaining >= 0, not 1!",
            ),
            (
                TestCaseCalcOutGivenInFailure(
                    in_=100,
                    share_reserves=100_000,
                    bond_reserves=1_000_000,
                    token_out="base",
                    fee_percent=0.01,
                    time_remaining=1.1,
                    share_price=2,
                    init_share_price=1.5,
                ),
                "pricing_models.calc_out_given_in: ERROR: expected 1 > time_remaining >= 0, not 1.1!",
            ),
            (
                TestCaseCalcOutGivenInFailure(
                    in_=100,
                    share_reserves=100_000,
                    bond_reserves=1_000_000,
                    token_out="base",
                    fee_percent=0.01,
                    time_remaining=0.25,
                    share_price=2,
                    init_share_price=0,
                ),
                "pricing_models.calc_out_given_in: ERROR: expected share_price >= init_share_price >= 1, not share_price=2 and init_share_price=0!",
            ),
            (
                TestCaseCalcOutGivenInFailure(
                    in_=100,
                    share_reserves=100_000,
                    bond_reserves=1_000_000,
                    token_out="base",
                    fee_percent=0.01,
                    time_remaining=0.25,
                    share_price=1,
                    init_share_price=1.5,
                ),
                "pricing_models.calc_out_given_in: ERROR: expected share_price >= init_share_price >= 1, not share_price=1 and init_share_price=1.5!",
            ),
            (
                TestCaseCalcOutGivenInFailure(
                    in_=100,
                    share_reserves=100_000,
                    bond_reserves=1_000_000,
                    token_out="base",
                    fee_percent=0.01,
                    time_remaining=0.25,
                    share_price=0,
                    init_share_price=1.5,
                ),
                "pricing_models.calc_out_given_in: ERROR: expected share_price >= init_share_price >= 1, not share_price=0 and init_share_price=1.5!",
            ),
            (
                TestCaseCalcOutGivenInFailure(
                    in_=100,
                    share_reserves=100_000,
                    bond_reserves=1_000_000,
                    token_out="fyt",
                    fee_percent=0.01,
                    time_remaining=0.25,
                    share_price=2,
                    init_share_price=1.5,
                ),
                'pricing_models.calc_out_given_in: ERROR: expected token_out == "base" or token_out == "pt", not fyt!',
            ),
            (
                TestCaseCalcOutGivenInFailure(
                    in_=10_000_000,
                    share_reserves=100_000,
                    bond_reserves=1_000_000,
                    token_out="pt",
                    fee_percent=0.01,
                    time_remaining=0.25,
                    share_price=2,
                    init_share_price=1.5,
                ),
                "pricing_models.calc_out_given_in: ERROR: with_fee should be a float, not <class 'complex'>!",
            ),
        ]

        # Iterate over all of the test cases and verify that the pricing model
        # raises the expected AssertionError for each test case.
        for (test_case, expected_error_message) in test_cases:
            with self.assertRaisesRegex(AssertionError, expected_error_message):
                pricing_model.calc_out_given_in(
                    test_case.in_,
                    test_case.share_reserves,
                    test_case.bond_reserves,
                    test_case.token_out,
                    test_case.fee_percent,
                    test_case.time_remaining,
                    test_case.init_share_price,
                    test_case.share_price,
                )

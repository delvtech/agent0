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
            (
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
                ),  # expected: without_fee_or_slippage, with_fee, without_fee, fee
                # slippage is 0.001439052282364628
            ),
        ]
        for [test_case, expected] in test_cases:
            time_stretch = pricing_model.calc_time_stretch(test_case.time_stretch_apy)
            time_remaining = pricing_model._stretch_time(
                pricing_model.days_to_time_remaining(test_case.days_remaining), time_stretch
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
            actual = TradeResult(without_fee_or_slippage, with_fee, without_fee, fee)
            compare_trade_results(actual, expected)

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
                # - k = 302929.51067963685
                (
                    # Using the spot price, the expected output without slippage or fees is given by:
                    #   1.0250671833648672 * 100 = 102.50671833648673
                    102.50671833648673,
                    # Combining the without_fee and the fee, we calculate with_fee as:
                    #   with_fee = 102.50516899477225 - 0.02506718336486724
                    102.48010181140738,
                    # We set up the problem as:
                    #   100_100 ^ (1 - T) + (300_000 - d_y) ^ (1 - T) = k
                    #
                    # Solving for d_y, we get the following calculation:
                    #   d_y = 300_000 - (k - 100_100 ^ (1 - T)) ^ (1 / (1 - T)) = 102.50516899477225
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
                # - k = 302929.51067963685
                (
                    # Using the spot price, the expected output without slippage or fees is given by:
                    #   1.0250671833648672 * 100 = 102.50671833648673
                    102.50671833648673,
                    # Combining the without_fee and the fee, we calculate with_fee as:
                    #   with_fee = 102.50516899477225 - 0.5013436672973448 = 102.0038253274749
                    102.0038253274749,
                    # We set up the problem as:
                    #   100_100 ^ (1 - T) + (300_000 - d_y) ^ (1 - T) = k
                    #
                    # Solving for d_y, we get the following calculation:
                    #   d_y = 300_000 - (k - 100_100 ^ (1 - T)) ^ (1 / (1 - T)) = 102.50516899477225
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
                # - k = 302929.51067963685
                (
                    # Using the spot price, the expected output without slippage or fees is given by:
                    #   1.0250671833648672 * 10_000 = 10250.671833648672
                    10250.671833648672,
                    # Combining the without_fee and the fee, we calculate with_fee as:
                    #   with_fee = 10235.514826394327 - 2.506718336486724 = 10233.00810805784
                    10233.00810805784,
                    # We set up the problem as:
                    #   110_000 ^ (1 - T) + (300_000 - d_y) ^ (1 - T) = k
                    #
                    # Solving for d_y, we get the following calculation:
                    #   d_y = 300_000 - (k - 110_000 ^ (1 - T)) ^ (1 / (1 - T)) = 10235.514826394327
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
                # - k = 302929.51067963685
                (
                    # Using the spot price, the expected output without slippage or fees is given by:
                    #   1.0250671833648672 * 80_000 = 82005.37466918938
                    82005.37466918938,
                    # Combining the without_fee and the fee, we calculate with_fee as:
                    #   with_fee = 81138.27602200207 - 20.053746691893792 = 81118.22227531018
                    81118.22227531018,
                    # We set up the problem as:
                    #   180_000 ^ (1 - T) + (300_000 - d_y) ^ (1 - T) = k
                    #
                    # Solving for d_y, we get the following calculation:
                    #   d_y = 300_000 - (k - 180_000 ^ (1 - T)) ^ (1 / (1 - T)) = 81138.27602200207
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
                # - k = 451988.7122137336
                (
                    # Using the spot price, the expected output without slippage or fees is given by:
                    #   1.0223499142867662 * 200 = 204.46998285735324
                    204.46998285735324,
                    # Combining the without_fee and the fee, we calculate with_fee as:
                    #   with_fee = 204.46650180319557 - 0.044699828573532496 = 204.42180197462204
                    204.42180197462204,
                    # We set up the problem as:
                    #   (2 / 1.5) * (1.5 * 100_100) ^ (1 - T) + (400_000 - d_y) ^ (1 - T) = k
                    #
                    # Solving for d_y, we get the following calculation:
                    #   d_y = 400_000 - (k - (2 / 1.5) * (1.5 * 100_100) ^ (1 - T)) ^ (1 / (1 - T)) = 204.46650180319557
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
                # - k = 2_303_312.315329303
                (
                    # Using the spot price, the expected output without slippage or fees is given by:
                    #   1.0623907066406753 * 200 = 212.47814132813505
                    212.47814132813505,
                    # Combining the without_fee and the fee, we calculate with_fee as:
                    #   with_fee = 212.47551672440022 - 0.1247814132813505 = 212.35073531111888
                    212.35073531111888,
                    # We set up the problem as:
                    #   (2 / 1.5) * (1.5 * 100_100) ^ (1 - T) + (2_200_000 - d_y) ^ (1 - T) = k
                    #
                    # Solving for d_y, we get the following calculation:
                    #   d_y = 2_200_000 - (k - (2 / 1.5) * (1.5 * 100_100) ^ (1 - T)) ^ (1 / (1 - T)) = 212.47551672440022
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
        base_out_test_cases = []

        # Iterate over all of the test cases and verify that the pricing model
        # produces the expected outputs for each test case.
        test_cases = pt_out_test_cases + base_out_test_cases
        for (
            test_case,
            (expected_without_fee_or_slippage, expected_with_fee, expected_without_fee, expected_fee),
        ) in test_cases:
            time_stretch = pricing_model.calc_time_stretch(test_case.time_stretch_apy)
            time_remaining = pricing_model._stretch_time(
                pricing_model.days_to_time_remaining(test_case.days_remaining), time_stretch
            )

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

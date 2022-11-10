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
    __test__ = False

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
    __test__ = False

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


class TestHyperdrivePricingModel(unittest.TestCase):
    def test_calc_in_given_out(self):
        pricing_model = HyperdrivePricingModel(False)
        test_cases = []
        for [
            test_case,
            (expected_without_fee_or_slippage, expected_with_fee, expected_without_fee, expected_fee),
        ] in test_cases:
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
            assert without_fee_or_slippage == expected_without_fee_or_slippage
            assert with_fee == expected_with_fee
            assert without_fee == expected_without_fee
            assert fee == expected_fee

    def test_calc_out_given_in(self):
        pricing_model = HyperdrivePricingModel(False)
        test_cases = [
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
                    #   1.0250671833648672 * 100 = 102.50671833648673 (using python precision).
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
        ]
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

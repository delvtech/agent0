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
            # FIXME: Use the correct output.
            #
            # (
            #     TestCaseCalcOutGivenIn(
            #         in_=100,
            #         share_reserves=100_000,
            #         bond_reserves=100_000,
            #         token_out="pt",
            #         fee_percent=0.01,
            #         days_remaining=182.5,
            #         time_stretch_apy=0.05,
            #         share_price=1,
            #         init_share_price=1,
            #     ),
            #     (0, 0, 0, 0),
            # ),
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
            assert without_fee_or_slippage == expected_without_fee_or_slippage
            assert with_fee == expected_with_fee
            assert without_fee == expected_without_fee
            assert fee == expected_fee

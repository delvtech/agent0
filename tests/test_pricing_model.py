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


class TestHyperdrivePricingModel(unittest.TestCase):
    def test_calc_in_given_out(self):
        # FIXME
        return ()

    # FIXME: Apply real asserts.
    #
    # FIXME: Use table driven testing.
    def test_calc_out_given_in(self):
        # Set up the pricing model.
        pricing_model = HyperdrivePricingModel(False)

        # Set up the testing values.
        in_ = 100
        share_reserves = 100_000
        bond_reserves = 100_000
        token_out = "pt"
        fee_percent = 0.01
        days_remaining = 182.5
        time_stretch = pricing_model.calc_time_stretch(0.05)
        time_remaining = pricing_model._stretch_time(pricing_model.days_to_time_remaining(days_remaining), time_stretch)
        init_share_price = 1
        share_price = 1

        print(f"\n\ttime_remaining={time_remaining}" f"\n\t1/1-time_remaining={1/(1 - time_remaining)}")

        bond_reserves_ = 2 * bond_reserves + share_price * share_reserves
        k = (share_price / init_share_price) * (init_share_price * share_reserves) ** (1 - time_remaining) + (
            bond_reserves_
        ) ** (1 - time_remaining)
        share_reserves_ = (share_reserves + in_) ** (1 - time_remaining)

        print(
            f"\n\tk = {k}"
            f"\n\tshare_reserves_ = {share_reserves_}"
            f"\n\tk - share_reserves_ = {k  - share_reserves_}"
            f"\n\t(k - share_reserves_) ** (1 / (1 - t)) = {(k  - share_reserves_) ** (1 / (1 - time_remaining))}"
            f"\n\tbond_reserves_ - (k - share_reserves_) ** (1 / (1 - t)) = {bond_reserves_ - (k  - share_reserves_) ** (1 / (1 - time_remaining))}"
        )

        # Calculate the amount of bonds purchased.
        (without_fee_or_slippage, with_fee, without_fee, fee) = pricing_model.calc_out_given_in(
            in_,
            share_reserves,
            bond_reserves,
            token_out,
            fee_percent,
            time_remaining,
            init_share_price,
            share_price,
        )

        # FIXME: Use real assertions.
        print(
            f"\n\twithout_fee_or_slippage={without_fee_or_slippage}"
            f"\n\twith_fee={with_fee}"
            f"\n\twithout_fee={without_fee}"
            f"\n\tfee={fee}"
        )

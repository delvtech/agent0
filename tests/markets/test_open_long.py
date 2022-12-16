"""Tests that cover the open_long action in the market"""

import unittest

from elfpy.markets import Market
from elfpy.pricing_models.hyperdrive import HyperdrivePricingModel
from elfpy.types import MarketAction, MarketState, Quantity, StretchedTime
import elfpy.utils.price as price_utils


class TestOpenLong(unittest.TestCase):
    """Unit tests for the open_long action"""

    # TODO: Flesh out the test to include edge cases and more varied inputs.
    def test_open_long(self):
        """Tests for the open long action"""

        pricing_model = HyperdrivePricingModel()

        # Set up the testing inputs.
        wallet_address = 1337
        mint_time = 1234
        fee_percent = 0.1
        apr = 0.05
        share_reserves = 100_000
        position_duration = StretchedTime(days=365, time_stretch=pricing_model.calc_time_stretch(apr=0.05))
        trade_amount = 1_000
        market_state = MarketState(
            share_reserves=share_reserves,
            bond_reserves=price_utils.calc_bond_reserves(
                apr=apr,
                share_reserves=share_reserves,
                time_remaining=position_duration,
                init_share_price=1.0,
                share_price=1.0,
            ),
        )

        # Apply the trade to the market and pricing model.
        trade_result = pricing_model.calc_out_given_in(
            in_=Quantity(amount=trade_amount, unit="base"),
            market_state=market_state,
            fee_percent=fee_percent,
            time_remaining=position_duration,
        )
        market = Market(
            fee_percent=fee_percent,
            market_state=market_state,
            position_duration=position_duration,
        )
        (market_deltas, wallet_deltas) = market._open_long(
            pricing_model=pricing_model,
            agent_action=MarketAction(
                action_type="open_long",
                trade_amount=trade_amount,
                wallet_address=wallet_address,
                mint_time=mint_time,
            ),
            time_remaining=market.position_duration,
        )

        # Sanity check that the trade makes sense.
        implied_apr = (abs(trade_result.user_result.d_bonds) - abs(trade_result.user_result.d_base)) / (
            abs(trade_result.user_result.d_base) * position_duration.normalized_time
        )
        self.assertGreater(
            apr,
            implied_apr,
        )

        # Verify the market deltas
        self.assertEqual(
            market_deltas.d_share_reserves,
            trade_result.market_result.d_shares,
        )
        self.assertEqual(
            market_deltas.d_bond_reserves,
            trade_result.market_result.d_bonds,
        )
        self.assertEqual(
            market_deltas.d_share_buffer,
            -trade_result.market_result.d_bonds,
        )
        self.assertEqual(
            market_deltas.d_bond_buffer,
            0.0,
        )
        self.assertEqual(
            market_deltas.d_lp_reserves,
            0.0,
        )

        # Verify the wallet deltas
        self.assertEqual(
            wallet_deltas.address,
            wallet_address,
        )
        self.assertEqual(
            wallet_deltas.base_in_wallet,
            trade_result.user_result.d_base,
        )
        self.assertEqual(
            wallet_deltas.lp_in_wallet,
            0.0,
        )
        # FIXME: One of the first orders of business should be fixing up the
        #        naming in the wallet. I have no idea what token_in_wallet is
        #        supposed to represent.
        self.assertEqual(
            wallet_deltas.token_in_wallet,
            {},
        )
        self.assertEqual(
            wallet_deltas.base_in_protocol,
            {},
        )
        self.assertEqual(
            wallet_deltas.token_in_protocol,
            {mint_time: trade_result.user_result.d_bonds},
        )
        # FIXME: Why is the effective price 0?
        self.assertEqual(
            wallet_deltas.effective_price,
            0.0,
        )

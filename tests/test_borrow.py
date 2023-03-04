"""Testing the Borrow Market"""

import logging
import itertools
import unittest

import numpy as np
from elfpy.time.time import BlockTime

import elfpy.types as types
import elfpy.utils.outputs as output_utils
import elfpy.markets.borrow as borrow_market


class TestBorrow(unittest.TestCase):
    """Testing the Borrow Market"""

    def test_open_borrow(self, delete_logs=True):
        """Borrow 100 BASE"""
        output_utils.setup_logging(log_filename=".logging/test_borrow.log", log_level=logging.DEBUG)
        for loan_to_value, collateral_exponent, collateral_token in itertools.product(
            range(1, 100, 5), range(0, 8, 2), types.TokenType
        ):
            spot_price_range = [1]
            if collateral_token == types.TokenType.PT:
                spot_price_range = np.arange(0.01, 1.01, 0.05)
            for spot_price in spot_price_range:
                collateral_amount = 10**collateral_exponent
                collateral = types.Quantity(unit=collateral_token, amount=collateral_amount)
                loan_to_value_ratios = {
                    types.TokenType.BASE: loan_to_value / 100,
                    types.TokenType.PT: loan_to_value / 100,
                }
                borrow = borrow_market.Market(
                    pricing_model=borrow_market.PricingModel(),
                    block_time=BlockTime(),
                    market_state=borrow_market.MarketState(loan_to_value_ratio=loan_to_value_ratios),
                )
                market_deltas, agent_deltas = borrow.calc_open_borrow(
                    wallet_address=1,
                    collateral=collateral,
                    spot_price=spot_price,
                )
                expected_borrow_amount = collateral_amount * loan_to_value / 100 * spot_price
                logging.debug(
                    "LTV=%g, collateral=%g -> expect=%g\n\tactual = (mkt=%g, borrowed_amount_into_agent=%g)",
                    loan_to_value,
                    collateral_amount,
                    expected_borrow_amount,
                    market_deltas.d_borrow_shares,
                    agent_deltas.borrows[0].borrow_amount,
                )
                np.testing.assert_almost_equal(market_deltas.d_borrow_shares, expected_borrow_amount)
                np.testing.assert_almost_equal(agent_deltas.borrows[0].borrow_amount, expected_borrow_amount)
                if delete_logs:
                    output_utils.close_logging()

    def test_close_borrow(self):
        """Borrow 100 BASE"""

        # TODO: add more test cases
        collateral_amount = 100
        collateral = types.Quantity(unit=types.TokenType.BASE, amount=collateral_amount)
        loan_to_value = 1

        # borrow is always in DAI, this allows tracking the increasing value of loans over time
        borrow = borrow_market.Market(
            pricing_model=borrow_market.PricingModel(),
            block_time=BlockTime(),
            market_state=borrow_market.MarketState(
                loan_to_value_ratio={types.TokenType.BASE: loan_to_value},
                borrow_shares=100,
                collateral={},
                borrow_outstanding=100,  # sum of Dai that went out the door
                borrow_closed_interest=0.0,  # interested collected from closed borrows
            ),
        )

        market_deltas = borrow.calc_close_borrow(
            wallet_address=1,
            collateral=collateral,
            spot_price=0.9,
        )[0]

        expected_d_borrow_shares: float = -100  # borrow is always in DAI
        expected_d_collateral = types.Quantity(amount=-100, unit=types.TokenType.BASE)
        expected_d_borrow_closed_interest: float = 0  # realized interest from closed borrows

        self.assertEqual(expected_d_borrow_shares, market_deltas.d_borrow_shares)
        self.assertEqual(expected_d_collateral, market_deltas.d_collateral)
        self.assertEqual(expected_d_borrow_shares, market_deltas.d_borrow_shares)
        self.assertEqual(expected_d_borrow_closed_interest, market_deltas.d_borrow_closed_interest)


if __name__ == "__main__":
    unittest.main()

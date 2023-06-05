"""Testing the Borrow Market"""

import itertools
import logging
import unittest

import numpy as np
from elfpy.markets.borrow import BorrowPricingModel, BorrowMarketState

import elfpy.time as time
import elfpy.types as types
import elfpy.utils.outputs as output_utils

from elfpy.markets.borrow import BorrowMarket
from elfpy.math import FixedPoint


class TestBorrow(unittest.TestCase):
    """Testing the Borrow Market"""

    APPROX_EQ: FixedPoint = FixedPoint(1e-6)

    def test_open_borrow(self, delete_logs=True):
        """Borrow 100 BASE"""
        output_utils.setup_logging(log_filename=".logging/test_borrow.log", log_level=logging.DEBUG)
        for loan_to_value, collateral_exponent, collateral_token in itertools.product(
            range(1, 100, 5), range(0, 8, 2), [types.TokenType.BASE, types.TokenType.PT]
        ):
            if collateral_token == types.TokenType.PT:
                spot_price_range = np.arange(0.01, 1.01, 0.05)
            else:
                spot_price_range = np.array([1.0])
            for spot_price in spot_price_range:
                spot_price = spot_price.item()  # convert from Numpy type to Python type
                collateral_amount = FixedPoint(10**collateral_exponent)
                collateral = types.Quantity(unit=collateral_token, amount=collateral_amount)
                loan_to_value_ratios = {
                    types.TokenType.BASE: FixedPoint(loan_to_value / 100),
                    types.TokenType.PT: FixedPoint(loan_to_value / 100),
                }
                borrow = BorrowMarket(
                    pricing_model=BorrowPricingModel(),
                    block_time=time.BlockTime(),
                    market_state=BorrowMarketState(loan_to_value_ratio=loan_to_value_ratios),
                )
                market_deltas, agent_deltas = borrow.calc_open_borrow(
                    collateral=collateral,
                    spot_price=FixedPoint(spot_price),
                )
                expected_borrow_amount = collateral_amount * FixedPoint(loan_to_value / 100) * FixedPoint(spot_price)
                logging.debug(
                    "LTV=%s, collateral=%s -> expect=%s\n\tactual = (mkt=%s, borrowed_amount_into_agent=%s)",
                    loan_to_value,
                    collateral_amount,
                    expected_borrow_amount,
                    market_deltas.d_borrow_shares,
                    agent_deltas.borrows[FixedPoint(0)].borrow_amount,
                )
                self.assertAlmostEqual(market_deltas.d_borrow_shares, expected_borrow_amount, delta=self.APPROX_EQ)
                self.assertAlmostEqual(
                    agent_deltas.borrows[FixedPoint(0)].borrow_amount, expected_borrow_amount, delta=self.APPROX_EQ
                )
                if delete_logs:
                    output_utils.close_logging()

    def test_close_borrow(self):
        """Borrow 100 BASE"""

        # TODO: add more test cases
        collateral_amount = FixedPoint("100.0")
        collateral = types.Quantity(unit=types.TokenType.BASE, amount=collateral_amount)
        loan_to_value = FixedPoint("1.0")

        # borrow is always in DAI, this allows tracking the increasing value of loans over time
        borrow = BorrowMarket(
            pricing_model=BorrowPricingModel(),
            block_time=time.BlockTime(),
            market_state=BorrowMarketState(
                loan_to_value_ratio={types.TokenType.BASE: loan_to_value},
                borrow_shares=FixedPoint("100.0"),
                collateral={},
                borrow_outstanding=FixedPoint("100.0"),  # sum of Dai that went out the door
                borrow_closed_interest=FixedPoint(0),  # interested collected from closed borrows
            ),
        )

        market_deltas = borrow.calc_close_borrow(
            collateral=collateral,
            spot_price=FixedPoint("0.9"),
        )[0]

        expected_d_borrow_shares: FixedPoint = FixedPoint("-100.0")  # borrow is always in DAI
        expected_d_collateral = types.Quantity(unit=types.TokenType.BASE, amount=FixedPoint("-100.0"))
        expected_d_borrow_closed_interest: FixedPoint = FixedPoint(0)  # realized interest from closed borrows

        self.assertEqual(expected_d_borrow_shares, market_deltas.d_borrow_shares)
        self.assertEqual(expected_d_collateral, market_deltas.d_collateral)
        self.assertEqual(expected_d_borrow_shares, market_deltas.d_borrow_shares)
        self.assertEqual(expected_d_borrow_closed_interest, market_deltas.d_borrow_closed_interest)


if __name__ == "__main__":
    unittest.main()

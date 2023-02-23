"""Testing the Borrow Market"""

import itertools
import unittest

import numpy as np

import elfpy.types as types
from elfpy.markets.borrow import Market as BorrowMarket
from elfpy.markets.borrow import MarketState as BorrowMarketState


class TestBorrow(unittest.TestCase):
    """Testing the Borrow Market"""

    def test_open_borrow(self):
        """Borrow 100 BASE"""

        for loan_to_value, collateral_exponent in itertools.product(range(1, 100), range(8)):
            for collateral_token in types.TokenType:
                spot_price_range = [1]
                if collateral_token == types.TokenType.PT:
                    spot_price_range = np.arange(0.01, 1.01, 0.01)
                for spot_price in spot_price_range:
                    collateral_amount = 10**collateral_exponent
                    collateral = types.Quantity(unit=collateral_token, amount=collateral_amount)

                    loan_to_value_ratios = {
                        types.TokenType.BASE: loan_to_value / 100,
                        types.TokenType.PT: loan_to_value / 100,
                    }
                    borrow_market = BorrowMarket(
                        market_state=BorrowMarketState(loan_to_value_ratio=loan_to_value_ratios)
                    )

                    market_deltas, agent_deltas = borrow_market.open_borrow(
                        wallet_address=1,
                        collateral=collateral,
                        spot_price=spot_price,
                    )

                    borrowed_amount_into_market = market_deltas.d_borrow_shares
                    borrowed_amount_into_agent = agent_deltas.borrow

                    expected_borrow_amount = collateral_amount * loan_to_value / 100 * spot_price

                    print(
                        f"LTV={loan_to_value}, collateral={collateral_amount} -> "
                        f"expect={expected_borrow_amount} actual=(mkt={borrowed_amount_into_market}"
                        f" 🤖{borrowed_amount_into_agent})"
                    )

                    np.testing.assert_almost_equal(borrowed_amount_into_market, expected_borrow_amount)
                    np.testing.assert_almost_equal(borrowed_amount_into_agent, expected_borrow_amount)

    def test_close_borrow(self):
        """Borrow 100 BASE"""

        # TODO: add more test cases
        collateral_amount = 100
        collateral = types.Quantity(unit=types.TokenType.BASE, amount=collateral_amount)
        loan_to_value = 1

        borrow_market = BorrowMarket(
            market_state=BorrowMarketState(
                loan_to_value_ratio={types.TokenType.BASE: loan_to_value},
                borrow_shares=100,  # borrow is always in DAI, this allows tracking the increasing value of loans over time
                collateral={},
                borrow_outstanding=100,  # sum of Dai that went out the door
                borrow_closed_interest=0.0,  # interested collected from closed borrows
            )
        )

        market_deltas, agent_deltas = borrow_market.close_borrow(
            wallet_address=1,
            collateral=collateral,
            spot_price=0.9,
        )

        borrowed_amount_into_market = market_deltas.d_borrow_shares
        borrowed_amount_into_agent = agent_deltas.borrow

        expected_d_borrow_shares: float = 100  # borrow is always in DAI
        expected_d_collateral = types.Quantity(amount=100, unit=types.TokenType.BASE)
        expected_d_borrow_outstanding: float = 100  # changes based on borrow_shares * borrow_share_price
        expected_d_borrow_closed_interest: float = 0  # realized interest from closed borrows

        self.assertEqual(expected_d_borrow_shares, market_deltas.d_borrow_shares)
        self.assertEqual(expected_d_collateral, market_deltas.d_collateral)
        self.assertEqual(expected_d_borrow_shares, market_deltas.d_borrow_shares)
        self.assertEqual(expected_d_borrow_closed_interest, market_deltas.d_borrow_closed_interest)


if __name__ == "__main__":
    unittest.main()

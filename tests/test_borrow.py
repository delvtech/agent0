"""Testing the Borrow Market"""

import itertools
import unittest

import elfpy.types as types
from elfpy.markets.borrow import Market as BorrowMarket


class TestBorrow(unittest.TestCase):
    """Testing the Borrow Market"""

    def test_borrow(self):
        """Borrow 100 BASE"""

        for loan_to_value, collateral_exponent in itertools.product(range(100), range(8)):
            collateral_amount = 10**collateral_exponent
            collateral = types.Quantity(unit=types.TokenType.BASE, amount=collateral_amount)

            borrow_market = BorrowMarket(
                base=types.TokenType.BASE,
                quote=types.TokenType.QUOTE,
                loan_to_value=loan_to_value,
                interest_rate=0.1,
                liquidation_penalty=0.1,
                liquidation_ratio=0.5,
            )

            market_deltas, agent_deltas = borrow_market.open_borrow(
                wallet_address=1,
                collateral=collateral,
                spot_price=0.9,
            )

            borrowed_amount_into_market = market_deltas[types.TokenType.BASE]
            borrowed_amount_into_agent = agent_deltas.base

            expected_borrow_amount = collateral_amount * loan_to_value / 100

            self.assertEqual(borrowed_amount_into_market, expected_borrow_amount)
            self.assertEqual(borrowed_amount_into_agent, expected_borrow_amount)


if __name__ == "__main__":
    unittest.main()

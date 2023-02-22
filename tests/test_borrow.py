"""Testing the Borrow Market"""
import unittest

from elfpy.types import Quantity, TokenType


class TestBorrow(unittest.TestCase):
    """Testing the Borrow Market"""

    def test_borrow_100(self):
        collateral = Quantity(unit=TokenType.BASE, amount=100)

        borrow_market = BorrowMarket()

        book = Book("The Hitchhiker's Guide to the Galaxy", "Douglas Adams")
        # Act
        book.borrow()
        # Assert
        self.assertTrue(book.borrowed)

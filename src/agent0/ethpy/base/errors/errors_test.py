"""Tests for errors.py"""

from __future__ import annotations

import pytest

from .errors import decode_error_selector_for_contract


class TestDecodeErrorSelector:
    """Tests for decode_error_selector_for_contract."""

    @pytest.fixture
    def mock_contract(self):
        """Fixture that returns a MockContract.

        Returns
        -------
        MockContract
            Mock contract for testing.
        """

        class MockContract:
            """Mock contract for testing."""

            abi = [
                {"name": "InvalidToken", "inputs": [], "type": "error"},
                {"name": "OutOfGas", "inputs": [], "type": "error"},
                {"name": "CustomError", "inputs": [{"type": "uint256"}, {"type": "bool"}], "type": "error"},
            ]

        return MockContract()

    def test_decode_error_selector_for_contract_error_found(self, mock_contract):
        """Test happy path."""
        # Test no inputs
        error_selector = "0xc1ab6dc1"
        result = decode_error_selector_for_contract(error_selector, mock_contract)
        assert result == "InvalidToken"

        # Test with inputs
        error_selector = "0x659c1f59"
        result = decode_error_selector_for_contract(error_selector, mock_contract)
        assert result == "CustomError"

    def test_decode_error_selector_for_contract_error_not_found(self, mock_contract):
        """Test unhappy path."""
        error_selector = "0xdeadbeef"
        result = decode_error_selector_for_contract(error_selector, mock_contract)
        assert result == "UnknownError"

    def test_decode_error_selector_for_contract_no_abi(self, mock_contract):
        """Test bad abi."""
        mock_contract.abi = []
        error_selector = "0xdeadbeef"
        with pytest.raises(ValueError):
            decode_error_selector_for_contract(error_selector, mock_contract)

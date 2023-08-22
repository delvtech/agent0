"""Tests for ABI utilities."""

from ethpy.test_fixtures import local_chain, local_hyperdrive_chain  # pylint: disable=unused-import, ungrouped-imports
from ethpy.test_fixtures.local_chain import LocalHyperdriveChain

from .abi import get_structs_for_abi

# using pytest fixtures necessitates this.
# pylint: disable=redefined-outer-name


class TestStructs:
    """Tests pipeline from bots making trades to viewing the trades in the db"""

    def test_hyperdrive_structs(
        self,
        local_hyperdrive_chain: LocalHyperdriveChain,
    ):
        """Runs the entire pipeline and checks the database at the end.
        All arguments are fixtures.
        """

        structs = get_structs_for_abi(local_hyperdrive_chain.hyperdrive_contract.abi)

        actual = list(structs)
        expected = ["Checkpoint", "MarketState", "Fees", "PoolConfig", "PoolInfo", "WithdrawPool"]
        assert actual == expected
        assert all([a == b for a, b in zip(actual, expected)])

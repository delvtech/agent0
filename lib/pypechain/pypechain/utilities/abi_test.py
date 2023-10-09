"""Tests for ABI utilities."""
from ethpy.hyperdrive import DeployedHyperdrivePool

from .abi import get_structs_for_abi


class TestStructs:
    """Tests pipeline from bots making trades to viewing the trades in the db"""

    def test_hyperdrive_structs(
        self,
        local_hyperdrive_pool: DeployedHyperdrivePool,
    ):
        """Runs the entire pipeline and checks the database at the end.
        All arguments are fixtures.
        """

        structs = get_structs_for_abi(local_hyperdrive_pool.hyperdrive_contract.abi)

        actual = list(structs)
        expected = ["Checkpoint", "MarketState", "Fees", "PoolConfig", "PoolInfo", "WithdrawPool"]
        assert actual == expected
        assert all(a == b for a, b in zip(actual, expected))

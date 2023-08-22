"""Tests bringing up local chain"""


class TestLocalChain:
    """Tests bringing up local chain"""

    # This is using 2 fixtures. Since hyperdrive_contract_address depends on local_chain, we need both here
    # This is due to adding test fixtures through imports
    def test_hyperdrive_init_and_deploy(self, local_chain: str, local_hyperdrive_chain: dict):
        """Create and entry"""
        print(local_chain)
        print(local_hyperdrive_chain)

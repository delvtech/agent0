"""System test for end to end testing of elf-simulations"""
from chainsync.test_fixtures import db_session  # pylint: disable=unused-import
from ethpy.test_fixtures import hyperdrive_contract_address, local_chain  # pylint: disable=unused-import

# fixture arguments in test function have to be the same as the fixture name
# pylint: disable=redefined-outer-name


class TestLocalChain:
    """CRUD tests for checkpoint table"""

    # This is using 2 fixtures. Since hyperdrive_contract_address depends on local_chain, we need both here
    # This is due to adding test fixtures through imports
    def test_hyperdrive_init_and_deploy(self, local_chain, hyperdrive_contract_address):
        """Create and entry"""
        print(local_chain)
        print(hyperdrive_contract_address)

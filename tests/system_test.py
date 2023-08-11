"""System test for end to end testing of elf-simulations"""
from chainsync.test_fixtures import db_session  # pylint: disable=unused-import
from ethpy.test_fixtures import hyperdrive_chain, local_chain  # pylint: disable=unused-import

# fixture arguments in test function have to be the same as the fixture name
# pylint: disable=redefined-outer-name


class TestLocalChain:
    """CRUD tests for checkpoint table"""

    def test_hyperdrive_init_and_deploy(self, local_chain, hyperdrive_chain):
        """Create and entry"""
        print(hyperdrive_chain)

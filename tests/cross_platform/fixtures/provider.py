"""Provider fixture"""
import ape
from ape.api.providers import ProviderAPI

import pytest

# TODO: convert to not use ape
__test__ = False

@pytest.fixture(scope="function")
def provider() -> ProviderAPI:
    """Creates the provider for the local blockchain."""
    # This is the prescribed pattern, ignore the pylint warning about using __enter__
    # pylint: disable=unnecessary-dunder-call
    return ape.networks.parse_network_choice("ethereum:local:foundry").__enter__()

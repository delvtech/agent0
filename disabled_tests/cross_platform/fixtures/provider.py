"""Provider fixture"""
import pytest

import ape
from ape.api.providers import ProviderAPI


# TODO: convert to not use ape
pytestmark = pytest.mark.skip("disabled until converted to not use ape")


@pytest.fixture(scope="function")
def provider() -> ProviderAPI:
    """Creates the provider for the local blockchain."""
    # This is the prescribed pattern, ignore the pylint warning about using __enter__
    # pylint: disable=unnecessary-dunder-call
    return ape.networks.parse_network_choice("ethereum:local:foundry").__enter__()

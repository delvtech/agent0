"""Test executing transactions."""
import pytest
from fixedpointmath import FixedPoint

from agent0.hyperdrive.interactive import InteractiveHyperdrive, LocalChain
from ethpy.base.transactions import smart_contract_transact


@pytest.mark.anvil
def test_smart_contract_transact_success(chain: LocalChain):
    """Transact with a known correct function."""
    interactive_hyperdrive = InteractiveHyperdrive(chain)
    alice = interactive_hyperdrive.init_agent(base=FixedPoint(100), name="alice")
    _deployed_hyperdrive = interactive_hyperdrive._deployed_hyperdrive  # pylint: disable=protected-access
    smart_contract_transact(
        chain._web3,  # pylint: disable=protected-access
        _deployed_hyperdrive.base_token_contract,
        _deployed_hyperdrive.deploy_account,
        "mint(address,uint256)",
        alice.agent.checksum_address,
        FixedPoint(100).scaled_value,
    )


@pytest.mark.anvil
def test_smart_contract_transact_failure(chain: LocalChain):
    """Transact with a known incorrect function name."""
    interactive_hyperdrive = InteractiveHyperdrive(chain)
    alice = interactive_hyperdrive.init_agent(base=FixedPoint(100), name="alice")
    _deployed_hyperdrive = interactive_hyperdrive._deployed_hyperdrive  # pylint: disable=protected-access
    smart_contract_transact(
        chain._web3,  # pylint: disable=protected-access
        _deployed_hyperdrive.base_token_contract,
        _deployed_hyperdrive.deploy_account,
        "mintx(address,uint256)",
        alice.agent.checksum_address,
        FixedPoint(100).scaled_value,
    )

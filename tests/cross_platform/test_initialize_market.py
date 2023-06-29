"""
Test initialization of markets.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from fixedpointmath import FixedPoint

# elfpy core repo
from conftest import HyperdriveFixture, TestCaseWithHyperdriveFixture
from tests.cross_platform import utils

if TYPE_CHECKING:
    from ape.contracts.base import ContractInstance


#########################
# Example with class test
#########################
class TestInitialize(TestCaseWithHyperdriveFixture):
    """Test case for initializing the market"""

    APPROX_EQ = FixedPoint(scaled_value=10)

    def test_market_initialization(self):
        """Verify both markets initialized correctly."""

        self.inititalize()

        fx = self.fixture  # pylint: disable=invalid-name
        deployer = fx.deployer
        config = fx.config
        position_duration_seconds = config.position_duration_seconds
        checkpoint_duration_days = int(config.checkpoint_duration_seconds / 60 / 60 / 24)

        market_state_sol = utils.get_simulation_market_state_from_contract(
            hyperdrive_data_contract=fx.contracts.hyperdrive_data_contract,
            agent_address=deployer.address,
            position_duration_seconds=FixedPoint(position_duration_seconds),
            checkpoint_duration_days=FixedPoint(checkpoint_duration_days),
            variable_apr=config.initial_apr,
            config=config,
        )

        self.assertAlmostEqual(
            market_state_sol.share_reserves, fx.hyperdrive_sim.market_state.share_reserves, delta=self.APPROX_EQ
        )
        # TODO: figure out why these are different!
        # print(f"{market_state_sol.share_reserves=}")
        # print(f"{fx.hyperdrive_sim.market_state.share_reserves=}")
        # print(f"\n{market_state_sol.bond_reserves=}")
        # print(f"{fx.hyperdrive_sim.market_state.bond_reserves=}")
        # self.assertAlmostEqual(market_state_sol.bond_reserves, float(hyperdrive_sim.market_state.bond_reserves))
        # self.assertAlmostEqual(market_state_sol.lp_total_supply, float(hyperdrive_sim.market_state.lp_total_supply))


############################
# Example without class test
############################
# initial TestCase for standalone test case defs
tc = TestCaseWithHyperdriveFixture()


def test_market_initialization(hyperdrive_fixture: HyperdriveFixture):
    """Verify both markets initialized correctly."""

    approx_eq = FixedPoint(scaled_value=10)
    fx = hyperdrive_fixture  # pylint: disable=invalid-name
    tc.inititalize(fx)
    config = fx.config
    position_duration_seconds = config.position_duration_seconds
    checkpoint_duration_days = int(config.checkpoint_duration_seconds / 60 / 60 / 24)

    hyperdrive_data_contract: ContractInstance = fx.project.MockHyperdriveDataProviderTestnet.at(
        fx.contracts.hyperdrive_contract.address
    )  # type: ignore
    market_state_sol = utils.get_simulation_market_state_from_contract(
        hyperdrive_data_contract=hyperdrive_data_contract,
        agent_address=fx.deployer.address,
        position_duration_seconds=FixedPoint(position_duration_seconds),
        checkpoint_duration_days=FixedPoint(checkpoint_duration_days),
        variable_apr=config.initial_apr,
        config=fx.config,
    )

    tc.assertAlmostEqual(
        market_state_sol.share_reserves, fx.hyperdrive_sim.market_state.share_reserves, delta=approx_eq
    )
    # TODO: figure out why these are different!
    # self.assertAlmostEqual(market_state_sol.bond_reserves, float(hyperdrive_sim.market_state.bond_reserves))
    # self.assertAlmostEqual(market_state_sol.lp_total_supply, float(hyperdrive_sim.market_state.lp_total_supply))

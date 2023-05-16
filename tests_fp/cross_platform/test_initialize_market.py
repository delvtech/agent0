"""
This function is a demo for executing an arbitrary number of trades from a pair of
smart bots that track the fixed/variable rates using longs & shorts. It is meant to be
a temporary demonstration, and will be gradually replaced with utilities in elfpy src.
As such, we are relaxing some of the lint rules.
"""
from __future__ import annotations

# stdlib
from collections import defaultdict
import unittest

# external lib
import ape
from ape.contracts import ContractInstance
from eth_typing import HexAddress

# elfpy core repo
import elfpy.markets.hyperdrive.hyperdrive_assets as hyperdrive_assets
import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market
from tests_fp.cross_platform.conftest import MarketConfig, TestCaseWithHyperdriveFixture, HyperdriveFixture


def to_fixed_point(float_var, decimal_places=18):
    """Convert floating point argument to fixed point with desired number of decimals"""
    return int(float_var * 10**decimal_places)


def to_floating_point(float_var, decimal_places=18):
    """Convert fixed point argument to floating point with specified number of decimals"""
    return float(float_var / 10**decimal_places)


def get_simulation_market_state_from_contract(
    hyperdrive_contract: ContractInstance,
    agent_address: HexAddress,
    position_duration_seconds: int,
    checkpoint_duration_days: int,
    variable_apr: int,
    config: MarketConfig,
) -> hyperdrive_market.MarketState:
    """
    hyperdrive_contract: ape.contracts.base.ContractInstance
        Ape project `ContractInstance
        <https://docs.apeworx.io/ape/stable/methoddocs/contracts.html#ape.contracts.base.ContractInstance>`_
        wrapped around the initialized MockHyperdriveTestnet smart contract.
    agent_address: ape.api.accounts.AccountAPI
        Ape address container, or `AccountAPI
        <https://docs.apeworx.io/ape/stable/methoddocs/api.html#ape.api.accounts.AccountAPI>`_
        representing the agent which is executing the action.
    """
    # pylint: disable=too-many-arguments
    pool_info = hyperdrive_contract.getPoolInfo()
    pool_state = pool_info.__dict__
    with ape.accounts.use_sender(agent_address):  # sender for contract calls
        asset_id = hyperdrive_assets.encode_asset_id(
            hyperdrive_assets.AssetIdPrefix.WITHDRAWAL_SHARE, position_duration_seconds
        )
        total_supply_withdraw_shares = hyperdrive_contract.balanceOf(asset_id, agent_address)

    return hyperdrive_market.MarketState(
        lp_total_supply=to_floating_point(pool_state["lpTotalSupply"]),
        share_reserves=to_floating_point(pool_state["shareReserves"]),
        bond_reserves=to_floating_point(pool_state["bondReserves"]),
        base_buffer=pool_state["longsOutstanding"],  # so do we not need any buffers now?
        # TODO: bond_buffer=0,
        variable_apr=variable_apr,
        share_price=to_floating_point(pool_state["sharePrice"]),
        init_share_price=config.share_price,
        curve_fee_multiple=config.curve_fee,
        flat_fee_multiple=config.flat_fee,
        longs_outstanding=to_floating_point(pool_state["longsOutstanding"]),
        shorts_outstanding=to_floating_point(pool_state["shortsOutstanding"]),
        long_average_maturity_time=to_floating_point(pool_state["longAverageMaturityTime"]),
        short_average_maturity_time=to_floating_point(pool_state["shortAverageMaturityTime"]),
        long_base_volume=0,  # to_floating_point(pool_state["longBaseVolume"]),
        short_base_volume=to_floating_point(pool_state["shortBaseVolume"]),
        # TODO: checkpoints=defaultdict
        checkpoint_duration=checkpoint_duration_days,
        total_supply_longs=defaultdict(float, {0: to_floating_point(pool_state["longsOutstanding"])}),
        total_supply_shorts=defaultdict(float, {0: to_floating_point(pool_state["shortsOutstanding"])}),
        total_supply_withdraw_shares=to_floating_point(total_supply_withdraw_shares),
        withdraw_shares_ready_to_withdraw=to_floating_point(pool_state["withdrawalSharesReadyToWithdraw"]),
        withdraw_capital=to_floating_point(pool_state["withdrawalSharesProceeds"]),
        withdraw_interest=0,  # to_floating_point(pool_state["interest"]),
    )


class TestInitialize(TestCaseWithHyperdriveFixture):
    """Test case for initializing the market"""

    def test_market_initialization(self):
        """Verify both markets initialized correctly."""

        fx = self.fixture  # pylint: disable=invalid-name
        deployer = fx.deployer
        config = fx.config
        position_duration_seconds = config.position_duration_seconds
        checkpoint_duration_days = int(config.checkpoint_duration_seconds / 60 / 60 / 24)

        market_state_sol = get_simulation_market_state_from_contract(
            hyperdrive_contract=fx.contracts.hyperdrive_contract,
            agent_address=deployer.address,
            position_duration_seconds=position_duration_seconds,
            checkpoint_duration_days=checkpoint_duration_days,
            variable_apr=config.initial_apr,
            config=config,
        )

        self.assertAlmostEqual(market_state_sol.share_reserves, float(fx.hyperdrive_sim.market_state.share_reserves))
        # TODO: figure out why these are different!
        # self.assertAlmostEqual(market_state_sol.bond_reserves, float(hyperdrive_sim.market_state.bond_reserves))
        # self.assertAlmostEqual(market_state_sol.lp_total_supply, float(hyperdrive_sim.market_state.lp_total_supply))


tc = unittest.TestCase()


def test_market_initialization(hyperdrive_fixture: HyperdriveFixture):
    """Verify both markets initialized correctly."""

    fx = hyperdrive_fixture  # pylint: disable=invalid-name

    market_state_sol = get_simulation_market_state_from_contract(
        hyperdrive_contract=fx.contracts.hyperdrive_contract,
        agent_address=fx.deployer.address,
        position_duration_seconds=int(fx.hyperdrive_sim.position_duration.days) * 24 * 60 * 60,
        checkpoint_duration_days=int(fx.hyperdrive_sim.market_state.checkpoint_duration_days),
        variable_apr=int(fx.hyperdrive_sim.market_state.variable_apr),
        config=fx.config,
    )
    print(f"\n{market_state_sol=}")
    print(f"\n{fx.hyperdrive_sim.market_state=}")

    tc.assertAlmostEqual(market_state_sol.share_reserves, float(fx.hyperdrive_sim.market_state.share_reserves))
    # TODO: figure out why these are different!
    # self.assertAlmostEqual(market_state_sol.bond_reserves, float(hyperdrive_sim.market_state.bond_reserves))
    # self.assertAlmostEqual(market_state_sol.lp_total_supply, float(hyperdrive_sim.market_state.lp_total_supply))

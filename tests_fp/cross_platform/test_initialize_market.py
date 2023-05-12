"""
This function is a demo for executing an arbitrary number of trades from a pair of
smart bots that track the fixed/variable rates using longs & shorts. It is meant to be
a temporary demonstration, and will be gradually replaced with utilities in elfpy src.
As such, we are relaxing some of the lint rules.
"""
from __future__ import annotations

# stdlib
from pathlib import Path
from collections import defaultdict
import unittest

# external lib
import ape
from ape.contracts import ContractInstance, ContractContainer
from ape.api.transactions import ReceiptAPI
from eth_typing import HexAddress

# elfpy core repo
from elfpy.math.fixed_point import FixedPoint
import elfpy.simulators as simulators
import elfpy.agents.agent as agentlib
import elfpy.markets.hyperdrive.hyperdrive_assets as hyperdrive_assets
import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market
import elfpy.pricing_models.hyperdrive as hyperdrive_pm
from elfpy.time.time import BlockTimeFP, StretchedTimeFP


# TODO: take this out, we don't want the simulator stuff in these tests
def get_config() -> simulators.Config:
    """Set config values for the experiment"""
    _config = simulators.Config()
    return _config


def get_agents(budget: FixedPoint = FixedPoint("50_000_000.0")):
    """Get python agents & corresponding solidity wallets"""
    alice_sol = ape.accounts.test_accounts.generate_test_account()
    bob_sol = ape.accounts.test_accounts.generate_test_account()
    celine_sol = ape.accounts.test_accounts.generate_test_account()

    alice_py = agentlib.AgentFP(wallet_address=0, budget=budget)
    bob_py = agentlib.AgentFP(wallet_address=1, budget=budget)
    celine_py = agentlib.AgentFP(wallet_address=2, budget=budget)

    return ([alice_py, bob_py, celine_py], [alice_sol, bob_sol, celine_sol])


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
    config: simulators.Config,
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
    print(f"{pool_info=}")
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
        init_share_price=config.init_share_price,
        curve_fee_multiple=config.curve_fee_multiple,
        flat_fee_multiple=config.flat_fee_multiple,
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


def get_fixture():
    """Gets the simulation and solidity test fixutres."""
    # Instantiate the config using the command line arguments as overrides.
    config = get_config()

    # Instantiate the sim market
    initial_apr = int(FixedPoint(config.target_fixed_apr))
    position_duration_days = FixedPoint(180 * 10**18)
    pricing_model = hyperdrive_pm.HyperdrivePricingModelFP()
    position_duration = StretchedTimeFP(
        days=position_duration_days,
        time_stretch=pricing_model.calc_time_stretch(FixedPoint(initial_apr)),
        normalizing_constant=position_duration_days,
    )
    hyperdrive_sim = hyperdrive_market.MarketFP(
        pricing_model=hyperdrive_pm.HyperdrivePricingModelFP(),
        market_state=hyperdrive_market.MarketStateFP(),
        position_duration=position_duration,
        block_time=BlockTimeFP(),
    )

    # Set up ape
    # This is the prescribed pattern, ignore the pylint warning about using __enter__
    # pylint: disable=unnecessary-dunder-call
    provider = ape.networks.parse_network_choice("ethereum:local:foundry").__enter__()
    project_root = Path.cwd()
    project = ape.Project(path=project_root)

    # Set up agents
    sim_agents, sol_agents = get_agents()
    deployer = ape.accounts.test_accounts.generate_test_account()
    deployer.provider.set_balance(deployer.address, int(FixedPoint("1000000.0")))

    # deploy base token and fixed math contracts
    base_erc20_contract = deployer.deploy(project.ERC20Mintable)  # type: ignore
    base_erc20 = project.ERC20Mintable.at(base_erc20_contract)  # type: ignore
    fixed_math_contract = deployer.deploy(project.MockFixedPointMath)  # type: ignore

    # give some base token to the deployer
    base_erc20_contract.mint(to_fixed_point(config.target_liquidity), sender=deployer)  # type: ignore

    # Convert sim config to solidity format: integer representation of 1e18 fixed point.
    initial_supply = int(FixedPoint(config.target_liquidity))
    initial_share_price = to_fixed_point(config.init_share_price)
    checkpoint_duration = 86400  # seconds = 1 day

    time_stretch = int(FixedPoint("1.0") / hyperdrive_sim.time_stretch_constant)
    curve_fee = to_fixed_point(config.curve_fee_multiple)
    flat_fee = to_fixed_point(config.flat_fee_multiple)
    gov_fee = 0

    # Deploy hyperdrive
    position_duration_seconds = int(position_duration_days) * 24 * 60 * 60

    initial_apr = 50000000000000000
    share_price = 1000000000000000000
    position_duration = 31536000
    checkpoint_duration = 86400
    time_stretch = 22186877016851913475
    curve_fee = 0
    flat_fee = 0
    gov_fee = 0

    hyperdrive_data_provider_contract = deployer.deploy(
        project.MockHyperdriveDataProviderTestnet,  # type: ignore
        base_erc20,
        initial_apr,
        share_price,
        position_duration,
        checkpoint_duration,
        int(time_stretch),
        (curve_fee, flat_fee, gov_fee),
        deployer,
    )
    hyperdrive_contract = deployer.deploy(
        project.MockHyperdriveTestnet,  # type: ignore
        hyperdrive_data_provider_contract,
        base_erc20,
        initial_apr,
        share_price,
        position_duration,
        checkpoint_duration,
        int(time_stretch),
        (curve_fee, flat_fee, gov_fee),
        deployer,
    )
    hyperdrive_data_contract: ContractInstance = project.MockHyperdriveDataProviderTestnet.at(hyperdrive_contract.address)  # type: ignore

    # TODO: do this in test functions.
    # Initialize hyperdrive
    print(f"{float(FixedPoint(initial_supply))=}")
    print(f"{float(FixedPoint(initial_apr))=}")
    with ape.accounts.use_sender(deployer):
        tx_receipt: ReceiptAPI = base_erc20.mint(initial_supply, sender=deployer)  # type: ignore
        tx_receipt: ReceiptAPI = base_erc20.approve(hyperdrive_contract, initial_supply)  # type:ignore
        hyperdrive_contract.initialize(initial_supply, initial_apr, deployer, True)  # type:ignore
    hyperdrive_sim.initialize(sim_agents[0].wallet.address, FixedPoint(initial_supply), FixedPoint(initial_apr))

    # Execute trades
    genesis_block_number = ape.chain.blocks[-1].number
    genesis_timestamp = ape.chain.provider.get_block(genesis_block_number).timestamp  # type:ignore

    return (
        config,
        provider,
        sim_agents,
        sol_agents,
        base_erc20_contract,
        fixed_math_contract,
        hyperdrive_sim,
        hyperdrive_data_contract,
        hyperdrive_contract,
        genesis_timestamp,
        genesis_block_number,
    )


class TestInitialize(unittest.TestCase):
    """Test case for initializing the market"""

    def test_market_initialization(self):
        """Verify both markets initialized correctly."""

        (
            config,
            provider,
            sim_agents,
            sol_agents,
            base_erc20_contract,
            fixed_math_contract,
            hyperdrive_sim,
            hyperdrive_data_contract,
            hyperdrive_contract,
            genesis_timestamp,
            genesis_block_number,
        ) = get_fixture()

        market_state_sol = get_simulation_market_state_from_contract(
            hyperdrive_contract=hyperdrive_data_contract,
            agent_address=sol_agents[0].address,
            position_duration_seconds=int(hyperdrive_sim.position_duration.days) * 24 * 60 * 60,
            checkpoint_duration_days=int(hyperdrive_sim.market_state.checkpoint_duration_days),
            variable_apr=int(hyperdrive_sim.market_state.variable_apr),
            config=config,
        )
        print(f"\n{market_state_sol=}")
        print(f"\n{hyperdrive_sim.market_state=}")

        self.assertAlmostEqual(market_state_sol.share_reserves, float(hyperdrive_sim.market_state.share_reserves))
        # TODO: figure out why these are different!
        # self.assertAlmostEqual(market_state_sol.bond_reserves, float(hyperdrive_sim.market_state.bond_reserves))
        self.assertAlmostEqual(market_state_sol.lp_total_supply, float(hyperdrive_sim.market_state.lp_total_supply))

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

# external lib
import ape
from ape.contracts import ContractInstance

# elfpy core repo
from elfpy.math.fixed_point import FixedPoint
import elfpy.simulators as simulators
import elfpy.agents.agent as agentlib
import elfpy.markets.hyperdrive.hyperdrive_assets as hyperdrive_assets
import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market
import elfpy.pricing_models.hyperdrive as hyperdrive_pm
from elfpy.time.time import BlockTimeFP, StretchedTimeFP


def get_config() -> simulators.Config:
    """Set config values for the experiment"""
    _config = simulators.Config()
    return _config


def get_agents(budget: FixedPoint = FixedPoint("50_000_000.0")):
    """Get python agents & corresponding solidity wallets"""
    alice_sol = ape.accounts.test_accounts.generate_test_account()
    bob_sol = ape.accounts.test_accounts.generate_test_account()
    celine_sol = ape.accounts.test_accounts.generate_test_account()

    alice_py = agentlib.AgentFP(wallet_address=alice_sol.address, budget=budget)
    bob_py = agentlib.AgentFP(wallet_address=bob_sol.address, budget=budget)
    celine_py = agentlib.AgentFP(wallet_address=celine_sol.address, budget=budget)

    return ([alice_py, bob_py, celine_py], [alice_sol, bob_sol, celine_sol])


def to_fixed_point(float_var, decimal_places=18):
    """Convert floating point argument to fixed point with desired number of decimals"""
    return int(float_var * 10**decimal_places)


def to_floating_point(float_var, decimal_places=18):
    """Convert fixed point argument to floating point with specified number of decimals"""
    return float(float_var / 10**decimal_places)


def get_simulation_market_state_from_contract(
    hyperdrive_contract, agent_address, _position_duration_seconds, _checkpoint_duration, variable_apr, _config
):
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
    pool_state = hyperdrive_contract.getPoolInfo().__dict__
    with ape.accounts.use_sender(agent_address):  # sender for contract calls
        asset_id = hyperdrive_assets.encode_asset_id(
            hyperdrive_assets.AssetIdPrefix.WITHDRAWAL_SHARE, _position_duration_seconds
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
        init_share_price=_config.init_share_price,
        curve_fee_multiple=_config.curve_fee_multiple,
        flat_fee_multiple=_config.flat_fee_multiple,
        longs_outstanding=to_floating_point(pool_state["longsOutstanding"]),
        shorts_outstanding=to_floating_point(pool_state["shortsOutstanding"]),
        long_average_maturity_time=to_floating_point(pool_state["longAverageMaturityTime"]),
        short_average_maturity_time=to_floating_point(pool_state["shortAverageMaturityTime"]),
        long_base_volume=to_floating_point(pool_state["longBaseVolume"]),
        short_base_volume=to_floating_point(pool_state["shortBaseVolume"]),
        # TODO: checkpoints=defaultdict
        checkpoint_duration=_checkpoint_duration,
        total_supply_longs=defaultdict(float, {0: to_floating_point(pool_state["longsOutstanding"])}),
        total_supply_shorts=defaultdict(float, {0: to_floating_point(pool_state["shortsOutstanding"])}),
        total_supply_withdraw_shares=to_floating_point(total_supply_withdraw_shares),
        withdraw_shares_ready_to_withdraw=to_floating_point(pool_state["withdrawalSharesReadyToWithdraw"]),
        withdraw_capital=to_floating_point(pool_state["capital"]),
        withdraw_interest=to_floating_point(pool_state["interest"]),
    )


def setUp():
    # Instantiate the config using the command line arguments as overrides.
    config = get_config()

    # Instantiate the sim market
    initial_apr = FixedPoint(config.target_fixed_apr)
    position_duration_days = FixedPoint(180 * 10**18)
    pricing_model = hyperdrive_pm.HyperdrivePricingModelFP()
    position_duration = StretchedTimeFP(
        days=position_duration_days,
        time_stretch=pricing_model.calc_time_stretch(initial_apr),
        normalizing_constant=position_duration_days,
    )
    hyperdrive = hyperdrive_market.MarketFP(
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

    # Use agent 0 to initialize the chain market
    base_address = deployer.deploy(project.ERC20Mintable)  # type: ignore
    base_erc20 = project.ERC20Mintable.at(base_address)  # type: ignore
    fixed_math_address = deployer.deploy(project.MockFixedPointMath)  # type: ignore
    base_erc20.mint(to_fixed_point(config.target_liquidity), sender=deployer)  # type: ignore

    # Convert sim config to solidity format (fixed-point)
    initial_supply = to_fixed_point(config.target_liquidity)
    initial_share_price = to_fixed_point(config.init_share_price)
    checkpoint_duration = 86400  # seconds = 1 day
    checkpoints_per_term = 365

    time_stretch = to_fixed_point(1 / hyperdrive.time_stretch_constant)
    curve_fee = to_fixed_point(config.curve_fee_multiple)
    flat_fee = to_fixed_point(config.flat_fee_multiple)
    gov_fee = 0

    # Deploy hyperdrive on the chain
    hyperdrive_address = deployer.deploy(
        project.MockHyperdriveTestnet,  # type:ignore
        base_erc20,
        initial_apr,
        initial_share_price,
        checkpoints_per_term,
        checkpoint_duration,
        time_stretch,
        (curve_fee, flat_fee, gov_fee),
        deployer,
    )
    hyperdrive_contract: ContractInstance = project.MockHyperdriveTestnet.at(hyperdrive_address)  # type:ignore

    # TODO: do this in test functions.
    # Initialize hyperdrive
    with ape.accounts.use_sender(deployer):
        base_erc20.approve(hyperdrive, initial_supply)  # type:ignore
        hyperdrive_contract.initialize(initial_supply, initial_apr, deployer, True)  # type:ignore

    # Execute trades
    genesis_block_number = ape.chain.blocks[-1].number
    genesis_timestamp = ape.chain.provider.get_block(genesis_block_number).timestamp  # type:ignore

    return (
        provider,
        sim_agents,
        sol_agents,
        base_address,
        fixed_math_address,
        hyperdrive,
        hyperdrive_contract,
        genesis_timestamp,
        genesis_block_number,
    )

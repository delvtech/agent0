# %%
from __future__ import annotations

from numpy.random._generator import Generator as NumpyGenerator

import elfpy.agents.agent as agent
import elfpy.utils.sim_utils as sim_utils
import elfpy.simulators as simulators
import elfpy.utils.outputs as output_utils
import elfpy.agents.policies.random_agent as random_agent

# %% [markdown]
# ### Setup experiment parameters

# %%
config = simulators.Config()

config.title = "trade tape demo"
config.pricing_model_name = "Hyperdrive"  # can be yieldspace or hyperdrive

config.num_trading_days = 5  # Number of simulated trading days
config.num_blocks_per_day = 10  # Blocks in a given day (7200 means ~12 sec per block)
config.num_position_days = 8
config.trade_fee_percent = 0.10  # fee percent collected on trades
config.redemption_fee_percent = 0.005  # 5 bps

num_agents = 4  # int specifying how many agents you want to simulate
agent_budget = 1_000_000  # max money an agent can spend
trade_chance = 5 / (
    config.num_trading_days * config.num_blocks_per_day
)  # on a given block, an agent will trade with probability `trade_chance`

config.target_fixed_apr = 0.01  # target fixed APR of the initial market after the LP
config.target_liquidity = 500_000_000  # target total liquidity of the initial market, before any trades

# Define the variable apr
config.variable_apr = [0.03] * config.num_trading_days

config.do_dataframe_states = True

config.log_level = output_utils.text_to_log_level("WARNING")  # Logging level, should be in ["DEBUG", "INFO", "WARNING"]
config.log_filename = "trade_tape"  # Output filename for logging

config.freeze()  # type: ignore

# %% [markdown]
# ### Setup agents

# %%
def get_example_agents(
    rng: NumpyGenerator, budget: int, new_agents: int, existing_agents: int = 0
) -> list[agent.Agent]:
    """Instantiate a set of custom agents"""
    agents = []
    for address in range(existing_agents, existing_agents + new_agents):
        agent = random_agent.Policy(
            rng=rng,
            trade_chance=trade_chance,
            wallet_address=address,
            budget=budget,
        )
        agent.log_status_report()
        agents += [agent]
    return agents


# %% [markdown]
# ### Setup simulation objects

# %%
# define root logging parameters
output_utils.setup_logging(log_filename=config.log_filename, log_level=config.log_level)

# get an instantiated simulator object
simulator = sim_utils.get_simulator(config)

# %% [markdown]
# ### Run the simulation

# %%
# add the random agents
rnd_agents = get_example_agents(
    rng=simulator.rng,
    budget=agent_budget,
    new_agents=num_agents,
    existing_agents=1,
)
simulator.add_agents(rnd_agents)
print(f"Simulator has {len(simulator.agents)} agents")
print("With budgets =", [sim_agent.budget for sim_agent in simulator.agents.values()])

# %%
# run the simulation
simulator.run_simulation()

# %%
sim_trades = simulator.new_simulation_state.trade_updates.trade_action.tolist()
print("User trades:\n")
print("\n\n".join([f"{trade}" for trade in sim_trades]))

# %%
import ape
from ape import accounts, chain, networks, Project
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

# %% [markdown]
# ### Apeworx Network setup

# %%
networks.parse_network_choice("ethereum:local:foundry").__enter__()
project_root = Path.cwd().parent.parent
project = Project(path=project_root)

# %% [markdown]
# ### Generate agent accounts

# %%
governance = accounts.test_accounts.generate_test_account()
sol_agents = {"governance": governance}
for agent_address, sim_agent in simulator.agents.items():
    sol_agent = accounts.test_accounts.generate_test_account()  # make a fake agent with its own wallet
    sol_agent.balance = int(sim_agent.budget * 10**18)
    sol_agents[f"agent_{agent_address}"] = sol_agent

# %% [markdown]
# ### Deploy contracts

# %%
# use agent 0 to initialize the market
base_address = sol_agents["agent_0"].deploy(project.ERC20Mintable)
base_ERC20 = project.ERC20Mintable.at(base_address)

fixed_math_address = sol_agents["agent_0"].deploy(project.MockFixedPointMath)
fixed_math = project.MockFixedPointMath.at(fixed_math_address)

base_ERC20.mint(int(config.target_liquidity * 10**18), sender=sol_agents["agent_0"])

initial_supply = int(config.target_liquidity * 10**18)
initial_apr = int(config.target_fixed_apr * 10**18)
initial_share_price = int(config.init_share_price * 10**18)
checkpoint_duration = 86400  # seconds = 1 day
checkpoints_per_term = 365
position_duration_seconds = checkpoint_duration * checkpoints_per_term
time_stretch = int(1 / simulator.market.time_stretch_constant * 10**18)
curve_fee = int(config.trade_fee_percent * 10**18)
flat_fee = int(config.redemption_fee_percent * 10**18)
gov_fee = 0

hyperdrive_address = sol_agents["agent_0"].deploy(
    project.MockHyperdriveTestnet,
    base_ERC20,
    initial_apr,
    initial_share_price,
    checkpoints_per_term,
    checkpoint_duration,
    time_stretch,
    (curve_fee, flat_fee, gov_fee),
    governance,
)
hyperdrive = project.MockHyperdriveTestnet.at(hyperdrive_address)

with accounts.use_sender(sol_agents["agent_0"]):
    base_ERC20.approve(hyperdrive, initial_supply)
    hyperdrive.initialize(initial_supply, initial_apr, sol_agents["agent_0"], False)


# %% [markdown]
# ### Define & execute trades

# %%
def open_short(hyperdrive_agent, bond_amount):
    with accounts.use_sender(hyperdrive_agent):
        # Mint DAI & approve ERC20 usage by contract
        base_ERC20.mint(bond_amount * 2)
        base_ERC20.approve(hyperdrive, bond_amount * 2)
        # Open short
        max_deposit = bond_amount
        as_underlying = False
        print(f"\t{hyperdrive_agent=}")
        print(f"\t{hyperdrive_agent.balance=}")
        print(f"\t{bond_amount=}")
        print(f"\t{max_deposit=}")
        print(f"\t{as_underlying=}")
        print(f"\t{hyperdrive.getPoolInfo().__dict__=}")
        tx_receipt = hyperdrive.openShort(
            bond_amount,
            max_deposit,
            hyperdrive_agent,
            as_underlying,
        )
        print(f"\t{hyperdrive.getPoolInfo().__dict__=}")
    # Return the updated pool state & transaction result
    transfer_single_event = [tx_event for tx_event in tx_receipt.events if tx_event.event_name == "TransferSingle"][0]
    token_id = transfer_single_event["id"]
    mask = (1 << 248) - 1
    maturity_timestamp = token_id & mask
    pool_state = hyperdrive.getPoolInfo().__dict__
    pool_state["block_number_"] = tx_receipt.block_number
    pool_state["mint_timestamp_"] = maturity_timestamp - position_duration_seconds
    pool_state["maturity_timestamp_"] = maturity_timestamp
    return pool_state, tx_receipt


def close_short(hyperdrive_agent, bond_amount, maturity_time):
    with accounts.use_sender(hyperdrive_agent):
        min_output = 0
        as_underlying = False
        print(f"\t{hyperdrive_agent=}")
        print(f"\t{bond_amount=}")
        print(f"\t{maturity_time=}")
        print(f"\t{min_output=}")
        print(f"\t{as_underlying=}")
        print(f"\t{hyperdrive.getPoolInfo().__dict__=}")
        my_contract = project.ContractContainer.at(address)
        tx_receipt = my_contract.doSomething(args)
        # ContractLogicError: Transaction failed.
        tx_receipt = hyperdrive.closeShort(
            maturity_time,
            bond_amount,
            min_output,
            hyperdrive_agent,
            as_underlying,
        )
        print(f"\t{hyperdrive.getPoolInfo().__dict__=}")
    # Return the updated pool state & transaction result
    pool_state = hyperdrive.getPoolInfo().__dict__
    pool_state["block_number_"] = tx_receipt.block_number
    return pool_state, tx_receipt


def open_long(hyperdrive_agent, base_amount):
    with accounts.use_sender(hyperdrive_agent):
        # Mint DAI & approve ERC20 usage by contract
        base_ERC20.mint(base_amount)
        base_ERC20.approve(hyperdrive, base_amount)
        # Open long
        min_output = 0
        as_underlying = False
        print(f"\t{hyperdrive_agent=}")
        print(f"\t{hyperdrive_agent.balance=}")
        print(f"\t{base_amount=}")
        print(f"\t{min_output=}")
        print(f"\t{as_underlying=}")
        print(f"\t{hyperdrive.getPoolInfo().__dict__=}")
        tx_receipt = hyperdrive.openLong(
            base_amount,
            min_output,
            hyperdrive_agent,
            as_underlying,
        )
        hyperdrive.query_manager.query
        print(f"\t{hyperdrive.getPoolInfo().__dict__=}")
    # Return the updated pool state & transaction result
    transfer_single_event = [tx_event for tx_event in tx_receipt.events if tx_event.event_name == "TransferSingle"][0]
    token_id = transfer_single_event["id"]
    mask = (1 << 248) - 1
    maturity_timestamp = token_id & mask
    pool_state = hyperdrive.getPoolInfo().__dict__
    pool_state["block_number_"] = tx_receipt.block_number
    pool_state["mint_timestamp_"] = maturity_timestamp - position_duration_seconds
    pool_state["maturity_timestamp_"] = maturity_timestamp
    return pool_state, tx_receipt


def close_long(hyperdrive_agent, bond_amount, maturity_time):
    with accounts.use_sender(hyperdrive_agent):
        min_output = 0
        as_underlying = False
        print(f"\t{hyperdrive_agent=}")
        print(f"\t{bond_amount=}")
        print(f"\t{maturity_time=}")
        print(f"\t{min_output=}")
        print(f"\t{as_underlying=}")
        print(f"\t{hyperdrive.getPoolInfo().__dict__=}")
        tx_receipt = hyperdrive.closeLong(
            maturity_time,
            bond_amount,
            min_output,
            hyperdrive_agent,
            as_underlying,
        )
        print(f"\t{hyperdrive.getPoolInfo().__dict__=}")
    # Return the updated pool state & transaction result
    pool_state = hyperdrive.getPoolInfo().__dict__
    pool_state["block_number_"] = tx_receipt.block_number
    return pool_state, tx_receipt


# %%
# get current block
genesis_block_number = chain.blocks[-1].number
genesis_timestamp = chain.provider.get_block(genesis_block_number).timestamp

# set the current block?
pool_state = [hyperdrive.getPoolInfo().__dict__]
pool_state[0]["block_number_"] = genesis_block_number
print(f"{pool_state=}\n")

sim_to_block_time = {}
trade_receipts = []
for trade in sim_trades:

    agent_key = f"agent_{trade.wallet.address}"
    trade_amount = int(trade.trade_amount * 10**18)
    print("\n", agent_key, trade.action_type.name)
    print(f"\t{trade.mint_time=}")

    if trade.action_type.name in ["ADD_LIQUIDITY", "REMOVE_LIQUIDITY"]:
        continue  # todo

    if trade.action_type.name == "OPEN_SHORT":
        new_state, trade_details = open_short(sol_agents[agent_key], trade_amount)
        sim_to_block_time[trade.mint_time] = new_state["maturity_timestamp_"]

    elif trade.action_type.name == "CLOSE_SHORT":
        maturity_time = int(sim_to_block_time[trade.mint_time])
        print(f"\t{maturity_time=}")
        print(f"\t{position_duration_seconds=}")
        new_state, trade_details = close_short(sol_agents[agent_key], trade_amount, maturity_time)

    elif trade.action_type.name == "OPEN_LONG":
        new_state, trade_details = open_long(sol_agents[agent_key], trade_amount)
        sim_to_block_time[trade.mint_time] = new_state["maturity_timestamp_"]

    elif trade.action_type.name == "CLOSE_LONG":
        maturity_time = int(sim_to_block_time[trade.mint_time])
        print(f"\t{maturity_time=}")
        print(f"\t{position_duration_seconds=}")
        new_state, trade_details = close_long(sol_agents[agent_key], trade_amount, maturity_time)

    trade_receipts.append(trade_details)
    pool_state.append(new_state)

# %%
dir(trade_receipts[1])

# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.14.5
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# # Bot Trades on Hyperdrive Contracts

# +
# test: skip-notebook
from __future__ import annotations
import logging

import os
import numpy as np
from numpy.random._generator import Generator as NumpyGenerator

import pytest
import elfpy
import elfpy.agents.agent as agent
import elfpy.agents.policies.random_agent as random_agent
import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market
import elfpy.simulators as simulators
import elfpy.utils.sim_utils as sim_utils
import elfpy.utils.outputs as output_utils
import elfpy.utils.apeworx_integrations as ape_utils
import elfpy.utils.post_processing as post_utils

import ape
from ape_ethereum.transactions import Receipt
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

# system copy
# os.system("cp ../../../hyperdrive/Lib/forge-std/src/console*.sol ../../../hyperdrive/contracts/src/")


def fmt(value, precision=3, min_digits=0, debug=False):
    """
    Format a float to a string with a given precision
    this follows the significant figure behavior, irrepective of number size
    """
    # TODO: Include more specific error handling in the except statement
    # pylint: disable=broad-except
    if debug:
        print(f"value: {value}, type: {type(value)}, precision: {precision}, min_digits: {min_digits}")
    if np.isinf(value):
        return "inf"
    if np.isnan(value):
        return "nan"
    if value == 0:
        return "0"
    try:
        digits = int(np.floor(np.log10(abs(value)))) + 1  #  calculate number of digits in value
    except Exception as err:
        if debug:
            print(
                f"Error in float_to_string: value={value}({type(value)}), precision={precision},"
                f" min_digits={min_digits}, \n error={err}"
            )
        return str(value)
    decimals = np.clip(precision - digits, min_digits, precision)  # sigfigs to the right of the decimal
    if debug:
        print(f"value: {value}, type: {type(value)} calculated digits: {digits}, decimals: {decimals}")
    if abs(value) > 0.01:
        string = f"{value:,.{decimals}f}"
    else:  # add an additional sigfig if the value is really small
        string = f"{value:0.{precision-1}e}"
    return string


def idfn(val):
    """Custom id function for pytest parametrize"""
    return f"term={val:.0f}"


@pytest.mark.parametrize("term_length", range(8, 366, 50), ids=idfn)
def test_run_bots_on_solidity(term_length: int, num_agents: int = 4, agent_budget: int = 1_000_000, trade_chance=None):
    config = simulators.Config()

    config.title = "random bot demo"
    config.pricing_model_name = "Hyperdrive"  # can be yieldspace or hyperdrive

    config.num_trading_days = 5  # Number of simulated trading days
    config.num_blocks_per_day = 10  # Blocks in a given day (7200 means ~12 sec per block)
    config.num_position_days = term_length  # 8
    config.trade_fee_percent = 0.10  # fee percent collected on trades
    config.redemption_fee_percent = 0.05  # fee percent collected on maturity
    config.governance_fee_percent = 0.10  # share of fees that go to governance

    num_agents = num_agents  # int specifying how many agents you want to simulate
    agent_budget = agent_budget  # max money an agent can spend

    # on a given block, an agent will trade with probability `trade_chance`
    trade_chance = 5 / (config.num_trading_days * config.num_blocks_per_day) if trade_chance is None else trade_chance

    config.target_fixed_apr = 0.05  # target fixed APR of the initial market after the LP
    config.target_liquidity = 500_000_000  # target total liquidity of the initial market, before any trades

    # Define the variable apr
    config.variable_apr = [0.03] * config.num_trading_days

    config.do_dataframe_states = True

    config.log_level = output_utils.text_to_log_level("DEBUG")  # Logging level
    config.log_filename = "random_bots"  # Output filename for logging

    config.freeze()  # type: ignore

    # -

    # ### Setup agents

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

    # ### Setup simulation objects

    # +
    # define root logging parameters
    output_utils.setup_logging(log_filename=config.log_filename, log_level=config.log_level, delete_previous_logs=True)

    # get an instantiated simulator object
    simulator = sim_utils.get_simulator(config)
    # -

    # ### Run the simulation

    # add the random agents
    rnd_agents = get_example_agents(
        rng=simulator.rng,
        budget=agent_budget,
        new_agents=num_agents,
        existing_agents=1,
    )
    simulator.add_agents(rnd_agents)
    logging.info(
        "Simulator has %d agents with budgets =%s.",
        len(simulator.agents),
        [sim_agent.budget for sim_agent in simulator.agents.values()],
    )

    # +
    # run the simulation
    simulator.run_simulation()

    # get the trade tape
    sim_trades = simulator.new_simulation_state.trade_updates.trade_action.tolist()
    logging.info(
        "User trades:\n%s",
        "\n\n".join([f"{trade}" for trade in sim_trades]),
    )
    # -

    sim_trades_df = post_utils.compute_derived_variables(simulator)
    # print(list(sim_trades_df.columns))
    # print(
    #     sim_trades_df.loc[
    #         0,
    #         [
    #             "fixed_apr",
    #             "position_duration",
    #             "share_price",
    #             "share_reserves",
    #             "bond_reserves",
    #             "lp_total_supply",
    #             "longs_outstanding",
    #             "shorts_outstanding",
    #             "delta_shares",
    #             "delta_base",
    #         ],
    #     ]
    # )

    fig, axs, _ = output_utils.get_gridspec_subplots()
    ax = axs[0]
    ax.step(sim_trades_df["trade_number"].iloc[1:], sim_trades_df["shorts_outstanding"].iloc[1:], label="Shorts")
    ax.step(sim_trades_df["trade_number"].iloc[1:], sim_trades_df["longs_outstanding"].iloc[1:], label="Longs")
    ax.set_xlabel("Trade number")
    ax.set_ylabel("Outstanding balance")
    ax.set_title(f"Random Bots (Python, n={len(sim_trades_df)})")
    ax.set_xlim([1, sim_trades_df["trade_number"].iloc[-1] - 2])
    y_max = round(max(max(sim_trades_df["shorts_outstanding"]), max(sim_trades_df["longs_outstanding"])))
    ax.set_ylim([0, y_max])
    ax.ticklabel_format(axis="both", style="sci")
    ax.legend()

    fig, axs, _ = output_utils.get_gridspec_subplots()
    ax = axs[0]
    ax.step(sim_trades_df["trade_number"].iloc[1:-1], sim_trades_df["fixed_apr"].iloc[1:-1], label="APR")
    ax.set_xlabel("Trade number")
    ax.set_ylabel("Fixed APR")
    ax.set_title("Random longs & shorts")
    Path("./figs").mkdir(parents=True, exist_ok=True)  # create folder if it doesn't exist
    fig.savefig(f"./figs/fixed_apr")

    lp_trades = sim_trades_df.groupby("trade_number").agg({f"agent_{0}_pnl": ["sum"]})
    lp_trades.columns = ["_".join(col).strip() for col in lp_trades.columns.values]
    lp_trades = lp_trades.reset_index()

    fig, axs, _ = output_utils.get_gridspec_subplots()
    ax = axs[0]
    ax.step(lp_trades["trade_number"].iloc[1:-1], lp_trades["agent_0_pnl_sum"].iloc[1:-1], label="PNL")
    ax.set_xlabel("Trade number")
    ax.set_ylabel("Agent 0 PNL share proceeds")
    ax.set_title("Random longs & shorts")
    fig.savefig(f"./figs/LP_PNL")

    # ### Apeworx Network setup

    provider = ape.networks.parse_network_choice("ethereum:local:foundry").__enter__()
    project_root = Path.cwd().parent.parent
    project = ape.Project(path=project_root)

    # ### Generate agent accounts

    governance = ape.accounts.test_accounts.generate_test_account()
    sol_agents = {"governance": governance}
    for agent_address, sim_agent in simulator.agents.items():
        sol_agent = ape.accounts.test_accounts.generate_test_account()  # make a fake agent with its own wallet
        sol_agent.balance = int(sim_agent.budget * 10**18)
        sol_agents[f"agent_{agent_address}"] = sol_agent

    # ### Deploy contracts

    # +
    # use agent 0 to initialize the market
    base_address = sol_agents["agent_0"].deploy(project.ERC20Mintable)
    base_ERC20 = project.ERC20Mintable.at(base_address)

    fixed_math_address = sol_agents["agent_0"].deploy(project.MockFixedPointMath)
    fixed_math = project.MockFixedPointMath.at(fixed_math_address)

    hyperdrive_math_address = sol_agents["agent_0"].deploy(project.MockHyperdriveMath)
    hyperdrive_math = project.MockHyperdriveMath.at(hyperdrive_math_address)

    base_ERC20.mint(int(config.target_liquidity * 10**18), sender=sol_agents["agent_0"])

    initial_supply = int(config.target_liquidity * 10**18)
    initial_apr = int(config.target_fixed_apr * 10**18)
    # print(f"{fmt(initial_apr/1e18)=}")
    initial_share_price = int(config.init_share_price * 10**18)
    checkpoint_duration = 86400  # seconds = 1 day
    checkpoints_per_term = 365
    position_duration_seconds = checkpoint_duration * checkpoints_per_term
    position_duration_days = position_duration_seconds / 86400
    # print(f"{position_duration_days=}")
    # print(f"{initial_share_price/1e18=}")
    time_stretch = int(1 / simulator.market.time_stretch_constant * 10**18)
    # print(f"{time_stretch=}")
    actual_time_stretch = 1 / (time_stretch / 10**18)
    # print(f"{actual_time_stretch=}")
    curve_fee = int(config.trade_fee_percent * 10**18)
    flat_fee = int(config.redemption_fee_percent * 10**18)
    gov_fee = int(config.governance_fee_percent * 10**18)

    # print("=== SETUP ===")
    # print(f"{fmt(initial_supply/1e18)=}")
    # print(f"{fmt(initial_apr/1e18)=}")
    # print(f"{fmt(initial_share_price/1e18)=}")
    # print(f"{fmt(checkpoints_per_term/1e18)=}")
    # print(f"{fmt(checkpoint_duration/1e18)=}")
    # print(f"{fmt(time_stretch/1e18)=}")
    # print(f"{fmt(curve_fee/1e18)=}")
    # print(f"{fmt(flat_fee/1e18)=}")
    # print(f"{fmt(gov_fee/1e18)=}")
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
    # print(f"{dir(hyperdrive)=}")

    # print(f"{fmt(initial_supply/1e18)=}")
    with ape.accounts.use_sender(sol_agents["agent_0"]):
        base_ERC20.approve(hyperdrive, initial_supply)
        as_underlying = True
        result: Receipt = hyperdrive.initialize(
            initial_supply, initial_apr, sol_agents["agent_0"], as_underlying, show_trace=True
        )
        hyper_config = hyperdrive.getPoolConfiguration()
        # print(f"{hyper_config=}")
        pool_info = hyperdrive.getPoolInfo()
        # print(f"{pool_info=}")
        result.show_trace()
        apr: Receipt = hyperdrive_math.calculateSpotPrice(
            pool_info["shareReserves_"],  # shareReserves
            pool_info["bondReserves_"],  # bondReserves
            hyper_config["initialSharePrice_"],  # initalSharePrice
            hyper_config["positionDuration_"],  # timeRemaining
            hyper_config["timeStretch_"],  # timeStretch
        )
        # print(f"{hyper_config['positionDuration_']/86400=}")
        # print(f"{fmt(apr/1e18)=}")
    # -

    # ### Execute trades

    # +
    # get current block
    genesis_block_number = ape.chain.blocks[-1].number
    genesis_timestamp = ape.chain.provider.get_block(genesis_block_number).timestamp

    # set the current block?
    pool_state = [hyperdrive.getPoolInfo().__dict__]
    pool_state[0]["block_number_"] = genesis_block_number
    logging.info("pool_state=%s\n", pool_state)

    sim_to_block_time = {}
    trade_receipts = []
    for trade in sim_trades:
        agent_key = f"agent_{trade.wallet.address}"
        trade_amount = int(trade.trade_amount * 10**18)
        logging.info(
            "agent_key=%s, action=%s, mint_time=%s",
            agent_key,
            trade.action_type.name,
            trade.mint_time,
        )
        # print(f"{agent_key=}")
        if trade.action_type.name == "ADD_LIQUIDITY":
            with ape.accounts.use_sender(sol_agents[agent_key]):  # sender for contract calls
                # Mint DAI & approve ERC20 usage by contract
                base_ERC20.mint(trade_amount)
                base_ERC20.approve(hyperdrive.address, trade_amount)
            new_state, trade_details = ape_utils.ape_open_position(
                hyperdrive_market.AssetIdPrefix.LP,
                hyperdrive,
                sol_agents[agent_key],
                trade_amount,
            )
        elif trade.action_type.name == "REMOVE_LIQUIDITY":
            new_state, trade_details = ape_utils.ape_close_position(
                hyperdrive_market.AssetIdPrefix.LP,
                hyperdrive,
                sol_agents[agent_key],
                trade_amount,
            )
        elif trade.action_type.name == "OPEN_SHORT":
            with ape.accounts.use_sender(sol_agents[agent_key]):  # sender for contract calls
                # Mint DAI & approve ERC20 usage by contract
                base_ERC20.mint(trade_amount)
                base_ERC20.approve(hyperdrive.address, trade_amount)
            new_state, trade_details = ape_utils.ape_open_position(
                hyperdrive_market.AssetIdPrefix.SHORT,
                hyperdrive,
                sol_agents[agent_key],
                trade_amount,
            )
            sim_to_block_time[trade.mint_time] = new_state["maturity_timestamp_"]
        elif trade.action_type.name == "CLOSE_SHORT":
            maturity_time = int(sim_to_block_time[trade.mint_time])
            new_state, trade_details = ape_utils.ape_close_position(
                hyperdrive_market.AssetIdPrefix.SHORT,
                hyperdrive,
                sol_agents[agent_key],
                trade_amount,
                maturity_time,
            )
        elif trade.action_type.name == "OPEN_LONG":
            with ape.accounts.use_sender(sol_agents[agent_key]):  # sender for contract calls
                # Mint DAI & approve ERC20 usage by contract
                base_ERC20.mint(trade_amount)
                base_ERC20.approve(hyperdrive.address, trade_amount)
            new_state, trade_details = ape_utils.ape_open_position(
                hyperdrive_market.AssetIdPrefix.LONG,
                hyperdrive,
                sol_agents[agent_key],
                trade_amount,
            )
            sim_to_block_time[trade.mint_time] = new_state["maturity_timestamp_"]
        elif trade.action_type.name == "CLOSE_LONG":
            maturity_time = int(sim_to_block_time[trade.mint_time])
            new_state, trade_details = ape_utils.ape_close_position(
                hyperdrive_market.AssetIdPrefix.LONG,
                hyperdrive,
                sol_agents[agent_key],
                trade_amount,
                maturity_time,
            )
        else:
            raise ValueError(f"{trade.action_type=} must be opening or closing a long or short")
        trade_receipts.append(trade_details)
        new_state["action_type"] = trade.action_type.name
        new_state["trade_amount"] = trade_amount / 1e18
        new_state["agent_key"] = agent_key
        pool_state.append(new_state)
    # -

    trades_df = pd.DataFrame(pool_state)
    # print(trades_df.columns)

    fig, axs, _ = output_utils.get_gridspec_subplots()
    ax = axs[0]
    ax.step(range(1, len(trades_df)), trades_df["shortsOutstanding_"].iloc[1:] / 1e18, label="Shorts")
    ax.step(range(1, len(trades_df)), trades_df["longsOutstanding_"].iloc[1:] / 1e18, label="Longs")
    ax.set_xlabel("Trade number")
    ax.set_ylabel("Outstanding balance")
    ax.set_title(f"Random Bots (Solidity, n={len(trades_df)})")
    ax.set_xlim([1, len(trades_df)])
    y_max = round(max(max(trades_df["shortsOutstanding_"]) / 1e18, max(trades_df["longsOutstanding_"]) / 1e18))
    ax.set_ylim([0, y_max])
    ax.ticklabel_format(axis="both", style="sci")
    ax.legend()

    trades_df
    fig, axs, _ = output_utils.get_gridspec_subplots()
    ax = axs[0]
    ax.step(
        range(len(sim_trades_df) - 2), sim_trades_df["lp_total_supply"].iloc[1:-1] * 2.975, label="Python Simulation"
    )
    ax.step(range(len(trades_df) - 2), trades_df["lpTotalSupply"].iloc[1:-1] / 1e18, label="Solidity Contracts")
    max_x = max(len(sim_trades_df), len(trades_df)) - 1
    ax.set_xlim([0, max_x])
    ax.set_xlabel("Trade number")
    ax.set_ylabel("# of tokens")
    ax.set_title("LP Total Supply")
    Path("./figs").mkdir(parents=True, exist_ok=True)  # create folder if it doesn't exist
    fig.savefig(f"./figs/lp_total_supply")
    ax.legend()

    # print(list(sim_trades_df.columns))
    # print(list(trades_df.columns))
    n = 10  # len(trades_df)-1
    for i in range(n):
        print(
            f"{i=:4.0f}, Python=("
            # f"shorts={sim_trades_df['shorts_outstanding'].iloc[i+0]:10.2f}, longs={sim_trades_df['longs_outstanding'].iloc[i+0]:10.2f})"
            f"shares={fmt(sim_trades_df['share_reserves'].iloc[i+0])}, bonds={fmt(sim_trades_df['bond_reserves'].iloc[i+0])}"
            f", lp={fmt(sim_trades_df['lp_total_supply'].iloc[i+0])}"
            f"), Solidity=("
            # f"shorts={trades_df['shortsOutstanding_'].iloc[i+1]/1e18:10.2f}, longs={trades_df['longsOutstanding_'].iloc[i+1]/1e18:10.2f})"
            f"shares={fmt(trades_df['shareReserves_'].iloc[i+1]/1e18)}, bonds={fmt(trades_df['bondReserves_'].iloc[i+1]/1e18)}"
            f", lp={fmt(trades_df['lpTotalSupply'].iloc[i+1]/1e18)}"
            f")"
        )

    # +
    df = trades_df[["agent_key", "action_type", "trade_amount"]].round({"trade_amount": 2}).reset_index().iloc[1:]

    fig, ax = plt.subplots()
    fig.set_size_inches(4.0, 7.0)
    ax.xaxis.set_visible(False)  # hide the x axis
    ax.yaxis.set_visible(False)  # hide the y axis
    ax.set_frame_on(False)  # no visible frame
    table = ax.table(
        cellText=df.values,
        colLabels=df.columns,
        loc="center",
        cellColours=[[elfpy.GREY] * (len(df.columns))] * len(df),
        colColours=[elfpy.GREY] * (len(df.columns)),
    )
    table.set_fontsize(12)
    table.scale(1.4, 1.4)  # change size table

    # set edge lines color to light grey
    for i in range(len(df) + 1):
        for j in range(len(df.columns)):
            if i == 0:
                table[i, j].set_linestyle("-")
                table[i, j].set_edgecolor(elfpy.LIGHTGREY)
            table[i, j].set_linestyle("-")
            table[i, j].set_edgecolor(elfpy.LIGHTGREY)

    table.auto_set_column_width(col=list(range(1, len(df.columns))))

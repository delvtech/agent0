"""A demo for executing an arbitrary number of trades bots on testnet."""
# pylint: disable=too-many-lines
# pyright: reportOptionalMemberAccess=false, reportGeneralTypeIssues=false
from __future__ import annotations  # types will be strings by default in 3.11

# stdlib
import argparse
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from time import sleep
from time import time as now
from typing import cast

# external lib
import ape
import numpy as np
import pandas as pd
import requests
from ape import accounts
from ape.api import ProviderAPI
from ape.contracts import ContractInstance
from ape.logging import logger as ape_logger
from ape.utils import generate_dev_accounts
from ape_accounts.accounts import KeyfileAccount
from dotenv import load_dotenv
from eth_account import Account as EthAccount
from fixedpointmath import FixedPoint
from numpy.random._generator import Generator as NumpyGenerator

# elfpy core repo
import elfpy
import elfpy.utils.apeworx_integrations as ape_utils
import elfpy.utils.logs as log_utils
from elfpy import types
from elfpy.agents.agent import Agent
from elfpy.agents.policies import LongLouie, RandomAgent, ShortSally
from elfpy.agents.policies.base import BasePolicy
from elfpy.bots import DEFAULT_USERNAME, EnvironmentConfig
from elfpy.bots.bot_info import BotInfo
from elfpy.data import postgres
from elfpy.markets.hyperdrive import HyperdriveMarket, HyperdrivePricingModel
from elfpy.utils.format import format_numeric_string

ape_logger.set_level(logging.ERROR)


def get_devnet_addresses(
    bot_config: EnvironmentConfig, addresses: dict[str, str] | None = None
) -> tuple[dict[str, str], str]:
    """Get devnet addresses from address file."""
    if addresses is None:
        addresses = {}
    deployed_addresses = {}
    # get deployed addresses from local file, if it exists
    address_file_path = bot_config.scratch["project_dir"] / "hyperdrive_solidity/artifacts/addresses.json"
    if os.path.exists(address_file_path):
        logging.info("Loading addresses.json from local file. This should only be used for development.")
        with open(address_file_path, "r", encoding="utf-8") as file:
            deployed_addresses = json.load(file)
    else:  # otherwise get deployed addresses from artifacts server
        logging.info(
            "Attempting to load addresses.json, which requires waiting for the contract deployment to complete."
        )
        num_attempts = 120
        for attempt_num in range(num_attempts):
            logging.info("\tAttempt %s out of %s to %s", attempt_num + 1, num_attempts, bot_config.artifacts_url)
            try:
                response = requests.get(f"{bot_config.artifacts_url}/addresses.json", timeout=10)
                if response.status_code == 200:
                    deployed_addresses = response.json()
                    break
            except requests.exceptions.ConnectionError as exc:
                logging.info("Connection error: %s", exc)
            sleep(1)
        logging.info("Contracts deployed; addresses loaded.")
    if "baseToken" in deployed_addresses:
        addresses["baseToken"] = deployed_addresses["baseToken"]
        logging.info("found devnet base address: %s", addresses["baseToken"])
    else:
        addresses["baseToken"] = None
    if "mockHyperdrive" in deployed_addresses:
        addresses["hyperdrive"] = deployed_addresses["mockHyperdrive"]
        logging.info("found devnet hyperdrive address: %s", addresses["hyperdrive"])
    elif "hyperdrive" in deployed_addresses:
        addresses["hyperdrive"] = deployed_addresses["hyperdrive"]
        logging.info("found devnet hyperdrive address: %s", addresses["hyperdrive"])
    else:
        addresses["hyperdrive"] = None
    if "mockHyperdriveMath" in deployed_addresses:
        addresses["hyperdriveMath"] = deployed_addresses["mockHyperdriveMath"]
        logging.info("found devnet hyperdriveMath address: %s", addresses["hyperdriveMath"])
    return addresses


def get_accounts(bot_config: EnvironmentConfig) -> list[KeyfileAccount]:
    """Generate dev accounts and turn on auto-sign."""
    num = sum(bot_config.scratch[f"num_{bot}"] for bot in bot_config.scratch["bot_names"])
    assert (mnemonic := " ".join(["wolf"] * 24)), "You must provide a mnemonic in .env to run this script."
    keys = generate_dev_accounts(mnemonic=mnemonic, number_of_accounts=num)
    for num, key in enumerate(keys):
        path = accounts.containers["accounts"].data_folder.joinpath(f"agent_{num}.json")
        path.write_text(json.dumps(EthAccount.encrypt(private_key=key.private_key, password="based")))  # overwrites
    dev_accounts: list[KeyfileAccount] = [
        cast(KeyfileAccount, accounts.load(alias=f"agent_{num}")) for num in range(len(keys))
    ]
    logging.disable(logging.WARNING)  # disable logging warnings to do dangerous things below
    for account in dev_accounts:
        account.set_autosign(enabled=True, passphrase="based")
    logging.disable(logging.NOTSET)  # re-enable logging warnings
    return dev_accounts


def create_agent(
    bot: BotInfo,
    dev_accounts: list[KeyfileAccount],
    faucet: ContractInstance | None,
    base_instance: ContractInstance,
    trade_history: pd.DataFrame,
    hyperdrive_contract: ContractInstance,
    bot_config: EnvironmentConfig,
    rng: NumpyGenerator,
) -> Agent:
    """Create an agent as defined in bot_info, assign its address, give it enough base.

    Parameters
    ----------
    bot : BotInfo
        The bot to create.
    dev_accounts : list[KeyfileAccount]
        The list of dev accounts.
    faucet : `ape.contracts.ContractInstance <https://docs.apeworx.io/ape/stable/methoddocs/contracts.html#ape.contracts.base.ContractInstance>`_
        Contract for faucet that mints the testnet base token
    base_instance : `ape.contracts.ContractInstance <https://docs.apeworx.io/ape/stable/methoddocs/contracts.html#ape.contracts.base.ContractInstance>`_
        Contract for base token
    trade_history : pd.DataFrame
        History of previously completed trades.
    hyperdrive_contract : `ape.contracts.ContractInstance <https://docs.apeworx.io/ape/stable/methoddocs/contracts.html#ape.contracts.base.ContractInstance>`_
        Contract for hyperdrive
    bot_config : EnvironmentConfig
        Configuration parameters for the experiment
    rng : NumpyGenerator
        The random number generator.

    Returns
    -------
    agent : Agent
        The agent object used in elf-simulations.
    """
    # pylint: disable=too-many-arguments
    assert bot.index is not None, "Bot must have an index."
    assert isinstance(bot.policy, type(Agent)), "Bot must have a policy of type Agent."
    params = {"trade_chance": FixedPoint(bot.trade_chance), "budget": bot.budget.sample_budget(rng)}
    params["rng"] = rng
    if bot.risk_threshold and bot.name != "random":  # random agent doesn't use risk threshold
        params["risk_threshold"] = FixedPoint(bot.risk_threshold)  # if risk threshold is manually set, we use it
    if bot.name != "random":  # if risk threshold isn't manually set, we get a random one
        params["risk_threshold"] = FixedPoint(
            np.clip(rng.normal(loc=bot.risk.mean, scale=bot.risk.std), bot.risk.min, bot.risk.max).item()
        )
    agent = Agent(wallet_address=dev_accounts[bot.index].address, policy=bot.policy(**params))
    agent.contract = dev_accounts[bot.index]  # assign its onchain contract
    if bot_config.devnet:
        agent.contract.balance += int(1e18)  # give it some eth

    # mint base tokens for the agents
    if (need_to_mint := (params["budget"].scaled_value - base_instance.balanceOf(agent.contract.address)) / 1e18) > 0:
        logging.info(" agent_%s needs to mint %s Base", agent.contract.address[:8], format_numeric_string(need_to_mint))
        if bot_config.devnet:
            txn_args = agent.contract.address, int(50_000 * 1e18)
            ape_utils.attempt_txn(agent.contract, base_instance.mint, *txn_args)
        else:
            assert faucet is not None, "Faucet must be provided to mint base on testnet."
            txn_args = base_instance.address, agent.wallet.address, int(50_000 * 1e18)
            ape_utils.attempt_txn(agent.contract, faucet.mint, *txn_args)
    logging.info(
        " agent_%s is a %s with budget=%s Eth=%s Base=%s",
        bot.index,
        bot.name,
        format_numeric_string(params["budget"]),
        format_numeric_string(agent.contract.balance / 1e18),
        format_numeric_string(base_instance.balanceOf(agent.contract.address) / 1e18),
    )
    agent.wallet = ape_utils.get_wallet_from_trade_history(
        address=agent.contract.address,
        index=bot.index,
        trade_history=trade_history,
        hyperdrive_contract=hyperdrive_contract,
        base_contract=base_instance,
        tolerance=None,  # when recovering form crash, set tolerance to 1e16
    )
    return agent


def set_up_agents(
    bot_config: EnvironmentConfig,
    provider: ProviderAPI,
    hyperdrive_instance: ContractInstance,
    base_instance: ContractInstance,
    addresses: dict[str, str],
    rng: NumpyGenerator,
    trade_history: pd.DataFrame | None = None,
) -> tuple[dict[str, Agent], pd.DataFrame]:
    """Set up python agents & corresponding on-chain accounts.

    Parameters
    ----------
    bot_config : EnvironmentConfig
        Configuration parameters for the experiment
    provider : `ape.api.ProviderAPI <https://docs.apeworx.io/ape/stable/methoddocs/api.html#ape.api.providers.ProviderAPI>`_
        The Ape object that represents your connection to the Ethereum network.
    hyperdrive_instance : `ape.contracts.ContractInstance <https://docs.apeworx.io/ape/stable/methoddocs/contracts.html#ape.contracts.base.ContractInstance>`_
        The hyperdrive contract instance.
    base_instance : `ape.contracts.ContractInstance <https://docs.apeworx.io/ape/stable/methoddocs/contracts.html#ape.contracts.base.ContractInstance>`_
        The base token contract instance.
    addresses : dict[str, str]
        Addresses of deployed contracts.
    rng : NumpyGenerator
        The random number generator.
    trade_history : pd.DataFrame, Optional
        History of previously completed trades.

    Returns
    -------
    sim_agents : dict[str, Agent]
        Dict of agents used in the simulation.
    trade_history : pd.DataFrame
        History of previously completed trades.
    """
    # pylint: disable=too-many-arguments, too-many-locals
    dev_accounts: list[KeyfileAccount] = get_accounts(bot_config)
    faucet = None
    if not bot_config.devnet:
        faucet = ape_utils.get_instance(addresses["goerli_faucet"], provider=provider)
    bot_num = 0
    for bot_name in bot_config.scratch["bot_names"]:
        policy = bot_config.scratch[bot_name].policy
        logging.info(
            "%s: n=%s with policy=%s",
            bot_name,
            bot_config.scratch[f"num_{bot_name}"],
            policy.__name__ if policy.__module__ == "__main__" else policy.__module__,
        )
        bot_num += bot_config.scratch[f"num_{bot_name}"]
    sim_agents = {}
    start_time_ = now()
    if trade_history is None:
        trade_history = ape_utils.get_trade_history(hyperdrive_contract=hyperdrive_instance)
    logging.debug("Getting on-chain trade info took %s seconds", format_numeric_string(now() - start_time_))
    for bot_name in [name for name in bot_config.scratch["bot_names"] if bot_config.scratch[f"num_{name}"] > 0]:
        bot_info = bot_config.scratch[bot_name]
        bot_info.name = bot_name
        for _ in range(bot_config.scratch[f"num_{bot_name}"]):  # loop across number of bots of this type
            bot_info.index = len(sim_agents)
            logging.info("Creating %s agent %s/%s: %s", bot_name, bot_info.index + 1, bot_num, bot_info)
            agent = create_agent(
                bot=bot_info,
                dev_accounts=dev_accounts,
                faucet=faucet,
                base_instance=base_instance,
                trade_history=trade_history,
                hyperdrive_contract=hyperdrive_instance,
                bot_config=bot_config,
                rng=rng,
            )
            sim_agents[f"agent_{agent.wallet.address}"] = agent
    return sim_agents, trade_history


def do_trade(
    market_trade: types.Trade,
    sim_agents: dict[str, Agent],
    hyperdrive_instance: ContractInstance,
    base_instance: ContractInstance,
) -> ape_utils.PoolState:
    """Execute agent trades on hyperdrive solidity contract.

    Parameters
    ----------
    market_trade : types.Trade
        The trade to execute.
    sim_agents : dict[str, Agent]
        Dict of agents used in the simulation.
    hyperdrive_instance : `ape.contracts.ContractInstance <https://docs.apeworx.io/ape/stable/methoddocs/contracts.html#ape.contracts.base.ContractInstance>`_
        The hyperdrive contract instance.
    base_instance : `ape.contracts.ContractInstance <https://docs.apeworx.io/ape/stable/methoddocs/contracts.html#ape.contracts.base.ContractInstance>`_
        The base token contract instance.

    Returns
    -------
    pool_state : ape_utils.PoolSatate
        The Hyperdrive pool state after the trade.
    txn_receipt : `ape.api.transactions.ReceiptAPI <https://docs.apeworx.io/ape/stable/methoddocs/api.html#ape.api.transactions.ReceiptAPI>`_
        The Ape transaction receipt.
    """
    # TODO: add market-state-dependent trading for smart bots
    # market_state = get_simulation_market_state_from_contract(
    #     hyperdrive_contract=hyperdrive_contract, agent_address=contract
    # )
    # market_type = trade_obj.market
    trade = market_trade.trade
    agent_contract = sim_agents[f"agent_{trade.wallet.address}"].contract
    amount = trade.trade_amount.scaled_value  # ape works with ints

    # If agent does not have enough base approved for this trade, then approve another 50k
    # allowance(address owner, address spender) → uint256
    initial_allowance = base_instance.allowance(agent_contract.address, hyperdrive_instance.address)
    allowance_shortfall = amount / 1e18 - initial_allowance
    if allowance_shortfall > 0:
        try:
            txn_args = hyperdrive_instance.address, int(50_000 * 1e8)
            ape_utils.attempt_txn(agent_contract, base_instance.approve, *txn_args)
            logging.info(
                "Allowance too low by %s, at %s for a trade of %s, approving an additional 50k base.",
                allowance_shortfall,
                initial_allowance,
                amount / 1e18,
            )
            updated_allowance = base_instance.allowance(agent_contract.address, hyperdrive_instance.address)
            change_in_allowance = updated_allowance - initial_allowance
            logging.info(
                "Allowance increased by %s from %s to %s", change_in_allowance, initial_allowance, updated_allowance
            )
        except Exception as exc:
            raise ValueError("Failed to approve allowance") from exc
    params = {
        "trade_type": trade.action_type.name,
        "hyperdrive_contract": hyperdrive_instance,
        "agent": agent_contract,
        "amount": amount,
    }
    if trade.action_type.name in ["CLOSE_LONG", "CLOSE_SHORT"]:
        params["maturity_time"] = int(trade.mint_time + elfpy.SECONDS_IN_YEAR)
    logging.info(
        "agent_%s has Eth=%s Base=%s",
        agent_contract.address[:8],
        format_numeric_string(agent_contract.balance / 1e18),
        format_numeric_string(base_instance.balanceOf(agent_contract.address) / 1e18),
    )
    logging.info("\trade %s", trade.action_type.name)
    # execute the trade using key-word arguments
    pool_state, _ = ape_utils.ape_trade(**params)
    return pool_state


def save_trade_streak(current_streak, trade_streak_file, reset: bool = False):
    """Save to file our trade streak so we can resume it on interrupt."""
    streak = 0 if reset is True else current_streak + 1
    with open(trade_streak_file, "w", encoding="utf-8") as file:
        file.write(f"{streak}")
    return streak


def log_and_show_block_info(provider: ape.api.ProjectAPI, trade_streak: int, block_number: int, block_timestamp: int):
    """Get and show the latest block number and gas fees.

    Parameters
    ----------
    provider : `ape.api.ProviderAPI <https://docs.apeworx.io/ape/stable/methoddocs/api.html#ape.api.providers.ProviderAPI>`_
        The Ape object that represents your connection to the Ethereum network.
    trade_streak : int
        The number of trades without crashing.
    block_number : int
        The number of the latest block.
    block_timestamp : int
        The timestamp of the latest block.
    """
    block = provider.get_block(block_number)
    if not hasattr(block, "base_fee"):
        raise ValueError("latest block does not have base_fee")
    base_fee = getattr(block, "base_fee") / 1e9
    logging.info(
        "Block number: %s, Block time: %s, Trades without crashing: %s, base_fee: %s",
        format_numeric_string(block_number),
        datetime.fromtimestamp(block_timestamp),
        trade_streak,
        base_fee,
    )


def set_up_devnet(
    addresses,
    project: ape_utils.HyperdriveProject,
    provider,
    bot_config: EnvironmentConfig,
    pricing_model: HyperdrivePricingModel,
) -> tuple[ContractInstance, ContractInstance, dict[str, str]]:
    """Load deployed devnet addresses or deploy new contracts.

    Parameters
    ----------
    addresses : dict
        The addresses of the deployed contracts.
    project : HyperdriveProject
        The Ape project that contains a Hyperdrive contract.
    provider : `ape.api.ProviderAPI <https://docs.apeworx.io/ape/stable/methoddocs/api.html#ape.api.providers.ProviderAPI>`_
        The Ape object that represents your connection to the Ethereum network.
    bot_config : EnvironmentConfig
        Configuration parameters for the experiment
    pricing_model : HyperdrivePricingModel
        The elf-simulations pricing model.

    Returns
    -------
    base_instance : `ape.contracts.ContractInstance <https://docs.apeworx.io/ape/stable/methoddocs/contracts.html#ape.contracts.base.ContractInstance>`_
        Ape object representing an instance of a deployed base token contract.
    hyperdrive_instance : `ape.contracts.ContractInstance <https://docs.apeworx.io/ape/stable/methoddocs/contracts.html#ape.contracts.base.ContractInstance>`_
        Ape object representing an instance of a deployed base Hyperdrive contract.
    addresses : dict
        The addresses of deployed Hyperdrive contracts.
    deployer_account : KeyfileAccount
        The account used to deploy the contracts.
    """
    # pylint: disable=too-many-arguments
    deployer_account = ape.accounts.test_accounts[0]
    deployer_account.balance += int(1e18)  # eth, for spending on gas, not erc20
    if addresses["baseToken"]:  # use existing base token deployment
        base_instance = ape_utils.get_instance(
            address=addresses["baseToken"],
            contract_type=project.get_contract("ERC20Mintable").contract_type,
            provider=provider,
        )
    else:  # deploy a new base token
        base_instance: ContractInstance = deployer_account.deploy(project.get_contract("ERC20Mintable"))
        addresses["baseToken"] = base_instance.address
    if addresses["hyperdrive"]:  # use existing hyperdrive deployment
        hyperdrive_instance: ContractInstance = ape_utils.get_instance(
            address=addresses["hyperdrive"],
            contract_type=project.get_contract("IHyperdrive").contract_type,
            provider=provider,
        )
    else:  # deploy a new hyperdrive
        hyperdrive_instance: ContractInstance = ape_utils.deploy_hyperdrive(
            bot_config, base_instance, deployer_account, pricing_model, project
        )
        addresses["hyperdrive"] = hyperdrive_instance.address
    return base_instance, hyperdrive_instance, addresses


def set_up_experiment(
    bot_config: EnvironmentConfig,
    provider_settings: dict,
    addresses: dict,
    network_choice: str,
    pricing_model: HyperdrivePricingModel,
    rng: NumpyGenerator,
) -> tuple[ProviderAPI, ContractInstance, ContractInstance, dict, pd.DataFrame, dict[str, Agent], NumpyGenerator,]:
    r"""Set up Ape objects, agent addresses, trade history, and simulation agents.

    Parameters
    ----------
    bot_config : EnvironmentConfig
        Configuration parameters for the experiment
    provider_settings : dict
        Custom parameters passed to the provider.
    addresses : dict
        The addresses of the deployed contracts.
    network_choice : str
        The network to connect to.
    pricing_model : BasePricingModel
        The elf-simulations pricing model to use.
    rng : NumpyGenerator
        The random number generator.

    Returns
    -------
    provider : `ape.api.ProviderAPI <https://docs.apeworx.io/ape/stable/methoddocs/api.html#ape.api.providers.ProviderAPI>`_
        The Ape object that represents your connection to the Ethereum network.
    base_instance : `ape.contracts.ContractInstance <https://docs.apeworx.io/ape/stable/methoddocs/contracts.html#ape.contracts.base.ContractInstance>`_
        The deployed base token instance.
    hyperdrive_instance : `ape.contracts.ContractInstance <https://docs.apeworx.io/ape/stable/methoddocs/contracts.html#ape.contracts.base.ContractInstance>`_
        The deployed Hyperdrive instance.
    hyperdrive_config : dict
        The configuration of the deployed Hyperdrive instance
    trade_history : pd.DataFrame
        History of previously completed trades.
    sim_agents : dict[str, Agent]
        Dict of agents used in the simulation.
    rng : NumpyGenerator
        The random number generator.
    """
    # pylint: disable=too-many-arguments
    provider: ProviderAPI = ape.networks.parse_network_choice(
        network_choice=network_choice,
        provider_settings=provider_settings,
    ).push_provider()
    logging.info(
        "connected to %s, latest block %s",
        "devnet" if bot_config.devnet else network_choice,
        provider.get_block("latest").number,
    )
    project: ape_utils.HyperdriveProject = ape_utils.HyperdriveProject(
        path=Path.cwd(),
        hyperdrive_address=addresses["hyperdrive"] if bot_config.devnet else addresses["goerli_hyperdrive"],
    )
    if bot_config.devnet:  # we're on devnet
        base_instance, hyperdrive_instance, addresses = set_up_devnet(
            addresses, project, provider, bot_config, pricing_model
        )
    else:  # not on devnet, means we're on goerli, so we use known goerli addresses
        base_instance: ContractInstance = ape_utils.get_instance(
            addresses["goerli_sdai"],
            provider=provider,
        )
        hyperdrive_instance: ContractInstance = project.get_hyperdrive_contract()

    sim_agents, trade_history = set_up_agents(bot_config, provider, hyperdrive_instance, base_instance, addresses, rng)
    return (
        provider,
        provider.auto_mine,
        base_instance,
        hyperdrive_instance,
        ape_utils.get_hyperdrive_config(hyperdrive_instance),
        trade_history,
        sim_agents,
        rng,
    )


def do_policy(
    agent: BasePolicy,
    elfpy_market: HyperdriveMarket,
    trade_streak: int,
    trade_streak_file: Path.PathLike,
    sim_agents: dict[str, Agent],
    hyperdrive_instance: ContractInstance,
    base_instance: ContractInstance,
    trade_history: pd.DataFrame | None = None,
) -> int:
    """Execute an agent's policy.

    Parameters
    ----------
    agent : BasePolicy
        The agent object used in elf-simulations.
    elfpy_market : HyperdriveMarket
        The elf-simulations object representing the Hyperdrive market.
    trade_streak : int
        Number of trades in a row without a crash.
    trade_streak_file : Path.PathLike
        Location of the file to which we store our trade streak (continues on interrupt, resets on crash).
    sim_agents : dict[str, Agent]
        Dict of agents used in the simulation.
    hyperdrive_instance : `ape.contracts.ContractInstance <https://docs.apeworx.io/ape/stable/methoddocs/contracts.html#ape.contracts.base.ContractInstance>`_
        The hyperdrive contract instance.
    base_instance : `ape.contracts.ContractInstance <https://docs.apeworx.io/ape/stable/methoddocs/contracts.html#ape.contracts.base.ContractInstance>`_
        Contract for base token
    bot_config : EnvironmentConfig
        The bot configuration.
    trade_history : pd.DataFrame, Optional
        History of previously completed trades. If not provided, it will be queried.

    Returns
    -------
    trade_streak : int
        Number of trades in a row without a crash.
    """
    # pylint: disable=too-many-arguments
    trades: list[types.Trade] = agent.get_trades(market=elfpy_market)
    for trade_object in trades:
        logging.debug(trade_object)
        do_trade(trade_object, sim_agents, hyperdrive_instance, base_instance)
        # marginal update to wallet
        agent.wallet = ape_utils.get_wallet_from_trade_history(
            address=agent.contract.address,
            trade_history=trade_history,
            hyperdrive_contract=hyperdrive_instance,
            base_contract=base_instance,
            add_to_existing_wallet=agent.wallet,
        )
        logging.debug("%s", agent.wallet)
        trade_streak = save_trade_streak(trade_streak, trade_streak_file)  # set and save to file
    return trade_streak


def main(
    bot_config: EnvironmentConfig,
    rng: NumpyGenerator,
    network_choice: str,
    provider_settings: str,
):
    """Run the simulation."""
    # pylint: disable=too-many-locals, too-many-branches, too-many-statements
    # Custom parameters for this experiment

    # Check for default name and exit if is default
    if bot_config.username == DEFAULT_USERNAME:
        raise ValueError("Default username detected, please update 'username' in bot configuration")

    bot_config.scratch["project_dir"] = Path.cwd().parent if Path.cwd().name == "examples" else Path.cwd()
    bot_config.scratch["trade_streak"] = (
        bot_config.scratch["project_dir"] / f".logging/trade_streak{'_devnet' if config.devnet else ''}.txt"
    )
    if "num_louie" not in bot_config.scratch:
        bot_config.scratch["num_louie"]: int = 1
    if "num_sally" not in bot_config.scratch:
        bot_config.scratch["num_sally"]: int = 1
    if "num_random" not in bot_config.scratch:
        bot_config.scratch["num_random"]: int = 1
    bot_config.scratch["louie"] = BotInfo(
        policy=LongLouie,
        trade_chance=bot_config.default_trade_chance,
        risk_threshold=bot_config.default_risk_threshold,
    )
    bot_config.scratch["sally"] = BotInfo(
        policy=ShortSally,
        trade_chance=bot_config.default_trade_chance,
        risk_threshold=bot_config.default_risk_threshold,
    )
    bot_config.scratch["random"] = BotInfo(
        policy=RandomAgent,
        trade_chance=bot_config.default_trade_chance,
        risk_threshold=bot_config.default_risk_threshold,
    )
    bot_config.scratch["bot_names"] = {"louie", "sally", "random"}
    # hard-code goerli addresses
    addresses = {
        "goerli_faucet": "0xe2bE5BfdDbA49A86e27f3Dd95710B528D43272C2",
        "goerli_sdai": "0x11fe4b6ae13d2a6055c8d9cf65c55bac32b5d844",
        "goerli_hyperdrive": "0xB311B825171AF5A60d69aAD590B857B1E5ed23a2",
    }
    if bot_config.devnet:
        addresses = get_devnet_addresses(bot_config, addresses)
    pricing_model = HyperdrivePricingModel()
    (
        provider,
        automine,
        base_instance,
        hyperdrive_instance,
        hyperdrive_config,
        trade_history,
        sim_agents,
        rng,
    ) = set_up_experiment(bot_config, provider_settings, addresses, network_choice, pricing_model, rng)
    assert isinstance(sim_agents, dict), "sim_agents wasn't created or loaded properly."
    ape_utils.dump_agent_info(sim_agents, bot_config)
    logging.info("Constructed %s agents:", len(sim_agents))
    for agent_name in sim_agents:
        logging.info("\t%s", agent_name)

    # Set up postgres to write username to agent wallet addr
    # initialize the postgres session
    wallet_addrs = [agent.contract.address for _, agent in sim_agents.items()]
    session = postgres.initialize_session()
    postgres.add_user_map(bot_config.username, wallet_addrs, session)
    postgres.close_session(session)

    start_timestamp = ape.chain.blocks[-1].timestamp
    trade_streak = 0
    last_executed_block = 0
    while True:  # hyper drive forever into the sunset
        latest_block = ape.chain.blocks[-1]
        block_number = latest_block.number
        block_timestamp = latest_block.timestamp
        if block_number > last_executed_block:
            log_and_show_block_info(provider, trade_streak, block_number, block_timestamp)
            # marginal update to trade_history
            start_block = trade_history.block_number.max() + 1 if trade_history is not None else 0
            start_time = now()
            trade_history = ape_utils.get_trade_history(hyperdrive_instance, start_block, block_number, trade_history)
            logging.debug("Trade history updated in %s seconds", now() - start_time)
            # create market object needed for agent execution
            elfpy_market = ape_utils.create_elfpy_market(
                pricing_model, hyperdrive_instance, hyperdrive_config, block_number, block_timestamp, start_timestamp
            )
            try:
                for agent in sim_agents.values():
                    trade_streak = do_policy(
                        agent,
                        elfpy_market,
                        trade_streak,
                        bot_config.scratch["trade_streak"],
                        sim_agents,
                        hyperdrive_instance,
                        base_instance,
                        trade_history,
                    )
            except Exception as exc:  # we want to catch all exceptions (pylint: disable=broad-exception-caught)
                logging.info("Crashed with error: %s", exc)
                trade_streak = save_trade_streak(
                    trade_streak, bot_config.scratch["trade_streak"], reset=True
                )  # set and save to file
                if bot_config.halt_on_errors:
                    raise exc
            last_executed_block = block_number
        if bot_config.devnet and automine:
            # "automine" means anvil automatically mines a new block after you send a transaction, not time-based.
            ape.chain.mine()
        else:  # either on goerli or on devnet with automine disabled (which means time-based mining is enabled)
            sleep(1)


def get_argparser() -> argparse.ArgumentParser:
    """Define & parse arguments from stdin."""
    parser = argparse.ArgumentParser(
        prog="evm_bots",
        description="Example execution script for running bots using Elfpy",
        epilog="See the README on https://github.com/delvtech/elf-simulations/ for more implementation details",
    )
    parser.add_argument(
        "configuration_json",
        nargs=1,
        default="",
        type=str,
        help="Location of the configuration json file.",
    )
    return parser


if __name__ == "__main__":
    # Get postgres env variables if exists
    load_dotenv()

    config = EnvironmentConfig()
    args = get_argparser().parse_args()
    config.load_from_json(args.configuration_json[0])
    log_utils.setup_logging(
        log_filename=config.log_filename,
        max_bytes=config.max_bytes,
        log_level=config.log_level,
        delete_previous_logs=config.delete_previous_logs,
        log_stdout=config.log_stdout,
        log_format_string=config.log_formatter,
    )
    # inputs
    NETWORK_CHOICE = "ethereum:local:" + ("alchemy" if config.alchemy else "foundry")
    PROVIDER_SETTINGS = {"host": config.rpc_url}
    main(config, np.random.default_rng(config.random_seed), NETWORK_CHOICE, PROVIDER_SETTINGS)

"""A demo for executing an arbitrary number of trades bots on testnet."""
# pylint: disable=too-many-lines
from __future__ import annotations  # types will be strings by default in 3.11

# pyright: reportOptionalMemberAccess=false, reportGeneralTypeIssues=false
# stdlib
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
import requests
import tqdm
from ape import accounts
from ape.api import ProviderAPI, ReceiptAPI
from ape.contracts import ContractInstance
from ape.utils import generate_dev_accounts
from ape_accounts.accounts import KeyfileAccount
from eth_account import Account as EthAccount
from tqdm import trange

import elfpy.markets.hyperdrive.hyperdrive_assets as hyperdrive_assets

# elfpy core repo
import elfpy.utils.apeworx_integrations as ape_utils
import elfpy.utils.outputs as output_utils
from elfpy import SECONDS_IN_YEAR, types
from elfpy.agents.agent import Agent
from elfpy.agents.policies.base import BasePolicy
from elfpy.bots.bot_info import BotInfo
from elfpy.bots.get_config import get_config
from elfpy.bots.get_env_args import EnvironmentArguments, get_env_args
from elfpy.markets.base import BaseMarket, BasePricingModel
from elfpy.markets.hyperdrive import HyperdrivePricingModel
from elfpy.math import FixedPoint
from elfpy.simulators.config import Config
from elfpy.utils.outputs import log_and_show
from elfpy.utils.outputs import number_to_string as fmt


def set_up_experiment(
    experiment_config: Config, args: EnvironmentArguments
) -> tuple[BasePricingModel, str, str, dict[str, str], dict]:
    """Declare and assign experiment variables.

    Parameters
    ----------
    experiment_config : simulators.Config
        The config object.
    args : EnvironmentArguments
        The arguments from environmental variables.

    Returns
    -------
    pricing_model : BasePricingModel
        The elf-simulations pricing model.
    crash_file : str
        The path to the crash file.
    network_choice : str
        Network to connect to, e.g. "ethereum:local:alchemy".
    provider_settings : dict[str, str]
        Settings passed to the Ape provider when instantiating it.
    addresses : dict
        Dict of deployed addresses.
    """
    pricing_model = HyperdrivePricingModel()
    # inputs
    crash_file = f".logging/no_crash_streak{'_devnet' if args.devnet else ''}.txt"
    network_choice = "ethereum:local:" + ("alchemy" if args.alchemy else "foundry")
    provider_settings = {"host": args.rpc_url}
    # hard-code goerli addresses
    addresses = {
        "goerli_faucet": "0xe2bE5BfdDbA49A86e27f3Dd95710B528D43272C2",
        "goerli_sdai": "0x11fe4b6ae13d2a6055c8d9cf65c55bac32b5d844",
        "goerli_hyperdrive": "0xB311B825171AF5A60d69aAD590B857B1E5ed23a2",
    }

    # dynamically load devnet addresses from address file
    if args.devnet:
        addresses = get_devnet_addresses(experiment_config, args, addresses)
    return pricing_model, crash_file, network_choice, provider_settings, addresses


def get_devnet_addresses(
    experiment_config: Config, args: EnvironmentArguments, addresses: dict[str, str]
) -> tuple[dict[str, str], str]:
    """Get devnet addresses from address file."""
    deployed_addresses = {}
    # get deployed addresses from local file, if it exists
    address_file_path = experiment_config.scratch["project_dir"] / "hyperdrive_solidity/artifacts/addresses.json"
    if os.path.exists(address_file_path):
        with open(address_file_path, "r", encoding="utf-8") as file:
            deployed_addresses = json.load(file)
    else:  # otherwise get deployed addresses from artifacts server
        for _ in trange(100, desc="artifacts.."):
            response = requests.get(args.artifacts_url + "/addresses.json", timeout=1)
            if response.status_code == 200:
                deployed_addresses = response.json()
                break
            tqdm.desc = f"artifacts.. {response.status_code}"
            sleep(1)
    if "baseToken" in deployed_addresses:
        addresses["baseToken"] = deployed_addresses["baseToken"]
        log_and_show(f"found devnet base address: {addresses['baseToken']}")
    else:
        addresses["baseToken"] = None
    if "hyperdrive" in deployed_addresses:
        addresses["hyperdrive"] = deployed_addresses["hyperdrive"]
        log_and_show(f"found devnet hyperdrive address: {addresses['hyperdrive']}")
    else:
        addresses["hyperdrive"] = None
    return addresses


def get_accounts(experiment_config: Config) -> list[KeyfileAccount]:
    """Generate dev accounts and turn on auto-sign."""
    num = sum(experiment_config.scratch[f"num_{bot}"] for bot in experiment_config.scratch["bot_names"])
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
    on_chain_trade_info: ape_utils.OnChainTradeInfo,
    hyperdrive_contract: ContractInstance,
    experiment_config: Config,
    args: EnvironmentArguments,
    deployer_account: KeyfileAccount,
) -> Agent:
    """Create an agent as defined in bot_info, assign its address, give it enough base.

    Parameters
    ----------
    bot : BotInfo
        The bot to create.
    dev_accounts : list[KeyfileAccount]
        The list of dev accounts.
    faucet : ContractInstance
        Contract for faucet that mints the testnet base token
    base_instance : ContractInstance
        Contract for base token
    on_chain_trade_info : ape_utils.OnChainTradeInfo
        Information about on-chain trades.
    hyperdrive_contract : ContractInstance
        Contract for hyperdrive
    experiment_config : simulators.Config
        The experiment config.
    args : EnvironmentArguments
        The command line arguments.
    deployer_account : KeyfileAccount
        The deployer account.

    Returns
    -------
    agent : Agent
        The agent object used in elf-simulations.
    """
    # pylint: disable=too-many-arguments
    assert bot.index is not None, "Bot must have an index."
    assert isinstance(bot.policy, type(Agent)), "Bot must have a policy of type Agent."
    params = {
        "trade_chance": experiment_config.scratch["trade_chance"],
        "budget": FixedPoint(
            str(
                np.clip(
                    experiment_config.rng.normal(loc=bot.budget.mean, scale=bot.budget.std),
                    bot.budget.min,
                    bot.budget.max,
                )
            )
        ),
    }
    params["rng"] = experiment_config.rng
    if bot.risk_threshold and bot.name != "random":  # random agent doesn't use risk threshold
        params["risk_threshold"] = bot.risk_threshold  # if risk threshold is manually set, we use it
    if bot.name != "random":  # if risk threshold isn't manually set, we get a random one
        params["risk_threshold"] = np.clip(
            experiment_config.rng.normal(loc=bot.risk.mean, scale=bot.risk.std), bot.risk.min, bot.risk.max
        )
    agent = Agent(wallet_address=dev_accounts[bot.index].address, policy=bot.policy(**params))
    agent.contract = dev_accounts[bot.index]  # assign its onchain contract
    if args.devnet:
        agent.contract.balance += int(1e18)  # give it some eth
    if (need_to_mint := (params["budget"].scaled_value - base_instance.balanceOf(agent.contract.address)) / 1e18) > 0:
        log_and_show(f" agent_{agent.contract.address[:8]} needs to mint {fmt(need_to_mint)} Base")
        with ape.accounts.use_sender(agent.contract):
            if args.devnet:
                txn_receipt: ReceiptAPI = base_instance.mint(
                    agent.contract.address, int(50_000 * 1e18), sender=deployer_account
                )
            else:
                assert faucet is not None, "Faucet must be provided to mint base on testnet."
                txn_receipt: ReceiptAPI = faucet.mint(base_instance.address, agent.wallet.address, int(50_000 * 1e18))
            txn_receipt.await_confirmations()
    log_and_show(
        f" agent_{agent.contract.address[:8]} is a {bot.name} with budget={fmt(params['budget'])}"
        f" Eth={fmt(agent.contract.balance/1e18)} Base={fmt(base_instance.balanceOf(agent.contract.address)/1e18)}"
    )
    agent.wallet = ape_utils.get_wallet_from_onchain_trade_info(
        address=agent.contract.address,
        index=bot.index,
        info=on_chain_trade_info,
        hyperdrive_contract=hyperdrive_contract,
        base_contract=base_instance,
    )
    return agent


def set_up_agents(
    experiment_config: Config,
    args: EnvironmentArguments,
    provider: ProviderAPI,
    hyperdrive_instance: ContractInstance,
    base_instance: ContractInstance,
    addresses: dict[str, str],
    deployer_account: KeyfileAccount,
) -> tuple[dict[str, Agent], ape_utils.OnChainTradeInfo]:
    """Set up python agents & corresponding on-chain accounts.

    Parameters
    ----------
    experiment_config : simulators.Config
        The experiment config.
    args : EnvironmentArguments
        The env var arguments.
    provider : ape.api.ProviderAPI
        The Ape object that connects to the Ethereum network.
    hyperdrive_instance : ContractInstance
        The hyperdrive contract instance.
    base_instance : ContractInstance
        The base token contract instance.
    addresses : dict[str, str]
        Addresses of deployed contracts.
    deployer_account : KeyfileAccount
        The deployer account.

    Returns
    -------
    sim_agents : dict[str, Agent]
        Dict of agents used in the simulation.
    on_chain_trade_info : ape_utils.OnChainTradeInfo
        Information about on-chain trades.
    """
    # pylint: disable=too-many-arguments, too-many-locals
    dev_accounts: list[KeyfileAccount] = get_accounts(experiment_config)
    faucet = None
    if not args.devnet:
        faucet = ape_utils.get_instance(addresses["goerli_faucet"], provider=provider)
    bot_num = 0
    for bot_name in experiment_config.scratch["bot_names"]:
        policy = experiment_config.scratch[bot_name].policy
        log_and_show(
            f"{bot_name:6s}: n={experiment_config.scratch[f'num_{bot_name}']}  "
            f"policy={policy.__name__ if policy.__module__ == '__main__' else policy.__module__:20s}"
        )
        bot_num += experiment_config.scratch[f"num_{bot_name}"]
    sim_agents = {}
    start_time_ = now()
    on_chain_trade_info: ape_utils.OnChainTradeInfo = ape_utils.get_on_chain_trade_info(
        hyperdrive_contract=hyperdrive_instance
    )
    log_and_show(f"Getting on-chain trade info took {fmt(now() - start_time_)} seconds")
    for bot_name in [
        name for name in experiment_config.scratch["bot_names"] if experiment_config.scratch[f"num_{name}"] > 0
    ]:
        bot_info = experiment_config.scratch[bot_name]
        bot_info.name = bot_name
        for _ in range(experiment_config.scratch[f"num_{bot_name}"]):  # loop across number of bots of this type
            bot_info.index = len(sim_agents)
            logging.debug("Creating %s agent %s/%s: %s", bot_name, bot_info.index + 1, bot_num, bot_info)
            agent = create_agent(
                bot=bot_info,
                dev_accounts=dev_accounts,
                faucet=faucet,
                base_instance=base_instance,
                on_chain_trade_info=on_chain_trade_info,
                hyperdrive_contract=hyperdrive_instance,
                experiment_config=experiment_config,
                args=args,
                deployer_account=deployer_account,
            )
            sim_agents[f"agent_{agent.wallet.address}"] = agent
    return sim_agents, on_chain_trade_info


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
    hyperdrive_instance : ContractInstance
        The hyperdrive contract instance.
    base_instance : ContractInstance
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

    # print(f"scaling down from {type(amount)}{amount=}", end="")
    ## amount = int(np.floor(amount/1e18) * 1e18)
    ## amount -= int(1e18)
    # amount = int(amount / 2)
    # print(f" to {type(amount)}{amount=}")

    # If agent does not have enough base approved for this trade, then approve another 50k
    # allowance(address owner, address spender) → uint256
    if base_instance.allowance(agent_contract.address, hyperdrive_instance.address) < amount:
        txn_args = (
            hyperdrive_instance.address,
            FixedPoint("50_000.0", decimal_places=18).scaled_value,
        )
        ape_utils.attempt_txn(agent_contract, base_instance.approve, *txn_args)
        logging.info("Trade had insufficient allowance, approving an additional 50k base.")
    params = {
        "trade_type": trade.action_type.name,
        "hyperdrive_contract": hyperdrive_instance,
        "agent": agent_contract,
        "amount": amount,
    }
    if trade.action_type.name in ["CLOSE_LONG", "CLOSE_SHORT"]:
        params["maturity_time"] = int(trade.mint_time + SECONDS_IN_YEAR)

        # check if we have enough on-chain balance to close this
        prefix = 1 if trade.action_type.name == "CLOSE_LONG" else 2  # LONG = 1, SHORT = 2
        position_id = hyperdrive_assets.encode_asset_id(prefix=prefix, timestamp=params["maturity_time"])
        on_chain_balance = hyperdrive_instance.balanceOf(position_id, agent_contract.address)
        print(f"trying to {trade.action_type.name} {params['amount']=} with {on_chain_balance=}")

        if params["amount"] > on_chain_balance:
            print("oops")

    log_and_show(
        f" agent_{agent_contract.address[:8]} has"
        f" Eth={fmt(agent_contract.balance/1e18)}"
        f" Base={fmt(base_instance.balanceOf(agent_contract.address)/1e18)}"
    )

    # execute the trade using key-word arguments
    pool_state, _ = ape_utils.ape_trade(**params)
    return pool_state


def set_days_without_crashing(current_streak, crash_file, reset: bool = False):
    """Calculate the number of days without crashing."""
    streak = 0 if reset is True else current_streak + 1
    with open(crash_file, "w", encoding="utf-8") as file:
        file.write(f"{streak}")
    return streak


def log_and_show_block_info(
    provider: ape.api.ProjectAPI, no_crash_streak: int, block_number: int, block_timestamp: int
):
    """Get and show the latest block number and gas fees.

    Parameters
    ----------
    provider : ape.api.ProviderAPI
        The Ape object that connects to the Ethereum blockchain.
    no_crash_streak : int
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
    log_and_show(
        "Block number: %s, Block time: %s, Trades without crashing: %s, base_fee: %s",
        fmt(block_number),
        datetime.fromtimestamp(block_timestamp),
        no_crash_streak,
        base_fee,
    )


def set_up_devnet(
    addresses, project, provider, experiment_config, pricing_model
) -> tuple[ContractInstance, ContractInstance, dict[str, str]]:
    """Load deployed devnet addresses or deploy new contracts.

    Parameters
    ----------
    addresses : dict
        The addresses of the deployed contracts.
    project : ape_utils.HyperdriveProject
        The Ape project that contains a Hyperdrive contract.
    provider : ape.api.ProviderAPI
        The Ape object that connects to the Ethereum blockchain.
    experiment_config : simulators.Config
        The experiment configuration object.
    pricing_model : BasePricingModel
        The elf-simulations pricing model.

    Returns
    -------
    addresses : dict
        The addresses of the deployed contracts.
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
            experiment_config, base_instance, deployer_account, pricing_model, project
        )
        addresses["hyperdrive"] = hyperdrive_instance.address
    return base_instance, hyperdrive_instance, addresses, deployer_account


def set_up_ape(
    experiment_config: Config,
    args: EnvironmentArguments,
    provider_settings: dict,
    addresses: dict,
    network_choice: str,
    pricing_model: BasePricingModel,
) -> tuple[ProviderAPI, ContractInstance, ContractInstance, dict, KeyfileAccount]:
    r"""Set up ape.

    Parameters
    ----------
    experiment_config : simulators.Config
        The experiment configuration, a list of variables that define the elf-simulations run.
    args : EnvironmentArguments
        The environmental vars arguments.
    provider_settings : dict
        Custom parameters passed to the provider.
    addresses : dict
        The addresses of the deployed contracts.
    network_choice : str
        The network to connect to.
    pricing_model : BasePricingModel
        The elf-simulations pricing model to use.

    Returns
    -------
    provider : ProviderAPI
        The Ape object that represents your connection to the Ethereum network.
    base_instance : ContractInstance
        The deployed base token instance.
    hyperdrive_instance : ContractInstance
        The deployed Hyperdrive instance.
    hyperdrive_config : dict
        The configuration of the deployed Hyperdrive instance
    deployer_account : KeyfileAccount
        The account used to deploy the contracts.
    """
    # pylint: disable=too-many-arguments
    # sourcery skip: inline-variable, move-assign
    deployer_account = None
    provider: ProviderAPI = ape.networks.parse_network_choice(
        network_choice=network_choice,
        provider_settings=provider_settings,
    ).push_provider()
    log_and_show(
        "connected to %s, latest block %s",
        "devnet" if args.devnet else network_choice,
        provider.get_block("latest").number,
    )
    project: ape_utils.HyperdriveProject = ape_utils.HyperdriveProject(
        path=Path.cwd(),
        hyperdrive_address=addresses["hyperdrive"] if args.devnet else addresses["goerli_hyperdrive"],
    )

    # quick test
    # hyperdrive_instance = project.get_contract("IHyperdrive").at("0xCf7Ed3AccA5a467e9e704C703E8D87F634fB0Fc9")
    # test_result = hyperdrive_instance.getPoolConfig()

    if args.devnet:  # we're on devnet
        base_instance, hyperdrive_instance, addresses, deployer_account = set_up_devnet(
            addresses, project, provider, experiment_config, pricing_model
        )
    else:  # not on devnet, means we're on goerli, so we use known goerli addresses
        base_instance: ContractInstance = ape_utils.get_instance(
            addresses["goerli_sdai"],
            provider=provider,
        )
        hyperdrive_instance: ContractInstance = project.get_hyperdrive_contract()
    # read the hyperdrive config from the contract, and log (and print) it
    hyperdrive_config = ape_utils.get_hyperdrive_config(hyperdrive_instance)
    # becomes provider.get_auto_mine() with this PR: https://github.com/ApeWorX/ape-foundry/pull/51
    automine = provider._make_request("anvil_getAutomine", parameters={})  # pylint: disable=protected-access
    return provider, automine, base_instance, hyperdrive_instance, hyperdrive_config, deployer_account


def do_policy(
    agent: BasePolicy,
    elfpy_market: BaseMarket,
    no_crash_streak: int,
    crash_file: str,
    sim_agents: dict[str, Agent],
    hyperdrive_instance: ContractInstance,
    base_instance: ContractInstance,
    args: EnvironmentArguments,
):  # pylint: disable=too-many-arguments
    """Execute an agent's policy."""
    trades: list[types.Trade] = agent.get_trades(market=elfpy_market)
    for trade_object in trades:
        try:
            logging.debug(trade_object)
            do_trade(trade_object, sim_agents, hyperdrive_instance, base_instance)
            # marginal update to wallet
            agent.wallet = ape_utils.get_wallet_from_onchain_trade_info(
                address=agent.contract.address,
                info=ape_utils.get_on_chain_trade_info(hyperdrive_instance, ape.chain.blocks[-1].number),
                hyperdrive_contract=hyperdrive_instance,
                base_contract=base_instance,
                add_to_existing_wallet=agent.wallet,
            )
            logging.debug("%s", agent.wallet)
            no_crash_streak = set_days_without_crashing(no_crash_streak, crash_file)  # set and save to file
        except Exception as exc:  # we want to catch all exceptions (pylint: disable=broad-exception-caught)
            log_and_show("Crashed with error: %s", exc)
            no_crash_streak = set_days_without_crashing(no_crash_streak, crash_file, reset=True)  # set and save to file
            if args.halt_on_errors:
                raise exc
    return no_crash_streak


def main():
    """Run the simulation."""
    # pylint: disable=too-many-locals
    args = get_env_args()

    experiment_config = get_config(args)
    pricing_model, crash_file, network_choice, provider_settings, addresses = set_up_experiment(experiment_config, args)
    no_crash_streak = 0
    last_executed_block = 0
    output_utils.setup_logging(
        log_filename=experiment_config.log_filename, log_level=experiment_config.log_level, max_bytes=args.max_bytes
    )
    provider, automine, base_instance, hyperdrive_instance, hyperdrive_config, deployer_account = set_up_ape(
        experiment_config, args, provider_settings, addresses, network_choice, pricing_model
    )
    sim_agents, _ = set_up_agents(
        experiment_config, args, provider, hyperdrive_instance, base_instance, addresses, deployer_account
    )
    ape_utils.dump_agent_info(sim_agents, experiment_config)

    start_timestamp = ape.chain.blocks[-1].timestamp
    while True:  # hyper drive forever into the sunset
        latest_block = ape.chain.blocks[-1]
        block_number = latest_block.number
        block_timestamp = latest_block.timestamp
        if block_number > last_executed_block:
            log_and_show_block_info(provider, no_crash_streak, block_number, block_timestamp)
            elfpy_market = ape_utils.create_elfpy_market(
                pricing_model, hyperdrive_instance, hyperdrive_config, block_number, block_timestamp, start_timestamp
            )
            for agent in sim_agents.values():
                no_crash_streak = do_policy(
                    agent,
                    elfpy_market,
                    no_crash_streak,
                    crash_file,
                    sim_agents,
                    hyperdrive_instance,
                    base_instance,
                    args,
                )
            last_executed_block = block_number
        if args.devnet and automine:  # anvil automatically mines after you send a transaction. or manually.
            ape.chain.mine()
        else:  # either on goerli or on devnet with automine disabled (which means time-based mining is enabled)
            sleep(1)


if __name__ == "__main__":
    main()

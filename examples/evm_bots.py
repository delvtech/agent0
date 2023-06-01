"""A demo for executing an arbitrary number of trades bots on testnet."""
# pylint: disable=too-many-lines
from __future__ import annotations  # types will be strings by default in 3.11

# pyright: reportOptionalMemberAccess=false, reportGeneralTypeIssues=false
# stdlib
import argparse
import json
import logging
import os
from collections import namedtuple
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from time import sleep
from time import time as now
from typing import Type, cast

# external lib
import ape
import numpy as np
from ape import accounts
from ape.api import ProviderAPI, ReceiptAPI
from ape.contracts import ContractInstance
from ape.logging import logger as ape_logger
from ape.utils import generate_dev_accounts
from ape_accounts.accounts import KeyfileAccount
from dotenv import load_dotenv
from eth_account import Account as EthAccount
from numpy.random._generator import Generator as NumpyGenerator

# elfpy core repo
import elfpy
import elfpy.agents.agent as elfpy_agent
import elfpy.pricing_models.hyperdrive as hyperdrive_pm
import elfpy.utils.apeworx_integrations as ape_utils
import elfpy.utils.outputs as output_utils
from elfpy import simulators, time, types
from elfpy.agents.policies import random_agent
from elfpy.markets.hyperdrive import hyperdrive_actions, hyperdrive_market
from elfpy.math import FixedPoint
from elfpy.simulators.config import Config
from elfpy.utils import sim_utils
from elfpy.utils.outputs import log_and_show
from elfpy.utils.outputs import number_to_string as fmt


class FixedFrida(elfpy_agent.Agent):
    """Agent that paints & opens fixed rate borrow positions."""

    def __init__(  # pylint: disable=too-many-arguments # noqa: PLR0913
        self,
        rng: NumpyGenerator,
        trade_chance: float,
        risk_threshold: float,
        wallet_address: int,
        budget: FixedPoint = FixedPoint("10_000.0"),
    ) -> None:
        """Add custom stuff then call basic policy init."""
        self.trade_chance = trade_chance
        self.risk_threshold: FixedPoint = FixedPoint(risk_threshold)
        self.rng = rng
        super().__init__(wallet_address, budget)

    def action(self, market: hyperdrive_market.Market) -> list[types.Trade]:
        """Implement a Fixed Frida user strategy.

        I'm an actor with a high risk threshold
        I'm willing to open up a fixed-rate borrow (aka a short) if the fixed rate is ~2% higher than the variable rate
            approx means gauss mean=0.02; std=0.005, clipped at 0, 5
        I will never close my short until the simulation stops
            UNLESS my short reaches the token duration mark (e.g. 6mo)
            realistically, people might leave them hanging
        I have total budget of 2k -> 250k (gauss mean=75k; std=50k, i.e. 68% values are within 75k +/- 50k)
        I only open one short at a time

        Parameters
        ----------
        market : Market
            the trading market

        Returns
        -------
        action_list : list[MarketAction]
        """
        # Any trading at all is based on a weighted coin flip -- they have a trade_chance% chance of executing a trade
        gonna_trade = self.rng.choice([True, False], p=[self.trade_chance, 1 - self.trade_chance])
        if not gonna_trade:
            return []
        action_list = []
        for short_time, short in self.wallet.shorts.items():  # loop over shorts
            if (market.block_time.time - short_time) >= market.annualized_position_duration:  # if any short is mature
                trade_amount = short.balance  # close the whole thing
                action_list += [
                    types.Trade(
                        market=types.MarketType.HYPERDRIVE,
                        trade=hyperdrive_actions.MarketAction(
                            action_type=hyperdrive_actions.MarketActionType.CLOSE_SHORT,
                            trade_amount=trade_amount,
                            wallet=self.wallet,
                            mint_time=short_time,
                        ),
                    )
                ]
        short_balances = [short.balance for short in self.wallet.shorts.values()]
        has_opened_short = any((short_balance > 0 for short_balance in short_balances))
        # only open a short if the fixed rate is 0.02 or more lower than variable rate
        if (market.fixed_apr - market.market_state.variable_apr) < self.risk_threshold and not has_opened_short:
            # TODO: This is a hack until we fix get_max
            # issue # 440
            # maximum amount the agent can short given the market and the agent's wallet
            # trade_amount = self.get_max_short(market)
            maximum_trade_amount_in_bonds = (
                market.market_state.share_reserves * market.market_state.share_price / FixedPoint("2.0")
            )
            # WEI <= trade_amount <= max_short
            trade_amount = max(elfpy.WEI, min(FixedPoint("0.0"), maximum_trade_amount_in_bonds))
            if trade_amount > elfpy.WEI:
                action_list += [
                    types.Trade(
                        market=types.MarketType.HYPERDRIVE,
                        trade=hyperdrive_actions.MarketAction(
                            action_type=hyperdrive_actions.MarketActionType.OPEN_SHORT,
                            trade_amount=trade_amount,
                            wallet=self.wallet,
                            mint_time=market.block_time.time,
                        ),
                    )
                ]
        return action_list


class LongLouie(elfpy_agent.Agent):
    """Long-nosed agent that opens longs."""

    def __init__(  # pylint: disable=too-many-arguments # noqa: PLR0913
        self,
        rng: NumpyGenerator,
        trade_chance: float,
        risk_threshold: float,
        wallet_address: int,
        budget: FixedPoint = FixedPoint("10_000.0"),
    ) -> None:
        """Add custom stuff then call basic policy init."""
        self.trade_chance = trade_chance
        self.risk_threshold: FixedPoint = FixedPoint(risk_threshold)
        self.rng = rng
        super().__init__(wallet_address, budget)

    def action(self, market: hyperdrive_market.Market) -> list[types.Trade]:
        """Implement a Long Louie user strategy.

        I'm not willing to open a long if it will cause the fixed-rate apr to go below the variable rate
            I simulate the outcome of my trade, and only execute on this condition
        I only close if the position has matured
        I have total budget of 2k -> 250k (gauss mean=75k; std=50k, i.e. 68% values are within 75k +/- 50k)
        I only open one long at a time

        Parameters
        ----------
        market : Market
            the trading market

        Returns
        -------
        action_list : list[MarketAction]
        """
        # Any trading at all is based on a weighted coin flip -- they have a trade_chance% chance of executing a trade
        gonna_trade = self.rng.choice([True, False], p=[self.trade_chance, 1 - self.trade_chance])
        if not gonna_trade:
            return []
        action_list = []
        for long_time, long in self.wallet.longs.items():  # loop over longs
            if (market.block_time.time - long_time) >= market.annualized_position_duration:  # if any long is mature
                trade_amount = long.balance  # close the whole thing
                action_list += [
                    types.Trade(
                        market=types.MarketType.HYPERDRIVE,
                        trade=hyperdrive_actions.MarketAction(
                            action_type=hyperdrive_actions.MarketActionType.CLOSE_LONG,
                            trade_amount=trade_amount,
                            wallet=self.wallet,
                            mint_time=long_time,
                        ),
                    )
                ]

        long_balances = [long.balance for long in self.wallet.longs.values()]
        has_opened_long = any((long_balance > 0 for long_balance in long_balances))
        # only open a long if the fixed rate is higher than variable rate
        if (
            market.fixed_apr - market.market_state.variable_apr
        ) > self.risk_threshold and not has_opened_long:  # risk_threshold = 0
            total_bonds_to_match_variable_apr = market.pricing_model.calc_bond_reserves(
                target_apr=market.market_state.variable_apr,  # fixed rate targets the variable rate
                time_remaining=market.position_duration,
                market_state=market.market_state,
            )
            # get the delta bond amount & convert units
            new_bonds_to_match_variable_apr = (
                market.market_state.bond_reserves - total_bonds_to_match_variable_apr
            ) * market.spot_price
            # divide by 2 to adjust for changes in share reserves when the trade is executed
            adjusted_bonds = new_bonds_to_match_variable_apr / FixedPoint("2.0")
            # TODO: This is a hack until we fix get_max
            # issue # 440
            # get the maximum amount the agent can long given the market and the agent's wallet
            # max_trade_amount = self.get_max_long(market)
            maximum_trade_amount_in_base = market.market_state.bond_reserves * market.spot_price / FixedPoint("2.0")
            # WEI <= trade_amount <= max_short
            # don't want to trade more than the agent has or more than the market can handle
            trade_amount = max(elfpy.WEI, min(adjusted_bonds, maximum_trade_amount_in_base))
            if trade_amount > elfpy.WEI:
                action_list += [
                    types.Trade(
                        market=types.MarketType.HYPERDRIVE,
                        trade=hyperdrive_actions.MarketAction(
                            action_type=hyperdrive_actions.MarketActionType.OPEN_LONG,
                            trade_amount=trade_amount,
                            wallet=self.wallet,
                            mint_time=market.block_time.time,
                        ),
                    )
                ]
        return action_list


def get_argparser() -> argparse.ArgumentParser:
    """Define & parse arguments from stdin.

    List of arguments:
        log_filename : Optional output filename for logging. Default is "testnet_bots".
        log_level : Logging level, should be in ["DEBUG", "INFO", "WARNING"]. Default is "INFO".
        max_bytes : Maximum log file output size, in bytes. Default is 1MB.
        num_louie : Number of Long Louie agents to run. Default is 0.
        num_frida : Number of Fixed Rate Frida agents to run. Default is 0.
        num_random: Number of Random agents to run. Default is 0.
        trade_chance : Chance for a bot to execute a trade. Default is 0.1.

    Returns
    -------
    parser : argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog="TestnetBots",
        description="Execute bots on testnet",
        epilog="See the README on https://github.com/element-fi/elf-simulations/ for more implementation details",
    )
    parser.add_argument("--log_filename", help="Optional output filename for logging", default="testnet_bots", type=str)
    parser.add_argument(
        "--log_level",
        help='Logging level, should be in ["DEBUG", "INFO", "WARNING"]. Default is "INFO".',
        default="INFO",
        type=str,
    )
    parser.add_argument(
        "--max_bytes",
        help=f"Maximum log file output size, in bytes. Default is {elfpy.DEFAULT_LOG_MAXBYTES} bytes."
        "More than 100 files will cause overwrites.",
        default=elfpy.DEFAULT_LOG_MAXBYTES,
        type=int,
    )
    parser.add_argument("--num_louie", help="Number of Louie agents (default=0)", default=0, type=int)
    parser.add_argument("--num_frida", help="Number of Frida agents (default=0)", default=0, type=int)
    parser.add_argument("--num_random", help="Number of Random agents (default=4)", default=4, type=int)
    parser.add_argument(
        "--trade_chance",
        help="Percent chance that a agent gets to trade on a given block (default = 0.1, i.e. 10%)",
        default=0.1,
        type=float,
    )
    parser.add_argument("--alchemy", help="Use Alchemy as a provider", action="store_true")  # default is false

    parser.add_argument("--devnet", help="Run on devnet", action="store_true")  # stroe_true because default is false
    parser.add_argument("--fork_url", help="Override for url to fork from", default=None, type=str)
    parser.add_argument("--fork_port", help="Override for port for fork to use", default=None, type=int)
    return parser


@dataclass
class BotInfo:
    """Information about a bot.

    Attributes
    ----------
    policy : Type[Agent]
        The agent's policy.
    trade_chance : float
        Percent chance that a agent gets to trade on a given block.
    risk_threshold : float | None
        The risk threshold for the agent.
    budget : Budget[mean, std, min, max]
        The budget for the agent.
    risk : Risk[mean, std, min, max]
        The risk for the agent.
    index : int | None
        The index of the agent in the list of ALL agents.
    name : str
        The name of the agent.
    """

    Budget = namedtuple("Budget", ["mean", "std", "min", "max"])
    Risk = namedtuple("Risk", ["mean", "std", "min", "max"])
    policy: Type[elfpy_agent.Agent]
    trade_chance: float = 0.1
    risk_threshold: float | None = None
    budget: Budget = Budget(mean=5_000, std=2_000, min=1_000, max=10_000)
    risk: Risk = Risk(mean=0.02, std=0.01, min=0.0, max=0.06)
    index: int | None = None
    name: str = "botty mcbotface"

    def __repr__(self) -> str:
        """Return a string representation of the object."""
        return f"{self.name} " + ",".join(
            [f"{key}={value}" if value else "" for key, value in self.__dict__.items() if key not in ["name", "policy"]]
        )


def get_config(args: argparse.Namespace) -> Config:
    """Instantiate a config object with elf-simulation parameters.

    Parameters
    ----------
    args : argparse.Namespace
        The parsed arguments from stdin.

    Returns
    -------
    config : simulators.Config
        The config object.
    """
    load_dotenv(dotenv_path=f"{Path.cwd() if Path.cwd().name != 'examples' else Path.cwd().parent}/.env")
    ape_logger.set_level(logging.ERROR)
    config = Config()
    config.log_level = output_utils.text_to_log_level(args.log_level)
    random_seed_file = f".logging/random_seed{'_devnet' if args.devnet else ''}.txt"
    if os.path.exists(random_seed_file):
        with open(random_seed_file, "r", encoding="utf-8") as file:
            config.random_seed = int(file.read()) + 1
    else:  # make parent directory if it doesn't exist
        os.makedirs(os.path.dirname(random_seed_file), exist_ok=True)
    logging.info("Random seed=%s", config.random_seed)
    with open(random_seed_file, "w", encoding="utf-8") as file:
        file.write(str(config.random_seed))
    config.title = "evm bots"
    for key, value in args.__dict__.items():
        if hasattr(config, key):
            config[key] = value
        else:
            config.scratch[key] = value
    config.log_filename += "_devnet" if args.devnet else ""

    # Custom parameters for this experiment
    config.scratch["project_dir"] = Path.cwd().parent if Path.cwd().name == "examples" else Path.cwd()
    config.scratch["louie"] = BotInfo(risk_threshold=0.0, policy=LongLouie, trade_chance=config.scratch["trade_chance"])
    config.scratch["frida"] = BotInfo(policy=FixedFrida, trade_chance=config.scratch["trade_chance"])
    config.scratch["random"] = BotInfo(policy=random_agent.RandomAgent, trade_chance=config.scratch["trade_chance"])
    config.scratch["bot_names"] = {"louie", "frida", "random"}

    config.freeze()
    return config


def set_up_experiment(
    experiment_config: Config, args: argparse.Namespace
) -> tuple[elfpy.pricing_models.base.PricingModel, str, str, dict[str, str], dict]:
    """Declare and assign experiment variables.

    Parameters
    ----------
    experiment_config : simulators.Config
        The config object.
    args : argparse.Namespace
        The parsed arguments from stdin.

    Returns
    -------
    pricing_model : elfpy.pricing_models.base.PricingModel
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
    pricing_model = hyperdrive_pm.HyperdrivePricingModel()
    # inputs
    crash_file = f".logging/no_crash_streak{'_devnet' if args.devnet else ''}.txt"
    network_choice = "ethereum:local:" + ("alchemy" if args.alchemy else "foundry")
    provider_settings = {
        "fork_url": args.fork_url or "https://localhost:8545",
        "port": args.fork_port or 8545,
    }
    # hard-code goerli addresses
    addresses = {
        "goerli_faucet": "0xe2bE5BfdDbA49A86e27f3Dd95710B528D43272C2",
        "goerli_sdai": "0x11fe4b6ae13d2a6055c8d9cf65c55bac32b5d844",
        "goerli_hyperdrive": "0xB311B825171AF5A60d69aAD590B857B1E5ed23a2",
    }

    # dynamically load devnet addresses from address file
    address_file = None
    if args.devnet:
        addresses, address_file = get_devnet_addresses(experiment_config, addresses)
    return pricing_model, crash_file, network_choice, provider_settings, addresses, address_file


def get_devnet_addresses(experiment_config: Config, addresses: dict[str, str]) -> tuple[dict[str, str], str]:
    """Get devnet addresses from address file."""
    address_file = experiment_config.scratch["project_dir"] / "artifacts" / "addresses.json"
    # make parent folder if it doesn't exist
    os.makedirs(os.path.dirname(address_file), exist_ok=True)
    address_file_data = {}
    if Path.exists(address_file):
        with open(address_file, "r", encoding="utf-8") as file:
            address_file_data = json.load(file)
    if "baseToken" in address_file_data:
        addresses["baseToken"] = address_file_data["baseToken"]
        log_and_show(f"found devnet base address: {addresses['baseToken']}")
    else:
        addresses["baseToken"] = None
    if "hyperdrive" in address_file_data:
        addresses["hyperdrive"] = address_file_data["hyperdrive"]
        log_and_show(f"found devnet hyperdrive address: {addresses['hyperdrive']}")
    else:
        addresses["hyperdrive"] = None
    return addresses, address_file


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
    args: dict,
    deployer_account: KeyfileAccount,
) -> elfpy.agents.agent.Agent:
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
    args : dict
        The command line arguments.
    deployer_account : KeyfileAccount
        The deployer account.

    Returns
    -------
    agent : elfpy.agents.agent.Agent
        The agent object used in elf-simulations.
    """
    # pylint: disable=too-many-arguments
    assert bot.index is not None, "Bot must have an index."
    assert isinstance(bot.policy, type(elfpy_agent.Agent)), "Bot must have a policy of type Agent."
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
        "wallet_address": dev_accounts[bot.index].address,
    }
    params["rng"] = experiment_config.rng
    if bot.risk_threshold and bot.name != "random":  # random agent doesn't use risk threshold
        params["risk_threshold"] = bot.risk_threshold  # if risk threshold is manually set, we use it
    if bot.name != "random":  # if risk threshold isn't manually set, we get a random one
        params["risk_threshold"] = np.clip(
            experiment_config.rng.normal(loc=bot.risk.mean, scale=bot.risk.std), bot.risk.min, bot.risk.max
        )
    agent = bot.policy(**params)  # instantiate the agent with its policy and params
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
        address_=agent.contract.address,
        index=bot.index,
        info=on_chain_trade_info,
        hyperdrive_contract=hyperdrive_contract,
        base_contract=base_instance,
    )
    return agent


def set_up_agents(
    experiment_config: Config,
    args: argparse.Namespace,
    provider: ProviderAPI,
    hyperdrive_instance: ContractInstance,
    base_instance: ContractInstance,
    addresses: dict[str, str],
    deployer_account: KeyfileAccount,
) -> dict[str, elfpy.agents.agent.Agent]:
    """Set up python agents & corresponding on-chain accounts.

    Parameters
    ----------
    experiment_config : simulators.Config
        The experiment config.
    args : dict
        The command line arguments.
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
    sim_agents : dict[str, elfpy.agents.agent.Agent]
        Dict of agents used in the simulation.
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
    return sim_agents


def do_trade(
    market_trade: types.Trade,
    sim_agents: dict[str, elfpy.agents.agent.Agent],
    hyperdrive_instance: ContractInstance,
    base_instance: ContractInstance,
):
    """Execute agent trades on hyperdrive solidity contract.

    Parameters
    ----------
    market_trade : types.Trade
        The trade to execute.
    sim_agents : dict[str, elfpy.agents.agent.Agent]
        Dict of agents used in the simulation.
    hyperdrive_instance : ContractInstance
        The hyperdrive contract instance.
    base_instance : ContractInstance
        The base token contract instance.
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
        params["maturity_time"] = int(trade.mint_time + elfpy.SECONDS_IN_YEAR)
    log_and_show(
        f" agent_{agent_contract.address[:8]} has"
        f" Eth={fmt(agent_contract.balance/1e18)}"
        f" Base={fmt(base_instance.balanceOf(agent_contract.address)/1e18)}"
    )

    # execute the trade using key-word arguments
    ape_utils.ape_trade(**params)


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


def get_simulator(
    experiment_config: Config, pricing_model: elfpy.pricing_models.base.PricingModel
) -> simulators.Simulator:
    """Instantiate and return an initialized elfpy Simulator object."""
    market, _, _ = sim_utils.get_initialized_hyperdrive_market(
        pricing_model=pricing_model, block_time=time.BlockTime(), config=experiment_config
    )
    return simulators.Simulator(experiment_config, market, time.BlockTime())


def deploy_hyperdrive(
    experiment_config: Config,
    base_instance: ContractInstance,
    deployer_account: KeyfileAccount,
    pricing_model: elfpy.pricing_models.base.PricingModel,
    project: ape_utils.HyperdriveProject,
) -> ContractInstance:
    """Deploy Hyperdrive when operating on a fresh fork.

    Parameters
    ----------
    experiment_config : simulators.Config
        The experiment configuration object.
    base_instance : ContractInstance
        The base token contract instance.
    deployer_account : Account
        The account used to deploy smart contracts.
    pricing_model : elfpy.pricing_models.base.PricingModel
        The elf-simulations pricing model.
    project : ape_utils.HyperdriveProject
        The Ape project that contains a Hyperdrive contract.

    Returns
    -------
    hyperdrive : ContractInstance
        The deployed Hyperdrive contract instance.
    """
    initial_supply = FixedPoint(experiment_config.target_liquidity, decimal_places=18)
    initial_apr = FixedPoint(experiment_config.target_fixed_apr, decimal_places=18)
    simulator = get_simulator(experiment_config, pricing_model)  # Instantiate the sim market
    base_instance.mint(
        initial_supply.scaled_value,
        sender=deployer_account,  # minted amount goes to sender
    )
    hyperdrive: ContractInstance = deployer_account.deploy(
        project.get_contract("MockHyperdriveTestnet"),
        base_instance,
        initial_apr.scaled_value,
        FixedPoint(experiment_config.init_share_price).scaled_value,
        365,  # checkpoints per term
        86400,  # checkpoint duration in seconds (1 day)
        (
            FixedPoint("1.0") / (simulator.market.time_stretch_constant)
        ).scaled_value,  # time stretch in solidity format (inverted)
        (
            FixedPoint(experiment_config.curve_fee_multiple).scaled_value,
            FixedPoint(experiment_config.flat_fee_multiple).scaled_value,
            FixedPoint(experiment_config.governance_fee_multiple).scaled_value,
        ),
        deployer_account,
    )
    with ape.accounts.use_sender(deployer_account):
        base_instance.approve(hyperdrive, initial_supply.scaled_value)
        hyperdrive.initialize(
            initial_supply.scaled_value,
            initial_apr.scaled_value,
            deployer_account,
            True,
        )
    return hyperdrive


def set_up_devnet(
    addresses, project, provider, experiment_config, pricing_model, address_file
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
    pricing_model : elfpy.pricing_models.base.PricingModel
        The elf-simulations pricing model.
    address_file : str
        The path to the file containing the addresses of the deployed contracts.

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
            contract_type=project.get_contract("MockHyperdriveTestnet").contract_type,
            provider=provider,
        )
    else:  # deploy a new hyperdrive
        hyperdrive_instance: ContractInstance = deploy_hyperdrive(
            experiment_config, base_instance, deployer_account, pricing_model, project
        )
        addresses["hyperdrive"] = hyperdrive_instance.address
    with open(address_file, "w", encoding="utf-8") as file:
        json.dump(addresses, file)
    return base_instance, hyperdrive_instance, addresses, deployer_account


def get_hyperdrive_config(hyperdrive_instance) -> dict:
    """Get the hyperdrive config from a deployed hyperdrive contract.

    Parameters
    ----------
    hyperdrive_instance : ContractInstance
        The deployed hyperdrive contract instance.

    Returns
    -------
    hyperdrive_config : dict
        The hyperdrive config.
    """
    hyperdrive_config: dict = hyperdrive_instance.getPoolConfig().__dict__
    hyperdrive_config["timeStretch"] = 1 / (hyperdrive_config["timeStretch"] / 1e18)
    log_and_show(f"Hyperdrive config deployed at {hyperdrive_instance.address}:")
    for key, value in hyperdrive_config.items():
        divisor = 1 if key in ["positionDuration", "checkpointDuration", "timeStretch"] else 1e18
        log_and_show(f" {key}: {fmt(value/divisor)}")
    hyperdrive_config["term_length"] = 365  # days
    return hyperdrive_config


def set_up_ape(
    experiment_config: Config,
    args: argparse.Namespace,
    provider_settings: dict,
    addresses: dict,
    network_choice: str,
    address_file: str,
    pricing_model: elfpy.pricing_models.base.PricingModel,
) -> tuple[ProviderAPI, ContractInstance, ContractInstance, dict, KeyfileAccount]:
    r"""Set up ape.

    Parameters
    ----------
    experiment_config : simulators.Config
        The experiment configuration, a list of variables that define the elf-simulations run.
    args : argparse.Namespace
        The command line arguments.
    provider_settings : dict
        Custom parameters passed to the provider.
    addresses : dict
        The addresses of the deployed contracts.
    network_choice : str
        The network to connect to.
    address_file : str
        The path to the file containing the addresses of the deployed contracts.
    pricing_model : elfpy.pricing_models.base.PricingModel
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
        hyperdrive_address=addresses["goerli_hyperdrive"],  # ignored on devnet
    )
    if args.devnet:  # we're on devnet
        base_instance, hyperdrive_instance, addresses, deployer_account = set_up_devnet(
            addresses, project, provider, experiment_config, pricing_model, address_file
        )
    else:  # not on devnet, means we're on goerli, so we use known goerli addresses
        base_instance: ContractInstance = ape_utils.get_instance(
            experiment_config.scratch[experiment_config.scratch["goerli_sdai_address"]],
            provider=provider,
        )
        hyperdrive_instance: ContractInstance = project.get_hyperdrive_contract()
    # read the hyperdrive config from the contract, and log (and print) it
    hyperdrive_config = get_hyperdrive_config(hyperdrive_instance)
    # becomes provider.get_auto_mine() with this PR: https://github.com/ApeWorX/ape-foundry/pull/51
    automine = provider._make_request("anvil_getAutomine", parameters={})  # pylint: disable=protected-access
    return provider, automine, base_instance, hyperdrive_instance, hyperdrive_config, deployer_account


def do_policy(
    policy: elfpy.agents.policy.Policy,
    elfpy_market: elfpy.markets.base.Market,
    no_crash_streak: int,
    crash_file: str,
    sim_agents: dict[str, elfpy.agents.agent.Agent],
    hyperdrive_instance: ContractInstance,
    base_instance: ContractInstance,
):  # pylint: disable=too-many-arguments
    """Execute an agent's policy."""
    trades: list[types.Trade] = policy.get_trades(market=elfpy_market)
    for trade_object in trades:
        try:
            logging.debug(trade_object)
            do_trade(trade_object, sim_agents, hyperdrive_instance, base_instance)
            no_crash_streak = set_days_without_crashing(no_crash_streak, crash_file)  # set and save to file
        except Exception as exc:  # we want to catch all exceptions (pylint: disable=broad-exception-caught)
            log_and_show("Crashed unexpectedly: %s", exc)
            no_crash_streak = set_days_without_crashing(no_crash_streak, crash_file, reset=True)  # set and save to file
            raise exc
    return no_crash_streak


def create_elfpy_market(
    pricing_model: elfpy.pricing_models.base.PricingModel,
    hyperdrive_instance: ContractInstance,
    hyperdrive_config: dict,
    block_number: int,
    block_timestamp: int,
    start_timestamp: int,
) -> hyperdrive_market.Market:
    """Create an elfpy market.

    Parameters
    ----------
    pricing_model : elfpy.pricing_models.base.PricingModel
        The pricing model to use.
    hyperdrive_instance : ContractInstance
        The deployed Hyperdrive instance.
    hyperdrive_config : dict
        The configuration of the deployed Hyperdrive instance
    block_number : int
        The block number of the latest block.
    block_timestamp : int
        The timestamp of the latest block.
    start_timestamp : int
        The timestamp for when we started the simulation.

    Returns
    -------
    hyperdrive_market.Market
        The elfpy market.
    """
    # pylint: disable=too-many-arguments
    return hyperdrive_market.Market(
        pricing_model=pricing_model,
        market_state=ape_utils.get_market_state_from_contract(hyperdrive_contract=hyperdrive_instance),
        position_duration=time.StretchedTime(
            days=FixedPoint(hyperdrive_config["term_length"]),
            time_stretch=FixedPoint(hyperdrive_config["timeStretch"]),
            normalizing_constant=FixedPoint(hyperdrive_config["term_length"]),
        ),
        block_time=time.BlockTime(
            _time=FixedPoint((block_timestamp - start_timestamp) / 365),
            _block_number=FixedPoint(block_number),
            _step_size=FixedPoint("1.0") / FixedPoint("365.0"),
        ),
    )


def main():
    """Run the simulation."""
    # pylint: disable=too-many-locals
    args = get_argparser().parse_args()
    experiment_config = get_config(args)
    pricing_model, crash_file, network_choice, provider_settings, addresses, address_file = set_up_experiment(
        experiment_config, args
    )
    no_crash_streak = 0
    last_executed_block = 0
    output_utils.setup_logging(log_filename=experiment_config.log_filename, log_level=experiment_config.log_level)
    provider, automine, base_instance, hyperdrive_instance, hyperdrive_config, deployer_account = set_up_ape(
        experiment_config, args, provider_settings, addresses, network_choice, address_file, pricing_model
    )
    sim_agents: dict[str, elfpy.agents.agent.Agent] = set_up_agents(
        experiment_config, args, provider, hyperdrive_instance, base_instance, addresses, deployer_account
    )

    start_timestamp = ape.chain.blocks[-1].timestamp
    while True:  # hyper drive forever into the sunset
        latest_block = ape.chain.blocks[-1]
        block_number = latest_block.number
        block_timestamp = latest_block.timestamp
        if block_number > last_executed_block:
            log_and_show_block_info(provider, no_crash_streak, block_number, block_timestamp)
            elfpy_market = create_elfpy_market(
                pricing_model, hyperdrive_instance, hyperdrive_config, block_number, block_timestamp, start_timestamp
            )
            for policy in sim_agents.values():
                no_crash_streak = do_policy(
                    policy, elfpy_market, no_crash_streak, crash_file, sim_agents, hyperdrive_instance, base_instance
                )
            last_executed_block = block_number
        if args.devnet and automine:  # anvil automatically mines after you send a transaction. or manually.
            ape.chain.mine()
        else:  # either on goerli or on devnet with automine disabled (which means time-based mining is enabled)
            sleep(1)


if __name__ == "__main__":
    main()

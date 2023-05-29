"""A demo for executing an arbitrary number of trades bots on testnet."""
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


def get_config() -> simulators.Config:
    """Set _config values for the experiment."""
    load_dotenv(dotenv_path=f"{Path.cwd() if Path.cwd().name != 'examples' else Path.cwd().parent}/.env")
    args = get_argparser().parse_args()
    ape_logger.set_level(logging.ERROR)
    config = simulators.Config()
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
    # invariants
    config.scratch["louie"] = BotInfo(risk_threshold=0.0, policy=LongLouie, trade_chance=config.scratch["trade_chance"])
    config.scratch["frida"] = BotInfo(policy=FixedFrida, trade_chance=config.scratch["trade_chance"])
    config.scratch["random"] = BotInfo(policy=random_agent.RandomAgent, trade_chance=config.scratch["trade_chance"])
    config.scratch["bot_names"] = {"louie", "frida", "random"}
    config.scratch["pricing_model"] = hyperdrive_pm.HyperdrivePricingModel()
    # inputs
    config.scratch["devnet"] = args.devnet
    config.scratch["crash_file"] = f".logging/no_crash_streak{'_devnet' if args.devnet else ''}.txt"
    config.scratch["in_docker"] = os.path.exists("/.dockerenv")
    config.scratch["network_choice"] = "ethereum:local:foundry"
    if args.alchemy:
        config.scratch["network_choice"] = "ethereum:goerli:alchemy"
    config.scratch["provider_settings"] = {}
    if args.fork_url:
        config.scratch["provider_settings"].update({"fork_url": args.fork_url})
    if args.fork_port:
        config.scratch["provider_settings"].update({"port": args.fork_port})
    if args.devnet:
        with open(
            (Path.cwd() if Path.cwd().name == "examples" else Path.cwd()) / "artifacts" / "addresses.json",
            "r",
            encoding="utf-8",
        ) as file:
            addresses = json.load(file)
        if "baseToken" in addresses:
            config.scratch["base_address"] = addresses["baseToken"]
            log_and_show(f"found devnet base address: {config.scratch['base_address']}")
        if "hyperdrive" in addresses:
            config.scratch["hyperdrive_address"] = addresses["hyperdrive"]
            log_and_show(f"found devnet hyperdrive address: {config.scratch['hyperdrive_address']}")

    config.scratch["faucet_address"] = "0xe2bE5BfdDbA49A86e27f3Dd95710B528D43272C2"
    config.scratch["no_crash_streak"] = 0
    config.scratch["last_executed_block"] = 0

    config.freeze()
    return config


def get_accounts(config: simulators.Config) -> list[KeyfileAccount]:
    """Generate dev accounts and turn on auto-sign."""
    num = sum(config.scratch[f"num_{bot}"] for bot in config.scratch["bot_names"])
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
    base_: ContractInstance,
    on_chain_trade_info: ape_utils.OnChainTradeInfo,
    hyperdrive_contract: ContractInstance,
    experiment_config: simulators.Config,
):  # pylint: disable=too-many-arguments
    """Create an agent as defined in bot_info, assign its address, give it enough base.

    Parameters
    ----------
    bot : BotInfo
        The bot to create.
    dev_accounts : list[KeyfileAccount]
        The list of dev accounts.
    faucet : ContractInstance
        Contract for faucet that mints the testnet base token
    base_ : ContractInstance
        Contract for base token
    on_chain_trade_info : ape_utils.OnChainTradeInfo
        Information about on-chain trades.
    hyperdrive_contract : ContractInstance
        Contract for hyperdrive
    experiment_config : simulators.Config
        The experiment config.

    Returns
    -------
    Agent
        The agent.
    """
    assert bot.index is not None, "Bot must have an index."
    assert isinstance(bot.policy, type(elfpy_agent.Agent)), "Bot must have a policy of type Agent."
    params = {
        "trade_chance": experiment_config.scratch["trade_chance"],
        "budget": FixedPoint(
            np.clip(
                experiment_config.rng.normal(loc=bot.budget.mean, scale=bot.budget.std), bot.budget.min, bot.budget.max
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
    if experiment_config.scratch["devnet"]:
        agent.contract.balance += int(1e18)  # give it some eth
    if (need_to_mint := params["budget"] - base_.balanceOf(agent.contract.address) / 1e18) > 0:
        log_and_show(f" agent_{agent.contract.address[:8]} needs to mint {fmt(need_to_mint)} Base")
        with ape.accounts.use_sender(agent.contract):
            if experiment_config.scratch["devnet"]:
                txn_receipt: ReceiptAPI = base_.mint(
                    agent.contract.address, int(50_000 * 1e18), sender=experiment_config.scratch["deployer_account"]
                )
            else:
                assert faucet is not None, "Faucet must be provided to mint base on testnet."
                txn_receipt: ReceiptAPI = faucet.mint(base_.address, agent.wallet.address, int(50_000 * 1e18))
            txn_receipt.await_confirmations()
    log_and_show(
        f" agent_{agent.contract.address[:8]} is a {bot.name} with budget={fmt(params['budget'])}"
        f" Eth={fmt(agent.contract.balance/1e18)} Base={fmt(base_.balanceOf(agent.contract.address)/1e18)}"
    )
    agent.wallet = ape_utils.get_wallet_from_onchain_trade_info(
        address_=agent.contract.address,
        index=bot.index,
        info=on_chain_trade_info,
        hyperdrive_contract=hyperdrive_contract,
        base_contract=base_,
    )
    return agent


def set_up_agents(experiment_config: simulators.Config):
    """Set up python agents & corresponding on-chain accounts.

    Parameters
    ----------
    experiment_config : simulators.Config
        The experiment config.
    """
    dev_accounts: list[KeyfileAccount] = get_accounts(experiment_config)
    faucet = None
    if not experiment_config.scratch["devnet"]:
        faucet = ape_utils.get_instance(
            experiment_config.scratch["faucet_address"], provider=experiment_config.scratch["provider"]
        )
    bot_num = 0
    for bot_name in experiment_config.scratch["bot_names"]:
        _policy = experiment_config.scratch[bot_name].policy
        log_and_show(
            f"{bot_name:6s}: n={experiment_config.scratch[f'num_{bot_name}']}  "
            f"policy={_policy.__name__ if _policy.__module__ == '__main__' else _policy.__module__:20s}"
        )
        bot_num += experiment_config.scratch[f"num_{bot_name}"]
    _sim_agents = {}
    start_time_ = now()
    on_chain_trade_info: ape_utils.OnChainTradeInfo = ape_utils.get_on_chain_trade_info(
        hyperdrive_contract=experiment_config.scratch["hyperdrive_instance"]
    )
    log_and_show(f"Getting on-chain trade info took {fmt(now() - start_time_)} seconds")
    for bot_name in [
        name for name in experiment_config.scratch["bot_names"] if experiment_config.scratch[f"num_{name}"] > 0
    ]:
        bot_info = experiment_config.scratch[bot_name]
        bot_info.name = bot_name
        for _ in range(experiment_config.scratch[f"num_{bot_name}"]):  # loop across number of bots of this type
            bot_info.index = len(_sim_agents)
            logging.debug("Creating %s agent %s/%s: %s", bot_name, bot_info.index + 1, bot_num, bot_info)
            agent = create_agent(
                bot=bot_info,
                dev_accounts=dev_accounts,
                faucet=faucet,
                base_=experiment_config.scratch["base_instance"],
                on_chain_trade_info=on_chain_trade_info,
                hyperdrive_contract=experiment_config.scratch["hyperdrive_instance"],
                experiment_config=experiment_config,
            )
            _sim_agents[f"agent_{agent.wallet.address}"] = agent
    experiment_config.scratch["sim_agents"] = _sim_agents


def do_trade(market_trade: types.Trade, experiment_config):
    """Execute agent trades on hyperdrive solidity contract."""
    # TODO: add market-state-dependent trading for smart bots
    # market_state = get_simulation_market_state_from_contract(
    #     hyperdrive_contract=hyperdrive_contract, agent_address=contract
    # )
    # market_type = trade_obj.market
    trade = market_trade.trade
    agent_contract = experiment_config.scratch["sim_agents"][f"agent_{trade.wallet.address}"].contract
    amount = trade.trade_amount.int_value
    # If agent does not have enough base approved for this trade, then approve another 50k
    # allowance(address owner, address spender) → uint256
    if (
        experiment_config.scratch["base_instance"].allowance(
            agent_contract.address, experiment_config.scratch["hyperdrive_instance"].address
        )
        < amount
    ):
        txn_args = (
            experiment_config.scratch["hyperdrive_instance"].address,
            FixedPoint("50_000.0", decimal_places=18).scaled_value,
        )
        ape_utils.attempt_txn(agent_contract, experiment_config.scratch["base_instance"].approve, *txn_args)
        logging.info("Trade had insufficient allowance, approving an additional 50k base.")
    params = {
        "trade_type": trade.action_type.name,
        "hyperdrive_contract": experiment_config.scratch["hyperdrive_instance"],
        "agent": agent_contract,
        "amount": amount,
    }
    if trade.action_type.name in ["CLOSE_LONG", "CLOSE_SHORT"]:
        params["maturity_time"] = int(trade.mint_time + elfpy.SECONDS_IN_YEAR)
    _, _ = ape_utils.ape_trade(**params)


def set_days_without_crashing(experiment_config: simulators.Config, reset: bool = False):
    """Calculate the number of days without crashing."""
    streak = 0 if reset is True else experiment_config.scratch["no_crash_streak"] + 1
    with open(experiment_config.scratch["crash_file"], "w", encoding="utf-8") as file:
        file.write(f"{streak}")
    experiment_config.scratch["no_crash_streak"] = streak


def log_and_show_block_info(experiment_config):
    """Get and show the latest block number and gas fees."""
    block = ape.chain.get_block(experiment_config.scratch["block_number"])
    if not hasattr(block, "base_fee"):
        raise ValueError("latest block does not have base_fee")
    base_fee = getattr(block, "base_fee") / 1e9
    log_and_show(
        "Block number: %s, Block time: %s, Trades without crashing: %s, base_fee: %s",
        fmt(getattr(block, "block_number")),
        datetime.fromtimestamp(experiment_config.scratch["block_timestamp"]),
        experiment_config.scratch["no_crash_streak"],
        base_fee,
    )


def get_simulator(experiment_config: simulators.Config) -> simulators.Simulator:
    """Instantiate and return an initialized elfpy Simulator object."""
    market, _, _ = sim_utils.get_initialized_hyperdrive_market(
        pricing_model=experiment_config.scratch["pricing_model"], block_time=time.BlockTime(), config=experiment_config
    )
    return simulators.Simulator(experiment_config, market, time.BlockTime())


def deploy_hyperdrive(experiment_config: simulators.Config) -> ContractInstance:
    """Deploy Hyperdrive when operating on a fresh fork."""
    initial_supply = FixedPoint(experiment_config.target_liquidity, decimal_places=18)
    initial_apr = FixedPoint(experiment_config.target_fixed_apr, decimal_places=18)
    simulator = get_simulator(experiment_config)  # Instantiate the sim market
    experiment_config.scratch["base_instance"].mint(
        initial_supply.scaled_value,
        sender=experiment_config.scratch["deployer_account"],  # minted amount goes to sender
    )
    hyperdrive: ContractInstance = experiment_config.scratch["deployer_account"].deploy(
        experiment_config.scratch["project"].get_contract("MockHyperdriveTestnet"),
        experiment_config.scratch["base_instance"],
        initial_apr.scaled_value,
        experiment_config.init_share_price * 1e18,
        365,  # checkpoints per term
        86400,  # checkpoint duration in seconds (1 day)
        (1 / simulator.market.time_stretch_constant) * 1e18,  # time stretch in solidity format (inverted)
        (
            experiment_config.curve_fee_multiple * 1e18,
            experiment_config.flat_fee_multiple * 1e18,
            experiment_config.gov_fee * 1e18,
        ),
        experiment_config.scratch["deployer_account"],
    )
    with ape.accounts.use_sender(experiment_config.scratch["deployer_account"]):
        experiment_config.scratch["base_instance"].approve(hyperdrive, initial_supply.scaled_value)
        hyperdrive.initialize(
            initial_supply.scaled_value,
            initial_apr.scaled_value,
            experiment_config.scratch["deployer_account"],
            True,
        )
    return hyperdrive


def set_up_ape(experiment_config) -> simulators.Config:
    r"""Set up ape.

    Parameters
    ----------
    experiment_config : simulators.Config
        The experiment configuration, which stores default elfpy simulator variables as well as custom variables.

    Returns
    -------
    simulators.Config
        The experiment configuration, augmented with: `base_instance`, `hyperdrive_instance`, `hyperdrive_config`,
        and `provider`.
    """
    # sourcery skip: inline-variable, move-assign
    experiment_config.scratch["deployer_account"] = None
    experiment_config.scratch["provider"]: ProviderAPI = ape.networks.parse_network_choice(
        network_choice=experiment_config.scratch["network_choice"],
        provider_settings=experiment_config.scratch["provider_settings"],
    ).push_provider()
    log_and_show(
        "connected to %s, latest block %s",
        "devnet" if experiment_config.scratch["devnet"] else experiment_config.scratch["network_choice"],
        experiment_config.scratch["provider"].get_block("latest").number,
    )
    project = ape_utils.HyperdriveProject(Path.cwd())

    if experiment_config.scratch["devnet"]:  # if devnet setting is enabled
        experiment_config.scratch["deployer_account"] = ape.accounts.test_accounts[0]
        experiment_config.scratch["deployer_account"].balance += int(1e18)  # eth, for spending on gas, not erc20
        if experiment_config.scratch["base_address"]:  # use existing base token deployment
            experiment_config.scratch["base_instance"] = ape_utils.get_instance(
                address=experiment_config.scratch["base_address"],
                contract_type=project.get_contract("ERC20Mintable").contract_type,
                provider=experiment_config.scratch["provider"],
            )
        else:  # deploy a new base token
            experiment_config.scratch["base_instance"]: ContractInstance = experiment_config.scratch[
                "deployer_account"
            ].deploy(project.get_contract("ERC20Mintable"))
        if experiment_config.scratch["hyperdrive_address"]:  # use existing hyperdrive deployment
            experiment_config.scratch["hyperdrive_instance"]: ContractInstance = ape_utils.get_instance(
                address=experiment_config.scratch["hyperdrive_address"],
                contract_type=project.get_contract("MockHyperdriveTestnet").contract_type,
                provider=experiment_config.scratch["provider"],
            )
        else:  # deploy a new hyperdrive
            experiment_config.scratch["hyperdrive_instance"]: ContractInstance = deploy_hyperdrive(experiment_config)
    else:  # not on devnet, means we're on goerli, so we use known goerli addresses
        experiment_config.scratch["base_instance"]: ContractInstance = ape_utils.get_instance(
            experiment_config.scratch["0x11fe4b6ae13d2a6055c8d9cf65c55bac32b5d844"],
            provider=experiment_config.scratch["provider"],
        )
        experiment_config.scratch["hyperdrive_instance"]: ContractInstance = project.get_hyperdrive_contract()

    # read the hyperdrive config from the contract, and log (and print) it
    experiment_config.scratch["hyperdrive_config"]: dict = (
        experiment_config.scratch["hyperdrive_instance"].getPoolConfig().__dict__
    )
    experiment_config.scratch["hyperdrive_config"]["timeStretch"] = 1 / (
        experiment_config.scratch["hyperdrive_config"]["timeStretch"] / 1e18
    )
    log_and_show(f"Hyperdrive config deployed at {experiment_config.scratch['hyperdrive_instance'].address}:")
    for key, value in experiment_config.scratch["hyperdrive_config"].items():
        divisor = 1 if key in ["positionDuration", "checkpointDuration", "timeStretch"] else 1e18
        log_and_show(f" {key}: {fmt(value/divisor)}")
    experiment_config.scratch["hyperdrive_config"]["term_length"] = 365  # days
    return experiment_config


def do_policy(policy, elfpy_market, experiment_config):
    """Execute an agent's policy."""
    trades: list[types.Trade] = policy.get_trades(market=elfpy_market)
    for trade_object in trades:
        try:
            logging.debug(trade_object)
            do_trade(trade_object, experiment_config)
            set_days_without_crashing(experiment_config)  # set and save to file
        except Exception as exc:  # we want to catch all exceptions (pylint: disable=broad-exception-caught)
            log_and_show("Crashed unexpectedly: %s", exc)
            set_days_without_crashing(experiment_config, 0)  # set and save to file


def create_elfpy_market(experiment_config):
    """Create an elfpy market."""
    return hyperdrive_market.Market(
        pricing_model=experiment_config.scratch["pricing_model"],
        market_state=ape_utils.get_market_state_from_contract(
            hyperdrive_contract=experiment_config.scratch["hyperdrive_instance"]
        ),
        position_duration=time.StretchedTime(
            days=FixedPoint(experiment_config.scratch["hyperdrive_config"]["term_length"]),
            time_stretch=FixedPoint(experiment_config.scratch["hyperdrive_config"]["timeStretch"]),
            normalizing_constant=FixedPoint(experiment_config.scratch["hyperdrive_config"]["term_length"]),
        ),
        block_time=time.BlockTime(
            _time=FixedPoint(
                (experiment_config.scratch["start_timestamp"] - experiment_config.scratch["start_timestamp"]) / 365
            ),
            _block_number=FixedPoint(experiment_config.scratch["block_number"]),
            _step_size=FixedPoint("1.0") / FixedPoint("365.0"),
        ),
    )


def main():
    """Run the simulation."""
    experiment_config = get_config()
    output_utils.setup_logging(log_filename=experiment_config.log_filename, log_level=experiment_config.log_level)
    experiment_config = set_up_ape(experiment_config=experiment_config)
    set_up_agents(experiment_config=experiment_config)

    experiment_config.scratch["start_timestamp"] = ape.chain.blocks[-1].timestamp
    while True:  # hyper drive forever into the sunset
        experiment_config.scratch["block_number"] = ape.chain.blocks[-1].number
        experiment_config.scratch["block_timestamp"] = ape.chain.blocks[-1].timestamp
        if experiment_config.scratch["block_number"] > experiment_config.scratch["last_executed_block"]:
            log_and_show_block_info(experiment_config)
            elfpy_market = create_elfpy_market(experiment_config)
            for policy in experiment_config.scratch["sim_agents"].values():
                do_policy(policy, elfpy_market, experiment_config)
            experiment_config.scratch["last_executed_block"] = experiment_config.scratch["block_number"]
        sleep(1)


if __name__ == "__main__":
    main()

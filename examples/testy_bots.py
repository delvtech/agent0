"""A demo for executing an arbitrary number of trades bots on testnet."""

from __future__ import annotations  # types will be strings by default in 3.11

# stdlib
import argparse
import json
import logging
import os
from pathlib import Path
from time import sleep
from typing import cast, Optional, Type
from collections import namedtuple
from dataclasses import dataclass

# external lib
import ape
import numpy as np
from ape import Contract, accounts
from ape.api import ProviderAPI, ReceiptAPI
from ape.contracts import ContractInstance
from ape.utils import generate_dev_accounts
from ape_accounts.accounts import KeyfileAccount
from dotenv import load_dotenv
from eth_account import Account as EthAccount
from numpy.random._generator import Generator as NumpyGenerator

# elfpy core repo
import elfpy
import elfpy.agents.agent as agentlib
import elfpy.pricing_models.hyperdrive as hyperdrive_pm
import elfpy.utils.apeworx_integrations as ape_utils
import elfpy.utils.outputs as output_utils
from elfpy.utils.apeworx_integrations import to_fixed_point
from elfpy.utils.outputs import number_to_string as fmt
from elfpy.utils.outputs import log_and_show
from elfpy import simulators, time, types
from elfpy.agents.policies import random_agent
from elfpy.markets.hyperdrive import hyperdrive_actions, hyperdrive_market

load_dotenv(dotenv_path=f"{Path.cwd() if Path.cwd().name != 'examples' else Path.cwd().parent}/.env")

NO_CRASH = 0
USE_ALCHEMY = False

DEVNET = True
CRASH_FILE = f"no_crash{'_devnet' if DEVNET else ''}.txt"

examples_dir = Path.cwd() if Path.cwd().name == "examples" else Path.cwd() / "examples"

if USE_ALCHEMY:
    from dotenv import load_dotenv

    # load env from up one level
    load_dotenv(dotenv_path=examples_dir.parent / ".env")


class FixedFrida(agentlib.Agent):
    """Agent that paints & opens fixed rate borrow positions."""

    def __init__(  # pylint: disable=too-many-arguments # noqa: PLR0913
        self, rng: NumpyGenerator, trade_chance: float, risk_threshold: float, wallet_address: int, budget: int = 10_000
    ) -> None:
        """Add custom stuff then call basic policy init."""
        self.trade_chance = trade_chance
        self.risk_threshold = risk_threshold
        self.rng = rng
        super().__init__(wallet_address, budget)

    def action(self, _market: hyperdrive_market.Market) -> list[types.Trade]:
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
        _market : Market
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
            trade_amount = self.get_max_short(
                market
            )  # maximum amount the agent can short given the market and the agent's wallet
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


class LongLouie(agentlib.Agent):
    """Long-nosed agent that opens longs."""

    def __init__(  # pylint: disable=too-many-arguments # noqa: PLR0913
        self, rng: NumpyGenerator, trade_chance: float, risk_threshold: float, wallet_address: int, budget: int = 10_000
    ) -> None:
        """Add custom stuff then call basic policy init."""
        self.trade_chance = trade_chance
        self.risk_threshold = risk_threshold
        self.rng = rng
        super().__init__(wallet_address, budget)

    def action(self, _market: hyperdrive_market.Market) -> list[types.Trade]:
        """Implement a Long Louie user strategy.

        I'm not willing to open a long if it will cause the fixed-rate apr to go below the variable rate
            I simulate the outcome of my trade, and only execute on this condition
        I only close if the position has matured
        I have total budget of 2k -> 250k (gauss mean=75k; std=50k, i.e. 68% values are within 75k +/- 50k)
        I only open one long at a time

        Parameters
        ----------
        _market : Market
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
            adjusted_bonds = new_bonds_to_match_variable_apr / 2
            # get the maximum amount the agent can long given the market and the agent's wallet
            max_trade_amount = self.get_max_long(market)
            trade_amount = np.minimum(
                max_trade_amount, adjusted_bonds
            )  # don't want to trade more than the agent has or more than the market can handle
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
    return parser


@dataclass
class BotInfo:
    """Information about a bot."""

    Budget = namedtuple("Budget", ["mean", "std", "min", "max"])
    Risk = namedtuple("Risk", ["mean", "std", "min", "max"])

    policy: Type[agentlib.Agent]
    trade_chance: float = 0.1
    risk_threshold: Optional[float] = None
    budget: Budget = Budget(mean=5_000, std=2_000, min=1_000, max=10_000)
    risk: Risk = Risk(mean=0.02, std=0.01, min=0.0, max=0.06)


def get_config() -> simulators.Config:
    """Set _config values for the experiment."""
    args = get_argparser().parse_args()
    _config = simulators.Config()
    _config.log_level = output_utils.text_to_log_level(args.log_level)
    _config.log_filename = "testnet_bots"
    if os.path.exists("random_seed.txt"):
        with open("random_seed.txt", "r", encoding="utf-8") as file:
            _config.random_seed = int(file.read()) + 1
    logging.info("Random seed=%s", _config.random_seed)
    with open("random_seed.txt", "w", encoding="utf-8") as file:
        file.write(str(_config.random_seed))
    _config.title = "testnet bots"
    for key, value in args.__dict__.items():
        if hasattr(_config, key):
            _config[key] = value
        else:
            _config.scratch[key] = value
    trade_chance = _config.scratch["trade_chance"]
    _config.scratch["louie"] = BotInfo(risk_threshold=0.0, policy=LongLouie, trade_chance=trade_chance)
    _config.scratch["frida"] = BotInfo(policy=FixedFrida, trade_chance=trade_chance)
    _config.scratch["random"] = BotInfo(policy=random_agent.Policy, trade_chance=trade_chance)
    _config.scratch["bot_names"] = {"louie", "frida", "random"}
    _config.scratch["pricing_model"] = hyperdrive_pm.HyperdrivePricingModel()
    _config.freeze()
    return _config


def get_accounts() -> list[KeyfileAccount]:
    """Generate dev accounts and turn on auto-sign."""
    num = sum(config.scratch[f"num_{bot}"] for bot in config.scratch["bot_names"])
    assert (mnemonic := os.environ["MNEMONIC"]), "You must provide a mnemonic in .env to run this script."
    keys = generate_dev_accounts(mnemonic=mnemonic, number_of_accounts=num)
    for num, key in enumerate(keys):
        path = accounts.containers["accounts"].data_folder.joinpath(f"agent_{num}.json")
        path.write_text(json.dumps(EthAccount.encrypt(private_key=key.private_key, password="based")))  # overwrites
    _dev_accounts: list[KeyfileAccount] = [
        cast(KeyfileAccount, accounts.load(alias=f"agent_{num}")) for num in range(len(keys))
    ]
    logging.disable(logging.WARNING)  # disable logging warnings to do dangerous things below
    for account in _dev_accounts:
        account.set_autosign(enabled=True, passphrase="based")
    logging.disable(logging.NOTSET)  # re-enable logging warnings
    return _dev_accounts


def create_agent(agent_num, bot_info, bot_name, _dev_accounts, faucet, base, agent_index, on_chain_trade_info):
    """Create an agent as defined in bot_info, assign its address, give it enough base"""
    budget_mean, budget_std, budget_min, budget_max = bot_info.budget
    _policy = bot_info.policy
    params = {
        "trade_chance": config.scratch["trade_chance"],
        "budget": np.clip(config.rng.normal(loc=budget_mean, scale=budget_std), budget_min, budget_max),
    }
    if bot_info.risk_threshold and bot_name != "random":  # random agent doesn't use risk threshold
        params["risk_threshold"] = bot_info.risk_threshold  # if risk threshold is manually set, we use it
    if bot_name != "random":  # if risk threshold isn't manually set, we get a random one
        risk_mean, risk_std, risk_min, risk_max = bot_info.risk
        params["risk_threshold"] = np.clip(config.rng.normal(loc=risk_mean, scale=risk_std), risk_min, risk_max)
    agent = _policy(rng=config.rng, wallet_address=_dev_accounts[agent_num].address, **params)
    agent.contract = _dev_accounts[agent_num]  # assign its onchain address
    if (need_to_mint := params["budget"] - base.balanceOf(agent.contract.address) / 1e18) > 0:
        log_and_show(f" agent_{agent.wallet.address[:8]} needs to mint {fmt(need_to_mint)} Base")
        with ape.accounts.use_sender(agent.contract):
            txn_receipt: ReceiptAPI = faucet.mint(base.address, agent.wallet.address, to_fixed_point(50_000))
            txn_receipt.await_confirmations()
    log_string = f" agent_{agent.wallet.address[:8]} is a {bot_name} with budget={fmt(params['budget'])}"
    log_string += f" Eth={fmt(agent.contract.balance/1e18)}"
    log_string += f" Base={fmt(base.balanceOf(agent.contract.address)/1e18)}"
    log_and_show(log_string)
    agent.wallet = ape_utils.get_wallet_from_onchain_trade_info(
        address_=agent.wallet.address,
        index=agent_index,
        on_chain_trade_info=on_chain_trade_info,
        hyperdrive=hyperdrive,
        base=base,
    )
    return agent


def get_agents():  # sourcery skip: merge-dict-assign, use-fstring-for-concatenation
    """Get python agents & corresponding solidity wallets."""
    _dev_accounts: list[KeyfileAccount] = get_accounts()
    faucet = Contract("0xe2bE5BfdDbA49A86e27f3Dd95710B528D43272C2")

    for bot_name in config.scratch["bot_names"]:
        _policy = config.scratch[bot_name].policy
        log_string = f"{bot_name:6s}: n={config.scratch['num_'+bot_name]}  "
        log_string += f"policy={(_policy.__name__ if _policy.__module__ == '__main__' else _policy.__module__):20s}"
        log_and_show(log_string)
    _sim_agents = {}
    for bot_name in [name for name in config.scratch["bot_names"] if config.scratch[f"num_{name}"] > 0]:
        bot_info = config.scratch[bot_name]
        for agent_index in range(config.scratch[f"num_{bot_name}"]):  # loop across number of bots of this type
            agent = create_agent(
                agent_num=len(_sim_agents),
                bot_info=bot_info,
                bot_name=bot_name,
                _dev_accounts=_dev_accounts,
                faucet=faucet,
                base=dai,
                agent_index=agent_index,
                on_chain_trade_info=ape_utils.get_on_chain_trade_info(hyperdrive),
            )
            _sim_agents[f"agent_{agent.wallet.address}"] = agent
    return _sim_agents, _dev_accounts


def do_trade():
    """Execute agent trades on hyperdrive solidity contract."""
    # TODO: add market-state-dependent trading for smart bots
    # market_state = get_simulation_market_state_from_contract(hyperdrive_contract=hyperdrive, agent_address=contract)
    # market_type = trade_obj.market
    trade = trade_object.trade
    agent = sim_agents[f"agent_{trade.wallet.address}"].contract
    amount = to_fixed_point(trade.trade_amount)
    if dai.allowance(agent.address, hyperdrive.address) < amount:  # allowance(address owner, address spender) → uint256
        args = hyperdrive.address, to_fixed_point(50_000)
        ape_utils.attempt_txn(agent, dai.approve, *args)
    params = {"trade_type": trade.action_type.name, "hyperdrive": hyperdrive, "agent": agent, "amount": amount}
    if trade.action_type.name in ["CLOSE_LONG", "CLOSE_SHORT"]:
        params["maturity_time"] = int(trade.mint_time) + elfpy.SECONDS_IN_YEAR
    _, _ = ape_utils.ape_trade(**params)


def set_days_without_crashing(no_crash: int):
    """Calculate the number of days without crashing."""
    with open(CRASH_FILE, "w", encoding="utf-8") as file:
        file.write(f"{no_crash}")
    return no_crash


def get_and_show_block_and_gas():
    """Get and show the latest block number and gas fees."""
    max_max_fee, avg_max_fee, max_priority_fee, avg_priority_fee = ape_utils.get_gas_fees(latest_block)
    log_string = "Block number: {}, Block time: {}, Trades without crashing: {}"
    log_string += ", max_fee(max={},avg={}) priority_fee(max={},avg={})"
    log_vars = block_number, block_time, NO_CRASH
    log_vars += fmt(max_max_fee), fmt(avg_max_fee), fmt(max_priority_fee), fmt(avg_priority_fee)
    log_and_show(log_string, *log_vars)


if __name__ == "__main__":
    config = get_config()  # Instantiate the config using the command line arguments as overrides.
    output_utils.setup_logging(log_filename=config.log_filename, log_level=config.log_level)

    # Set up ape
    PROVIDER_STRING = "alchemy" if USE_ALCHEMY else "http://localhost:8547"
    provider: ProviderAPI = ape.networks.parse_network_choice(f"ethereum:goerli:{PROVIDER_STRING}").push_provider()
    project = ape_utils.HyperdriveProject(Path.cwd())
    dai: ContractInstance = Contract("0x11fe4b6ae13d2a6055c8d9cf65c55bac32b5d844")  # sDai
    hyperdrive: ContractInstance = project.get_hyperdrive_contract()
    sim_agents, dev_accounts = get_agents()  # Set up agents and their dev accounts

    # read the hyperdrive config from the contract, and log (and print) it
    hyper_config = hyperdrive.getPoolConfig().__dict__
    hyper_config["timeStretch"] = 1 / (hyper_config["timeStretch"] / 1e18)
    log_and_show(f"Hyperdrive config deployed at {hyperdrive.address}:")
    for k, v in hyper_config.items():
        divisor = 1 if k in ["positionDuration", "checkpointDuration", "timeStretch"] else 1e18
        log_and_show(f" {k}: {fmt(v/divisor)}")
    hyper_config["term_length"] = 365  # days

    while True:  # hyper drive forever into the sunset
        latest_block = ape.chain.blocks[-1]
        block_number = latest_block.number or 0
        block_time = latest_block.timestamp
        start_time = locals().get("start_time", block_time)  # get variable if it exists, otherwise set to block_time
        if block_number > locals().get("last_executed_block", 0):  # get variable if it exists, otherwise set to 0
            get_and_show_block_and_gas()
            market_state = ape_utils.get_market_state_from_contract(contract=hyperdrive)
            market: hyperdrive_market.Market = hyperdrive_market.Market(
                pricing_model=config.scratch["pricing_model"],
                market_state=market_state,
                position_duration=time.StretchedTime(
                    days=hyper_config["term_length"],
                    time_stretch=hyper_config["timeStretch"],
                    normalizing_constant=hyper_config["term_length"],
                ),
                block_time=time.BlockTime(block_number=block_number, time=(block_time - start_time) / 365),
            )
            for bot, policy in sim_agents.items():
                trades: list[types.Trade] = policy.get_trades(market=market)
                for trade_object in trades:
                    # try:
                    logging.debug(trade_object)
                    do_trade()
                    NO_CRASH = set_days_without_crashing(NO_CRASH + 1)  # set and save to file
                    # except Exception as exc:  # we want to catch all exceptions (pylint: disable=broad-exception-caught)
                    #     LOG_STRING = "Crashed in Python simulation: {}"
                    #     log_and_show(LOG_STRING, exc)
                    #     NO_CRASH = set_days_without_crashing(0)  # set and save to file
                    #     print("break here")
            last_executed_block = block_number
        sleep(1)

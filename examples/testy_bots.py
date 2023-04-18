"""
This function is a demo for executing an arbitrary number of trades from a pair of
smart bots that track the fixed/variable rates using longs & shorts. It is meant to be
a temporary demonstration, and will be gradually replaced with utilities in elfpy src.
As such, we are relaxing some of the lint rules.
"""
from __future__ import annotations  # types will be strings by default in 3.11

# stdlib
import os
import json
import logging
from logging.handlers import RotatingFileHandler
from eth_account import Account as EthAccount
import argparse
from time import sleep
from pathlib import Path
from collections import defaultdict

# external lib
import ape
from ape import accounts, Contract
from ape.contracts import ContractInstance
from ape.utils import generate_dev_accounts
from ape.api import ProviderAPI, ReceiptAPI
import numpy as np
from numpy.random._generator import Generator as NumpyGenerator
from dotenv import load_dotenv

# elfpy core repo
import elfpy
import elfpy.time as time
import elfpy.types as types
import elfpy.simulators as simulators
import elfpy.agents.agent as agentlib
import elfpy.agents.policies.random_agent as random_agent
import elfpy.pricing_models.hyperdrive as hyperdrive_pm
import elfpy.markets.hyperdrive.hyperdrive_assets as hyperdrive_assets
import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market
import elfpy.markets.hyperdrive.hyperdrive_actions as hyperdrive_actions
import elfpy.utils.apeworx_integrations as ape_utils
import elfpy.utils.outputs as output_utils
from elfpy.utils.fmt import fmt

# Apeworx does not get along well with pyright
# Also ignoring a handful of pylint errors
# pylint: disable=too-many-arguments,redefined-outer-name,invalid-name,unnecessary-dunder-call

load_dotenv()


class FixedFrida(agentlib.Agent):
    """Agent that paints & opens fixed rate borrow positions"""

    def __init__(
        self, rng: NumpyGenerator, trade_chance: float, risk_threshold: float, wallet_address: int, budget: int = 10_000
    ) -> None:
        """Add custom stuff then call basic policy init"""
        self.trade_chance = trade_chance
        self.risk_threshold = risk_threshold
        self.rng = rng
        super().__init__(wallet_address, budget)

    def action(self, market: hyperdrive_market.Market) -> list[types.Trade]:
        """Implement a Fixed Frida user strategy

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
    """Long-nosed agent that opens longs"""

    def __init__(
        self, rng: NumpyGenerator, trade_chance: float, risk_threshold: float, wallet_address: int, budget: int = 10_000
    ) -> None:
        """Add custom stuff then call basic policy init"""
        self.trade_chance = trade_chance
        self.risk_threshold = risk_threshold
        self.rng = rng
        super().__init__(wallet_address, budget)

    def action(self, market: hyperdrive_market.Market) -> list[types.Trade]:
        """Implement a Long Louie user strategy

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
    """Define & parse arguments from stdin"""
    parser = argparse.ArgumentParser(
        prog="TestnetBots",
        description="Execute bots on testnet",
        epilog="See the README on https://github.com/element-fi/elf-simulations/ for more implementation details",
    )
    parser.add_argument("--log_filename", help="Optional output filename for logging", default="testnet_bots", type=str)
    parser.add_argument(
        "--max_bytes",
        help=f"Maximum log file output size, in bytes. Default is {elfpy.DEFAULT_LOG_MAXBYTES} bytes."
        "More than 100 files will cause overwrites.",
        default=elfpy.DEFAULT_LOG_MAXBYTES,
        type=int,
    )
    parser.add_argument(
        "--log_level",
        help='Logging level, should be in ["DEBUG", "INFO", "WARNING"]. Default uses the config.',
        default="INFO",
        type=str,
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


def get_config() -> simulators.Config:
    """Set config values for the experiment"""
    args = get_argparser().parse_args()
    config = simulators.Config()
    config.log_level = output_utils.text_to_log_level(args.log_level)
    config.log_filename = "testnet_bots"
    if os.path.exists("random_seed.txt"):
        with open("random_seed.txt", "r") as f:  # read random seed from file
            config.random_seed = int(f.read()) + 1
    logging.info("Random seed=%s", config.random_seed)
    with open("random_seed.txt", "w") as f:  # write new random seed to file
        f.write(str(config.random_seed))
    config.title = "testnet bots"
    for key, value in args.__dict__.items():
        if hasattr(config, key):
            config[key] = value
        else:
            config.scratch[key] = value
    config.scratch["louie_risk_threshold"] = 0.0
    config.scratch["louie_budget_mean"] = 5_000
    config.scratch["louie_budget_std"] = 2_000
    config.scratch["louie_budget_max"] = 10_000
    config.scratch["louie_budget_min"] = 1_000
    config.scratch["frida_budget_mean"] = 5_000
    config.scratch["frida_budget_std"] = 2_000
    config.scratch["frida_budget_max"] = 10_000
    config.scratch["frida_budget_min"] = 1_000
    config.scratch["frida_risk_min"] = 0.0
    config.scratch["frida_risk_max"] = 0.06
    config.scratch["frida_risk_mean"] = 0.02
    config.scratch["frida_risk_std"] = 0.01
    config.scratch["random_budget_mean"] = 5_000
    config.scratch["random_budget_std"] = 2_000
    config.scratch["random_budget_max"] = 10_000
    config.scratch["random_budget_min"] = 1_000
    config.scratch["bot_types"] = {"louie": LongLouie, "frida": FixedFrida, "random": random_agent.Policy}
    config.scratch["pricing_model"] = hyperdrive_pm.HyperdrivePricingModel()
    config.freeze()  # type: ignore
    return config


def get_accounts(config, bot_types):
    """Generate dev accounts and turn on auto-sign"""
    num = sum(config.scratch[f"num_{bot}"] for bot in bot_types)
    assert (mnemonic := os.environ["MNEMONIC"]), "You must provide a mnemonic in .env to run this script."
    keys = generate_dev_accounts(mnemonic=mnemonic, number_of_accounts=num)
    for num, key in enumerate(keys):
        path = accounts.containers["accounts"].data_folder.joinpath(f"agent_{num}.json")
        path.write_text(json.dumps(EthAccount.encrypt(private_key=key.private_key, password="based")))  # overwrites
    dev_accounts = [accounts.load(alias=f"agent_{num}") for num in range(len(keys))]
    logging.disable(logging.WARNING)  # disable logging warnings to do dangerous things below
    for account in dev_accounts:
        account.set_autosign(enabled=True, passphrase="based")  # type: ignore
    logging.disable(logging.NOTSET)  # re-enable logging warnings
    return dev_accounts


def get_agents(config, Dai: ContractInstance):  # sourcery skip: merge-dict-assign, use-fstring-for-concatenation
    """Get python agents & corresponding solidity wallets"""
    bot_types = config.scratch["bot_types"]
    for bot, policy in bot_types.items():
        print(f"{bot:6s}: n={config.scratch['num_'+bot]}", end="  ")
        print(f"policy={(policy.__name__ if policy.__module__ == '__main__' else policy.__module__):20s}")
    dev_accounts = get_accounts(config, bot_types)
    faucet = Contract("0xe2bE5BfdDbA49A86e27f3Dd95710B528D43272C2")

    sim_agents = {}
    for bot, policy in [item for item in bot_types.items() if config.scratch[f"num_{item[0]}"] > 0]:
        for _ in range(config.scratch[f"num_{bot}"]):
            params = {}
            agent_num = len(sim_agents)
            params["trade_chance"] = config.scratch["trade_chance"]
            params["wallet_address"] = dev_accounts[agent_num].address
            params["budget"] = np.clip(
                config.rng.normal(loc=config.scratch[f"{bot}_budget_mean"], scale=config.scratch[f"{bot}_budget_std"]),
                config.scratch[f"{bot}_budget_min"],
                config.scratch[f"{bot}_budget_max"],
            )
            if hasattr(config, f"{bot}_risk_min"):
                params["risk_threshold"] = np.clip(
                    config.rng.normal(loc=config.scratch[f"{bot}_risk_mean"], scale=config.scratch[f"{bot}_risk_std"]),
                    config.scratch[f"{bot}_risk_min"],
                    config.scratch[f"{bot}_risk_max"],
                )
            elif hasattr(config, f"{bot}_risk_threshold"):
                params["risk_threshold"] = config.scratch[f"{bot}_risk_threshold"]
            agent = policy(rng=config.rng, **params)  # instantiate the agent
            agent.contract = dev_accounts[agent_num]  # assign its wallet
            if (need_to_mint := params["budget"] - Dai.balanceOf(agent.contract.address) / 1e18) > 0:
                print(f" agent_{agent.wallet.address[:7]} needs to mint {fmt(need_to_mint)} DAI")
                with ape.accounts.use_sender(agent.contract):
                    txn_receipt: ReceiptAPI = faucet.mint(Dai.address, agent.wallet.address, to_fixed_point(50_000))
                    txn_receipt.await_confirmations()
            print(f" agent_{agent.wallet.address[:7]} is a {bot} with budget={fmt(params['budget'])}", end=" ")
            print(f"Eth={fmt(agent.contract.balance/1e18)}", end=" ")
            print(f"Dai={fmt(Dai.balanceOf(agent.contract.address)/1e18)}")
            sim_agents[f"agent_{agent.wallet.address}"] = agent
    return sim_agents, dev_accounts


def to_fixed_point(float_var, decimal_places=18):
    """Convert floating point argument to fixed point with specified number of decimals"""
    return int(float_var * 10**decimal_places)


def to_floating_point(float_var, decimal_places=18):
    """Convert fixed point argument to floating point with specified number of decimals"""
    return float(float_var / 10**decimal_places)


def get_market_state_from_contract(contract: ContractInstance):
    """
    contract: ape.contracts.base.ContractInstance
        Ape project `ContractInstance
        <https://docs.apeworx.io/ape/stable/methoddocs/contracts.html#ape.contracts.base.ContractInstance>`_
        wrapped around the initialized MockHyperdriveTestnet smart contract.
    """
    pool_state = contract.getPoolInfo().__dict__
    asset_id = hyperdrive_assets.encode_asset_id(
        hyperdrive_assets.AssetIdPrefix.WITHDRAWAL_SHARE, hyper_config["positionDuration"]
    )
    total_supply_withdraw_shares = hyperdrive.balanceOf(asset_id, dev_accounts[0].address)

    return hyperdrive_market.MarketState(
        lp_total_supply=to_floating_point(pool_state["lpTotalSupply"]),
        share_reserves=to_floating_point(pool_state["shareReserves"]),
        bond_reserves=to_floating_point(pool_state["bondReserves"]),
        base_buffer=to_floating_point(pool_state["longsOutstanding"]),  # so do we not need any buffers now?
        # TODO: bond_buffer=0,
        variable_apr=0.01,  # TODO: insert real value
        share_price=to_floating_point(pool_state["sharePrice"]),
        init_share_price=to_floating_point(hyper_config["initialSharePrice"]),
        curve_fee_multiple=to_floating_point(hyper_config["curveFee"]),
        flat_fee_multiple=to_floating_point(hyper_config["flatFee"]),
        governance_fee_multiple=to_floating_point(hyper_config["governanceFee"]),
        longs_outstanding=to_floating_point(pool_state["longsOutstanding"]),
        shorts_outstanding=to_floating_point(pool_state["shortsOutstanding"]),
        long_average_maturity_time=to_floating_point(pool_state["longAverageMaturityTime"]),
        short_average_maturity_time=to_floating_point(pool_state["shortAverageMaturityTime"]),
        long_base_volume=to_floating_point(pool_state["longBaseVolume"]),
        short_base_volume=to_floating_point(pool_state["shortBaseVolume"]),
        # TODO: checkpoints=defaultdict
        checkpoint_duration=hyper_config["checkpointDuration"],
        total_supply_longs=defaultdict(float, {0: to_floating_point(pool_state["longsOutstanding"])}),
        total_supply_shorts=defaultdict(float, {0: to_floating_point(pool_state["shortsOutstanding"])}),
        total_supply_withdraw_shares=to_floating_point(total_supply_withdraw_shares),
        withdraw_shares_ready_to_withdraw=to_floating_point(pool_state["withdrawalSharesReadyToWithdraw"]),
        withdraw_capital=to_floating_point(pool_state["capital"]),
        withdraw_interest=to_floating_point(pool_state["interest"]),
    )


def do_trade(trade_obj: types.Trade, Dai: ContractInstance, hyperdrive: ContractInstance, sim_agents: dict):
    """Execute agent trades on hyperdrive solidity contract"""
    # TODO: add market-state-dependent trading
    # market_state = get_simulation_market_state_from_contract(hyperdrive_contract=hyperdrive, agent_address=contract)
    # market_type = trade_obj.market  # constant denoting market type (placeholder)
    trade: hyperdrive_actions.MarketAction = trade_obj.trade
    agent = sim_agents[f"agent_{trade.wallet.address}"].contract
    amount = to_fixed_point(trade.trade_amount)

    if Dai.allowance(agent.address, hyperdrive.address) < amount:  # allowance(address owner, address spender) → uint256
        args = hyperdrive.address, to_fixed_point(50_000)
        ape_utils.attempt_txn(agent, Dai.approve, *args)  # type: ignore
    params = {"trade_type": trade.action_type.name, "hyperdrive": hyperdrive, "agent": agent, "amount": amount}
    if trade.action_type.name in ["CLOSE_LONG", "CLOSE_SHORT"]:
        params["maturity_time"] = int(sim_to_block_time[trade.mint_time])
    new_state, _ = ape_utils.ape_trade(**params)
    if trade.action_type.name in ["OPEN_LONG", "OPEN_SHORT"] and new_state is not None:
        sim_to_block_time[trade.mint_time] = new_state["maturity_timestamp_"]


def log_and_print(string: str, *args, end="\n") -> None:
    """log to both the generic logger and to stdout"""
    if args:
        string = string.format(*args)
    logging.info(string + end)
    print(string, end=end)


if __name__ == "__main__":
    config = get_config()  # Instantiate the config using the command line arguments as overrides.
    output_utils.setup_logging(log_filename=config.log_filename, log_level=config.log_level)
    f = logging.getLogger().handlers[0].baseFilename.replace("testnet_bots", "testnet_bots_failblog")  # type: ignore
    logging.getLogger("failblog").handlers = [RotatingFileHandler(f, mode="w", maxBytes=elfpy.DEFAULT_LOG_MAXBYTES)]
    logging.getLogger("failblog").formatter = logging.getLogger().handlers[0].formatter  # type: ignore

    # Set up ape
    provider: ProviderAPI = ape.networks.parse_network_choice("ethereum:goerli:alchemy").__enter__()
    provider.network.config.goerli.required_confirmations = 1
    project_root = Path.cwd()
    project = ape.Project(path=project_root)

    Dai: ContractInstance = Contract("0x11fe4b6ae13d2a6055c8d9cf65c55bac32b5d844")  # sDai
    sim_agents, dev_accounts = get_agents(config=config, Dai=Dai)  # Set up agents and their dev accounts
    hyperdrive: ContractInstance = project.Hyperdrive.at("0xB311B825171AF5A60d69aAD590B857B1E5ed23a2")  # type: ignore
    hyper_config = hyperdrive.getPoolConfig().__dict__
    hyper_config["timeStretch"] = 1 / (hyper_config["timeStretch"] / 1e18)
    print(f"Hyperdrive config deployed at {hyperdrive.address}:")
    for k, v in hyper_config.items():
        divisor = 1e18 if k not in ["positionDuration", "checkpointDuration"] else 1
        print(f" {k}: {fmt(v/divisor)}")
    hyper_config["term_length"] = 365  # days

    sim_to_block_time = {}
    fist_time, last_executed_block, no_crash = 0, 0, 0
    max_max_fee, avg_max_fee, max_priority_fee, avg_priority_fee = None, None, None, None
    while True:
        latest_block = ape.chain.blocks[-1]
        block_number = latest_block.number or 0
        block_time = latest_block.timestamp
        fist_time = block_time if fist_time == 0 else fist_time
        if block_number > last_executed_block:
            if type2 := [txn for txn in latest_block.transactions if txn.type == 2]:
                max_fees, priority_fees = zip(*((txn.max_fee / 1e9, txn.max_priority_fee / 1e9) for txn in type2))  # type: ignore
                max_max_fee, avg_max_fee = max(max_fees), sum(max_fees) / len(max_fees)
                max_priority_fee, avg_priority_fee = max(priority_fees), sum(priority_fees) / len(priority_fees)
            log_string = "Block number: {}, Block time: {}, Trades without crashing: {}, Gas: max={},avg={}, Priority max={},avg={}"
            log_vars = block_number, block_time, no_crash, max_max_fee, avg_max_fee, max_priority_fee, avg_priority_fee
            log_and_print(log_string, *log_vars)
            market_state = get_market_state_from_contract(contract=hyperdrive)
            market: hyperdrive_market.Market = hyperdrive_market.Market(
                pricing_model=config.scratch["pricing_model"],
                market_state=market_state,
                position_duration=time.StretchedTime(
                    days=hyper_config["term_length"],
                    time_stretch=hyper_config["timeStretch"],
                    normalizing_constant=hyper_config["term_length"],
                ),
                block_time=time.BlockTime(block_number=block_number, time=(block_time - fist_time) / 365),
            )
            for bot, policy in sim_agents.items():
                trades: list[types.Trade] = policy.get_trades(market=market)
                for trade in trades:
                    try:
                        print(trade)
                        do_trade(trade_obj=trade, Dai=Dai, hyperdrive=hyperdrive, sim_agents=sim_agents)
                        no_crash += 1
                    except Exception as exc:
                        log_string = "Crashed in Python simulation: {}"
                        log_and_print(log_string, exc)
                        logging.getLogger("failblog").error(log_string, exc)
                        no_crash = 0
            last_executed_block = block_number
        sleep(1)

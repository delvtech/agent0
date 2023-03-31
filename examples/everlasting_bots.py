"""Example main.py file for illustrating a simulator workflow"""
from __future__ import annotations

# stdlib
import argparse
from pathlib import Path
from collections import defaultdict

# external lib
import ape
import numpy as np
from numpy.random._generator import Generator as NumpyGenerator

# elfpy core repo
import elfpy
import elfpy.time as time
import elfpy.types as types
import elfpy.simulators as simulators
import elfpy.agents.agent as agentlib
import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market
import elfpy.markets.hyperdrive.hyperdrive_actions as hyperdrive_actions
import elfpy.utils.apeworx_integrations as ape_utils
import elfpy.utils.sim_utils as sim_utils
import elfpy.utils.outputs as output_utils


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
        for short_time in self.wallet.shorts:  # loop over shorts
            if (market.block_time.time - short_time) >= market.annualized_position_duration:  # if any short is mature
                trade_amount = self.wallet.shorts[short_time].balance  # close the whole thing
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
        has_opened_short = bool(any(short_balance > 0 for short_balance in short_balances))
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
    """
    Long-nosed agent that opens longs
    """

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
        for long_time in self.wallet.longs:  # loop over longs
            if (market.block_time.time - long_time) >= market.annualized_position_duration:  # if any long is mature
                trade_amount = self.wallet.longs[long_time].balance  # close the whole thing
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
        has_opened_long = bool(any(long_balance > 0 for long_balance in long_balances))
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
        prog="ElfMain",
        description="Example execution script for running Elfpy bots on Hyperdrive",
        epilog="See the README on https://github.com/element-fi/elf-simulations/ for more implementation details",
    )
    parser.add_argument(
        "--log_filename", help="Optional output filename for logging", default="everlasting_bots", type=str
    )
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
    parser.add_argument(
        "--num_louies", help="Integer specifying how many Louie agents you want to simulate.", default=1, type=int
    )
    parser.add_argument(
        "--num_fridas", help="Integer specifying how many Frida agents you want to simulate.", default=1, type=int
    )
    parser.add_argument(
        "--vault_apr_type",
        help="Distribution type for the vault apr; must be 'constant'.",
        default="constant",
        type=str,
    )
    parser.add_argument(
        "--target_liquidity",
        help="Initial liquidity for the Hyperdrive market",
        default=50_000_000,
        type=int,
    )
    parser.add_argument(
        "--target_fixed_apr",
        help="Initial fixed APR for the Hyperdrive market",
        default=0.01,
        type=float,
    )
    return parser


def get_config() -> simulators.Config:
    args = get_argparser().parse_args()
    config = simulators.Config()
    config.log_level = output_utils.text_to_log_level(args.log_level)
    config.log_filename = "everlasting_bots"
    config.title = "everlasting bot demo"
    for key, value in args.__dict__.items():
        if hasattr(config, key):
            config[key] = value
        else:
            config.scratch[key] = value
    config.scratch["trade_chance"] = 0.1
    config.scratch["louie_risk_threshold"] = 0.0
    config.scratch["louie_budget_mean"] = 375_000
    config.scratch["louie_budget_std"] = 25_000
    config.scratch["louie_budget_max"] = 1_00_000
    config.scratch["louie_budget_min"] = 1_000
    config.scratch["frida_budget_mean"] = 500_000
    config.scratch["frida_budget_std"] = 10_000
    config.scratch["frida_budget_max"] = 1_000_000
    config.scratch["frida_budget_min"] = 1_000
    config.scratch["frida_risk_min"] = 0.0
    config.scratch["frida_risk_max"] = 0.06
    config.scratch["frida_risk_mean"] = 0.02
    config.scratch["frida_risk_std"] = 0.01
    return config


def get_agents(config):
    # Get agents
    init_agent = sim_utils.get_policy("init_lp")(wallet_address=0, budget=config.target_liquidity)  # type: ignore
    sim_agents = [init_agent]
    for address in range(1, 1 + config.scratch["num_fridas"]):
        risk_threshold = np.maximum(
            config.scratch["frida_risk_min"],
            np.minimum(
                config.scratch["frida_risk_max"],
                config.rng.normal(loc=config.scratch["frida_risk_mean"], scale=config.scratch["frida_risk_std"]),
            ),
        )
        budget = np.maximum(
            config.scratch["frida_budget_min"],
            np.minimum(
                config.scratch["frida_budget_max"],
                config.rng.normal(loc=config.scratch["frida_budget_mean"], scale=config.scratch["frida_budget_std"]),
            ),
        )
        agent = FixedFrida(
            rng=config.rng,
            trade_chance=config.scratch["trade_chance"],
            risk_threshold=risk_threshold,
            wallet_address=address,
            budget=budget,
        )
        sim_agents += [agent]
    for address in range(len(sim_agents), len(sim_agents) + config.scratch["num_louies"]):
        risk_threshold = config.scratch["louie_risk_threshold"]
        budget = np.maximum(
            config.scratch["louie_budget_min"],
            np.minimum(
                config.scratch["louie_budget_max"],
                config.rng.normal(loc=config.scratch["louie_budget_mean"], scale=config.scratch["louie_budget_std"]),
            ),
        )
        agent = LongLouie(
            rng=config.rng,
            trade_chance=config.scratch["trade_chance"],
            risk_threshold=risk_threshold,
            wallet_address=address,
            budget=budget,
        )
        sim_agents += [agent]

    governance = ape.accounts.test_accounts.generate_test_account()
    sol_agents = {"governance": governance}
    for agent_address, sim_agent in enumerate(sim_agents):
        sol_agent = ape.accounts.test_accounts.generate_test_account()  # make a fake agent with its own wallet
        sol_agent.balance = int(sim_agent.budget * 10**18)
        sol_agents[f"agent_{agent_address}"] = sol_agent
    return sol_agents, sim_agents


def get_simulator(config):
    pricing_model = sim_utils.get_pricing_model(config.pricing_model_name)
    block_time = time.BlockTime()
    market, _, _ = sim_utils.get_initialized_hyperdrive_market(pricing_model, block_time, config)
    return simulators.Simulator(config=config, market=market, block_time=block_time)


def to_fixed_point(input, decimal_places=18):
    return int(input * 10**decimal_places)


def to_floating_point(input, decimal_places=18):
    return float(input / 10**decimal_places)


def get_simulation_market_state_from_contract(
    hyperdrive_contract, agent_address, position_duration_seconds, checkpoint_duration, variable_apr, config
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
    pool_state = hyperdrive_contract.getPoolInfo().__dict__
    with ape.accounts.use_sender(agent_address):  # sender for contract calls
        asset_id = hyperdrive_market.encode_asset_id(
            hyperdrive_market.AssetIdPrefix.WITHDRAWAL_SHARE, position_duration_seconds
        )
        total_supply_withdraw_shares = hyperdrive.balanceOf(asset_id, agent_address)  # type: ignore
    return hyperdrive_market.MarketState(
        lp_total_supply=to_floating_point(pool_state["lpTotalSupply"]),
        share_reserves=to_floating_point(pool_state["shareReserves"]),
        bond_reserves=to_floating_point(pool_state["bondReserves"]),
        base_buffer=pool_state["longsOutstanding"],  # so do we not need any buffers now?
        # TODO: bond_buffer=0,
        variable_apr=variable_apr,
        share_price=to_floating_point(pool_state["sharePrice"]),
        init_share_price=config.init_share_price,
        trade_fee_percent=config.trade_fee_percent,
        redemption_fee_percent=config.redemption_fee_percent,
        longs_outstanding=to_floating_point(pool_state["longsOutstanding"]),
        shorts_outstanding=to_floating_point(pool_state["shortsOutstanding"]),
        long_average_maturity_time=to_floating_point(pool_state["longAverageMaturityTime"]),
        short_average_maturity_time=to_floating_point(pool_state["shortAverageMaturityTime"]),
        long_base_volume=to_floating_point(pool_state["longBaseVolume"]),
        short_base_volume=to_floating_point(pool_state["shortBaseVolume"]),
        # TODO: checkpoints=defaultdict
        checkpoint_duration=checkpoint_duration,
        total_supply_longs=defaultdict(float, {0: to_floating_point(pool_state["longsOutstanding"])}),
        total_supply_shorts=defaultdict(float, {0: to_floating_point(pool_state["shortsOutstanding"])}),
        total_supply_withdraw_shares=to_floating_point(total_supply_withdraw_shares),
        withdraw_shares_ready_to_withdraw=to_floating_point(pool_state["withdrawalSharesReadyToWithdraw"]),
        withdraw_capital=to_floating_point(pool_state["capital"]),
        withdraw_interest=to_floating_point(pool_state["interest"]),
    )


if __name__ == "__main__":
    # Instantiate the config using the command line arguments as overrides.
    config = get_config()
    # Set up ape
    provider = ape.networks.parse_network_choice("ethereum:local:foundry").__enter__()
    project_root = Path.cwd()
    project = ape.Project(path=project_root)
    # Set up agents
    sol_agents, sim_agents = get_agents(config)
    # Instantiate the sim market
    simulator = get_simulator(config)
    simulator.add_agents(sim_agents)
    # Use agent 0 to initialize the chain market
    base_address = sol_agents["agent_0"].deploy(project.ERC20Mintable)
    base_ERC20 = project.ERC20Mintable.at(base_address)
    fixed_math_address = sol_agents["agent_0"].deploy(project.MockFixedPointMath)
    fixed_math = project.MockFixedPointMath.at(fixed_math_address)
    base_ERC20.mint(to_fixed_point(config.target_liquidity), sender=sol_agents["agent_0"])
    # Convert sim config to solidity format (fixed-point)
    initial_supply = to_fixed_point(config.target_liquidity)
    initial_apr = to_fixed_point(config.target_fixed_apr)
    initial_share_price = to_fixed_point(config.init_share_price)
    checkpoint_duration = 86400  # seconds = 1 day
    checkpoints_per_term = 365
    position_duration_seconds = checkpoint_duration * checkpoints_per_term
    time_stretch = to_fixed_point(1 / simulator.market.time_stretch_constant)
    curve_fee = to_fixed_point(config.trade_fee_percent)
    flat_fee = to_fixed_point(config.redemption_fee_percent)
    gov_fee = 0
    # Deploy hyperdrive on the chain
    hyperdrive_address = sol_agents["agent_0"].deploy(
        project.MockHyperdriveTestnet,
        base_ERC20,
        initial_apr,
        initial_share_price,
        checkpoints_per_term,
        checkpoint_duration,
        time_stretch,
        (curve_fee, flat_fee, gov_fee),
        sol_agents["governance"],
    )
    hyperdrive = project.MockHyperdriveTestnet.at(hyperdrive_address)
    with ape.accounts.use_sender(sol_agents["agent_0"]):
        base_ERC20.approve(hyperdrive, initial_supply)
        as_underlying = True
        hyperdrive.initialize(initial_supply, initial_apr, sol_agents["agent_0"], as_underlying)
    # Execute trades
    genesis_block_number = ape.chain.blocks[-1].number
    genesis_timestamp = ape.chain.provider.get_block(genesis_block_number).timestamp

    simulator.market.market_state = get_simulation_market_state_from_contract(
        hyperdrive,
        sol_agents["agent_0"],
        position_duration_seconds,
        checkpoint_duration,
        simulator.market.market_state.variable_apr,
        config,
    )
    print(simulator.agents)
    print(list(range(1, len(sim_agents))))

    sim_to_block_time = {}
    for trade_number in range(15):
        print(f"{trade_number=}")
        # convert simulator bot outputs into just the tarde details
        trades = [
            trade[1].trade for trade in simulator.collect_trades(list(range(1, len(sim_agents))), liquidate=False)
        ]
        for trade in trades:
            agent_key = f"agent_{trade.wallet.address}"
            trade_amount = to_fixed_point(trade.trade_amount)
            if trade.action_type.name in ["ADD_LIQUIDITY", "REMOVE_LIQUIDITY"]:
                continue  # todo
            if trade.action_type.name == "OPEN_SHORT":
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

"""Example main.py file for illustrating a simulator workflow"""
# stdlib
import sys
import os
import argparse
import logging
from typing import Any
from logging.handlers import RotatingFileHandler

# external imports
import numpy as np

# elfpy core repo
import elfpy

# elfpy core classes
from elfpy.policies.basic import BasicPolicy  # agents
from elfpy.simulators import Simulator
from elfpy.markets import Market
from elfpy.pricing_models import PricingModel

# elfpy utils
from elfpy.utils import sim_utils  # utilities for setting up a simulation
import elfpy.utils.parse_config as config_utils


class CustomShorter(BasicPolicy):
    """
    Agent that is trying to optimize on a rising vault APR via shorts
    """

    def __init__(self, wallet_address: int, budget: int = 10_000) -> None:
        """call basic policy init then add custom stuff"""
        self.pt_to_short = 1_000
        super().__init__(wallet_address, budget)

    def action(self, market: Market, pricing_model: PricingModel) -> list[Any]:
        """
        implement user strategy
        short if you can, only once
        """
        block_position_list = list(self.wallet.token_in_protocol.values())
        has_opened_short = bool(any((x < -1 for x in block_position_list)))
        can_open_short = self.get_max_pt_short(market, pricing_model) >= self.pt_to_short
        vault_apy = market.share_price * 365 / market.init_share_price
        action_list = []
        if can_open_short:
            if vault_apy > market.get_rate(pricing_model):
                action_list.append(self.create_agent_action(action_type="open_short", trade_amount=self.pt_to_short))
            elif vault_apy < market.get_rate(pricing_model):
                if has_opened_short:
                    action_list.append(
                        self.create_agent_action(action_type="close_short", trade_amount=self.pt_to_short)
                    )
        return action_list


def setup_logging(filename: str, max_bytes: int, log_level: int) -> None:
    """Setup logging"""
    if filename is None:
        handler = logging.StreamHandler(sys.stdout)
    else:
        log_dir = os.path.dirname(filename)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        handler = RotatingFileHandler(filename, mode="w", maxBytes=max_bytes)
    logging.getLogger().setLevel(log_level)  # events of this level and above will be tracked
    handler.setFormatter(logging.Formatter(elfpy.DEFAULT_LOG_FORMATTER, elfpy.DEFAULT_LOG_DATETIME))
    logging.getLogger().handlers = [
        handler,
    ]


def get_example_agents(
    num_additional_agents: int,
    agents: dict[int, BasicPolicy] = None,
) -> dict[int, BasicPolicy]:
    """Instantiate a set of custom agents"""
    if agents is None:
        agents = {}
    for wallet_address in range(
        len(agents), num_additional_agents + len(agents)
    ):  # save wallet_address=0 for init_lp_agent
        agent = CustomShorter(wallet_address)
        agent.log_status_report()
        agents.update({agent.wallet_address: agent})
    return agents


if __name__ == "__main__":
    # define & parse script args
    parser = argparse.ArgumentParser(
        prog="ElfMain",
        description="Example execution script for running simulations using Elfpy",
        epilog="See the README on https://github.com/element-fi/elf-simulations/ for more implementation details",
    )
    parser.add_argument("-o", "--output", help="Optional output filename for logging", default=None)
    parser.add_argument(
        "--max_bytes", help="Maximum log file output size, in bytes. Default is 2e6 bytes (2MB).", default=2e6
    )
    parser.add_argument(
        "-l",
        "--log_level",
        help='Logging level, should be in ["DEBUG", "INFO", "WARNING"]. Default uses the config.',
        default=None,
    )
    parser.add_argument(
        "-c", "--config", help="Config file. Default uses the example config.", default="config/example_config.toml"
    )
    parser.add_argument(
        "-n", "--num_agents", help="Integer specifying how many agents you want to simulate.", default=1
    )
    parser.add_argument(
        "-p", "--pricing_model", help="Pricing model to be used in the simulation", default="Hyperdrive"
    )
    args = parser.parse_args()
    # get config & logging level
    config = config_utils.load_and_parse_config_file(args.config)
    if args.log_level is not None:
        config.simulator.logging_level = config_utils.text_to_logging_level(args.log_level)
    # define root logging parameters
    setup_logging(filename=args.output, max_bytes=args.max_bytes, log_level=config.simulator.logging_level)
    # instantiate random number generator
    rng = np.random.default_rng(config.simulator.random_seed)
    # run random number generators to get random simulation arguments
    random_sim_vars = sim_utils.get_random_variables(config, rng)
    # instantiate the pricing model
    sim_pricing_model = sim_utils.get_pricing_model(model_name=args.pricing_model)
    # instantiate the market
    sim_market = sim_utils.get_market(
        sim_pricing_model,
        random_sim_vars.target_pool_apy,
        random_sim_vars.fee_percent,
        config.simulator.token_duration,
        random_sim_vars.init_share_price,
    )
    # instantiate the init_lp agent
    init_agents = {
        0: sim_utils.get_init_lp_agent(
            config,
            sim_market,
            sim_pricing_model,
            random_sim_vars.target_liquidity,
            random_sim_vars.target_pool_apy,
            random_sim_vars.fee_percent,
        )
    }
    # set up simulator with only the init_lp_agent
    simulator = Simulator(
        config=config,
        pricing_model=sim_pricing_model,
        market=sim_market,
        agents=init_agents,
        rng=rng,
        random_simulation_variables=random_sim_vars,
    )
    # initialize the market using the LP agent
    simulator.collect_and_execute_trades()
    # get trading agent list
    simulator.agents = get_example_agents(num_additional_agents=args.num_agents, agents=init_agents)
    simulator.run_simulation()

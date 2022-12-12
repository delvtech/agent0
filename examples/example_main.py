import sys
import os
import logging
import argparse

import numpy as np

# core repo
import elfpy

# core classes
from elfpy.policies.basic import BasicPolicy  # agents
from elfpy.simulators import Simulator  # simulator
from elfpy.markets import Market  # market

# utils
import elfpy.utils.sim_utils as sim_utils  # utilities for setting up a simulation
from elfpy.utils.parse_config import text_to_logging_level, load_and_parse_config_file


class CustomShorter(BasicPolicy):
    """
    Agent that is trying to optimize on a rising vault APR via shorts
    """

    def __init__(self, market, rng, wallet_address, budget=10_000):
        """call basic policy init then add custom stuff"""
        self.pt_to_short = 1_000
        super().__init__(market, rng, wallet_address, budget)

    def action(self, market, pricing_model):
        """
        implement user strategy
        short if you can, only once
        """
        block_position_list = list(self.wallet.token_in_protocol.values())
        has_opened_short = bool(any((x < -1 for x in block_position_list)))
        can_open_short = self.get_max_pt_short(market, pricing_model) >= self.pt_to_short
        vault_apy = self.market.share_price * 365 / self.market.init_share_price
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


def setup_logging(filename, max_bytes, log_level):
    """Setup logging"""
    if filename is None:
        handler = logging.StreamHandler(sys.stdout)
    else:
        log_dir = os.path.dirname(filename)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        handler = logging.handlers.RotatingFileHandler(filename, mode="w", maxBytes=max_bytes)
    logging.getLogger().setLevel(text_to_logging_level(log_level))  # events of this level and above will be tracked
    handler.setFormatter(logging.Formatter(elfpy.DEFAULT_LOG_FORMATTER, elfpy.DEFAULT_LOG_DATETIME))
    logging.getLogger().handlers = [
        handler,
    ]


def get_example_agent(num_agents):
    """Instantiate a set of custom agents"""
    return [
        CustomShorter(),
    ] * num_agents


def get_market(init_pool_apy, fee_percent, token_duration, init_share_price):
    """setup market"""
    time_stretch_constant = pricing_model.calc_time_stretch(init_pool_apy)
    market = Market(
        fee_percent=fee_percent,  # g
        token_duration=token_duration,
        time_stretch_constant=time_stretch_constant,
        init_share_price=init_share_price,  # u from YieldSpace w/ Yield Baring Vaults
        share_price=init_share_price,  # c from YieldSpace w/ Yield Baring Vaults
    )
    return market


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
    config = load_and_parse_config_file(args.config)
    if args.log_level is None:
        log_level = config.simulator.log_level
    else:
        log_level = args.log_level
    rng = np.random.default_rng(config.simulator.random_seed)
    # define root logging parameters
    setup_logging(filename=args.output, max_bytes=args.max_bytes, log_level=log_level)
    # run random number generators to get random simulation arguments
    random_sim_vars = sim_utils.get_random_variables(config, rng)
    # instantiate the pricing model
    pricing_model = sim_utils.get_pricing_model(model_name=args.pricing_model)
    # instantiate the market
    market = get_market(
        random_sim_vars.init_pool_apy,
        random_sim_vars.fee_percent,
        config.simulator.token_duration,
        random_sim_vars.init_share_price,
    )
    # instantiate the init_lp agent
    init_lp_agent = sim_utils.get_init_lp_agent(
        random_sim_vars.target_liquidity,
        random_sim_vars.init_pool_apy,
        random_sim_vars.fee_percent,
    )
    # get trading agent list
    agent_list = get_example_agent(num_agents=args.num_agents)
    # set up simulator
    simulator = Simulator(
        config=config,
        pricing_model=pricing_model,
        market=market,
        agent_list=agent_list,
        rng=rng,
        random_simulation_variables=random_sim_vars,
    )

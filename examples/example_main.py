"""Example main.py file for illustrating a simulator workflow"""
from __future__ import annotations  # types will be strings by default in 3.11

# stdlib
import argparse
from typing import Any

# elfpy core repo
import elfpy

# elfpy core classes
from elfpy.agent import Agent
from elfpy.markets import Market
from elfpy.types import MarketActionType

# elfpy utils
from elfpy.utils import sim_utils  # utilities for setting up a simulation
import elfpy.utils.parse_config as config_utils
import elfpy.utils.outputs as output_utils


# pylint: disable=duplicate-code


class CustomShorter(Agent):
    """
    Agent that is trying to optimize on a rising vault APR via shorts
    """

    def __init__(self, wallet_address: int, budget: int = 10_000) -> None:
        """Add custom stuff then call basic policy init"""
        self.pt_to_short = 1_000
        super().__init__(wallet_address, budget)

    def action(self, market: Market) -> list[Any]:
        """Implement a custom user strategy"""
        shorts = list(self.wallet.shorts.values())
        has_opened_short = bool(any((short.balance > 0 for short in shorts)))
        can_open_short = self.get_max_short(market) >= self.pt_to_short
        vault_apr = market.market_state.vault_apr
        action_list = []
        if can_open_short:
            if vault_apr > market.rate:
                action_list.append(
                    self.create_agent_action(action_type=MarketActionType.OPEN_SHORT, trade_amount=self.pt_to_short)
                )
            elif vault_apr < market.rate:
                if has_opened_short:
                    action_list.append(
                        self.create_agent_action(
                            action_type=MarketActionType.CLOSE_SHORT,
                            trade_amount=self.pt_to_short,
                            open_share_price=1.0,
                        )
                    )
        return action_list


def get_example_agents(new_agents: int, existing_agents: int = 0) -> list[Agent]:
    """Instantiate a set of custom agents"""
    agents = []
    for address in range(existing_agents, existing_agents + new_agents):
        agent = CustomShorter(address)
        agent.log_status_report()
        agents += [agent]
    return agents


def get_argparser() -> argparse.ArgumentParser:
    """Define & parse arguments from stdin"""
    parser = argparse.ArgumentParser(
        prog="ElfMain",
        description="Example execution script for running simulations using Elfpy",
        epilog="See the README on https://github.com/element-fi/elf-simulations/ for more implementation details",
    )
    parser.add_argument("--output", help="Optional output filename for logging", default=None, type=str)
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
        default=None,
        type=str,
    )
    parser.add_argument(
        "--config", help="Config file. Default uses the example config.", default="config/example_config.toml", type=str
    )
    parser.add_argument(
        "--num_agents", help="Integer specifying how many agents you want to simulate.", default=1, type=int
    )
    parser.add_argument(
        "--pricing_model", help="Pricing model to be used in the simulation", default="Hyperdrive", type=str
    )
    parser.add_argument("--num_trading_days", help="Number of simulated trading days", default=None, type=int)
    parser.add_argument("--blocks_per_day", help="Number of simulated trading blocks per day", default=None, type=int)
    return parser


if __name__ == "__main__":
    # Instantiate the config using the command line arguments as overrides.
    args = get_argparser().parse_args()
    config = config_utils.load_and_parse_config_file(args.config)
    override_dict = {}
    if args.num_trading_days is not None:
        override_dict["num_trading_days"] = args.num_trading_days
    if args.blocks_per_day is not None:
        override_dict["num_blocks_per_day"] = args.blocks_per_day
    override_dict["pricing_model_name"] = args.pricing_model
    override_dict["vault_apr"] = {
        "type": "uniform",
        "low": 0.001,
        "high": 0.9,
    }
    config = config_utils.override_config_variables(config, override_dict)
    if args.log_level is not None:
        config.simulator.logging_level = args.log_level

    # Define root logging parameters.
    output_utils.setup_logging(
        log_filename=args.output,
        max_bytes=args.max_bytes,
        log_level=config_utils.text_to_logging_level(config.simulator.logging_level),
    )

    # Initialize the simulator.
    simulator = sim_utils.get_simulator(config, get_example_agents(new_agents=args.num_agents, existing_agents=1))

    # Run the simulation.
    simulator.run_simulation()

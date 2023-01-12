"""A minimum viable simulation"""
# stdlib
import argparse
from typing import Any, Optional

# external imports
import numpy as np
from numpy.random import Generator

# elfpy core repo
import elfpy

# elfpy core classes
from elfpy.agent import Agent
from elfpy.simulators import Simulator
from elfpy.markets import Market
from elfpy.types import MarketAction, MarketActionType

# elfpy utils
from elfpy.utils import sim_utils, parse_config as config_utils, outputs as output_utils
from elfpy.utils.config import Config
from elfpy.wallet import Long


# TODO: Add more configuration potential by allowing the initializer to
# influence the relative probability of things like shorting vs longing.
class RandomAgent(Agent):
    """
    Agent that randomly manages their portfolio
    """

    def __init__(self, rng: Generator, wallet_address: int, budget: int = 10_000) -> None:
        self.rng = rng
        super().__init__(wallet_address, budget)

    # TODO: Implement random short behavior.
    def action(self, market: Market) -> list[Any]:
        action_list = []

        # Flip a biased coin to see whether or not to make a trade.
        flip = self.rng.random()
        if flip >= 0.9:
            max_long = min(
                self.wallet.base,
                market.pricing_model.get_max_long(market.market_state, market.fee_percent, market.position_duration),
            )
            open_longs = list(self.wallet.longs.items())

            # Randomly open or close a position depending on the trader's
            # ability to perform these actions.
            if max_long > 0 and len(open_longs) == 0:
                action_list.append(self._open_long(max_long=max_long, market_time=market.time))
            elif max_long == 0 and len(open_longs) > 0:
                action_list.append(self._close_long(open_longs))
            elif max_long > 0 and len(open_longs) > 0:
                flip = self.rng.random()
                if flip < 0.5:
                    action_list.append(self._open_long(max_long=max_long, market_time=market.time))
                else:
                    action_list.append(self._close_long(open_longs))

        return action_list

    def _open_long(self, max_long: float, market_time: float) -> MarketAction:
        return self.create_agent_action(
            action_type=MarketActionType.OPEN_LONG,
            # Uniformly select trade amounts from (0, max_long].
            trade_amount=abs(self.rng.uniform(-max_long, 0)),
            mint_time=market_time,
        )

    def _close_long(self, open_longs: list[tuple[float, Long]]) -> MarketAction:
        (mint_time, long) = open_longs[self.rng.integers(0, len(open_longs))]
        return self.create_agent_action(
            action_type=MarketActionType.CLOSE_LONG,
            # Uniformly select trade amounts from (0, long_balance].
            trade_amount=abs(self.rng.uniform(-long.balance, 0)),
            mint_time=mint_time,
        )


def get_example_agents(
    rng: Generator,
    num_new_agents: int,
    agents: Optional[dict[int, Agent]] = None,
) -> dict[int, Agent]:
    """Instantiate a set of custom agents"""
    if agents is None:
        agents = {}
    loop_start = len(agents)  # number of existing agents
    loop_end = loop_start + num_new_agents
    for wallet_address in range(loop_start, loop_end):
        agent = RandomAgent(rng, wallet_address)
        agent.log_status_report()
        agents.update({agent.wallet.address: agent})
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
    parser.add_argument("--trading_days", help="Number of simulated trading days", default=None, type=int)
    parser.add_argument("--blocks_per_day", help="Number of simulated trading blocks per day", default=None, type=int)
    return parser


# TODO: This should live within the Simulator class.
def run_random_agent_simulation(config: Config):
    """Executes a simulation with random agents"""

    # Sample the random simulation arguments.
    rng = np.random.default_rng(config.simulator.random_seed)
    random_sim_vars = sim_utils.get_random_variables(config, rng)

    # Instantiate the pricing model and market.
    sim_pricing_model = sim_utils.get_pricing_model(model_name=args.pricing_model)
    sim_market = sim_utils.get_market(
        sim_pricing_model,
        random_sim_vars.target_pool_apr,
        random_sim_vars.fee_percent,
        config.simulator.token_duration,
        random_sim_vars.vault_apr,
        random_sim_vars.init_share_price,
    )

    # Instantiate the initial LP agent.
    init_agents = {
        0: sim_utils.get_init_lp_agent(
            sim_market,
            random_sim_vars.target_liquidity,
            random_sim_vars.target_pool_apr,
            random_sim_vars.fee_percent,
        )
    }

    # Initialize the simulator using only the initial LP.
    simulator = Simulator(
        config=config,
        market=sim_market,
        agents=init_agents,
        rng=rng,
        random_simulation_variables=random_sim_vars,
    )
    simulator.collect_and_execute_trades()

    # Add the other trading agents.
    simulator.agents = get_example_agents(rng=simulator.rng, num_new_agents=args.num_agents, agents=init_agents)

    # Run the simulation.
    simulator.run_simulation()


if __name__ == "__main__":
    # Initialize the configuration and apply overrides from the command line arguments.
    args = get_argparser().parse_args()
    override_dict = {}
    if args.trading_days is not None:
        override_dict["num_trading_days"] = args.trading_days
    if args.blocks_per_day is not None:
        override_dict["num_blocks_per_day"] = args.blocks_per_day
    if args.log_level is not None:
        override_dict["logging_level"] = args.log_level
    override_dict["vault_apr"] = {"type": "GeometricBrownianMotion", "initial": 0.05}
    config_ = config_utils.override_config_variables(
        config_utils.load_and_parse_config_file(args.config), override_dict
    )

    # Define root logging parameters.
    output_utils.setup_logging(
        log_filename=args.output,
        max_bytes=args.max_bytes,
        log_level=config_utils.text_to_logging_level(config_.simulator.logging_level),
    )

    # Run the simulation.
    run_random_agent_simulation(config_)

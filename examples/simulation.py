"""A minimum viable simulation"""
from __future__ import annotations  # types will be strings by default in 3.11

# stdlib
import argparse
from typing import Any

# external imports
from numpy.random import Generator
from stochastic.processes import GeometricBrownianMotion

# elfpy core repo
import elfpy
from elfpy.agent import Agent
from elfpy.markets import Market
from elfpy.types import MarketAction, MarketActionType, Config
from elfpy.utils import sim_utils
from elfpy.utils import outputs as output_utils
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
            max_long = self.get_max_long(market)
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
    new_agents: int,
    existing_agents: int,
) -> list[Agent]:
    """Instantiate a set of custom agents"""
    agents = []
    for address in range(existing_agents, existing_agents + new_agents):
        agent = RandomAgent(rng, address)
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
        "--num_agents", help="Integer specifying how many agents you want to simulate.", default=1, type=int
    )
    parser.add_argument(
        "--pricing_model", help="Pricing model to be used in the simulation", default="Hyperdrive", type=str
    )
    parser.add_argument("--trading_days", help="Number of simulated trading days", default=None, type=int)
    parser.add_argument("--blocks_per_day", help="Number of simulated trading blocks per day", default=None, type=int)
    return parser


if __name__ == "__main__":
    # Instantiate the config using the command line arguments as overrides.
    args = get_argparser().parse_args()
    config = Config()
    config.num_trading_days = args.num_trading_days
    config.num_blocks_per_day = args.blocks_per_day
    config.pricing_model_name = args.pricing_model
    config.vault_apr = (
        GeometricBrownianMotion(rng=config.rng).sample(n=config.num_trading_days - 1, initial=0.05)
    ).tolist()
    config.logging_level = sim_utils.text_to_logging_level(args.log_level)
    # NOTE: lint error false positives: This message may report object members that are created dynamically,
    # but exist at the time they are accessed.
    config.freeze()  # pylint: disable=no-member # type: ignore

    # Define root logging parameters.
    output_utils.setup_logging(
        log_filename=args.output,
        max_bytes=args.max_bytes,
        log_level=config.logging_level,
    )

    # Initialize the simulator.
    simulator = sim_utils.get_simulator(
        config, get_example_agents(rng=config.rng, new_agents=args.num_agents, existing_agents=1)
    )

    # Run the simulation.
    simulator.run_simulation()

"""
Config structure
"""
# dataclasses can have many attributes
# pylint: disable=too-many-instance-attributes


from dataclasses import dataclass, field
from typing import Callable, Union
import numpy as np
from numpy.random import Generator
from stochastic.processes import GeometricBrownianMotion

from elfpy.types import RandomSimulationVariables


@dataclass
class MarketConfig:
    """config parameters specific to the market"""

    min_target_liquidity: float = field(default=1e6, metadata={"hint": "shares"})
    max_target_liquidity: float = field(default=10e6, metadata={"hint": "shares"})
    min_target_volume: float = field(default=0.001, metadata={"hint": "fraction of pool liquidity"})
    max_target_volume: float = field(default=0.01, metadata={"hint": "fraction of pool liquidity"})
    min_vault_age: int = field(default=0, metadata={"hint": "fraction of a year"})
    max_vault_age: int = field(default=1, metadata={"hint": "fraction of a year"})
    vault_apr: Union[Callable, dict] = field(
        default_factory=lambda: {"type": "constant", "value": 0.3},
        metadata={"hint": "the underlying (variable) vault apr at each time step"},
    )
    base_asset_price: float = field(default=2e3, metadata={"hint": "market price"})

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)


@dataclass
class AMMConfig:
    """config parameters specific to the amm"""

    pricing_model_name: str = field(default="Hyperdrive", metadata={"hint": 'Must be "Hyperdrive", or "YieldSpace"'})
    min_fee: float = field(default=0.1, metadata={"hint": "decimal that assignes fee_percent"})
    max_fee: float = field(default=0.5, metadata={"hint": "decimal that assignes fee_percent"})
    min_pool_apr: float = field(default=0.02, metadata={"hint": "as a decimal"})
    max_pool_apr: float = field(default=0.9, metadata={"hint": "as a decimal"})
    floor_fee: float = field(default=0, metadata={"hint": "minimum fee percentage (bps)"})

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)


@dataclass
class SimulatorConfig:
    """config parameters specific to the simulator"""

    # durations
    num_trading_days: int = field(default=180, metadata={"hint": "in days; should be <= pool_duration"})
    num_blocks_per_day: int = field(default=7_200, metadata={"hint": "int"})
    token_duration: float = field(
        default=90 / 365, metadata={"hint": "time lapse between token mint and expiry as a yearfrac"}
    )

    # users
    shuffle_users: bool = field(default=True, metadata={"hint": "shuffle order of action (as if random gas paid)"})
    agent_policies: list = field(default_factory=list, metadata={"hint": "List of strings naming user policies"})
    init_lp: bool = field(default=True, metadata={"hint": "use initial LP to seed pool"})

    # vault
    compound_vault_apr: bool = field(
        default=True, metadata={"hint": "whether or not to use compounding revenue for the underlying yield source"}
    )
    init_vault_age: float = field(default=0, metadata={"hint": "initial vault age"})

    # logging
    logging_level: str = field(default="info", metadata={"hint": "Logging level, as defined by stdlib logging"})

    # numerical
    precision: int = field(default=64, metadata={"hint": "precision of calculations; max is 64"})

    # random
    random_seed: int = field(default=1, metadata={"hint": "int to be used for the random seed"})
    rng: Generator = field(
        init=False, compare=False, metadata={"hint": "random number generator used in the simulation"}
    )

    def __post_init__(self):
        self.rng = np.random.default_rng(self.random_seed)

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)


@dataclass
class Config:
    """Data object for storing user simulation config parameters"""

    market: MarketConfig = field(default_factory=MarketConfig)
    amm: AMMConfig = field(default_factory=AMMConfig)
    simulator: SimulatorConfig = field(default_factory=SimulatorConfig)

    def __getitem__(self, key):
        return getattr(self, key)


def setup_vault_apr(config: Config):
    """Construct the vault_apr list
    Note: callable type option would allow for infinite num_trading_days after small modifications

    Parameters
    ----------
    config : Config
        config object, as defined in elfpy.utils.config

    Returns
    -------
    vault_apr : list
        list of apr values that is the same length as num_trading_days
    """
    if isinstance(config.market.vault_apr, dict):  # dictionary specifies parameters for the callable
        if config.market.vault_apr["type"].lower() == "constant":
            vault_apr = [
                config.market.vault_apr["value"],
            ] * config.simulator.num_trading_days
        elif config.market.vault_apr["type"].lower() == "uniform":
            vault_apr = config.simulator.rng.uniform(
                low=config.market.vault_apr["low"],
                high=config.market.vault_apr["high"],
                size=config.simulator.num_trading_days,
            ).tolist()
        elif config.market.vault_apr["type"].lower() == "geometricbrownianmotion":
            # the n argument is number of steps, so the number of points is n+1
            vault_apr = (
                GeometricBrownianMotion(rng=config.simulator.rng).sample(
                    n=config.simulator.num_trading_days - 1, initial=config.market.vault_apr["initial"]
                )
            ).tolist()
        else:
            raise ValueError(
                f"{config.market.vault_apr['type']=} not one of \"constant\","
                f'"uniform", or "geometricbrownianmotion"'
            )
    elif isinstance(config.market.vault_apr, Callable):  # callable (optionally generator) function
        vault_apr = list(config.market.vault_apr())
    elif isinstance(config.market.vault_apr, list):  # user-defined list of values
        vault_apr = config.market.vault_apr
    elif isinstance(config.market.vault_apr, float):  # single constant value to be cast to a float
        vault_apr = [float(config.market.vault_apr)] * config.simulator.num_trading_days
    else:
        raise TypeError(
            f"config.market.vault_apr must be an int, list, dict, or callable, not {type(config.market.vault_apr)}"
        )
    return vault_apr


def get_random_variables(config: Config):
    """Use random number generator to assign initial simulation parameter values

    Parameters
    ----------
    config : Config
        config object, as defined in elfpy.utils.config

    Returns
    -------
    RandomSimulationVariables
        dataclass that contains variables for initiating and running simulations
    """
    random_vars = RandomSimulationVariables(
        target_liquidity=config.simulator.rng.uniform(
            low=config.market.min_target_liquidity, high=config.market.max_target_liquidity
        ),
        target_pool_apr=config.simulator.rng.uniform(
            low=config.amm.min_pool_apr, high=config.amm.max_pool_apr
        ),  # starting fixed apr as a decimal
        trade_fee_percent=config.simulator.rng.uniform(low=config.amm.min_fee, high=config.amm.max_fee),
        redemption_fee_percent=config.simulator.rng.uniform(low=config.amm.min_fee, high=config.amm.max_fee),
        vault_apr=setup_vault_apr(config),
        init_vault_age=config.simulator.rng.uniform(low=config.market.min_vault_age, high=config.market.max_vault_age),
    )
    return random_vars

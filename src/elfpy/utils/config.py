"""Config structure"""
from dataclasses import dataclass, field
from typing import Callable, Union

import numpy as np
from numpy.random import Generator
from stochastic.processes import GeometricBrownianMotion

from elfpy.types import RandomSimulationVariables

# dataclasses can have many attributes
# pylint: disable=too-many-instance-attributes


# TODO: Make freezable
# @freezable
@dataclass
class Config:
    """Data object for storing user simulation config parameters"""

    # Market
    min_target_liquidity: float = field(default=1e6, metadata={"hint": "shares"})
    max_target_liquidity: float = field(default=10e6, metadata={"hint": "shares"})
    target_liquidity: float = field(metadata=to_description("total size of the market pool (bonds + shares)"))
    min_target_volume: float = field(default=0.001, metadata={"hint": "fraction of pool liquidity"})
    max_target_volume: float = field(default=0.01, metadata={"hint": "fraction of pool liquidity"})
    min_vault_age: int = field(default=0, metadata={"hint": "fraction of a year"})
    max_vault_age: int = field(default=1, metadata={"hint": "fraction of a year"})
    init_vault_age: float = field(metadata=to_description("fraction of a year since the vault was opened"))
    vault_apr: Union[Callable, dict] = field(
        default_factory=lambda: {"type": "constant", "value": 0.3},
        metadata={"hint": "the underlying (variable) vault apr at each time step"},
    )
    vault_apr: list = field(metadata=to_description("yield bearing source APR"))
    base_asset_price: float = field(default=2e3, metadata={"hint": "market price"})
    # NOTE: We ignore the type error since the value will never be None after
    # initialization, and we don't want the value to be set to None downstream.
    init_share_price: float = field(
        default=None, metadata=to_description("initial market share price for the vault asset")  # type: ignore
    )

    # AMM
    pricing_model_name: str = field(default="Hyperdrive", metadata={"hint": 'Must be "Hyperdrive", or "YieldSpace"'})
    min_fee: float = field(default=0.1, metadata={"hint": "decimal that assignes fee_percent"})
    max_fee: float = field(default=0.5, metadata={"hint": "decimal that assignes fee_percent"})
    trade_fee_percent: float = field(metadata=to_description("LP fee percent to charge for trades"))
    redemption_fee_percent: float = field(metadata=to_description("LP fee percent to charge for redemption"))
    min_pool_apr: float = field(default=0.02, metadata={"hint": "as a decimal"})
    max_pool_apr: float = field(default=0.9, metadata={"hint": "as a decimal"})
    target_pool_apr: float = field(metadata=to_description("desired fixed apr for as a decimal"))
    floor_fee: float = field(default=0, metadata={"hint": "minimum fee percentage (bps)"})

    # Simulation
    # durations
    num_trading_days: int = field(default=180, metadata={"hint": "in days; should be <= pool_duration"})
    num_blocks_per_day: int = field(default=7_200, metadata={"hint": "int"})
    num_position_days: int = field(default=90, metadata={"hint": "time lapse between token mint and expiry as days"})

    # users
    shuffle_users: bool = field(default=True, metadata={"hint": "shuffle order of action (as if random gas paid)"})
    agent_policies: list = field(default_factory=list, metadata={"hint": "List of strings naming user policies"})
    init_lp: bool = field(default=True, metadata={"hint": "use initial LP to seed pool"})

    num_position_days: int = field(default=365, metadata={"hint": "Term length in days of a position"})

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
        r"""init_share_price & rng are a function of other random variables"""
        self.rng = np.random.default_rng(self.random_seed)
        if self.init_share_price is None:
            self.init_share_price = (1 + self.vault_apr[0]) ** self.init_vault_age

    def __getitem__(self, key):
        return getattr(self, key)

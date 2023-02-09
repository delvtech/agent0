"""Config structure"""
from dataclasses import dataclass, field
from typing import Callable, Union

import numpy as np
from numpy.random import Generator

from stochastic.processes import GeometricBrownianMotion
from elfpy.types import freezable, to_description

# dataclasses can have many attributes
# pylint: disable=too-many-instance-attributes


@freezable
@dataclass
class Config:
    """Data object for storing user simulation config parameters"""

    # Market
    target_liquidity: float = field(
        default=1e6, metadata=to_description("total size of the market pool (bonds + shares)")
    )
    target_volume: float = field(default=0.01, metadata=to_description("fraction of pool liquidity"))
    init_vault_age: float = field(default=0, metadata=to_description("fraction of a year since the vault was opened"))
    base_asset_price: float = field(default=2e3, metadata=to_description("market price"))
    # NOTE: We ignore the type error since the value will never be None after
    # initialization, and we don't want the value to be set to None downstream.
    vault_apr: list = field(
        default=None, metadata=to_description("the underlying (variable) vault APR at each time step")
    )
    init_share_price: float = field(
        default=None, metadata=to_description("initial market share price for the vault asset")  # type: ignore
    )

    # AMM
    pricing_model_name: str = field(
        default="Hyperdrive", metadata=to_description('Must be "Hyperdrive", or "YieldSpace"')
    )
    min_fee: float = field(default=0.1, metadata={"hint": "decimal that assignes fee_percent"})
    max_fee: float = field(default=0.5, metadata={"hint": "decimal that assignes fee_percent"})
    trade_fee_percent: float = field(
        default=0.05, metadata=to_description("LP fee factor (decimal) to charge for trades")
    )
    redemption_fee_percent: float = field(
        default=0.05, metadata=to_description("LP fee factor (decimal) to charge for redemption")
    )
    target_pool_apr: float = field(default=0.1, metadata=to_description("desired fixed apr for as a decimal"))
    floor_fee: float = field(default=0, metadata=to_description("minimum fee percentage (bps)"))

    # Simulation
    # durations
    num_trading_days: int = field(default=180, metadata=to_description("in days; should be <= pool_duration"))
    num_blocks_per_day: int = field(default=7_200, metadata=to_description("int; agents execute trades each block"))
    num_position_days: int = field(
        default=90, metadata=to_description("time lapse between token mint and expiry as days")
    )

    # users
    shuffle_users: bool = field(
        default=True, metadata=to_description("Shuffle order of action (as if random gas paid)")
    )
    agent_policies: list = field(default_factory=list, metadata=to_description("List of strings naming user policies"))
    init_lp: bool = field(default=True, metadata=to_description("If True, use an initial LP agent to seed pool"))
    num_position_days: int = field(default=365, metadata=to_description("Term length in days of a position"))

    # vault
    compound_vault_apr: bool = field(
        default=True,
        metadata=to_description("Whether or not to use compounding revenue for the underlying yield source"),
    )
    init_vault_age: float = field(default=0, metadata=to_description("initial vault age"))

    # logging
    logging_level: str = field(default="info", metadata=to_description("Logging level, as defined by stdlib logging"))

    # numerical
    precision: int = field(default=64, metadata=to_description("precision of calculations; max is 64"))

    # random
    random_seed: int = field(default=1, metadata=to_description("int to be used for the random seed"))
    rng: Generator = field(
        init=False, compare=False, metadata=to_description("random number generator used in the simulation")
    )

    def __post_init__(self):
        r"""init_share_price & rng are a function of other random variables"""
        self.rng = np.random.default_rng(self.random_seed)
        if self.vault_apr is None:
            self.vault_apr = [0.05] * self.num_trading_days
        if self.init_share_price is None:
            self.init_share_price = (1 + self.vault_apr[0]) ** self.init_vault_age

    def __getitem__(self, key):
        return getattr(self, key)

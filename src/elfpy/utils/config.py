"""
Config structure
"""
# dataclasses can have many attributes
# pylint: disable=too-many-instance-attributes


from dataclasses import dataclass, field
from typing import Callable


@dataclass
class MarketConfig:
    """config parameters specific to the market"""

    min_target_liquidity: float = field(default=1e6, metadata={"hint": "shares"})
    max_target_liquidity: float = field(default=10e6, metadata={"hint": "shares"})
    min_target_volume: float = field(default=0.001, metadata={"hint": "fraction of pool liquidity"})
    max_target_volume: float = field(default=0.01, metadata={"hint": "fraction of pool liquidity"})
    min_vault_age: int = field(default=0, metadata={"hint": "fraction of a year"})
    max_vault_age: int = field(default=1, metadata={"hint": "fraction of a year"})
    vault_apr: Callable | dict = field(
        default_factory=lambda: {"type": "constant", "value": 0.3}, metadata={"hint": "yield bearing vault apr"}
    )
    base_asset_price: float = field(default=2e3, metadata={"hint": "market price"})


@dataclass
class AMMConfig:
    """config parameters specific to the amm"""

    pricing_model_name: str = field(default="Hyperdrive", metadata={"hint": 'Must be "Hyperdrive", or "YieldSpace"'})
    min_fee: float = field(default=0.1, metadata={"hint": "decimal that assignes fee_percent"})
    max_fee: float = field(default=0.5, metadata={"hint": "decimal that assignes fee_percent"})
    min_pool_apy: float = field(default=0.02, metadata={"hint": "as a decimal"})
    max_pool_apy: float = field(default=0.9, metadata={"hint": "as a decimal"})
    floor_fee: float = field(default=0, metadata={"hint": "minimum fee percentage (bps)"})


@dataclass
class SimulatorConfig:
    """config parameters specific to the simulator"""

    # durations
    pool_duration: int = field(default=180, metadata={"hint": "in days"})
    num_trading_days: int = field(default=180, metadata={"hint": "in days; should be <= pool_duration"})
    num_blocks_per_day: int = field(default=7_200, metadata={"hint": "int"})
    token_duration: float = field(
        default=90 / 365, metadata={"hint": "time lapse between token mint and expiry as a yearfrac"}
    )

    # users
    shuffle_users: bool = field(default=True, metadata={"hint": "shuffle order of action (as if random gas paid)"})
    agent_policies: list = field(default_factory=list, metadata={"hint": "List of strings naming user policies"})
    init_lp: bool = field(default=True, metadata={"hint": "use initial LP to seed pool"})

    # trading
    target_liquidity: float = field(default=0, metadata={"hint": ""})
    target_daily_volume: float = field(default=0, metadata={"hint": "daily volume in base asset of trades"})
    fee_percent: float = field(default=0, metadata={"hint": ""})

    # vault
    init_vault_age: float = field(default=0, metadata={"hint": "initial vault age"})
    vault_apr: list[float] = field(
        default_factory=list, metadata={"hint": "the underlying (variable) vault apy at each time step"}
    )

    # logging
    logging_level: str = field(default="info", metadata={"hint": "Logging level, as defined by stdlib logging"})

    # numerical
    precision: int = field(default=64, metadata={"hint": "precision of calculations; max is 64"})
    random_seed: int = field(default=1, metadata={"hint": "int to be used for the random seed"})


@dataclass
class Config:
    """Data object for storing user simulation config parameters"""

    market: MarketConfig
    amm: AMMConfig
    simulator: SimulatorConfig

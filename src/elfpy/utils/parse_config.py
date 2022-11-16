"""
Utilities for parsing & loading user config TOML files

TODO: change floor_fee to be a decimal like min_fee and max_fee
"""


from dataclasses import dataclass, field


import tomli


@dataclass
class market_config:
    min_target_liquidity: float = field(default=1e6,
        metadata={"hint": "shares"})
    max_target_liquidity: float = field(default=10e6,
        metadata={"hint": "shares"})
    min_target_volume: float = field(default=0.001,
        metadata={"hint": "fraction of pool liquidity"})
    max_target_volume: float = field(default=0.01,
        metadata={"hint": "fraction of pool liquidity"})
    min_vault_age: int = field(default=0,
        metadata={"hint": "fraction of a year"})
    max_vault_age: int = field(default=1,
        metadata={"hint": "fraction of a year"})
    min_vault_apy: float = field(default=0.001,
        metadata={"hint": "decimal"})
    max_vault_apy: float = field(default=0.9,
        metadata={"hint": "decimal"})
    base_asset_price: float = field(default=2e3,
        metadata={"hint": "market price"})


@dataclass
class amm_config:
    min_fee: float = field(default=0.1,
        metadata={"hint": "decimal that assignes fee_percent"})
    max_fee: float = field(default=0.5,
        metadata={"hint": "decimal that assignes fee_percent"})
    min_pool_apy: float = field(default=0.02,
        metadata={"hint": "as a decimal"})
    max_pool_apy: float = field(default=0.9,
        metadata={"hint": "as a decimal"})
    floor_fee: float = field(default=0,
        metadata={"hint": "minimum fee percentage (bps)"})


@dataclass
class simulator_config:
    pool_duration: int = field(default=180,
        metadata={"hint": "in days"})
    num_trading_days: int = field(default=180,
        metadata={"hint": "in days; should be <= pool_duration"})
    num_blocks_per_day: int = field(default=7_200,
        metadata={"hint": "int"})
    token_duration: float = field(default=90/365,
        metadata={"hint": "time lapse between token mint and expiry as a yearfrac"})
    precision: int = field(default=64,
        metadata={"hint": "precision of calculations; max is 64"})
    pricing_model_name: str = field(default="Element",
        metadata={"hint": 'Must be "Element" or "Hyperdrive"'})
    user_policies: list = field(default_factory=list,
        metadata={"hint": "List of strings naming user strategies"})
    random_seed: int = field(default=1,
        metadata={"hint": "int to be used for the random seed"})
    verbose: bool = field(default=False,
        metadata={"hint": "verbosity level for logging"})


@dataclass
class config:
    market: market_config
    amm: amm_config
    simulator: simulator_config


def parse_simulation_config(config_file):
    """
    Parse the TOML config file and return a config object
    """
    with open(config_file, mode="rb") as file:
        toml_config = tomli.load(file)
    config_dc = config(
        market=market_config(**toml_config["market"]),
        amm=amm_config(**toml_config["amm"]),
        simulator=simulator_config(**toml_config["simulator"])
    )
    return config_dc

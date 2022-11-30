"""
Testing for the calc_in_given_out of the pricing models.
"""

# pylint: disable=too-many-lines
# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-locals
# pylint: disable=attribute-defined-outside-init

from typing import Union

from dataclasses import dataclass
import unittest
import numpy as np

from elfpy.utils import parse_config as config_utils
from elfpy.pricing_models import ElementPricingModel, HyperdrivePricingModel

class TestParseSimulationConfig(unittest.TestCase):
    """Unit tests for the parse_simulation_config function"""

    def test_parse_simulation_config_success(self):
        """Success tests for parse_simulation_config"""
        config = config_utils.parse_simulation_config("./tests/utils/test_parse_config_success_data.toml")
        # Config(market=MarketConfig(min_target_liquidity=1000000.0, max_target_liquidity=10000000.0, min_target_volume=0.001, max_target_volume=0.01, min_vault_age=0, max_vault_age=1, min_vault_apy=0.001, max_vault_apy=0.9, base_asset_price=2500.0), amm=AMMConfig(min_fee=0.1, max_fee=0.5, min_pool_apy=0.02, max_pool_apy=0.9, floor_fee=0), simulator=SimulatorConfig(pool_duration=180, num_trading_days=180, num_blocks_per_day=7200, token_duration=180, precision=64, pricing_model_name='Element', user_policies=['single_long'], random_seed=123, verbose=False))
        print(f"loaded market config: {config.market}")
        print(f"loaded amm config: {config.amm}")
        print(f"loaded simulator config: {config.simulator}")

    def test_parse_simulation_config_failure(self):
        """Failure tests for parse_simulation_config"""

        # Tests cases where all of [market], [amm], and [simulator] blocks 
        # have all fields filled out with valid parameters

        # title = "example simulation config"

        # [market]
        # min_target_liquidity = 1e6  # in shares. Positive integer >= 0
        # max_target_liquidity = 10e6  # in shares. Positive integer >= min_target_liquidity
        # min_target_volume = 0.001  # fraction of pool liquidity. Positive decimal <= 1
        # max_target_volume = 0.01  # fration of pool liquidity. Positive decimal >= min_target_volume but <= 1
        # min_vault_age = 0  # fraction of a year. Positive decimal
        # max_vault_age = 1  # fraction of a year. Positive decimal
        # min_vault_apy = 0.001  # as a decimal. Positive decimal
        # max_vault_apy = 0.9  # as a decimal. Positive decimal >= min_vault_apy
        # # fixed variables
        # base_asset_price = 2.5e3  # aka market price. Positive decimal

        # [amm]
        # # random variables
        # min_fee = 0.1  # decimal that assigns fee_percent. Positive decimal <= 1
        # max_fee = 0.5  # decimal that assigns fee_percent. Positive decimal >= min_fee but <= 1
        # min_pool_apy = 0.02  # as a decimal. Positive decimal
        # max_pool_apy = 0.9  # as a decimal. Positive decimal
        # # fixed variables
        # floor_fee = 0  # minimum fee percentage (bps). Positive decimal <= 1

        # [simulator]
        # # fixed variables
        # token_duration = 180  # in days. Positive integer
        # num_trading_days = 180  # should be <= pool_duration. Positive integer
        # num_blocks_per_day = 7200 # 24 * 60 * 60 / 12 = 12 second block time
        # precision = 64 # 64 is max precision (and the default for numpy)
        # pricing_model_name = "Element" # specify a pricing model. Must be "Hyperdrive" or "Element"
        # user_policies = ["single_long"] # specify a list of trading strategies by name
        # random_seed = 123 # to be passed to a rng. Positive integer
        # verbose = false # toggle verbose output level. Boolean
        pass
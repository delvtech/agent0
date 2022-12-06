"""
Testing for the ElfPy package modules
"""

# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-locals
# pylint: disable=attribute-defined-outside-init

import unittest
import itertools
import numpy as np
import pandas as pd
import os, sys

# sys.path.insert(1, os.path.join(os.getcwd(), "src"))

from elfpy.simulators import YieldSimulator
from elfpy.pricing_models import ElementPricingModel, HyperdrivePricingModel
from elfpy.markets import Market
from elfpy.utils.parse_config import AMMConfig, Config, MarketConfig, SimulatorConfig


class BaseTest(unittest.TestCase):
    """Generic test class"""


class TestSimulator(BaseTest):
    """Simulator test class"""

    def test_hyperdrive_sim(self):
        """Tests the simulator output to verify that indices are correct"""
        simulator = YieldSimulator(
            Config(
                market=MarketConfig(),
                amm=AMMConfig(verbose=True),
                simulator=SimulatorConfig(),
            )
        )
        for rng_index in range(1, 15):
            simulator.reset_rng(np.random.default_rng(rng_index))
            simulator.set_random_variables()
            simulator.run_simulation(
                {
                    "pricing_model_name": HyperdrivePricingModel().model_name(),
                }
            )

    def test_element_sim(self):
        """Tests the simulator output to verify that indices are correct"""
        simulator = YieldSimulator(
            Config(
                market=MarketConfig(),
                amm=AMMConfig(verbose=True),
                simulator=SimulatorConfig(),
            )
        )
        for rng_index in range(1, 15):
            simulator.reset_rng(np.random.default_rng(rng_index))
            simulator.set_random_variables()
            simulator.run_simulation(
                {
                    "pricing_model_name": ElementPricingModel().model_name(),
                }
            )

"""
Testing for the ElfPy package modules
"""

# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-locals
# pylint: disable=attribute-defined-outside-init
# pylint: disable=duplicate-code

import logging
import unittest
import sys
import numpy as np

from elfpy.simulators import YieldSimulator
from elfpy.utils.parse_config import AMMConfig, Config, MarketConfig, SimulatorConfig, apply_config_logging


class BaseTest(unittest.TestCase):
    """Generic test class"""

    logging_level = logging.INFO
    handler = logging.StreamHandler(sys.stdout)
    logging.getLogger().setLevel(logging_level)  # events of this level and above will be tracked
    handler.setFormatter(
        logging.Formatter("\n%(asctime)s: %(levelname)s: %(module)s.%(funcName)s:\n%(message)s", "%y-%m-%d %H:%M:%S")
    )
    logging.getLogger().handlers = [
        handler,
    ]


class TestSimulator(BaseTest):
    """Simulator test class"""

    def test_hyperdrive_sim(self):
        """Tests the simulator output to verify that indices are correct"""
        simulator = YieldSimulator(
            apply_config_logging(
                Config(
                    market=MarketConfig(),
                    amm=AMMConfig(),
                    simulator=SimulatorConfig(pricing_model_name="Hyperdrive"),
                )
            )
        )
        for rng_index in range(1, 15):
            simulator.reset_rng(np.random.default_rng(rng_index))
            simulator.set_random_variables()
            simulator.setup_simulated_entities()
            simulator.run_simulation()

    # def test_element_sim(self):
    #     """Tests the simulator output to verify that indices are correct"""
    #     simulator = YieldSimulator(
    #         apply_config_logging(
    #             Config(
    #                 market=MarketConfig(),
    #                 amm=AMMConfig(verbose=True),
    #                 simulator=SimulatorConfig(pricing_model_name="Element"),
    #             )
    #         )
    #     )
    #     for rng_index in range(1, 15):
    #         simulator.reset_rng(np.random.default_rng(rng_index))
    #         simulator.set_random_variables()
    #         simulator.setup_simulated_entities()
    #         simulator.run_simulation()

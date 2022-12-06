"""
Testing for the ElfPy package modules
"""

# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-locals
# pylint: disable=attribute-defined-outside-init
# pylint: disable=duplicate-code

import logging
import unittest
import os
import numpy as np

from elfpy.simulators import YieldSimulator
from elfpy.utils.parse_config import AMMConfig, Config, MarketConfig, SimulatorConfig, apply_config_logging


class TestSimulator(unittest.TestCase):
    """Simulator test class"""

    def test_hyperdrive_sim(self):
        """Tests the simulator output to verify that indices are correct"""
        logging_level = logging.INFO
        log_dir = ".logging"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        name = "test_sim.log"
        handler = logging.FileHandler(os.path.join(log_dir, name), "w")
        logging.getLogger().setLevel(logging_level)  # events of this level and above will be tracked
        handler.setFormatter(
            logging.Formatter(
                "\n%(asctime)s: %(levelname)s: %(module)s.%(funcName)s:\n%(message)s", "%y-%m-%d %H:%M:%S"
            )
        )
        logging.getLogger().handlers = [
            handler,
        ]
        simulator = YieldSimulator(
            apply_config_logging(
                Config(
                    market=MarketConfig(),
                    amm=AMMConfig(),
                    simulator=SimulatorConfig(
                        pricing_model_name="Hyperdrive", num_trading_days=10, num_blocks_per_day=10
                    ),
                )
            )
        )
        for rng_seed in range(1, 10):
            try:
                simulator.reset_rng(np.random.default_rng(rng_seed))
                simulator.set_random_variables()
                simulator.setup_simulated_entities()
                simulator.run_simulation()
            except Exception as exc:
                assert False, f"test failed at seed {rng_seed} with exception {exc}"
        # comment this to view the generated log files
        file_loc = logging.getLogger().handlers[0].baseFilename
        os.remove(file_loc)

    # TODO Update element pricing model to include lp calcs
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
    #     for rng_seed in range(1, 15):
    #         simulator.reset_rng(np.random.default_rng(rng_seed))
    #         simulator.set_random_variables()
    #         simulator.setup_simulated_entities()
    #         simulator.run_simulation()

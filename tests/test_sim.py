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
from elfpy.utils.parse_config import Config, AMMConfig, MarketConfig, SimulatorConfig


class TestSimulator(unittest.TestCase):
    """Simulator test class"""

    @staticmethod
    def setup_logging():
        """Setup logging and handlers for the test"""
        logging_level = logging.DEBUG
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

    def test_hyperdrive_sim(self):
        """Tests the simulator output to verify that indices are correct"""
        self.setup_logging()
        simulator = YieldSimulator(
            Config(
                market=MarketConfig(),
                amm=AMMConfig(pricing_model_name="Hyperdrive"),
                simulator=SimulatorConfig(
                    num_trading_days=10,
                    num_blocks_per_day=10,
                    logging_level=logging.INFO,
                ),
            )
        )
        for rng_seed in range(1, 10):
            try:
                simulator.reset_rng(np.random.default_rng(rng_seed))
                simulator.set_random_variables()
                simulator.setup_simulated_entities()
                simulator.run_simulation()

            # pylint: disable=broad-except
            except Exception as exc:
                assert False, f"ERROR: Test failed at seed {rng_seed} with exception\n{exc}"
        # comment this to view the generated log files
        file_loc = logging.getLogger().handlers[0].baseFilename
        os.remove(file_loc)

    # TODO Update element pricing model to include lp calcs
    # def test_element_sim(self):
    #     """Tests the simulator output to verify that indices are correct"""
    #     simulator = YieldSimulator(
    #        Config(
    #            market=MarketConfig(),
    #            amm=AMMConfig(pricing_model_name="Element"),
    #            simulator=SimulatorConfig(
    #                logging_level=logging.INFO,
    #            )
    #        )
    #     )
    #     for rng_seed in range(1, 15):
    #         simulator.reset_rng(np.random.default_rng(rng_seed))
    #         simulator.set_random_variables()
    #         simulator.setup_simulated_entities()
    #         simulator.run_simulation()

"""Testing for crash report logging."""
from __future__ import annotations

# TODO this shouldn't be using chainsync db schemas for crash reporting
# class TestCrashReport(unittest.TestCase):
#    """Run the tests."""
#
#    def test_hyperdrive_crash_report_logging(self):
#        """Tests hyperdrive crash report logging."""
#        setup_hyperdrive_crash_report_logging()
#        config = SimulationConfig()
#        config.pricing_model_name = "Yieldspace"
#        config.num_trading_days = 3
#        config.num_blocks_per_day = 3
#        config.variable_apr = [0.05] * config.num_trading_days
#        simulator = sim_utils.get_simulator(config)  # initialize
#        simulator.run_simulation()  # run
#
#        self.assertLogs(level=logging.CRITICAL)
#        log_hyperdrive_crash_report(
#            "CLOSE_LONG",
#            InvalidTransaction("Message"),
#            1.23,
#            "0x0000000000000000000000000000000000000000",
#            PoolInfo(blockNumber=1234, timestamp=datetime.fromtimestamp(12345678)),
#            PoolConfig(contractAddress="0x0000000000000000000000000000000000000000"),
#        )
#        log_utils.close_logging()

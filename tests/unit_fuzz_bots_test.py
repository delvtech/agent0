"""System test for running unit fuzz test."""

from __future__ import annotations

import pytest

from agent0 import LocalChain
from agent0.hyperfuzz.unit_fuzz import (
    fuzz_long_short_maturity_values,
    fuzz_path_independence,
    fuzz_present_value,
    fuzz_profit_check,
)


class TestUnitFuzzBots:
    """Test pipeline from bots making trades to viewing the trades in the db."""

    # TODO split this up into different functions that work with tests
    # pylint: disable=too-many-locals, too-many-statements
    @pytest.mark.anvil
    def test_unit_fuzz_bots(
        self,
    ):
        """Tests the local fuzz bots pipeline."""
        # We only run for 1 iteration to ensure the pipeline works

        chain_config = LocalChain.Config(db_port=3333, chain_port=3334)
        num_trades = 2
        num_paths_checked = 1

        long_maturity_vals_epsilon = 1e-14
        short_maturity_vals_epsilon = 1e-9
        fuzz_long_short_maturity_values(
            num_trades, long_maturity_vals_epsilon, short_maturity_vals_epsilon, chain_config
        )

        lp_share_price_epsilon = 1e-14
        effective_share_reserves_epsilon = 1e-4
        present_value_epsilon = 1e-4
        fuzz_path_independence(
            num_trades,
            num_paths_checked,
            lp_share_price_epsilon=lp_share_price_epsilon,
            effective_share_reserves_epsilon=effective_share_reserves_epsilon,
            present_value_epsilon=present_value_epsilon,
            chain_config=chain_config,
        )

        fuzz_profit_check(chain_config)

        present_value_epsilon = 0.01
        fuzz_present_value(test_epsilon=present_value_epsilon, chain_config=chain_config)

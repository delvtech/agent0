"""System test for running fuzzing pipeline."""

from __future__ import annotations

import pytest

from agent0.core.hyperdrive.interactive import LocalHyperdrive
from agent0.hyperfuzz.system_fuzz import run_fuzz_bots


class TestLocalFuzzBots:
    """Test pipeline from bots making trades to viewing the trades in the db."""

    # TODO split this up into different functions that work with tests
    # pylint: disable=too-many-locals, too-many-statements
    @pytest.mark.anvil
    def test_local_fuzz_bots(
        self,
        fast_hyperdrive_fixture: LocalHyperdrive,
    ):
        """Tests the local fuzz bots pipeline."""
        # We only run for 1 iteration to ensure the pipeline works

        # Run without lp share price test
        run_fuzz_bots(
            fast_hyperdrive_fixture,
            check_invariance=True,
            raise_error_on_failed_invariance_checks=False,
            raise_error_on_crash=False,
            log_to_rollbar=False,
            run_async=False,
            random_advance_time=True,
            random_variable_rate=True,
            num_iterations=1,
            lp_share_price_test=False,
        )

        # Run with lp share price test
        run_fuzz_bots(
            fast_hyperdrive_fixture,
            check_invariance=True,
            raise_error_on_failed_invariance_checks=False,
            raise_error_on_crash=False,
            log_to_rollbar=False,
            run_async=False,
            random_advance_time=True,
            random_variable_rate=True,
            num_iterations=1,
            lp_share_price_test=True,
        )

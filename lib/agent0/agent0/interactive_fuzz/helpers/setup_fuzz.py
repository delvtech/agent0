"""Setup an interactive enfironment for fuzz testing."""
from __future__ import annotations

import logging

import numpy as np
from fixedpointmath import FixedPoint
from hyperlogs import setup_logging
from numpy.random._generator import Generator

from agent0.hyperdrive.interactive import InteractiveHyperdrive, LocalChain


def setup_fuzz(
    log_filename: str,
    chain_config: LocalChain.Config | None = None,
    log_to_stdout: bool = False,
    log_to_rollbar: bool = True,
    crash_log_level: int | None = None,
    fuzz_test_name: str | None = None,
    fees=True,
    var_interest=None,
) -> tuple[LocalChain, int, Generator, InteractiveHyperdrive]:
    """Setup the fuzz experiment.

    Arguments
    ---------
    log_filename: str
        Output location for the logging file,
        which will include state information if the test fails.
    chain_config: LocalChain.Config, optional
        Configuration options for the local chain.
    log_to_stdout: bool, optional
        If True, log to stdout in addition to a file.
        Defaults to False.
    log_to_rollbar: bool, optional
        If True, log errors rollbar. Defaults to True.
    crash_log_level: int | None, optional
        The log level to log crashes at. Defaults to critical.
    fuzz_test_name: str | None, optional
        The prefix to prepend to rollbar exception messages
    fees: bool, optional
        If False, will turn off fees when deploying hyperdrive. Defaults to True.
    var_interest: FixedPoint | None, optional
        The variable interest rate. Defaults to using the default variable interest rate
        defined in interactive hyperdrive.

    Returns
    -------
    tuple[str, LocalChain, int, Generator, InteractiveHyperdrive]
        A tuple containing:
            chain: LocalChain
                An instantiated LocalChain.
            random_seed: int
                The random seed used to construct the Generator.
            rng: `Generator <https://numpy.org/doc/stable/reference/random/generator.html>`_
                The numpy Generator provides access to a wide range of distributions, and stores the random state.
            interactive_hyperdrive: InteractiveHyperdrive
                An instantiated InteractiveHyperdrive object.
    """
    # pylint: disable=too-many-arguments
    setup_logging(
        log_filename=log_filename,
        delete_previous_logs=False,
        log_stdout=log_to_stdout,
    )

    # Setup local chain
    config = chain_config if chain_config else LocalChain.Config()
    chain = LocalChain(config=config)
    random_seed = np.random.randint(
        low=1, high=99999999
    )  # No seed, we want this to be random every time it is executed
    rng = np.random.default_rng(random_seed)

    # Parameters for pool initialization.
    # Using a day for checkpoint duration to speed things up
    if crash_log_level is None:
        crash_log_level = logging.CRITICAL

    crash_report_additional_info = {
        "fuzz_random_seed": random_seed,
        "fuzz_test_name": fuzz_test_name,
    }

    initial_pool_config = InteractiveHyperdrive.Config(
        preview_before_trade=True,
        checkpoint_duration=86400,
        log_to_rollbar=log_to_rollbar,
        rollbar_log_prefix=fuzz_test_name,
        crash_log_level=crash_log_level,
        crash_log_ticker=True,
        # Put this
        crash_report_additional_info=crash_report_additional_info,
    )
    if not fees:
        initial_pool_config.curve_fee = FixedPoint(0)
        initial_pool_config.flat_fee = FixedPoint(0)
        initial_pool_config.governance_lp_fee = FixedPoint(0)
        initial_pool_config.max_curve_fee = FixedPoint(0)
        initial_pool_config.max_flat_fee = FixedPoint(0)
        initial_pool_config.max_governance_lp_fee = FixedPoint(0)

    if var_interest is not None:
        initial_pool_config.initial_variable_rate = var_interest

    interactive_hyperdrive = InteractiveHyperdrive(chain, initial_pool_config)

    return chain, random_seed, rng, interactive_hyperdrive

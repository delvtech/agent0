"""Setup an interactive environment for fuzz testing."""

from __future__ import annotations

import logging

import numpy as np
from fixedpointmath import FixedPoint
from numpy.random import Generator

from agent0.core.hyperdrive.interactive import LocalChain, LocalHyperdrive


def setup_fuzz(
    chain_config: LocalChain.Config | None = None,
    log_to_rollbar: bool = True,
    crash_log_level: int | None = None,
    fuzz_test_name: str | None = None,
    curve_fee: FixedPoint | None = None,
    flat_fee: FixedPoint | None = None,
    governance_lp_fee: FixedPoint | None = None,
    governance_zombie_fee: FixedPoint | None = None,
    var_interest: FixedPoint | None = None,
) -> tuple[LocalChain, int, Generator, LocalHyperdrive]:
    """Setup the fuzz experiment.

    Arguments
    ---------
    chain_config: LocalChain.Config, optional
        Configuration options for the local chain.
    log_to_rollbar: bool, optional
        If True, log errors rollbar. Defaults to True.
    crash_log_level: int | None, optional
        The log level to log crashes at. Defaults to critical.
    fuzz_test_name: str | None, optional
        The prefix to prepend to rollbar exception messages
    curve_fee: FixedPoint | None, optional
        The curve fee for the test. Defaults to using the default fee
    flat_fee: FixedPoint | None, optional
        The flat fee for the test. Defaults to using the default fee
    governance_lp_fee: FixedPoint | None, optional
        The governance lp fee for the test. Defaults to using the default fee
    governance_zombie_fee: FixedPoint | None, optional
        The governance zombie fee for the test. Defaults to using the default fee
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
    # pylint: disable=too-many-locals

    # Parameters for pool initialization.
    # Using a day for checkpoint duration to speed things up
    if crash_log_level is None:
        crash_log_level = logging.CRITICAL

    # Randomly generate a seed to track it in crash reporting
    random_seed = np.random.randint(low=1, high=99999999)
    rng = np.random.default_rng(random_seed)

    crash_report_additional_info = {
        "fuzz_random_seed": random_seed,
        "fuzz_test_name": fuzz_test_name,
    }

    # Setup local chain
    config = chain_config if chain_config else LocalChain.Config()
    # We explicitly set some config parameters here
    config.preview_before_trade = True
    config.log_to_rollbar = log_to_rollbar
    config.rollbar_log_prefix = fuzz_test_name
    config.crash_log_level = crash_log_level
    config.crash_log_ticker = True
    config.crash_report_additional_info = crash_report_additional_info
    config.calc_pnl = False

    chain = LocalChain(config=config)

    initial_pool_config = LocalHyperdrive.Config(
        checkpoint_duration=60 * 60 * 24,  # 1 day
        # TODO calc_max_short doesn't work with a week position duration, setting to 30 days
        position_duration=60 * 60 * 24 * 30,  # 30 days
    )

    if curve_fee is not None:
        initial_pool_config.curve_fee = curve_fee
    if flat_fee is not None:
        initial_pool_config.flat_fee = flat_fee
    if governance_lp_fee is not None:
        initial_pool_config.governance_lp_fee = governance_lp_fee
    if governance_zombie_fee is not None:
        initial_pool_config.governance_zombie_fee = governance_zombie_fee

    if var_interest is not None:
        initial_pool_config.initial_variable_rate = var_interest

    interactive_hyperdrive = LocalHyperdrive(chain, initial_pool_config)

    return chain, random_seed, rng, interactive_hyperdrive

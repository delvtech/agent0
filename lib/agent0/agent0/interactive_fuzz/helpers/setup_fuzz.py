"""Setup an interactive enfironment for fuzz testing."""
from __future__ import annotations

import numpy as np
from hyperlogs import setup_logging
from numpy.random._generator import Generator

from agent0.hyperdrive.interactive import InteractiveHyperdrive, LocalChain


def setup_fuzz(log_filename: str) -> tuple[LocalChain, int, Generator, InteractiveHyperdrive]:
    """Setup the fuzz experiment.

    Arguments
    ---------
    log_filename: str
        Output location for the logging file,
        which will include state information if the test fails.

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
    setup_logging(
        log_filename=log_filename,
        delete_previous_logs=True,
        log_stdout=False,
    )

    # Setup local chain
    chain_config = LocalChain.Config()
    chain = LocalChain(config=chain_config)
    random_seed = np.random.randint(
        low=1, high=99999999
    )  # No seed, we want this to be random every time it is executed
    rng = np.random.default_rng(random_seed)

    # Parameters for pool initialization.
    initial_pool_config = InteractiveHyperdrive.Config(preview_before_trade=True)
    interactive_hyperdrive = InteractiveHyperdrive(chain, initial_pool_config)

    return chain, random_seed, rng, interactive_hyperdrive

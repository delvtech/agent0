"""Script for fuzzing profit values on immediately opening & closing a long or short."""

# Imports
import json
import logging
from dataclasses import asdict
from typing import Any, NamedTuple, Sequence

import numpy as np
from fixedpointmath import FixedPoint
from hyperlogs import ExtendedJSONEncoder, setup_logging
from numpy.random._generator import Generator

from agent0.hyperdrive.interactive import InteractiveHyperdrive, LocalChain


def main():
    # Setup the environment
    log_filename, chain, random_seed, rng, interactive_hyperdrive = setup_fuzz()

    # Get a random trade amount
    trade_amount = FixedPoint(
        scaled_value=int(
            np.floor(
                rng.uniform(
                    low=interactive_hyperdrive.hyperdrive_interface.pool_config.minimum_transaction_amount.scaled_value,
                    high=int(1e23),
                )
            )
        )
    )

    # Generate funded trading agent
    long_agent = interactive_hyperdrive.init_agent(base=trade_amount, eth=FixedPoint(100), name="alice")
    # Open a long
    open_long_event = long_agent.open_long(base=trade_amount)
    # Let some time pass, as long as it is less than a checkpoint
    chain.advance_time(
        rng.integers(low=0, high=interactive_hyperdrive.hyperdrive_interface.pool_config.checkpoint_duration - 1),
        create_checkpoints=True,
    )
    # Close the long
    close_long_event = long_agent.close_long(
        maturity_time=open_long_event.maturity_time, bonds=open_long_event.bond_amount
    )

    # Generate funded trading agent
    short_agent = interactive_hyperdrive.init_agent(base=trade_amount, eth=FixedPoint(100), name="bob")
    # Open a short
    # Set trade amount to the new wallet position (due to losing money from the previous open/close)
    trade_amount = short_agent.wallet.balance.amount
    open_short_event = short_agent.open_short(bonds=trade_amount)
    # Let some time pass, as long as it is less than a checkpoint
    chain.advance_time(
        rng.integers(low=0, high=interactive_hyperdrive.hyperdrive_interface.pool_config.checkpoint_duration - 1),
        create_checkpoints=True,
    )
    # Close the short
    close_short_event = short_agent.close_short(
        maturity_time=open_short_event.maturity_time, bonds=open_short_event.bond_amount
    )

    # Ensure that the prior trades did not result in a profit
    check_data = {
        "trade_amount": trade_amount,
        "long_agent": long_agent,
        "short_agent": short_agent,
        "long_events": {"open": open_long_event, "close": close_long_event},
        "short_events": {"open": open_short_event, "close": close_short_event},
    }
    if invariant_check_failed(
        check_data,
        random_seed,
        interactive_hyperdrive,
    ):
        raise AssertionError(f"Testing failed; see logs in {log_filename}")


def setup_fuzz() -> tuple[str, LocalChain, int, Generator, InteractiveHyperdrive]:
    """Setup the fuzz experiment.

    Arguments
    ---------
    argv: Sequence[str]
        A sequnce containing the uri to the database server and the test epsilon.

    Returns
    -------
    tuple[Args, str, LocalChain, int, Generator, InteractiveHyperdrive]
        A tuple containing:
            parsed_args: Args
                A dataclass containing the parsed command line arguments.
            log_filename: str
                Where the log files are stored.
            chain: LocalChain
                An instantiated LocalChain.
            random_seed: int
                The random seed used to construct the Generator.
            rng: `Generator <https://numpy.org/doc/stable/reference/random/generator.html>`_
                The numpy Generator provides access to a wide range of distributions, and stores the random state.
            interactive_hyperdrive: InteractiveHyperdrive
                An instantiated InteractiveHyperdrive object.
    """
    log_filename = ".logging/fuzz_profit_check.log"
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

    return log_filename, chain, random_seed, rng, interactive_hyperdrive


def invariant_check_failed(
    check_data,
    random_seed,
    interactive_hyperdrive,
):
    """Check the pool state invariants.

    Arguments
    ---------
    check_data: dict[str, Any]
        The trade data to check.
    random_seed: int
        Random seed used to run the experiment.
    interactive_hyperdrive: InteractiveHyperdrive
        An instantiated InteractiveHyperdrive object.

    Returns
    -------
    bool
        If true, at least one of the checks failed.
    """
    failed = False
    if check_data["long_events"]["close"].base_amount >= check_data["long_events"]["open"].base_amount:
        logging.critical(
            (
                "LONG: Amount returned on closing was too large.\n"
                "base_amount_returned=%s should not be >= base_amount_proided=%s"
            ),
            check_data["long_events"]["close"].base_amount,
            check_data["long_events"]["open"].base_amount,
        )
        failed = True
    if check_data["long_agent"].wallet.balance.amount >= check_data["trade_amount"]:
        logging.critical(
            "LONG: Agent made a profit when the should not have.\nagent_balance=%s should not be >= trade_amount=%s",
            check_data["long_agent"].wallet.balance.amount,
            check_data["trade_amount"],
        )
        failed = True
    if check_data["short_events"]["close"].base_amount >= check_data["short_events"]["open"].base_amount:
        logging.critical(
            (
                "SHORT: Amount returned on closing was too large.\n"
                "base_amount_returned=%s should not be >= base_amount_proided=%s"
            ),
            check_data["short_events"]["close"].base_amount,
            check_data["short_events"]["open"].base_amount,
        )
        failed = True
    if check_data["short_agent"].wallet.balance.amount >= check_data["trade_amount"]:
        logging.critical(
            "SHORT: Agent made a profit when the should not have.\nagent_balance=%s should not be >= trade_amount=%s",
            check_data["short_agent"].wallet.balance.amount,
            check_data["trade_amount"],
        )
        failed = True

    if failed:
        pool_state = interactive_hyperdrive.hyperdrive_interface.current_pool_state
        logging.info(
            "random_seed = %s\npool_config = %s\n\npool_info = %s\n\nlatest_checkpoint = %s\n\nadditional_info = %s",
            random_seed,
            json.dumps(asdict(pool_state.pool_config), indent=2, cls=ExtendedJSONEncoder),
            json.dumps(asdict(pool_state.pool_info), indent=2, cls=ExtendedJSONEncoder),
            json.dumps(asdict(pool_state.checkpoint), indent=2, cls=ExtendedJSONEncoder),
            json.dumps(
                {
                    "hyperdrive_address": interactive_hyperdrive.hyperdrive_interface.hyperdrive_contract.address,
                    "base_token_address": interactive_hyperdrive.hyperdrive_interface.base_token_contract.address,
                    "spot_price": interactive_hyperdrive.hyperdrive_interface.calc_spot_price(pool_state),
                    "fixed_rate": interactive_hyperdrive.hyperdrive_interface.calc_fixed_rate(pool_state),
                    "variable_rate": pool_state.variable_rate,
                    "vault_shares": pool_state.vault_shares,
                },
                indent=2,
                cls=ExtendedJSONEncoder,
            ),
        )

    return failed


if __name__ == "__main__":
    main()

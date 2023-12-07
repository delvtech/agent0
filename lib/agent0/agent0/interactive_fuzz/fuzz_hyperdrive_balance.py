"""Fuzz test to verify that if all of the funds are removed from Hyperdrive, there is no base left in the contract."""
from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict
from typing import NamedTuple, Sequence

from fixedpointmath import FixedPoint
from hyperlogs import ExtendedJSONEncoder

from agent0.hyperdrive.interactive import InteractiveHyperdrive, LocalChain
from agent0.interactive_fuzz import close_random_trades, generate_trade_list, open_random_trades, setup_fuzz


def main(argv: Sequence[str] | None = None):
    """Primary entrypoint.

    Arguments
    ---------
    argv: Sequence[str]
        The argv values returned from argparser.
    """
    # Setup the environment
    parsed_args = parse_arguments(argv)
    log_filename = ".logging/fuzz_hyperdrive_balance.log"
    chain, random_seed, rng, interactive_hyperdrive = setup_fuzz(log_filename)

    # Get initial vault shares
    pool_state = interactive_hyperdrive.hyperdrive_interface.get_hyperdrive_state()
    initial_vault_shares = pool_state.vault_shares

    # Generate a list of agents that execute random trades
    trade_list = generate_trade_list(parsed_args.num_trades, rng, interactive_hyperdrive)

    # Open some trades
    trade_events = open_random_trades(trade_list, chain, rng, interactive_hyperdrive, advance_time=True)

    # Close the trades
    close_random_trades(trade_events, rng)

    # Check the reserve amounts; they should be unchanged now that all of the trades are closed
    if invariant_check_failed(initial_vault_shares, random_seed, interactive_hyperdrive, chain):
        chain.cleanup()
        raise AssertionError(f"Testing failed; see logs in {log_filename}")
    chain.cleanup()


class Args(NamedTuple):
    """Command line arguments for the invariant checker."""

    num_trades: int


def namespace_to_args(namespace: argparse.Namespace) -> Args:
    """Converts argprase.Namespace to Args.

    Arguments
    ---------
    namespace: argparse.Namespace
        Object for storing arg attributes.

    Returns
    -------
    Args
        Formatted arguments
    """
    return Args(
        num_trades=namespace.num_trades,
    )


def parse_arguments(argv: Sequence[str] | None = None) -> Args:
    """Parses input arguments.

    Arguments
    ---------
    argv: Sequence[str]
        The argv values returned from argparser.

    Returns
    -------
    Args
        Formatted arguments
    """
    parser = argparse.ArgumentParser(description="Runs a loop to check Hyperdrive invariants at each block.")
    parser.add_argument(
        "--num_trades",
        type=int,
        default=5,
        help="The number of random trades to open.",
    )
    # Use system arguments if none were passed
    if argv is None:
        argv = sys.argv
    return namespace_to_args(parser.parse_args())


def invariant_check_failed(
    initial_vault_shares: FixedPoint,
    random_seed: int,
    interactive_hyperdrive: InteractiveHyperdrive,
    chain: LocalChain,
) -> bool:
    """Check the pool state invariants.

    Arguments
    ---------
    initial_vault_shares: FixedPoint
        The number of vault shares owned by the Hyperdrive pool when it was deployed.
    random_seed: int
        Random seed used to run the experiment.
    interactive_hyperdrive: InteractiveHyperdrive
        An instantiated InteractiveHyperdrive object.
    chain: LocalChain
        An instantiated LocalChain object.

    Returns
    -------
    bool
        If true, at least one of the checks failed.
    """
    failed = False
    pool_state = interactive_hyperdrive.hyperdrive_interface.get_hyperdrive_state()
    if pool_state.vault_shares != initial_vault_shares:
        logging.critical("vault_shares=%s != initial_vault_shares=%s", pool_state.vault_shares, initial_vault_shares)
        failed = True
    if pool_state.pool_info.share_reserves < pool_state.pool_config.minimum_share_reserves:
        logging.critical(
            "share_reserves=%s < minimum_share_reserves=%s",
            pool_state.pool_info.share_reserves,
            pool_state.pool_config.minimum_share_reserves,
        )
        failed = True

    if failed:
        dump_state_dir = chain.save_state(save_prefix="fuzz_hyperdrive_balance")
        logging.info(
            "random_seed = %s\npool_config = %s\n\npool_info = %s\n\nlatest_checkpoint = %s\n\nadditional_info = %s",
            random_seed,
            json.dumps(asdict(pool_state.pool_config), indent=2, cls=ExtendedJSONEncoder),
            json.dumps(asdict(pool_state.pool_info), indent=2, cls=ExtendedJSONEncoder),
            json.dumps(asdict(pool_state.checkpoint), indent=2, cls=ExtendedJSONEncoder),
            json.dumps(
                {
                    "dump_state_dir": dump_state_dir,
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

"""Script to maintain trade events on an external db."""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import time
from typing import NamedTuple, Sequence

from agent0 import Chain, Hyperdrive
from agent0.chainsync.exec import acquire_data, analyze_data


def main(argv: Sequence[str] | None = None) -> None:
    """Check Hyperdrive invariants each block.

    Arguments
    ---------
    argv: Sequence[str]
        A sequence containing the uri to the database server.
    """
    # pylint: disable=too-many-locals
    # pylint: disable=too-many-branches
    # pylint: disable=too-many-statements

    # Placeholder in case we have cli args
    _ = parse_arguments(argv)

    # TODO Abstract this method out for infra scripts
    # Get the rpc uri from env variable
    rpc_uri = os.getenv("RPC_URI", None)
    if rpc_uri is None:
        raise ValueError("RPC_URI is not set")

    chain = Chain(rpc_uri, Chain.Config(use_existing_postgres=True))

    # Get the registry address from artifacts
    registry_address = os.getenv("REGISTRY_ADDRESS", None)
    if registry_address is None:
        raise ValueError("REGISTRY_ADDRESS is not set")

    logging.info("Checking for new pools...")
    deployed_pools = Hyperdrive.get_hyperdrive_pools_from_registry(chain, registry_address)

    interfaces = [pool.interface for pool in deployed_pools]

    # TODO backfill pool info
    # TODO periodic backup of db and load if we find the backup file

    # Loop forever, running db once an hour
    while True:
        acquire_data(
            interfaces=list(interfaces),
            db_session=chain.db_session,
            lookback_block_limit=None,
            backfill=False,
        )
        analyze_data(
            interfaces=list(interfaces),
            db_session=chain.db_session,
            calc_pnl=True,
        )
        time.sleep(3600)


class Args(NamedTuple):
    """Command line arguments for the script."""


# Placeholder for cli args
def namespace_to_args(namespace: argparse.Namespace) -> Args:  # pylint: disable=unused-argument
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
    return Args()


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
    parser = argparse.ArgumentParser(description="Populates a database with trade events on hyperdrive.")

    # Use system arguments if none were passed
    if argv is None:
        argv = sys.argv

    return namespace_to_args(parser.parse_args())


if __name__ == "__main__":
    main()

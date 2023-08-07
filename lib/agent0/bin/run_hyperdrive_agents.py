"""Main script for running bots on Hyperdrive"""
from __future__ import annotations

import argparse
import logging
import warnings

from agent0.hyperdrive.exec import setup_experiment, trade_if_new_block
from eth_typing import BlockNumber


def parse_args():
    """Define and parse arguments from stdin"""
    parser = argparse.ArgumentParser(
        prog="run_hyperdrive_agents",
        description="Example execution script for running agents on Hyperdrive",
        epilog="See the agent0 README in https://github.com/delvtech/elf-simulations/ for more details",
    )
    parser.add_argument(
        "--develop",
        default=False,
        type=bool,
        help="If set, then bots will get funded automatically by minting Ethereum and Base",
    )
    return parser.parse_args()


def main():
    """Entrypoint to load all configurations and run agents."""
    # Set sane logging defaults to avoid spam from dependencies
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("web3").setLevel(logging.WARNING)
    warnings.filterwarnings("ignore", category=UserWarning, module="web3.contract.base_contract")
    # Grab stdin args, fund bots if requested
    args = parse_args()
    if args.develop: # we need to fund the bots


    # exposing the base_token_contract for debugging purposes.
    # pylint: disable=unused-variable
    web3, hyperdrive_contract, base_token_contract, environment_config, agent_accounts = setup_experiment()
    last_executed_block = BlockNumber(0)
    while True:
        last_executed_block = trade_if_new_block(
            web3,
            hyperdrive_contract,
            agent_accounts,
            environment_config.halt_on_errors,
            last_executed_block,
        )


if __name__ == "__main__":
    main()

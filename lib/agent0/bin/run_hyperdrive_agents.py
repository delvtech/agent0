"""Main script for running bots on Hyperdrive"""
from __future__ import annotations

import argparse
import logging
import warnings

from agent0.base.config import DEFAULT_USERNAME
from agent0.hyperdrive.create_and_fund_accounts import create_and_fund_user_account
from agent0.hyperdrive.exec import register_username, setup_experiment, trade_if_new_block
from agent0.hyperdrive.fund_bots import fund_bots
from dotenv import load_dotenv
from eth_typing import BlockNumber

# pylint: disable=unused-variable


def parse_args():
    """Define and parse arguments from stdin"""
    parser = argparse.ArgumentParser(
        prog="run_hyperdrive_agents",
        description="Example execution script for running agents on Hyperdrive",
        epilog="See the agent0 README in https://github.com/delvtech/elf-simulations/ for more details",
    )
    parser.add_argument(
        "--develop",
        action="store_true",
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
    if args.develop:  # setup env automatically & fund the bots
        # exposing the user account for debugging purposes
        user_account = create_and_fund_user_account()
        fund_bots()  # uses env variables created above as inputs
    # exposing the base_token_contract for debugging purposes.
    web3, base_token_contract, hyperdrive_contract, environment_config, eth_config, agent_accounts = setup_experiment()
    if not args.develop:
        if environment_config.username == DEFAULT_USERNAME:
            # Check for default name and exit if is default
            raise ValueError(
                "Default username detected, please update 'username' in "
                "lib/agent0/agent0/hyperdrive/config/runner_config.py"
            )
        # Set up postgres to write username to agent wallet addr
        # initialize the postgres session
        wallet_addrs = [str(agent.checksum_address) for agent in agent_accounts]
        register_username(eth_config.USERNAME_REGISTER_URL, wallet_addrs, environment_config.username)
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
    # load user dotenv variables
    load_dotenv("accounts.env")
    main()

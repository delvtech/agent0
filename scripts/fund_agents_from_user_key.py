"""Helper script to generate a random private key."""

import argparse
import asyncio
import logging
import os

from eth_account.account import Account

from agent0.core import build_account_config_from_env
from agent0.core.hyperdrive import HyperdriveAgent
from agent0.core.hyperdrive.utilities.run_bots import async_fund_agents
from agent0.ethpy import build_eth_config
from agent0.ethpy.hyperdrive import HyperdriveReadInterface, fetch_hyperdrive_addresses_from_uri
from agent0.hyperlogs import setup_logging

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="fund_agents_from_user_key",
        description="Script for funding agents from a user key, given a written env file.",
        epilog=("See https://github.com/delvtech/agent0/src/agent0/core/README.md for more details."),
    )
    parser.add_argument(
        "-u",
        "--user_key",
        nargs=1,
        help="The user's private key for funding agents.",
        action="store",
        default=[None],
    )
    parser.add_argument("-f", "--file", nargs=1, help="The env file to use.", action="store", default=["account.env"])
    parser.add_argument(
        "--host", nargs=1, help="The host to connect to the chain.", action="store", default=["localhost"]
    )
    args = parser.parse_args()

    env_file = args.file[0]
    user_key = args.user_key[0]
    host = args.host[0]
    if user_key is None:
        logging.warning("User key not provided, looking in environment file")

    # Funding contains its own logging as this is typically run from a script or in debug mode
    setup_logging(".logging/fund_accounts.log", log_stdout=True, delete_previous_logs=True)

    # This script only loads configs from env
    # Load config from env
    account_key_config = build_account_config_from_env(env_file, user_key)
    if account_key_config.USER_KEY == "":
        raise ValueError("User key not provided as argument, and was not found in env file")

    # Load eth config from env vars
    eth_config = build_eth_config()

    hyperdrive_address = fetch_hyperdrive_addresses_from_uri(os.path.join(eth_config.artifacts_uri, "addresses.json"))[
        "erc4626_hyperdrive"
    ]
    user_account = HyperdriveAgent(Account().from_key(account_key_config.USER_KEY))

    interface = HyperdriveReadInterface(eth_config, hyperdrive_address, read_retry_count=5)

    asyncio.run(async_fund_agents(interface, user_account, account_key_config))

    # User key could have been passed in here, rewrite the accounts env file
    if user_key is not None:
        with open(env_file, "w", encoding="UTF-8") as file:
            file.write(account_key_config.to_env_str())
            file.write(account_key_config.to_env_str())

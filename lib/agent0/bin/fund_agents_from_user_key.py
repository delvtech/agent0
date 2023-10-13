"""Helper script to generate a random private key."""

import argparse
import asyncio
import logging
import os

from agent0 import build_account_config_from_env
from agent0.hyperdrive.agents import HyperdriveAgent
from agent0.hyperdrive.exec import async_fund_agents
from eth_account.account import Account
from ethpy import EthConfig
from ethpy.hyperdrive import fetch_hyperdrive_address_from_uri

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="fund_agents_from_user_key",
        description="Script for funding agents from a user key, given a written env file.",
        epilog=(
            "See the README on https://github.com/delvtech/elf-simulations/agent0/ for more implementation details"
        ),
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

    # This script only loads configs from env
    # Load config from env
    account_key_config = build_account_config_from_env(env_file, user_key)
    if account_key_config.USER_KEY == "":
        raise ValueError("User key not provided as argument, and was not found in env file")

    eth_config = EthConfig(artifacts_uri="http://" + host + ":8080", rpc_uri="http://" + host + ":8545")

    contract_addresses = fetch_hyperdrive_address_from_uri(os.path.join(eth_config.artifacts_uri, "addresses.json"))
    user_account = HyperdriveAgent(Account().from_key(account_key_config.USER_KEY))

    asyncio.run(async_fund_agents(user_account, eth_config, account_key_config, contract_addresses))

    # User key could have been passed in here, rewrite the accounts env file
    if user_key is not None:
        with open(env_file, "w", encoding="UTF-8") as file:
            file.write(account_key_config.to_env_str())

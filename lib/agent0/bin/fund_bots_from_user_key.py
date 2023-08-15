"""Helper script to generate a random private key."""

import argparse
import logging
import os

from agent0 import build_account_config_from_env
from agent0.hyperdrive import fund_bots
from agent0.hyperdrive.agents import HyperdriveAgent
from eth_account.account import Account
from ethpy import build_eth_config
from ethpy.hyperdrive.addresses import fetch_hyperdrive_address_from_url

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="fund_bots_from_user_key",
        description="Script for funding bots from a user key, given a written env file.",
        epilog=(
            "Run the script with a user's private key as argument to include it in the output."
            "Make sure you set the config variables in lib/agent0/agent0/hyperdrive/config/runner_config.py "
            "before running this script."
            "See the README on https://github.com/delvtech/elf-simulations/eth_bots/ for more implementation details"
        ),
    )
    parser.add_argument(
        "-u",
        "--user_key",
        nargs=1,
        help="The user's private key for funding bots.",
        action="store",
        default=[None],
    )
    parser.add_argument("-f", "--file", nargs=1, help="The env file to use.", action="store", default=["account.env"])
    args = parser.parse_args()

    env_file = args.file[0]
    user_key = args.user_key[0]
    if user_key is None:
        logging.warning("User key not provided, looking in environment file")

    # This script only loads configs from env
    # Load config from env
    account_key_config = build_account_config_from_env(env_file, user_key)
    if account_key_config.USER_KEY == "":
        raise ValueError("User key not provided as argument, and was not found in env file")

    eth_config = build_eth_config()
    contract_addresses = fetch_hyperdrive_address_from_url(os.path.join(eth_config.ARTIFACTS_URL, "addresses.json"))
    user_account = HyperdriveAgent(Account().from_key(account_key_config.USER_KEY))

    # TODO We hardcode ERC20Mintable here as the base contract name, since we don't have access to env_config here
    fund_bots(user_account, eth_config, "ERC20Mintable", account_key_config, contract_addresses)

    # User key could have been passed in here, rewrite the accounts env file
    if user_key is not None:
        with open(env_file, "w", encoding="UTF-8") as file:
            file.write(account_key_config.to_env_str())

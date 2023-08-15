"""Helper script to generate a random private key."""
import argparse

from agent0.hyperdrive.fund_bots import fund_bots
from agent0.hyperdrive.generate_env import generate_env

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="populate_env",
        description="Script for generating a .env file for eth_bots.",
        epilog=(
            "Run the script with a user's private key as argument to include it in the output."
            "Make sure you set the config variables in lib/agent0/agent0/hyperdrive/config/runner_config.py "
            "before running this script."
            "See the README on https://github.com/delvtech/elf-simulations/eth_bots/ for more implementation details"
        ),
    )
    parser.add_argument("user_key", type=str, help="The user's private key for funding bots.")
    args = parser.parse_args()
    # TODO how do you define the configuration before running this script?
    account_config = generate_env(str(args.user_key))
    fund_bots(account_config)
    print(account_config.to_env_str())

"""Helper script to generate a random private key."""
import argparse

from agent0.hyperdrive.fund_bots import fund_bots
from agent0.hyperdrive.generate_env import generate_env, set_env

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
    env_str = generate_env(str(args.user_key))
    set_env(env_str)
    fund_bots()  # uses env variables created above as inputs
    print(env_str)

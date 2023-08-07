"""Helper script to generate a random private key."""
import argparse
import json
import os

import numpy as np
from agent0.base.make_key import make_private_key
from agent0.hyperdrive.config import get_eth_bots_config


def generate_env(user_key: str) -> str:
    """Primary execution pipeline"""
    environment_config, agent_config = get_eth_bots_config()
    rng = np.random.default_rng(environment_config.random_seed)
    agent_private_keys = []
    agent_base_budgets = []
    agent_eth_budgets = []
    for agent_info in agent_config:
        for _ in range(agent_info.number_of_agents):
            agent_private_keys.append(make_private_key())
            agent_base_budgets.append(agent_info.base_budget.sample_budget(rng).scaled_value)
            agent_eth_budgets.append(agent_info.eth_budget.sample_budget(rng).scaled_value)
    env_str = ""
    if user_key is not None:
        env_str += "export USER_KEY='" + user_key + "'" + "\n"
    env_str += "export AGENT_KEYS='" + json.dumps(agent_private_keys) + "'" + "\n"
    env_str += "export AGENT_BASE_BUDGETS='" + json.dumps(agent_base_budgets) + "'" + "\n"
    env_str += "export AGENT_ETH_BUDGETS='" + json.dumps(agent_eth_budgets) + "'" + "\n"
    return env_str


def set_env(env_string: str) -> None:
    """Set the user environment according to the string provided

    env_string : str
        environment string as it would look in a `.env` file.
        EXPORT statements are converted and executed
    """
    for env_line in env_string.splitlines():
        # if there is anything in the line after stripping empty spaces
        # and if the env line is setting a variable
        if env_line.strip() and env_line.startswith("export "):
            key_value = env_line.replace("export ", "").split("=")
            if len(key_value) == 2:
                key, value = key_value
                value = value.strip("\"'")  # strip quotes
                os.environ[key] = value


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="populate_env",
        description="Script for generating a .env file for eth_bots.",
        epilog=(
            "Run the script with a user's private key as argument to include it in the output."
            "See the README on https://github.com/delvtech/elf-simulations/eth_bots/ for more implementation details"
        ),
    )
    parser.add_argument("user_key", type=str, help="The user's private key for funding bots.")
    args = parser.parse_args()
    print_str = generate_env(str(args.user_key))
    print(print_str)

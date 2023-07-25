"""Helper script to generate a random private key."""

import argparse
import json
import os

import numpy as np
from eth_account import Account
from eth_utils.conversions import to_bytes
from eth_utils.crypto import keccak
from eth_utils.curried import text_if_str

from examples.eth_bots.eth_bots_config import get_eth_bots_config

# pylint: disable=invalid-name
# pylint: disable=protected-access


def make_key() -> str:
    """Make a private key"""
    extra_key_bytes = text_if_str(to_bytes, "SOME STR")
    key_bytes = keccak(os.urandom(32) + extra_key_bytes)
    key = Account()._parsePrivateKey(key_bytes)
    return str(key)


if __name__ == "__main__":
    # get keys & RPC url from the environment
    parser = argparse.ArgumentParser(
        prog="make_private_key",
        description="Script for generating a private key",
        epilog=(
            "See the README on https://github.com/delvtech/elf-simulations/eth_bots/ for more implementation details"
        ),
    )
    parser.add_argument(
        "--use_config",
        help="If True, generate keys per config agent; else just generate one key.",
        action="store_true",
    )
    use_config: bool = bool(parser.parse_args().use_config)
    if use_config:
        environment_config, agent_config = get_eth_bots_config()
        rng = np.random.default_rng(environment_config.random_seed)
        agent_private_keys = []
        agent_base_budgets = []
        agent_eth_budgets = []
        for agent_info in agent_config:
            for policy_instance_index in range(agent_info.number_of_agents):
                agent_private_keys.append(make_key())
                agent_base_budgets.append(agent_info.base_budget.sample_budget(rng).scaled_value)
                agent_eth_budgets.append(agent_info.eth_budget.sample_budget(rng).scaled_value)
        print("export AGENT_KEYS='" + json.dumps(agent_private_keys) + "'")
        print("export AGENT_BASE_BUDGETS='" + json.dumps(agent_base_budgets) + "'")
        print("export AGENT_ETH_BUDGETS='" + json.dumps(agent_eth_budgets) + "'")
    else:
        print("export AGENT_KEYS='[\"" + make_key() + "\"]'")

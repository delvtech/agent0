"""Defines the accounts configuration from env vars."""
from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass

import numpy as np
from dotenv import load_dotenv

from .base.config import AgentConfig, Budget
from .base.make_key import make_private_key


@dataclass
class AccountKeyConfig:
    """The account config dataclass

    Attributes
    ----------
    USER_KEY: str | None
        The user's private key
    AGENT_KEYS: list[str]
        A list of agent private keys
    AGENT_ETH_BUDGETS: list[int]
        A list of agent eth budgets
    AGENT_BASE_BUDGETS: list[int]
        A list of agent base budgets
    """

    # default values for local contracts
    # Matching environment variables to search for
    # pylint: disable=invalid-name
    USER_KEY: str | None
    AGENT_KEYS: list[str]
    AGENT_ETH_BUDGETS: list[int]
    AGENT_BASE_BUDGETS: list[int]

    def to_env_str(self) -> str:
        """Convert the configuration dataclass to a string, ready to be written as an env file

        Returns
        -------
        str
            The env string, ready to be written as an env file
        """
        env_str = ""
        if self.USER_KEY is None:
            env_str += "USER_KEY=\n"
        else:
            env_str += "USER_KEY='" + self.USER_KEY + "'" + "\n"
        env_str += "AGENT_KEYS='" + json.dumps(self.AGENT_KEYS) + "'" + "\n"
        env_str += "AGENT_BASE_BUDGETS='" + json.dumps(self.AGENT_BASE_BUDGETS) + "'" + "\n"
        env_str += "AGENT_ETH_BUDGETS='" + json.dumps(self.AGENT_ETH_BUDGETS) + "'" + "\n"
        return env_str


def initialize_accounts(
    agent_config: list[AgentConfig], env_file: str | None = None, random_seed: int = 1, develop: bool = False
) -> AccountKeyConfig:
    """
    Build or load an accounts environment file.
    If it doesn't exist, create it based on agent_config.
    (if develop is off, print instructions on adding in user private key and running script to fund bots).
    If it does exist, read it in and use it.
    """
    # Default location
    if env_file is None:
        env_file = "account.env"

    if not os.path.exists(env_file):
        logging.info("Creating %s", env_file)
        # Create AccountKeyConfig from agent config
        account_key_config = build_account_key_config_from_agent_config(agent_config, random_seed)
        # Create file
        with open(env_file, "w", encoding="UTF-8") as file:
            file.write(account_key_config.to_env_str())
        if not develop:
            print(
                f"Account key config written {env_file}. "
                "Run the following command to fund the accounts, then rerun this script."
            )
            # Different commands depending on if default env file is used
            if env_file == "account.env":
                print("python lib/agent0/bin/fund_bots_from_user_key.py -u <user_private_key>")
            else:
                print(f"python lib/agent0/bin/fund_bots_from_user_key.py -u <user_private_key> -f {env_file}")
            # Clean exit
            sys.exit(0)
    else:
        logging.info("Loading %s", env_file)
        # Ensure account_config matches up with env_file
        # TODO this is where we would read state of bot from chain
        account_key_config = build_account_config_from_env(env_file)
        num_total_bots = sum(agent.number_of_agents for agent in agent_config)
        if num_total_bots != len(account_key_config.AGENT_KEYS):
            raise ValueError("Number of bots in agent config does not match number of bots in env file")

    return account_key_config


def build_account_key_config_from_agent_config(
    agent_configs: list[AgentConfig], random_seed: int, user_key: str | None = None
) -> AccountKeyConfig:
    """Build an Account Config from a provided agent config.

    Arguments
    --------
    user_key: str
        The provided user key to use
    agent_configs: list[AgentConfig]
        The provided agent configs

    Returns
    -------
    AccountConfig
        Config settings required to connect to the eth node
    """
    rng = np.random.default_rng(random_seed)
    agent_private_keys = []
    agent_base_budgets = []
    agent_eth_budgets = []
    for agent_info in agent_configs:
        for _ in range(agent_info.number_of_agents):
            agent_private_keys.append(make_private_key())

            if isinstance(agent_info.eth_budget_wei, Budget):
                agent_eth_budgets.append(agent_info.eth_budget_wei.sample_budget(rng).scaled_value)
            elif isinstance(agent_info.eth_budget_wei, int):
                agent_eth_budgets.append(agent_info.eth_budget_wei)
            else:
                raise ValueError(f"Unknown eth_budget_wei type: {type(agent_info.eth_budget_wei)}")

            if isinstance(agent_info.base_budget_wei, Budget):
                agent_base_budgets.append(agent_info.base_budget_wei.sample_budget(rng).scaled_value)
            elif isinstance(agent_info.base_budget_wei, int):
                agent_base_budgets.append(agent_info.base_budget_wei)
            else:
                raise ValueError(f"Unknown base_budget_wei type: {type(agent_info.base_budget_wei)}")

    return AccountKeyConfig(
        USER_KEY=user_key,
        AGENT_KEYS=agent_private_keys,
        AGENT_ETH_BUDGETS=agent_eth_budgets,
        AGENT_BASE_BUDGETS=agent_base_budgets,
    )


def build_account_config_from_env(env_file: str | None = None, user_key: str | None = None) -> AccountKeyConfig:
    """Build an Account Config from environmental variables.

    Returns
    -------
    AccountConfig
        Config settings required to connect to the eth node
    """
    # Default location
    if env_file is None:
        env_file = "account.env"

    # Look for and load local config if it exists
    load_dotenv(env_file)

    if user_key is None:
        # USER PRIVATE KEY
        user_key = os.environ.get("USER_KEY")
        if user_key is None:
            raise ValueError("USER_KEY environment variable must be set")

    # LIST OF AGENT PRIVATE KEYS
    # NOTE: The env var should follow the JSON specification: https://www.json.org/json-en.html
    # for example, `export AGENT_KEYS='["foo", "bar"]'`
    key_string = os.environ.get("AGENT_KEYS")
    if key_string is None:
        raise ValueError("AGENT_KEYS environment variable must be set")
    agent_keys = json.loads(key_string)
    # AGENT ETHEREUM FUNDING AMOUNTS
    eth_budget_string = os.environ.get("AGENT_ETH_BUDGETS")
    if eth_budget_string is None:
        raise ValueError("AGENT_ETH_BUDGETS environment variable must be set")
    agent_eth_budgets = [int(budget) for budget in json.loads(eth_budget_string)]
    # AGENT BASE FUNDING AMOUNTS
    base_budget_string = os.environ.get("AGENT_BASE_BUDGETS")
    if base_budget_string is None:
        raise ValueError("AGENT_BASE_BUDGETS environment variable must be set")
    agent_base_budgets = [int(budget) for budget in json.loads(base_budget_string)]
    if len(agent_keys) != len(agent_eth_budgets) or len(agent_keys) != len(agent_base_budgets):
        raise AssertionError(f"{len(agent_keys)=} must equal {len(agent_eth_budgets)=} and {len(agent_base_budgets)=}")

    return AccountKeyConfig(
        USER_KEY=user_key,
        AGENT_KEYS=agent_keys,
        AGENT_ETH_BUDGETS=agent_eth_budgets,
        AGENT_BASE_BUDGETS=agent_base_budgets,
    )

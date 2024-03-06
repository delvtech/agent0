"""Setup helper function for running eth agent experiments."""

from __future__ import annotations

import numpy as np

from agent0.core import AccountKeyConfig
from agent0.core.base.config import AgentConfig, EnvironmentConfig
from agent0.core.hyperdrive import HyperdriveAgent
from agent0.core.hyperdrive.crash_report import setup_hyperdrive_crash_report_logging
from agent0.ethpy.hyperdrive import HyperdriveReadInterface
from agent0.hyperlogs import setup_logging

from .get_agent_accounts import get_agent_accounts


def setup_experiment(
    environment_config: EnvironmentConfig,
    agent_config: list[AgentConfig],
    account_key_config: AccountKeyConfig,
    interface: HyperdriveReadInterface,
) -> list[HyperdriveAgent]:
    """Get agents according to provided config, provide eth, base token and approve hyperdrive.

    Arguments
    ---------
    environment_config: EnvironmentConfig
        The agent's environment configuration.
    agent_config: list[AgentConfig]
        The list of agent configurations.
    account_key_config: AccountKeyConfig
        Configuration linking to the env file for storing private keys and initial budgets.
    interface: HyperdriveReadInterface
        An interface for Hyperdrive with contracts deployed on any chain with an RPC url.

    Returns
    -------
    list[HyperdriveAgent]
        A list of HyperdriveAgent objects that contain a wallet address and Agent for determining trades
    """
    # this is the global rng object that generates child rng objects for each agent
    # random number generator should be used everywhere so that the experiment is repeatable
    # rng stores the state of the random number generator, so that we can pause and restart experiments from any point
    global_rng = np.random.default_rng(environment_config.global_random_seed)
    # setup logging
    setup_logging(
        log_filename=environment_config.log_filename,
        max_bytes=environment_config.max_bytes,
        log_level=environment_config.log_level,
        delete_previous_logs=environment_config.delete_previous_logs,
        log_stdout=environment_config.log_stdout,
        log_format_string=environment_config.log_formatter,
    )
    setup_hyperdrive_crash_report_logging()
    # load agent policies
    # rng is shared by the agents and can be accessed via `agent_accounts[idx].policy.rng`
    agent_accounts = get_agent_accounts(
        interface.web3,
        agent_config,
        account_key_config,
        interface.base_token_contract,
        interface.hyperdrive_contract.address,
        global_rng,
    )
    return agent_accounts

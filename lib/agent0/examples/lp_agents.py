"""Script to showcase running default implemented agents."""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from agent0 import initialize_accounts
from agent0.base.config import AgentConfig, EnvironmentConfig
from agent0.hyperdrive.exec import run_agents
from agent0.hyperdrive.policies import Zoo

# from ethpy.hyperdrive import fetch_hyperdrive_address_from_uri
from eth_typing import URI
from ethpy import EthConfig
from ethpy.eth_config import build_eth_config
from fixedpointmath import FixedPoint

# Define the unique env filename to use for this script
ENV_FILE = "hyperdrive_agents.account.env"
# Host of docker services
HOST = "localhost"
# Username binding of bots
USERNAME = "changeme"
# Run this file with this flag set to true to close out all open positions
LIQUIDATE = False
RESTART_DOCKER = True

os.environ["DEVELOP"] = "true"


def check_docker(restart: bool = False):
    """Check whether docker is running, and if not, start it, otherwise optionally restart it."""
    home_infra = Path(os.path.expanduser("~")) / "code" / "infra"
    if os.path.exists(home_infra):
        infra_folder = home_infra
    else:
        infra_folder = Path("/code/infra")
    dockerps = _get_docker_ps_and_log()
    number_of_running_services = dockerps.count("\n") - 1
    if number_of_running_services > 0:
        preamble_str = f"Found {number_of_running_services} running services"
        if restart:
            _start_docker(f"{preamble_str}, restarting docker...", infra_folder)
        else:
            logging.info("%s, using them.", preamble_str)
    else:
        _start_docker("Starting docker.", infra_folder)
    dockerps = os.popen("docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'").read()
    logging.info(dockerps)


def _start_docker(startup_str: str, infra_folder: Path):
    logging.info(startup_str)
    _run_cmd(infra_folder, " && docker-compose down -v", "Shut down docker in ")
    _run_cmd(
        infra_folder,
        " && docker images | awk '(NR>1) && ($2!~/none/) && ($1 ~ /^ghcr\\.io\\//) {print $1\":\"$2}' | xargs -L1 docker pull",
        "Updated docker in ",
    )
    _run_cmd(infra_folder, " && docker-compose up -d", "Started docker in ")


def _run_cmd(infra_folder: Path, cmd: str, timing_str: str):
    result = time.time()
    os.system(f"cd {infra_folder}{cmd}")
    formatted_str = f"{timing_str}{time.time() - result:.2f}s"  # don't use lazy % formatting, to get nice :.2f format
    logging.info(formatted_str)
    return result


def _get_docker_ps_and_log() -> str:
    dockerps = os.popen("docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'").read()
    logging.info(dockerps)
    return dockerps


check_docker(restart=True)

# Build configuration
eth_config = EthConfig(artifacts_uri=f"http://{HOST}:8080", rpc_uri=f"http://{HOST}:8545")

env_config = EnvironmentConfig(
    delete_previous_logs=False,
    halt_on_errors=True,
    log_filename="agent0-logs",
    log_level=logging.INFO,
    log_stdout=True,
    random_seed=1234,
    database_api_uri=f"http://{HOST}:5002",
    username=USERNAME,
)

agent_config: list[AgentConfig] = [
    AgentConfig(
        policy=Zoo.LPandArb,
        number_of_agents=1,
        slippage_tolerance=None,  # No slippage tolerance for arb bot
        # Fixed budgets
        base_budget_wei=FixedPoint(50_000).scaled_value,  # 50k base
        eth_budget_wei=FixedPoint(1).scaled_value,  # 1 base
        policy_config=Zoo.LPandArb.Config(
            lp_portion=FixedPoint("0.5"),  # LP with 50% of capital
            high_fixed_rate_thresh=FixedPoint(0.06),  # Upper fixed rate threshold
            low_fixed_rate_thresh=FixedPoint(0.04),  # Lower fixed rate threshold
        ),
    ),
    AgentConfig(
        policy=Zoo.random,
        number_of_agents=1,
        slippage_tolerance=FixedPoint("0.0001"),
        # Fixed budget
        base_budget_wei=FixedPoint(50_000).scaled_value,  # 50k base
        eth_budget_wei=FixedPoint(1).scaled_value,  # 1 base
        policy_config=Zoo.random.Config(trade_chance=FixedPoint("0.8")),
    ),
]

# not needed unless you're interacting directly with the smart contract, outside of the bot framework
# addresses = fetch_hyperdrive_address_from_uri(os.path.join(eth_config.artifacts_uri, "addresses.json"))

# Build accounts env var
# This function writes a user defined env file location.
# If it doesn't exist, create it based on agent_config
# (If os.environ["DEVELOP"] is False, will clean exit and print instructions on how to fund agent)
# If it does exist, read it in and use it
account_key_config = initialize_accounts(agent_config, env_file=ENV_FILE, random_seed=env_config.random_seed)
eth_config = build_eth_config()
eth_config.rpc_uri = URI("http://localhost:8546")

# Run agents
run_agents(
    env_config,
    agent_config,
    account_key_config,
    eth_config=eth_config,
    liquidate=LIQUIDATE,
)

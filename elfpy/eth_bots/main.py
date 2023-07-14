"""Main script for running bots on Hyperdrive"""
from __future__ import annotations

import logging
import os

import numpy as np

from fixedpointmath import FixedPoint
from web3.contract.contract import Contract

from elfpy import eth, hyperdrive_interface
from elfpy.agents import Agent
from elfpy.agents.load_agent_policies import load_builtin_policies, parse_folder_for_classes, get_invoked_path
from elfpy.utils import logs

from .bot_config import bot_config

def run_main(): # FIXME: Move much of this out of main

    # setup config
    config = bot_config
    rng = np.random.default_rng(config.random_seed)

    # setup logging
    logs.setup_logging(
        log_filename=config.log_filename,
        max_bytes=config.max_bytes,
        log_level=config.log_level,
        delete_previous_logs=config.delete_previous_logs,
        log_stdout=config.log_stdout,
        log_format_string=config.log_formatter,
    )
    
    # point to chain env
    web3 = eth.web3_setup.initialize_web3_with_http_provider(config.rpc_url)
    _ = web3.provider.make_request(method="anvil_reset", params=[])

    # setup base contract interface
    hyperdrive_abis = eth.abi.load_all_abis(BUILD_FOLDER)
    addresses = hyperdrive_interface.fetch_hyperdrive_address_from_url(os.path.join(config.artifacts_url, "addresses.json"))

    # set up the ERC20 contract for minting base tokens
    base_token_contract: Contract = web3.eth.contract(abi=hyperdrive_abis[BASE_ABI], address=addresses.base_token)

    # setup agents
    # load agent policies
    all_policies = load_builtin_policies()
    custom_policies_path = os.path.join(get_invoked_path(), "custom_policies")
    all_policies.update(parse_folder_for_classes(custom_policies_path))
    # make a list of agents
    agents: dict[str, tuple[eth.accounts.EthAccount, Agent]] = {}
    num_agents_so_far = []
    for agent_info in config.agents:
        kwargs = agent_info.init_kwargs
        kwargs["rng"] = rng
        kwargs["budget"] = agent_info.budget.sample_budget(rng)
        for policy_instance_index in range(agent_info.number_of_bots):
            agent_count = policy_instance_index + sum(num_agents_so_far)
            policy = all_policies[agent_info.name](**kwargs)
            agent = Agent(wallet_address=eth_account.checksum_address, policy=policy)
            eth_account = eth.accounts.EthAccount(extra_entropy=str(agent_count))
            # fund test account with ether
            rpc_response = eth.set_anvil_account_balance(web3, eth_account.checksum_address, int(web3.to_wei(1000, "ether")))
            # fund test account by minting with the ERC20 base account
            tx_receipt = eth.smart_contract_transact(web3, base_token_contract, "mint", eth_account.checksum_address, kwargs["budget"].scaled_value)
            agents[f"agent_{eth_account.checksum_address}"] = (eth_account, agent)
        num_agents_so_far.append(agent_info.number_of_bots)
    logging.info("Added %d agents", sum(num_agents_so_far))

    # hyperdrive into the sunset
    run_trade_loop(agents)
 

def run_trade_loop(agents: dict[str, tuple[eth.accounts.EthAccount, Agent]]):
    while True:
        try:
            for agent in agents:
                # do trades
        except:
            # deliver crash report
            # raise err if config.fail else continue

if __name__ == "__main__":
    HYPERDRIVE_ABI = "IHyperdrive"
    BASE_ABI = "ERC20Mintable"
    BUILD_FOLDER = "./hyperdrive_solidity/.build"
    run_main()

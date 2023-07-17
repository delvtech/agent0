"""Main script for running bots on Hyperdrive"""
from __future__ import annotations

import logging
import os
from datetime import datetime

import numpy as np
from web3.contract.contract import Contract

from elfpy import eth, hyperdrive_interface
from elfpy import types as elftypes
from elfpy.agents import Agent
from elfpy.agents.load_agent_policies import get_invoked_path, load_builtin_policies, parse_folder_for_classes
from elfpy.markets.hyperdrive import MarketActionType
from elfpy.time import time as elftime
from elfpy.utils import logs

from .bot_config import bot_config


def run_main(hyperdrive_abi, base_abi, build_folder):  # FIXME: Move much of this out of main
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
    web3 = eth.web3_setup.initialize_web3_with_http_provider(config.rpc_url, reset_provider=False)

    # setup base contract interface
    hyperdrive_abis = eth.abi.load_all_abis(build_folder)
    addresses = hyperdrive_interface.fetch_hyperdrive_address_from_url(
        os.path.join(config.artifacts_url, "addresses.json")
    )

    # set up the ERC20 contract for minting base tokens
    base_token_contract: Contract = web3.eth.contract(abi=hyperdrive_abis[base_abi], address=addresses.base_token)

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
            rpc_response = eth.set_anvil_account_balance(
                web3, eth_account.checksum_address, int(web3.to_wei(1000, "ether"))
            )
            print(f"{rpc_response=}")  # FIXME: raise issue on failure
            # fund test account by minting with the ERC20 base account
            tx_receipt = eth.smart_contract_transact(
                web3, base_token_contract, "mint", eth_account.checksum_address, kwargs["budget"].scaled_value
            )
            print(f"{tx_receipt=}")  # FIXME: raise issue on failure
            agents[f"agent_{eth_account.checksum_address}"] = (eth_account, agent)
        num_agents_so_far.append(agent_info.number_of_bots)
    logging.info("Added %d agents", sum(num_agents_so_far))
    # set up hyperdrive contract
    hyperdrive_contract: Contract = web3.eth.contract(
        abi=hyperdrive_abis[hyperdrive_abi],
        address=addresses.mock_hyperdrive,
    )

    # Run trade loop
    # """Hyperdrive forever into the sunset"""
    trade_streak = 0
    last_executed_block = 0
    while True:
        latest_block = web3.eth.get_block("latest")
        block_number = latest_block.number
        block_timestamp = latest_block.timestamp
        if block_number > last_executed_block:
            # log and show block info
            if not hasattr(latest_block, "base_fee"):
                raise ValueError("latest block does not have base_fee")
            base_fee = getattr(latest_block, "base_fee") / 1e9
            logging.info(
                "Block number: %d, Block time: %s, Trades without crashing: %s, base_fee: %s",
                block_number,
                datetime.fromtimestamp(block_timestamp),
                trade_streak,
                base_fee,
            )
            # get latest market
            hyperdrive_market = hyperdrive_interface.get_hyperdrive_market(web3, hyperdrive_contract)
            try:
                for agent_name, (eth_account, agent) in agents.items():
                    # do_policy
                    trades: list[elftypes.Trade] = agent.get_trades(market=hyperdrive_market)
                    for trade_object in trades:
                        # do_trade
                        trade_amount: int = trade_object.trade.trade_amount.scaled_value
                        # check that the hyperdrive contract has enough base approved for the trade
                        hyperdrive_allowance = eth.smart_contract_read(
                            base_token_contract, "allowance", eth_account.checksum_address, hyperdrive_contract.address
                        )
                        if hyperdrive_allowance < trade_amount:
                            tx_receipt = eth.smart_contract_transact(
                                web3,
                                base_token_contract,
                                "approve",
                                eth_account.checksum_address,
                                hyperdrive_contract.address,
                                int(50e21),  # 50k base
                            )
                        maturity_time = (
                            trade_object.trade.mint_time
                            + hyperdrive_market.position_duration.years * elftime.TimeUnit.SECONDS
                        )
                        # TODO: allow for min_output
                        min_output = 0
                        as_underlying = True
                        match trade_object.trade.action_type:
                            case MarketActionType.OPEN_LONG:
                                eth.smart_contract_transact(
                                    web3,
                                    hyperdrive_contract,
                                    "openLong",
                                    trade_amount,
                                    min_output,
                                    eth_account.checksum_address,
                                    as_underlying,
                                )
                            case MarketActionType.CLOSE_LONG:
                                min_output = 0
                                eth.smart_contract_transact(
                                    web3,
                                    hyperdrive_contract,
                                    "closeLong",
                                    maturity_time,
                                    trade_amount,
                                    min_output,
                                    eth_account.checksum_address,
                                    as_underlying,
                                )
                        # FIXME: TODO: update wallet
                        trade_streak += 1
            except Exception as exc:  # we want to catch all exceptions (pylint: disable=broad-exception-caught)
                if config.halt_on_errors:
                    raise exc
                else:
                    trade_streak = 0
                    # FIXME: TODO: deliver crash report
                    continue


if __name__ == "__main__":
    HYPERDRIVE_ABI = "IHyperdrive"
    BASE_ABI = "ERC20Mintable"
    BUILD_FOLDER = "./hyperdrive_solidity/.build"
    run_main(HYPERDRIVE_ABI, BASE_ABI, BUILD_FOLDER)

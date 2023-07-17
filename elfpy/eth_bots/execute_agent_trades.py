"""Main script for running bots on Hyperdrive"""
from __future__ import annotations

import logging
from datetime import datetime

from web3 import Web3
from web3.contract.contract import Contract

from elfpy import eth, hyperdrive_interface
from elfpy import types as elftypes
from elfpy.agents import Agent
from elfpy.markets.hyperdrive import MarketActionType
from elfpy.time import time as elftime

from .config.bot_config import BotConfig


def execute_agent_trades(
    config: BotConfig,
    web3: Web3,
    base_token_contract: Contract,
    hyperdrive_contract: Contract,
    agents: dict[str, tuple[eth.accounts.EthAccount, Agent]],
    last_executed_block: int,
    trade_streak: int,
):
    """Hyperdrive forever into the sunset"""
    latest_block = web3.eth.get_block("latest")
    block_number = latest_block.number
    block_timestamp = latest_block.timestamp
    if block_number > last_executed_block:
        # TODO: DELETE BASE_FEE IF IT IS NOT USED ELSEWHERE
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
                    # TODO: allow for min_output
                    min_output = 0
                    as_underlying = True
                    maturity_time = (
                        trade_object.trade.mint_time
                        + hyperdrive_market.position_duration.years * elftime.TimeUnit.SECONDS
                    )
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
    return trade_streak

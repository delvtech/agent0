"""Main script for running bots on Hyperdrive"""
from __future__ import annotations

import logging

from web3 import Web3
from web3.contract.contract import Contract

from elfpy import eth, hyperdrive_interface
from elfpy import types as elftypes
from elfpy.eth.accounts import EthAccount
from elfpy.markets.hyperdrive import MarketActionType
from elfpy.time import time as elftime

# TODO: Fix these up
# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals


def execute_agent_trades(
    web3: Web3,
    hyperdrive_contract: Contract,
    agent_accounts: list[EthAccount],
    trade_streak: int,
) -> int:
    """Hyperdrive forever into the sunset"""
    # get latest market
    hyperdrive_market = hyperdrive_interface.get_hyperdrive_market(web3, hyperdrive_contract)
    for account in agent_accounts:
        if account.agent is None:  # should never happen
            continue
        # do_policy
        trades: list[elftypes.Trade] = account.agent.get_trades(market=hyperdrive_market)
        for trade_object in trades:
            logging.info(
                "AGENT %s to perform %s for %g",
                str(account.checksum_address),
                trade_object.trade.action_type,
                float(trade_object.trade.trade_amount),
            )
            # do_trade
            trade_amount: int = trade_object.trade.trade_amount.scaled_value
            maturity_time = (
                trade_object.trade.mint_time
                + hyperdrive_market.position_duration.years * elftime.TimeUnit.SECONDS.value
            )
            # TODO: The following variables are hard coded for now, but should be specified in the trade spec
            max_deposit = trade_amount
            min_output = 0
            min_apr = int(1)
            max_apr = int(1e18)
            as_underlying = True
            # sort through the trades
            # TODO: raise issue on failure by looking at `tx_receipt` returned from function
            if trade_object.trade.action_type == MarketActionType.OPEN_LONG:
                _ = eth.smart_contract_transact(
                    web3,
                    hyperdrive_contract,
                    account,
                    "openLong",
                    trade_amount,  # base amount
                    min_output,
                    account.checksum_address,
                    as_underlying,
                )
            elif trade_object.trade.action_type == MarketActionType.CLOSE_LONG:
                _ = eth.smart_contract_transact(
                    web3,
                    hyperdrive_contract,
                    account,
                    "closeLong",
                    maturity_time,
                    trade_amount,  # base amount
                    min_output,
                    account.checksum_address,
                    as_underlying,
                )
            elif trade_object.trade.action_type == MarketActionType.OPEN_SHORT:
                _ = eth.smart_contract_transact(
                    web3,
                    hyperdrive_contract,
                    account,
                    "openShort",
                    trade_amount,  # bond amount
                    max_deposit,
                    account.checksum_address,
                    as_underlying,
                )
            elif trade_object.trade.action_type == MarketActionType.CLOSE_SHORT:
                _ = eth.smart_contract_transact(
                    web3,
                    hyperdrive_contract,
                    account,
                    "closeShort",
                    maturity_time,
                    trade_amount,  # bond amount
                    min_output,
                    account.checksum_address,
                    as_underlying,
                )
            elif trade_object.trade.action_type == MarketActionType.ADD_LIQUIDITY:
                _ = eth.smart_contract_transact(
                    web3,
                    hyperdrive_contract,
                    account,
                    "addLiquidity",
                    trade_amount,  # contribution amount
                    min_apr,
                    max_apr,
                    account.checksum_address,
                    as_underlying,
                )
            elif trade_object.trade.action_type == MarketActionType.REMOVE_LIQUIDITY:
                _ = eth.smart_contract_transact(
                    web3,
                    hyperdrive_contract,
                    account,
                    "removeLiquidity",
                    trade_amount,  # shares they want returned
                    min_output,
                    account.checksum_address,
                    as_underlying,
                )
            else:
                raise NotImplementedError(f"{trade_object.trade.action_type} is not implemented.")
            trade_streak += 1
    return trade_streak
    # TODO: update wallet

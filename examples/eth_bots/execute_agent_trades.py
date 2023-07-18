"""Main script for running bots on Hyperdrive"""
from __future__ import annotations

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
    base_token_contract: Contract,
    hyperdrive_contract: Contract,
    agent_accounts: list[EthAccount],
) -> None:
    """Hyperdrive forever into the sunset"""
    # get latest market
    hyperdrive_market = hyperdrive_interface.get_hyperdrive_market(web3, hyperdrive_contract)
    for account in agent_accounts:
        if account.agent is None:  # should never happen
            continue
        # do_policy
        trades: list[elftypes.Trade] = account.agent.get_trades(market=hyperdrive_market)
        for trade_object in trades:
            # do_trade
            trade_amount: int = trade_object.trade.trade_amount.scaled_value
            # check that the hyperdrive contract has enough base approved for the trade
            hyperdrive_allowance = eth.smart_contract_read(
                base_token_contract,
                "allowance",
                account.checksum_address,
                hyperdrive_contract.address,
            )["value"]
            if hyperdrive_allowance < trade_amount:
                eth.smart_contract_transact(
                    web3,
                    base_token_contract,
                    "approve",
                    account,
                    account.checksum_address,
                    hyperdrive_contract.address,
                    int(50e21),  # 50k base
                )
            # TODO: allow for min_output
            min_output = 0
            as_underlying = True
            maturity_time = (
                trade_object.trade.mint_time
                + hyperdrive_market.position_duration.years * elftime.TimeUnit.SECONDS.value
            )
            if trade_object.trade.action_type == MarketActionType.OPEN_LONG:
                eth.smart_contract_transact(
                    web3,
                    hyperdrive_contract,
                    "openLong",
                    account,
                    trade_amount,
                    min_output,
                    account.checksum_address,
                    as_underlying,
                )
            elif trade_object.trade.action_type == MarketActionType.CLOSE_LONG:
                min_output = 0
                eth.smart_contract_transact(
                    web3,
                    hyperdrive_contract,
                    "closeLong",
                    account,
                    maturity_time,
                    trade_amount,
                    min_output,
                    account.checksum_address,
                    as_underlying,
                )
            else:
                raise NotImplementedError(f"{trade_object.trade.action_type} is not implemented.")
            # TODO: update wallet

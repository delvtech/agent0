"""Main script for running bots on Hyperdrive"""
from __future__ import annotations

import logging

from fixedpointmath import FixedPoint
from web3 import Web3
from web3.contract.contract import Contract

from elfpy import eth, hyperdrive_interface
from elfpy import types as elftypes
from elfpy.eth.accounts import EthAccount
from elfpy.markets.hyperdrive import MarketActionType
from elfpy.time import time as elftime
from elfpy.types import Quantity, TokenType
from elfpy.wallet.wallet import Long, Short
from elfpy.wallet.wallet_deltas import WalletDeltas

# TODO: Fix these up when we refactor this file
# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals
# pylint: disable=too-many-branches
# pylint: disable=too-many-statements


def execute_agent_trades(
    web3: Web3,
    hyperdrive_contract: Contract,
    agent_accounts: list[EthAccount],
    trade_streak: int,
) -> int:
    """Hyperdrive forever into the sunset."""
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
            position_duration_years = hyperdrive_market.position_duration.years * elftime.TimeUnit.SECONDS.value
            mint_time: FixedPoint = trade_object.trade.mint_time
            maturity_time: int = (mint_time + position_duration_years).scaled_value
            # TODO: The following variables are hard coded for now, but should be specified in the trade spec
            # HyperdriveMarketAction does have min_amount_out
            max_deposit = trade_amount
            min_output = trade_amount + 1
            min_apr = int(1)
            max_apr = int(1e18)
            as_underlying = True
            # sort through the trades
            # TODO: raise issue on failure by looking at `tx_receipt` returned from function
            # TODO: figure out fees paid
            if trade_object.trade.action_type == MarketActionType.OPEN_LONG:
                fn_name = "openLong"
                tx_receipt = eth.smart_contract_transact(
                    web3,
                    hyperdrive_contract,
                    account,
                    fn_name,
                    trade_amount,  # base amount
                    min_output,
                    account.checksum_address,
                    as_underlying,
                )
                hyperdrive_event_logs = eth.get_transaction_logs(
                    web3,
                    hyperdrive_contract,
                    tx_receipt,
                    event_names=[fn_name[0].capitalize() + fn_name[1:]],
                )
                if len(hyperdrive_event_logs) > 1:
                    raise AssertionError("Too many logs found")
                mint_time = (
                    FixedPoint(scaled_value=hyperdrive_event_logs[0]["args"]["maturityTime"]) - position_duration_years
                )
                wallet_deltas = WalletDeltas(
                    balance=Quantity(
                        amount=-FixedPoint(scaled_value=hyperdrive_event_logs[0]["args"]["baseAmount"]),
                        unit=TokenType.BASE,
                    ),
                    longs={mint_time: Long(FixedPoint(scaled_value=hyperdrive_event_logs[0]["args"]["bondAmount"]))},
                )
            elif trade_object.trade.action_type == MarketActionType.CLOSE_LONG:
                fn_name = "closeLong"
                tx_receipt = eth.smart_contract_transact(
                    web3,
                    hyperdrive_contract,
                    account,
                    fn_name,
                    maturity_time,
                    trade_amount,  # base amount
                    min_output,
                    account.checksum_address,
                    as_underlying,
                )
                hyperdrive_event_logs = eth.get_transaction_logs(
                    web3,
                    hyperdrive_contract,
                    tx_receipt,
                    event_names=[fn_name[0].capitalize() + fn_name[1:]],
                )
                if len(hyperdrive_event_logs) > 1:
                    raise AssertionError("Too many logs found")
                mint_time = (
                    FixedPoint(scaled_value=hyperdrive_event_logs[0]["args"]["maturityTime"]) - position_duration_years
                )
                wallet_deltas = WalletDeltas(
                    balance=Quantity(
                        amount=FixedPoint(scaled_value=hyperdrive_event_logs[0]["args"]["baseAmount"]),
                        unit=TokenType.BASE,
                    ),
                    longs={mint_time: Long(-FixedPoint(scaled_value=hyperdrive_event_logs[0]["args"]["bondAmount"]))},
                )
            elif trade_object.trade.action_type == MarketActionType.OPEN_SHORT:
                fn_name = "openShort"
                tx_receipt = eth.smart_contract_transact(
                    web3,
                    hyperdrive_contract,
                    account,
                    fn_name,
                    trade_amount,  # bond amount
                    max_deposit,
                    account.checksum_address,
                    as_underlying,
                )
                hyperdrive_event_logs = eth.get_transaction_logs(
                    web3,
                    hyperdrive_contract,
                    tx_receipt,
                    event_names=[fn_name[0].capitalize() + fn_name[1:]],
                )
                if len(hyperdrive_event_logs) > 1:
                    raise AssertionError("Too many logs found")
                mint_time = (
                    FixedPoint(scaled_value=hyperdrive_event_logs[0]["args"]["maturityTime"]) - position_duration_years
                )
                wallet_deltas = WalletDeltas(
                    balance=Quantity(
                        amount=-FixedPoint(scaled_value=hyperdrive_event_logs[0]["args"]["baseAmount"]),
                        unit=TokenType.BASE,
                    ),
                    shorts={
                        mint_time: Short(
                            balance=FixedPoint(scaled_value=hyperdrive_event_logs[0]["args"]["bondAmount"]),
                            open_share_price=hyperdrive_market.market_state.share_price,
                        )
                    },
                )
            elif trade_object.trade.action_type == MarketActionType.CLOSE_SHORT:
                fn_name = "closeShort"
                tx_receipt = eth.smart_contract_transact(
                    web3,
                    hyperdrive_contract,
                    account,
                    fn_name,
                    maturity_time,
                    trade_amount,  # bond amount
                    min_output,
                    account.checksum_address,
                    as_underlying,
                )
                hyperdrive_event_logs = eth.get_transaction_logs(
                    web3,
                    hyperdrive_contract,
                    tx_receipt,
                    event_names=[fn_name[0].capitalize() + fn_name[1:]],
                )
                if len(hyperdrive_event_logs) > 1:
                    raise AssertionError("Too many logs found")
                mint_time = (
                    FixedPoint(scaled_value=hyperdrive_event_logs[0]["args"]["maturityTime"]) - position_duration_years
                )
                wallet_deltas = WalletDeltas(
                    balance=Quantity(
                        amount=FixedPoint(scaled_value=hyperdrive_event_logs[0]["args"]["baseAmount"]),
                        unit=TokenType.BASE,
                    ),
                    shorts={
                        mint_time: Short(
                            balance=-FixedPoint(scaled_value=hyperdrive_event_logs[0]["args"]["bondAmount"]),
                            open_share_price=account.agent.wallet.shorts[mint_time].open_share_price,
                        )
                    },
                )
            elif trade_object.trade.action_type == MarketActionType.ADD_LIQUIDITY:
                fn_name = "addLiquidity"
                tx_receipt = eth.smart_contract_transact(
                    web3,
                    hyperdrive_contract,
                    account,
                    fn_name,
                    trade_amount,  # contribution amount
                    min_apr,
                    max_apr,
                    account.checksum_address,
                    as_underlying,
                )
                hyperdrive_event_logs = eth.get_transaction_logs(
                    web3,
                    hyperdrive_contract,
                    tx_receipt,
                    event_names=[fn_name[0].capitalize() + fn_name[1:]],
                )
                if len(hyperdrive_event_logs) > 1:
                    raise AssertionError("Too many logs found")
                wallet_deltas = WalletDeltas(
                    balance=Quantity(
                        amount=-FixedPoint(scaled_value=hyperdrive_event_logs[0]["args"]["baseAmount"]),
                        unit=TokenType.BASE,
                    ),
                    lp_tokens=FixedPoint(scaled_value=hyperdrive_event_logs[0]["args"]["lpAmount"]),
                )
            elif trade_object.trade.action_type == MarketActionType.REMOVE_LIQUIDITY:
                fn_name = "removeLiquidity"
                tx_receipt = eth.smart_contract_transact(
                    web3,
                    hyperdrive_contract,
                    account,
                    fn_name,
                    trade_amount,  # shares they want returned
                    min_output,
                    account.checksum_address,
                    as_underlying,
                )
                hyperdrive_event_logs = eth.get_transaction_logs(
                    web3,
                    hyperdrive_contract,
                    tx_receipt,
                    event_names=[fn_name[0].capitalize() + fn_name[1:]],
                )
                wallet_deltas = WalletDeltas(
                    balance=Quantity(
                        amount=FixedPoint(scaled_value=hyperdrive_event_logs[0]["args"]["baseAmount"]),
                        unit=TokenType.BASE,
                    ),
                    lp_tokens=-FixedPoint(scaled_value=hyperdrive_event_logs[0]["args"]["lpAmount"]),
                    withdraw_shares=FixedPoint(scaled_value=hyperdrive_event_logs[0]["args"]["withdrawalShareAmount"]),
                )
            else:
                raise NotImplementedError(f"{trade_object.trade.action_type} is not implemented.")
            account.agent.wallet.update(wallet_deltas)
            trade_streak += 1
    return trade_streak

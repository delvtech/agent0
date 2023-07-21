"""Main script for running bots on Hyperdrive"""
from __future__ import annotations

import logging
from dataclasses import dataclass

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
# pylint: disable=too-many-locals


@dataclass
class ReceiptBreakdown:
    r"""A granular breakdown of important values in a trade receipt."""
    base_amount: FixedPoint = FixedPoint(0)
    bond_amount: FixedPoint = FixedPoint(0)
    maturity_time: FixedPoint = FixedPoint(0)
    lp_amount: FixedPoint = FixedPoint(0)
    withdrawal_share_amount: FixedPoint = FixedPoint(0)


def transact_and_parse_logs(
    web3: Web3, hyperdrive_contract: Contract, signer: EthAccount, fn_name: str, *fn_args
) -> ReceiptBreakdown:
    """Execute the hyperdrive smart contract transaction and decode the receipt to get the changes to the agent's funds.

    Arguments
    ---------
    web3 : Web3
        web3 provider object
    hyperdrive_contract : Contract
        Any deployed web3 contract
    signer : EthAccount
        The EthAccount that will be used to pay for the gas & sign the transaction
    fn_name : str
        This function must exist in the compiled contract's ABI
    fn_args : ordered list
        All remaining arguments will be passed to the contract function in the order received

    Returns
    -------
    ReceiptBreakdown
        A dataclass containing the maturity time and the absolute values for token quantities changed
    """
    tx_receipt = eth.smart_contract_transact(web3, hyperdrive_contract, signer, fn_name, *fn_args)
    # TODO: raise issue on failure by looking at `tx_receipt` returned from function
    hyperdrive_event_logs = eth.get_transaction_logs(
        web3,
        hyperdrive_contract,
        tx_receipt,
        event_names=[fn_name[0].capitalize() + fn_name[1:]],
    )
    if len(hyperdrive_event_logs) > 1:
        raise AssertionError("Too many logs found")
    log_args = hyperdrive_event_logs[0]["args"]
    trade_result = ReceiptBreakdown()
    if "baseAmount" in log_args:
        trade_result.base_amount = FixedPoint(scaled_value=log_args["baseAmount"])
    if "bondAmount" in log_args:
        trade_result.bond_amount = FixedPoint(scaled_value=log_args["bondAmount"])
    if "maturityTime" in log_args:
        trade_result.maturity_time = FixedPoint(scaled_value=log_args["maturityTime"])
    if "lpAmount" in log_args:
        trade_result.lp_amount = FixedPoint(scaled_value=log_args["lpAmount"])
    if "withdrawalShareAmount" in log_args:
        trade_result.withdrawal_share_amount = FixedPoint(scaled_value=log_args["withdrawalShareAmount"])
    return trade_result


def execute_agent_trades(
    web3: Web3,
    hyperdrive_contract: Contract,
    agent_accounts: list[EthAccount],
    trade_streak: int,
) -> int:
    """Hyperdrive forever into the sunset.

    Arguments
    ---------
    web3 : Web3
        web3 provider object
    hyperdrive_contract : Contract
        Any deployed web3 contract
    agent_accounts : list[EthAccount]
        A list of EthAccount that are conducting the trades
    trade_streak : int
        A counter for the number of successful trades so far

    Returns
    -------
    trade_streak : int
        A counter for the number of successful trades so far (that includes the new trades)
    """
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
            # TODO: figure out fees paid
            if trade_object.trade.action_type == MarketActionType.OPEN_LONG:
                trade_result = transact_and_parse_logs(
                    web3,
                    hyperdrive_contract,
                    account,
                    "openLong",
                    *(trade_amount, min_output, account.checksum_address, as_underlying),
                )
                mint_time = trade_result.maturity_time - position_duration_years
                wallet_deltas = WalletDeltas(
                    balance=Quantity(
                        amount=-trade_result.base_amount,
                        unit=TokenType.BASE,
                    ),
                    longs={mint_time: Long(trade_result.bond_amount)},
                )
            elif trade_object.trade.action_type == MarketActionType.CLOSE_LONG:
                trade_result = transact_and_parse_logs(
                    web3,
                    hyperdrive_contract,
                    account,
                    "closeLong",
                    *(maturity_time, trade_amount, min_output, account.checksum_address, as_underlying),
                )
                mint_time = trade_result.maturity_time - position_duration_years
                wallet_deltas = WalletDeltas(
                    balance=Quantity(
                        amount=trade_result.base_amount,
                        unit=TokenType.BASE,
                    ),
                    longs={mint_time: Long(-trade_result.bond_amount)},
                )
            elif trade_object.trade.action_type == MarketActionType.OPEN_SHORT:
                trade_result = transact_and_parse_logs(
                    web3,
                    hyperdrive_contract,
                    account,
                    "openShort",
                    *(trade_amount, max_deposit, account.checksum_address, as_underlying),
                )
                mint_time = trade_result.maturity_time - position_duration_years
                wallet_deltas = WalletDeltas(
                    balance=Quantity(
                        amount=-trade_result.base_amount,
                        unit=TokenType.BASE,
                    ),
                    shorts={
                        mint_time: Short(
                            balance=trade_result.bond_amount,
                            open_share_price=hyperdrive_market.market_state.share_price,
                        )
                    },
                )
            elif trade_object.trade.action_type == MarketActionType.CLOSE_SHORT:
                trade_result = transact_and_parse_logs(
                    web3,
                    hyperdrive_contract,
                    account,
                    "closeShort",
                    *(maturity_time, trade_amount, min_output, account.checksum_address, as_underlying),
                )
                mint_time = trade_result.maturity_time - position_duration_years
                wallet_deltas = WalletDeltas(
                    balance=Quantity(
                        amount=trade_result.base_amount,
                        unit=TokenType.BASE,
                    ),
                    shorts={
                        mint_time: Short(
                            balance=-trade_result.bond_amount,
                            open_share_price=account.agent.wallet.shorts[mint_time].open_share_price,
                        )
                    },
                )
            elif trade_object.trade.action_type == MarketActionType.ADD_LIQUIDITY:
                trade_result = transact_and_parse_logs(
                    web3,
                    hyperdrive_contract,
                    account,
                    "addLiquidity",
                    *(trade_amount, min_apr, max_apr, account.checksum_address, as_underlying),
                )
                mint_time = trade_result.maturity_time - position_duration_years
                wallet_deltas = WalletDeltas(
                    balance=Quantity(
                        amount=-trade_result.base_amount,
                        unit=TokenType.BASE,
                    ),
                    lp_tokens=trade_result.lp_amount,
                )
            elif trade_object.trade.action_type == MarketActionType.REMOVE_LIQUIDITY:
                trade_result = transact_and_parse_logs(
                    web3,
                    hyperdrive_contract,
                    account,
                    "removeLiquidity",
                    *(trade_amount, min_output, account.checksum_address, as_underlying),
                )
                wallet_deltas = WalletDeltas(
                    balance=Quantity(
                        amount=trade_result.base_amount,
                        unit=TokenType.BASE,
                    ),
                    lp_tokens=-trade_result.lp_amount,
                    withdraw_shares=trade_result.withdrawal_share_amount,
                )
            else:
                raise NotImplementedError(f"{trade_object.trade.action_type} is not implemented.")
            account.agent.wallet.update(wallet_deltas)
            trade_streak += 1
    return trade_streak

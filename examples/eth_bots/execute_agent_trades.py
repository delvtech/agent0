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
    asset_id: int = 0
    maturity_time: int = 0
    base_amount: FixedPoint = FixedPoint(0)
    bond_amount: FixedPoint = FixedPoint(0)
    lp_amount: FixedPoint = FixedPoint(0)
    withdrawal_share_amount: FixedPoint = FixedPoint(0)

    def __post_init__(self):
        if (
            self.base_amount < 0
            or self.bond_amount < 0
            or self.maturity_time < 0
            or self.lp_amount < 0
            or self.withdrawal_share_amount < 0
        ):
            raise ValueError(
                "All ReceiptBreakdown arguments must be positive,"
                " since they are expected to be unsigned integer values from smart contracts."
            )


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
    # TODO: raise issue on failure by looking at `tx_receipt` returned from function
    tx_receipt = eth.smart_contract_transact(web3, hyperdrive_contract, signer, fn_name, *fn_args)
    hyperdrive_event_logs = eth.get_transaction_logs(
        web3,
        hyperdrive_contract,
        tx_receipt,
        event_names=[fn_name[0].capitalize() + fn_name[1:]],
    )
    if len(hyperdrive_event_logs) == 0:
        raise AssertionError("Transaction receipt had no logs")
    if len(hyperdrive_event_logs) > 1:
        raise AssertionError("Too many logs found")
    log_args = hyperdrive_event_logs[0]["args"]
    trade_result = ReceiptBreakdown()
    if "assetId" in log_args:
        trade_result.asset_id = log_args["assetId"]
    if "maturityTime" in log_args:
        trade_result.maturity_time = log_args["maturityTime"]
    if "baseAmount" in log_args:
        trade_result.base_amount = FixedPoint(scaled_value=log_args["baseAmount"])
    if "bondAmount" in log_args:
        trade_result.bond_amount = FixedPoint(scaled_value=log_args["bondAmount"])
    if "lpAmount" in log_args:
        trade_result.lp_amount = FixedPoint(scaled_value=log_args["lpAmount"])
    if "withdrawalShareAmount" in log_args:
        trade_result.withdrawal_share_amount = FixedPoint(scaled_value=log_args["withdrawalShareAmount"])
    return trade_result


def execute_agent_trades(
    web3: Web3,
    hyperdrive_contract: Contract,
    agent_accounts: list[EthAccount],
) -> None:
    """Hyperdrive forever into the sunset.

    Arguments
    ---------
    web3 : Web3
        web3 provider object
    hyperdrive_contract : Contract
        Any deployed web3 contract
    agent_accounts : list[EthAccount]
        A list of EthAccount that are conducting the trades
    """
    # get latest market
    hyperdrive_market = hyperdrive_interface.get_hyperdrive_market(web3, hyperdrive_contract)
    for account in agent_accounts:
        # This condition is unlikely;
        # it would happen if they created an eth address but didn't associate it with an elfpy Agent
        if account.agent is None:
            continue
        trades: list[elftypes.Trade] = account.agent.get_trades(market=hyperdrive_market)
        for trade_object in trades:
            logging.info(
                "AGENT %s to perform %s for %g",
                str(account.checksum_address),
                trade_object.trade.action_type,
                float(trade_object.trade.trade_amount),
            )
            trade_amount: int = trade_object.trade.trade_amount.scaled_value
            # TODO: The following variables are hard coded for now, but should be specified in the trade spec
            # HyperdriveMarketAction does have min_amount_out
            max_deposit = trade_amount
            min_output = 0
            min_apr = int(1)
            max_apr = int(1e18)
            as_underlying = True
            # TODO: figure out fees paid
            match trade_object.trade.action_type:
                case MarketActionType.OPEN_LONG:
                    fn_args = (trade_amount, min_output, account.checksum_address, as_underlying)
                    trade_result = transact_and_parse_logs(
                        web3,
                        hyperdrive_contract,
                        account,
                        "openLong",
                        *fn_args,
                    )
                    maturity_time_years = FixedPoint(trade_result.maturity_time) / elftime.TimeUnit.YEARS.value
                    mint_time_years = maturity_time_years - hyperdrive_market.position_duration.years
                    wallet_deltas = WalletDeltas(
                        balance=Quantity(
                            amount=-trade_result.base_amount,
                            unit=TokenType.BASE,
                        ),
                        longs={FixedPoint(mint_time_years): Long(trade_result.bond_amount)},
                    )
                case MarketActionType.CLOSE_LONG:
                    mint_time_years: FixedPoint = trade_object.trade.mint_time
                    decoded_maturity_time_years = mint_time_years + hyperdrive_market.position_duration.years
                    decoded_maturity_time = int(decoded_maturity_time_years * elftime.TimeUnit.YEARS.value)
                    fn_args = (decoded_maturity_time, trade_amount, min_output, account.checksum_address, as_underlying)
                    trade_result = transact_and_parse_logs(
                        web3,
                        hyperdrive_contract,
                        account,
                        "closeLong",
                        *fn_args,
                    )
                    wallet_deltas = WalletDeltas(
                        balance=Quantity(
                            amount=trade_result.base_amount,
                            unit=TokenType.BASE,
                        ),
                        longs={mint_time_years: Long(-trade_result.bond_amount)},
                    )
                case MarketActionType.OPEN_SHORT:
                    fn_args = (trade_amount, max_deposit, account.checksum_address, as_underlying)
                    trade_result = transact_and_parse_logs(
                        web3,
                        hyperdrive_contract,
                        account,
                        "openShort",
                        *fn_args,
                    )
                    maturity_time_years = FixedPoint(trade_result.maturity_time) / elftime.TimeUnit.YEARS.value
                    mint_time_years = maturity_time_years - hyperdrive_market.position_duration.years
                    wallet_deltas = WalletDeltas(
                        balance=Quantity(
                            amount=-trade_result.base_amount,
                            unit=TokenType.BASE,
                        ),
                        shorts={
                            mint_time_years: Short(
                                balance=trade_result.bond_amount,
                                open_share_price=hyperdrive_market.market_state.share_price,
                            )
                        },
                    )
                case MarketActionType.CLOSE_SHORT:
                    mint_time_years: FixedPoint = trade_object.trade.mint_time
                    decoded_maturity_time_years = mint_time_years + hyperdrive_market.position_duration.years
                    decoded_maturity_time = int(decoded_maturity_time_years * elftime.TimeUnit.YEARS.value)
                    fn_args = (decoded_maturity_time, trade_amount, min_output, account.checksum_address, as_underlying)
                    trade_result = transact_and_parse_logs(
                        web3,
                        hyperdrive_contract,
                        account,
                        "closeShort",
                        *fn_args,
                    )
                    wallet_deltas = WalletDeltas(
                        balance=Quantity(
                            amount=trade_result.base_amount,
                            unit=TokenType.BASE,
                        ),
                        shorts={
                            mint_time_years: Short(
                                balance=-trade_result.bond_amount,
                                open_share_price=account.agent.wallet.shorts[mint_time_years].open_share_price,
                            )
                        },
                    )
                case MarketActionType.ADD_LIQUIDITY:
                    fn_args = (trade_amount, min_apr, max_apr, account.checksum_address, as_underlying)
                    trade_result = transact_and_parse_logs(
                        web3,
                        hyperdrive_contract,
                        account,
                        "addLiquidity",
                        *fn_args,
                    )
                    wallet_deltas = WalletDeltas(
                        balance=Quantity(
                            amount=-trade_result.base_amount,
                            unit=TokenType.BASE,
                        ),
                        lp_tokens=trade_result.lp_amount,
                    )
                case MarketActionType.REMOVE_LIQUIDITY:
                    fn_args = (trade_amount, min_output, account.checksum_address, as_underlying)
                    trade_result = transact_and_parse_logs(
                        web3,
                        hyperdrive_contract,
                        account,
                        "removeLiquidity",
                        *fn_args,
                    )
                    wallet_deltas = WalletDeltas(
                        balance=Quantity(
                            amount=trade_result.base_amount,
                            unit=TokenType.BASE,
                        ),
                        lp_tokens=-trade_result.lp_amount,
                        withdraw_shares=trade_result.withdrawal_share_amount,
                    )
                case action_type:
                    raise NotImplementedError(f"{action_type} is not implemented.")
            account.agent.wallet.update(wallet_deltas)

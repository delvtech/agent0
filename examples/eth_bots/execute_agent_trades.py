"""Main script for running bots on Hyperdrive."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import NoReturn

import eth_utils
from fixedpointmath import FixedPoint
from web3 import Web3
from web3.contract.contract import Contract

from elfpy import eth, hyperdrive_interface, types
from elfpy.eth.accounts import EthAccount
from elfpy.eth.errors.types import UnknownBlockError
from elfpy.eth.transactions import smart_contract_preview_transaction
from elfpy.markets.hyperdrive import HyperdriveMarket, MarketActionType
from elfpy.markets.hyperdrive.hyperdrive_actions import HyperdriveMarketAction
from elfpy.types import Quantity, TokenType
from elfpy.wallet.wallet import Long, Short
from elfpy.wallet.wallet_deltas import WalletDeltas

# TODO: Fix these up when we refactor this file
# pylint: disable=too-many-locals


@dataclass
class ReceiptBreakdown:
    r"""A granular breakdown of important values in a trade receipt."""
    asset_id: int = 0
    maturity_time_seconds: int = 0
    base_amount: FixedPoint = FixedPoint(0)
    bond_amount: FixedPoint = FixedPoint(0)
    lp_amount: FixedPoint = FixedPoint(0)
    withdrawal_share_amount: FixedPoint = FixedPoint(0)

    def __post_init__(self):
        if (
            self.base_amount < 0
            or self.bond_amount < 0
            or self.maturity_time_seconds < 0
            or self.lp_amount < 0
            or self.withdrawal_share_amount < 0
        ):
            raise ValueError(
                "All ReceiptBreakdown arguments must be positive,"
                " since they are expected to be unsigned integer values from smart contracts."
            )


async def async_transact_and_parse_logs(
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
    tx_receipt = await eth.async_smart_contract_transact(web3, hyperdrive_contract, signer, fn_name, *fn_args)
    # Sometimes, smart contract transact fails with status 0 with no error message
    # We throw custom error to catch in trades loop, ignore, and move on
    # TODO need to track down why this call fails and handle better
    status = tx_receipt.get("status", None)
    if status is None:
        raise AssertionError("Receipt did not return status")
    if status == 0:
        raise UnknownBlockError(f"Receipt has no status or status is 0 \n {tx_receipt=}")

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
        trade_result.maturity_time_seconds = log_args["maturityTime"]
    if "baseAmount" in log_args:
        trade_result.base_amount = FixedPoint(scaled_value=log_args["baseAmount"])
    if "bondAmount" in log_args:
        trade_result.bond_amount = FixedPoint(scaled_value=log_args["bondAmount"])
    if "lpAmount" in log_args:
        trade_result.lp_amount = FixedPoint(scaled_value=log_args["lpAmount"])
    if "withdrawalShareAmount" in log_args:
        trade_result.withdrawal_share_amount = FixedPoint(scaled_value=log_args["withdrawalShareAmount"])
    return trade_result


async def async_execute_single_agent_trade(
    account: EthAccount,
    web3: Web3,
    hyperdrive_contract: Contract,
    hyperdrive_market: HyperdriveMarket,
) -> None:
    """Executes a single agent's trade. This function is async as
    `match_contract_call_to_trade` waits for a transaction receipt

    Arguments
    ---------
    web3 : Web3
        web3 provider object
    hyperdrive_contract : Contract
        Any deployed web3 contract
    account: EthAccount
        The EthAccount that is conducting the trade
    hyperdrive_market: HyperdriveMarket:
        The hyperdrive market state
    """

    # This condition is unlikely;
    # it would happen if they created an eth address but didn't associate it with an elfpy Agent
    if account.agent is None:
        return

    trades: list[types.Trade] = account.agent.get_trades(market=hyperdrive_market)
    for trade_object in trades:
        logging.info(
            "AGENT %s to perform %s for %g",
            str(account.checksum_address),
            trade_object.trade.action_type,
            float(trade_object.trade.trade_amount),
        )
        try:
            wallet_deltas = await async_match_contract_call_to_trade(
                web3,
                hyperdrive_contract,
                hyperdrive_market,
                account,
                trade_object,
            )
            # NOTE this is assuming account.agent.wallet is unique to each agent!
            account.agent.wallet.update(wallet_deltas)
        except UnknownBlockError as exc:
            logging.error(exc)


async def async_execute_agent_trades(
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
    # TODO: This might _not_ be the latest market, due to async
    # get latest market
    hyperdrive_market = hyperdrive_interface.get_hyperdrive_market(web3, hyperdrive_contract)
    # Make calls per account to execute_single_agent_trade
    # Await all trades to finish before continuing
    await asyncio.gather(
        *[
            async_execute_single_agent_trade(account, web3, hyperdrive_contract, hyperdrive_market)
            for account in agent_accounts
        ]
    )


def assert_never(arg: NoReturn) -> NoReturn:
    """Helper function for exhaustive matching on ENUMS"""
    assert False, f"Unhandled type: {type(arg).__name__}"


async def async_match_contract_call_to_trade(
    web3: Web3,
    hyperdrive_contract: Contract,
    hyperdrive_market: HyperdriveMarket,
    account: EthAccount,
    trade: types.Trade[HyperdriveMarketAction],
) -> WalletDeltas:
    """Match statement that executes the smart contract trade based on the provided type.

    Arguments
    ---------
    web3 : Web3
        web3 provider object
    hyperdrive_contract : Contract
        Any deployed web3 contract
    hyperdrive_market : HyperdriveMarket
        The elfpy trading market
    account : EthAccount
        Object containing a wallet address and Elfpy Agent for determining trades
    trade_object : Trade
        A specific trade requested by the given account

    Returns
    -------
    WalletDeltas
        Deltas to be applied to the agent's wallet

    """
    # TODO: figure out fees paid
    # TODO: clean up this function, DRY it up to reduce number of statements
    # pylint: disable=too-many-statements
    trade_amount: int = trade.trade.trade_amount.scaled_value
    max_deposit: int = trade_amount

    # TODO: The following variables are hard coded for now, but should be specified in the trade spec
    min_apr = int(1)
    max_apr = int(1e18)
    as_underlying = True
    match trade.trade.action_type:
        case MarketActionType.OPEN_LONG:
            min_output = 0
            fn_args = (trade_amount, min_output, account.checksum_address, as_underlying)
            preview_result = smart_contract_preview_transaction(hyperdrive_contract, account, "openLong", *fn_args)
            min_output = (
                FixedPoint(scaled_value=preview_result["bondProceeds"])
                * (FixedPoint(1) - trade.trade.slippage_tolerance)
            ).scaled_value
            fn_args = (trade_amount, min_output, account.checksum_address, as_underlying)

            trade_result = await async_transact_and_parse_logs(
                web3,
                hyperdrive_contract,
                account,
                "openLong",
                *fn_args,
            )
            maturity_time_seconds = trade_result.maturity_time_seconds
            wallet_deltas = WalletDeltas(
                balance=Quantity(
                    amount=-trade_result.base_amount,
                    unit=TokenType.BASE,
                ),
                longs={FixedPoint(maturity_time_seconds): Long(trade_result.bond_amount)},
            )
        case MarketActionType.CLOSE_LONG:
            maturity_time_seconds = trade.trade.mint_time
            if not maturity_time_seconds:
                raise ValueError("Mint time wasnot provided, can't close long position.")
            decoded_maturity_time_seconds = int(maturity_time_seconds)
            min_output = 0

            fn_args = (
                decoded_maturity_time_seconds,
                trade_amount,
                min_output,
                account.checksum_address,
                as_underlying,
            )
            preview_result = smart_contract_preview_transaction(hyperdrive_contract, account, "closeLong", *fn_args)
            min_output = (
                FixedPoint(scaled_value=preview_result["value"]) * (FixedPoint(1) - trade.trade.slippage_tolerance)
            ).scaled_value
            fn_args = (decoded_maturity_time_seconds, trade_amount, min_output, account.checksum_address, as_underlying)
            trade_result = await async_transact_and_parse_logs(
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
                longs={maturity_time_seconds: Long(-trade_result.bond_amount)},
            )
        case MarketActionType.OPEN_SHORT:
            max_deposit = eth_utils.currency.MAX_WEI
            fn_args = (trade_amount, max_deposit, account.checksum_address, as_underlying)
            preview_result = smart_contract_preview_transaction(hyperdrive_contract, account, "openShort", *fn_args)
            max_deposit = (
                FixedPoint(scaled_value=preview_result["traderDeposit"])
                * (FixedPoint(1) + trade.trade.slippage_tolerance)
            ).scaled_value
            fn_args = (trade_amount, max_deposit, account.checksum_address, as_underlying)
            trade_result = await async_transact_and_parse_logs(
                web3,
                hyperdrive_contract,
                account,
                "openShort",
                *fn_args,
            )
            maturity_time_seconds = trade_result.maturity_time_seconds
            wallet_deltas = WalletDeltas(
                balance=Quantity(
                    amount=-trade_result.base_amount,
                    unit=TokenType.BASE,
                ),
                shorts={
                    FixedPoint(maturity_time_seconds): Short(
                        balance=trade_result.bond_amount,
                        open_share_price=hyperdrive_market.market_state.share_price,
                    )
                },
            )
        case MarketActionType.CLOSE_SHORT:
            maturity_time_seconds = trade.trade.mint_time
            if not maturity_time_seconds:
                raise ValueError("Mint time was not provided, can't close long position.")
            decoded_maturity_time_seconds = int(maturity_time_seconds)
            min_output = 0
            fn_args = (
                decoded_maturity_time_seconds,
                trade_amount,
                min_output,
                account.checksum_address,
                as_underlying,
            )
            preview_result = smart_contract_preview_transaction(hyperdrive_contract, account, "closeShort", *fn_args)
            min_output = (
                FixedPoint(scaled_value=preview_result["value"]) * (FixedPoint(1) - trade.trade.slippage_tolerance)
            ).scaled_value
            fn_args = (trade_amount, min_output, account.checksum_address, as_underlying)
            trade_result = await async_transact_and_parse_logs(
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
                    maturity_time_seconds: Short(
                        balance=-trade_result.bond_amount,
                        open_share_price=account.agent.wallet.shorts[maturity_time_seconds].open_share_price,
                    )
                },
            )
        case MarketActionType.ADD_LIQUIDITY:
            min_output = 0
            fn_args = (trade_amount, min_apr, max_apr, account.checksum_address, as_underlying)
            trade_result = await async_transact_and_parse_logs(
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
            min_output = 0
            fn_args = (trade_amount, min_output, account.checksum_address, as_underlying)
            trade_result = await async_transact_and_parse_logs(
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
        case MarketActionType.INITIALIZE_MARKET:
            raise ValueError(f"{trade.trade.action_type} not supported!")
        case _:
            assert_never(trade.trade.action_type)
    return wallet_deltas

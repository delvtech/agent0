"""High-level interface for the Hyperdrive market"""
from __future__ import annotations

import eth_utils
from eth_account.signers.local import LocalAccount
from eth_typing import URI, BlockNumber
from ethpy import EthConfig
from ethpy.base import async_smart_contract_transact, smart_contract_preview_transaction
from fixedpointmath import FixedPoint
from web3 import Web3
from web3.types import BlockData

from .get_web3_and_hyperdrive_contracts import get_web3_and_hyperdrive_contracts
from .interface import get_hyperdrive_config, get_hyperdrive_pool_info, parse_logs
from .receipt_breakdown import ReceiptBreakdown


class Hyperdrive:
    """End-point api for interfacing with Hyperdrive"""

    def __init__(
        self,
        eth_config: EthConfig | None = None,
        *,  # kw-args only from here forward
        artifacts_uri: str | URI | None = None,
        rpc_uri: str | URI | None = None,
        abi_dir: str | None = None,
    ) -> None:
        """The Hyperdrive API can be initialized with either an EthConfig,
        or strings corresponding to the required URIs and directories.
        """
        if eth_config is None:
            if artifacts_uri is None or rpc_uri is None or abi_dir is None:
                raise AssertionError("if eth_config is None, then all of the remaining arguments must be set.")
            self.config = EthConfig(artifacts_uri, rpc_uri, abi_dir)
        if eth_config is not None:
            if not all([artifacts_uri is None, rpc_uri is None, abi_dir is None]):
                raise AssertionError("if eth_config is not None, then none of the remaining arguments can be set.")
            self.config = eth_config
        self.web3, self.base_token_contract, self.hyperdrive_contract = get_web3_and_hyperdrive_contracts(self.config)

    @property
    def pool_config(self):
        """Returns the pool initialization config"""
        return get_hyperdrive_config(self.hyperdrive_contract)

    @property
    def pool_info(self):
        """Returns the current pool state info"""
        return get_hyperdrive_pool_info(self.web3, self.hyperdrive_contract, self.current_block_number)

    @property
    def current_block(self) -> BlockData:
        """The current block number, which must be set with a setter method"""
        return self.web3.eth.get_block("latest")

    @property
    def current_block_number(self) -> BlockNumber:
        """The current block number, which must be set with a setter method"""
        current_block_number = self.current_block.get("number", None)
        if current_block_number is None:
            raise AssertionError("The current block has no number")
        return current_block_number

    # FIXME:
    @property
    def spot_price(self) -> FixedPoint:
        """Returns the current market spot price"""
        raise NotImplementedError

    async def async_open_long(
        self, agent: LocalAccount, trade_amount: FixedPoint, slippage_tolerance: FixedPoint | None = None
    ) -> ReceiptBreakdown:
        """Contract call to open a long position.

        Arguments
        ---------
        agent: LocalAccount
            The account for the agent that is executing and signing the trade transaction.
        trade_amount: FixedPoint
            The size of the position, in base.
        slippage_tolerance: FixedPoint | None
            Amount of slippage allowed from the trade.
            If None, then execute the trade regardless of the slippage.
            If not None, then the trade will not execute unless the slippage is below this value.

        Returns
        -------
        ReceiptBreakdown
            A dataclass containing the maturity time and the absolute values for token quantities changed
        """
        agent_checksum_address = Web3.to_checksum_address(agent.address)
        min_output = 0
        as_underlying = True
        fn_args = (trade_amount.scaled_value, min_output, agent_checksum_address, as_underlying)
        if slippage_tolerance is not None:
            preview_result = smart_contract_preview_transaction(
                self.hyperdrive_contract, agent_checksum_address, "openLong", *fn_args
            )
            min_output = (
                FixedPoint(scaled_value=preview_result["bondProceeds"]) * (FixedPoint(1) - slippage_tolerance)
            ).scaled_value
            fn_args = (trade_amount.scaled_value, min_output, agent_checksum_address, as_underlying)
        tx_receipt = await async_smart_contract_transact(
            self.web3, self.hyperdrive_contract, agent, "openLong", *fn_args
        )
        trade_result = parse_logs(tx_receipt, self.hyperdrive_contract, "openLong")
        return trade_result

    async def async_close_long(
        self,
        agent: LocalAccount,
        trade_amount: FixedPoint,
        maturity_time: FixedPoint,
        slippage_tolerance: FixedPoint | None = None,
    ) -> ReceiptBreakdown:
        """Contract call to close a long position.

        Arguments
        ---------
        agent: LocalAccount
            The account for the agent that is executing and signing the trade transaction.
        trade_amount: FixedPoint
            The size of the position, in base.
        maturity_time: FixedPoint
            The token maturity time in seconds.
        slippage_tolerance: FixedPoint | None
            Amount of slippage allowed from the trade.
            If None, then execute the trade regardless of the slippage.
            If not None, then the trade will not execute unless the slippage is below this value.

        Returns
        -------
        ReceiptBreakdown
            A dataclass containing the maturity time and the absolute values for token quantities changed
        """
        agent_checksum_address = Web3.to_checksum_address(agent.address)
        maturity_time_seconds = int(maturity_time)
        min_output = 0
        as_underlying = True
        fn_args = (
            maturity_time_seconds,
            trade_amount.scaled_value,
            min_output,
            agent_checksum_address,
            as_underlying,
        )
        if slippage_tolerance:
            preview_result = smart_contract_preview_transaction(
                self.hyperdrive_contract, agent_checksum_address, "closeLong", *fn_args
            )
            min_output = (
                FixedPoint(scaled_value=preview_result["value"]) * (FixedPoint(1) - slippage_tolerance)
            ).scaled_value
            fn_args = (
                maturity_time_seconds,
                trade_amount.scaled_value,
                min_output,
                agent_checksum_address,
                as_underlying,
            )
        tx_receipt = await async_smart_contract_transact(
            self.web3, self.hyperdrive_contract, agent, "closeLong", *fn_args
        )
        trade_result = parse_logs(tx_receipt, self.hyperdrive_contract, "closeLong")
        return trade_result

    async def async_open_short(
        self,
        agent: LocalAccount,
        trade_amount: FixedPoint,
        slippage_tolerance: FixedPoint | None = None,
    ) -> ReceiptBreakdown:
        """Contract call to open a short position.

        Arguments
        ---------
        agent: LocalAccount
            The account for the agent that is executing and signing the trade transaction.
        trade_amount: FixedPoint
            The size of the position, in base.
        slippage_tolerance: FixedPoint | None
            Amount of slippage allowed from the trade.
            If None, then execute the trade regardless of the slippage.
            If not None, then the trade will not execute unless the slippage is below this value.

        Returns
        -------
        ReceiptBreakdown
            A dataclass containing the maturity time and the absolute values for token quantities changed
        """
        agent_checksum_address = Web3.to_checksum_address(agent.address)
        as_underlying = True
        max_deposit = eth_utils.currency.MAX_WEI
        fn_args = (trade_amount.scaled_value, max_deposit, agent_checksum_address, as_underlying)
        if slippage_tolerance:
            preview_result = smart_contract_preview_transaction(
                self.hyperdrive_contract, agent_checksum_address, "openShort", *fn_args
            )
            max_deposit = (
                FixedPoint(scaled_value=preview_result["traderDeposit"]) * (FixedPoint(1) + slippage_tolerance)
            ).scaled_value
        fn_args = (trade_amount.scaled_value, max_deposit, agent_checksum_address, as_underlying)
        tx_receipt = await async_smart_contract_transact(
            self.web3, self.hyperdrive_contract, agent, "openShort", *fn_args
        )
        trade_result = parse_logs(tx_receipt, self.hyperdrive_contract, "openShort")
        return trade_result

    # FIXME: TODO: other async trades

    # FIXME: TODO:
    # def balance_of(agent):

    # FIXME: TODO:
    # def get_max_long(budget):
    #     pyperdrive.get_max_long(...)

    # FIXME: TODO:
    # def get_max_short(budget):
    #     pyperdrive.get_max_short(...)

"""High-level interface for the Hyperdrive market"""
from __future__ import annotations

from eth_account.signers.local import LocalAccount
from eth_typing import BlockNumber
from ethpy.base import async_smart_contract_transact, smart_contract_preview_transaction
from fixedpointmath import FixedPoint
from web3 import Web3
from web3.contract.contract import Contract
from web3.types import BlockData

from .interface import get_hyperdrive_config, get_hyperdrive_pool_info, parse_logs
from .receipt_breakdown import ReceiptBreakdown


class Hyperdrive:
    """End-point api for interfacing with Hyperdrive"""

    def __init__(self, web3: Web3, hyperdrive_contract: Contract, base_contract: Contract):
        self.web3 = web3
        self.hyperdrive_contract = hyperdrive_contract
        self.base_contract = base_contract

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

    async def async_open_long(
        self, trade_amount: int, agent: LocalAccount, slippage_tolerance: FixedPoint | None = None
    ) -> ReceiptBreakdown:
        """Contract call to open a long position.

        Arguments
        ---------
        trade_amount: int
            The size of the position, in base.
        agent: LocalAccount
            The account for the agent that is executing and signing the trade transaction.
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
        fn_args = (trade_amount, min_output, agent_checksum_address, as_underlying)
        if slippage_tolerance is not None:
            preview_result = smart_contract_preview_transaction(
                self.hyperdrive_contract, agent_checksum_address, "openLong", *fn_args
            )
            min_output = (
                FixedPoint(scaled_value=preview_result["bondProceeds"]) * (FixedPoint(1) - slippage_tolerance)
            ).scaled_value
            fn_args = (trade_amount, min_output, agent_checksum_address, as_underlying)
        tx_receipt = await async_smart_contract_transact(
            self.web3, self.hyperdrive_contract, agent, "openLong", *fn_args
        )
        trade_result = parse_logs(tx_receipt, self.hyperdrive_contract, "openLong")
        return trade_result

    # FIXME: TODO: other async trades

    # FIXME: TODO:
    # def get_max_long(budget):
    #     pyperdrive.get_max_long(...)

    # FIXME: TODO:
    # def get_max_short(budget):
    #     pyperdrive.get_max_short(...)

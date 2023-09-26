"""High-level interface for the Hyperdrive market"""
from __future__ import annotations

import copy
import os
from typing import Any

import eth_utils
import pyperdrive
from eth_account.signers.local import LocalAccount
from eth_typing import BlockNumber
from ethpy import EthConfig, build_eth_config
from ethpy.base import (
    async_smart_contract_transact,
    get_account_balance,
    smart_contract_preview_transaction,
    smart_contract_read,
)
from ethpy.hyperdrive.addresses import HyperdriveAddresses
from fixedpointmath import FixedPoint
from pyperdrive.types import Fees, PoolConfig, PoolInfo
from web3 import Web3
from web3.types import BlockData, Timestamp

from .addresses import fetch_hyperdrive_address_from_uri
from .get_web3_and_hyperdrive_contracts import get_web3_and_hyperdrive_contracts
from .interface import (
    get_hyperdrive_checkpoint,
    get_hyperdrive_pool_config,
    get_hyperdrive_pool_info,
    parse_logs,
    process_hyperdrive_checkpoint,
    process_hyperdrive_pool_config,
    process_hyperdrive_pool_info,
)
from .receipt_breakdown import ReceiptBreakdown

# known issue where class properties aren't recognized as subscriptable
# https://github.com/pylint-dev/pylint/issues/5699
# pylint: disable=unsubscriptable-object


class HyperdriveInterface:
    """End-point api for interfacing with Hyperdrive."""

    # we expect to have many instance attributes since this is a large API
    # pylint: disable=too-many-instance-attributes

    def __init__(
        self,
        eth_config: EthConfig | None = None,
        addresses: HyperdriveAddresses | None = None,
    ) -> None:
        """The HyperdriveInterface API.

        HyperdriveInterface requires an EthConfig to initialize.
        If the user does not provide one, then it is constructed from environment variables.
        The user can optionally include an `artifacts` HyperdriveAddresses object.
        In this case, the `eth_config.artifacts_uri` variable is not used,
        and these Addresses are used instead.

        ## TODO: Change pyperdrive interface to take str OR python FixedPoint objs; use FixedPoint here.
        """
        if eth_config is None:
            eth_config = build_eth_config()
        self.config = eth_config
        if addresses is None:
            addresses = fetch_hyperdrive_address_from_uri(os.path.join(eth_config.artifacts_uri, "addresses.json"))
        self.web3, self.base_token_contract, self.hyperdrive_contract = get_web3_and_hyperdrive_contracts(
            self.config, addresses
        )
        self.last_state_block_number = copy.copy(self.current_block_number)
        self._contract_pool_config = get_hyperdrive_pool_config(self.hyperdrive_contract)
        self.pool_config = process_hyperdrive_pool_config(
            copy.deepcopy(self._contract_pool_config), self.hyperdrive_contract.address
        )
        self._contract_pool_info: dict[str, Any] = {}
        self._pool_info: dict[str, Any] = {}
        self._contract_latest_checkpoint: dict[str, int] = {}
        self._latest_checkpoint: dict[str, Any] = {}
        self.update_pool_info_and_checkpoint()  # fill these in initially

    @property
    def pool_info(self) -> dict[str, Any]:
        """Returns the current pool state info."""
        if self.current_block_number > self.last_state_block_number:
            self.last_state_block_number = copy.copy(self.current_block_number)
            self.update_pool_info_and_checkpoint()
        return self._pool_info

    @property
    def latest_checkpoint(self) -> dict[str, Any]:
        """Returns the latest checkpoint info."""
        if self.current_block_number > self.last_state_block_number:
            self.last_state_block_number = copy.copy(self.current_block_number)
            self.update_pool_info_and_checkpoint()
        return self._latest_checkpoint

    @property
    def current_block(self) -> BlockData:
        """The current block."""
        return self.web3.eth.get_block("latest")

    @property
    def current_block_number(self) -> BlockNumber:
        """The current block number."""
        current_block_number = self.current_block.get("number", None)
        if current_block_number is None:
            raise AssertionError("The current block has no number")
        return current_block_number

    @property
    def current_block_time(self) -> Timestamp:
        """The current block timestamp."""
        current_block_timestamp = self.current_block.get("timestamp", None)
        if current_block_timestamp is None:
            raise AssertionError("current_block_timestamp can not be None")
        return current_block_timestamp

    @property
    def spot_price(self) -> FixedPoint:
        """Get the current Hyperdrive pool spot price.

        Returns
        -------
        FixedPoint
            The current spot price.
        """
        pool_config_str = PoolConfig(
            base_token=self._contract_pool_config["baseToken"],
            initial_share_price=str(self._contract_pool_config["initialSharePrice"]),
            minimum_share_reserves=str(self._contract_pool_config["minimumShareReserves"]),
            position_duration=str(self._contract_pool_config["positionDuration"]),
            checkpoint_duration=str(self._contract_pool_config["checkpointDuration"]),
            time_stretch=str(self._contract_pool_config["timeStretch"]),
            governance=self._contract_pool_config["governance"],
            fee_collector=self._contract_pool_config["feeCollector"],
            fees=Fees(
                curve=str(self._contract_pool_config["fees"][0]),
                flat=str(self._contract_pool_config["fees"][1]),
                governance=str(self._contract_pool_config["fees"][2]),
            ),
            oracle_size=str(self._contract_pool_config["oracleSize"]),
            update_gap=str(self._contract_pool_config["updateGap"]),
        )
        pool_info_str = PoolInfo(
            share_reserves=str(self._contract_pool_info["shareReserves"]),
            bond_reserves=str(self._contract_pool_info["bondReserves"]),
            lp_total_supply=str(self._contract_pool_info["lpTotalSupply"]),
            share_price=str(self._contract_pool_info["sharePrice"]),
            longs_outstanding=str(self._contract_pool_info["longsOutstanding"]),
            long_average_maturity_time=str(self._contract_pool_info["longAverageMaturityTime"]),
            shorts_outstanding=str(self._contract_pool_info["shortsOutstanding"]),
            short_average_maturity_time=str(self._contract_pool_info["shortAverageMaturityTime"]),
            short_base_volume="0",  # TODO: remove this from Pyperdrive
            withdrawal_shares_ready_to_withdraw=str(self._contract_pool_info["withdrawalSharesReadyToWithdraw"]),
            withdrawal_shares_proceeds=str(self._contract_pool_info["withdrawalSharesProceeds"]),
            lp_share_price=str(self._contract_pool_info["lpSharePrice"]),
            long_exposure=str(self._contract_pool_info["longExposure"]),
        )
        spot_price = pyperdrive.get_spot_price(pool_config_str, pool_info_str)  # pylint: disable=no-member
        return FixedPoint(spot_price)

    def update_pool_info_and_checkpoint(self) -> None:
        """Update the cached pool info and latest checkpoint."""
        self._contract_pool_info = get_hyperdrive_pool_info(self.hyperdrive_contract, self.current_block_number)
        self._pool_info = process_hyperdrive_pool_info(
            copy.deepcopy(self._contract_pool_info),
            self.web3,
            self.hyperdrive_contract,
            self.pool_config["positionDuration"],
            self.current_block_number,
        )
        self._contract_latest_checkpoint = get_hyperdrive_checkpoint(
            self.hyperdrive_contract, self.current_block_number
        )
        self._latest_checkpoint = process_hyperdrive_checkpoint(
            copy.deepcopy(self._contract_latest_checkpoint), self.web3, self.current_block_number
        )

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
        maturity_time: int,
        slippage_tolerance: FixedPoint | None = None,
    ) -> ReceiptBreakdown:
        """Contract call to close a long position.

        Arguments
        ---------
        agent: LocalAccount
            The account for the agent that is executing and signing the trade transaction.
        trade_amount: FixedPoint
            The size of the position, in base.
        maturity_time: int
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
        min_output = 0
        as_underlying = True
        fn_args = (
            maturity_time,
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
                maturity_time,
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
        max_deposit = int(eth_utils.currency.MAX_WEI)
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

    async def async_close_short(
        self,
        agent: LocalAccount,
        trade_amount: FixedPoint,
        maturity_time: int,
        slippage_tolerance: FixedPoint | None = None,
    ) -> ReceiptBreakdown:
        """Contract call to close a short position.

        Arguments
        ---------
        agent: LocalAccount
            The account for the agent that is executing and signing the trade transaction.
        trade_amount: FixedPoint
            The size of the position, in base.
        maturity_time: int
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
        min_output = 0
        as_underlying = True
        fn_args = (
            maturity_time,
            trade_amount.scaled_value,
            min_output,
            agent_checksum_address,
            as_underlying,
        )
        if slippage_tolerance:
            preview_result = smart_contract_preview_transaction(
                self.hyperdrive_contract, agent_checksum_address, "closeShort", *fn_args
            )
            min_output = (
                FixedPoint(scaled_value=preview_result["value"]) * (FixedPoint(1) - slippage_tolerance)
            ).scaled_value
            fn_args = (maturity_time, trade_amount.scaled_value, min_output, agent_checksum_address, as_underlying)
        tx_receipt = await async_smart_contract_transact(
            self.web3, self.hyperdrive_contract, agent, "closeShort", *fn_args
        )
        trade_result = parse_logs(tx_receipt, self.hyperdrive_contract, "closeShort")
        return trade_result

    async def async_add_liquidity(
        self,
        agent: LocalAccount,
        trade_amount: FixedPoint,
        min_apr: FixedPoint,
        max_apr: FixedPoint,
    ) -> ReceiptBreakdown:
        """Contract call to add liquidity to the Hyperdrive pool.

        Arguments
        ---------
        agent: LocalAccount
            The account for the agent that is executing and signing the trade transaction.
        trade_amount: FixedPoint
            The size of the position, in base.
        min_apr: FixedPoint
            The minimum allowable APR after liquidity is added.
        max_apr: FixedPoint
            The maximum allowable APR after liquidity is added.

        Returns
        -------
        ReceiptBreakdown
            A dataclass containing the absolute values for token quantities changed
        """
        agent_checksum_address = Web3.to_checksum_address(agent.address)
        as_underlying = True
        fn_args = (
            trade_amount.scaled_value,
            min_apr.scaled_value,
            max_apr.scaled_value,
            agent_checksum_address,
            as_underlying,
        )
        tx_receipt = await async_smart_contract_transact(
            self.web3, self.hyperdrive_contract, agent, "addLiquidity", *fn_args
        )
        trade_result = parse_logs(tx_receipt, self.hyperdrive_contract, "addLiquidity")
        return trade_result

    async def async_remove_liquidity(
        self,
        agent: LocalAccount,
        trade_amount: FixedPoint,
    ) -> ReceiptBreakdown:
        """Contract call to remove liquidity from the Hyperdrive pool.

        Arguments
        ---------
        agent: LocalAccount
            The account for the agent that is executing and signing the trade transaction.
        trade_amount: FixedPoint
            The size of the position, in base.

        Returns
        -------
        ReceiptBreakdown
            A dataclass containing the absolute values for token quantities changed
        """
        agent_checksum_address = Web3.to_checksum_address(agent.address)
        min_output = 0
        as_underlying = True
        fn_args = (trade_amount.scaled_value, min_output, agent_checksum_address, as_underlying)
        tx_receipt = await async_smart_contract_transact(
            self.web3, self.hyperdrive_contract, agent, "removeLiquidity", *fn_args
        )
        trade_result = parse_logs(tx_receipt, self.hyperdrive_contract, "removeLiquidity")
        return trade_result

    async def async_redeem_withdraw_shares(
        self,
        agent: LocalAccount,
        trade_amount: FixedPoint,
    ) -> ReceiptBreakdown:
        """Contract call to redeem withdraw shares from Hyperdrive pool.

        This should be done after closing liquidity.

        .. note::
            This is not guaranteed to redeem all shares.  The pool will try to redeem as
            many as possible, up to the withdrawPool.readyToRedeem limit, without reverting.
            Only a min_output that is too high will cause a revert here, or trying to
            withdraw more shares than the user has obviously.

        Arguments
        ---------
        agent: LocalAccount
            The account for the agent that is executing and signing the trade transaction.
        trade_amount: FixedPoint
            The size of the position, in base.
        min_output: FixedPoint
            The minimum output amount

        Returns
        -------
        ReceiptBreakdown
            A dataclass containing the absolute values for token quantities changed
        """
        # for now, assume an underlying vault share price of at least 1, should be higher by a bit
        agent_checksum_address = Web3.to_checksum_address(agent.address)
        min_output = FixedPoint(scaled_value=1)
        as_underlying = True
        fn_args = (trade_amount.scaled_value, min_output.scaled_value, agent_checksum_address, as_underlying)
        tx_receipt = await async_smart_contract_transact(
            self.web3, self.hyperdrive_contract, agent, "redeemWithdrawalShares", *fn_args
        )
        trade_result = parse_logs(tx_receipt, self.hyperdrive_contract, "redeemWithdrawalShares")
        return trade_result

    def get_eth_base_balances(self, agent: LocalAccount) -> tuple[FixedPoint, FixedPoint]:
        """Get the agent's balance on the Hyperdrive & base contracts.

        Arguments
        ---------
        agent: LocalAccount
            The account for the agent that is executing and signing the trade transaction.

        Returns
        -------
        tuple[FixedPoint]
            A tuple containing the [agent_eth_balance, agent_base_balance]
        """
        agent_checksum_address = Web3.to_checksum_address(agent.address)
        agent_eth_balance = get_account_balance(self.web3, agent_checksum_address)
        agent_base_balance = smart_contract_read(
            self.base_token_contract,
            "balanceOf",
            agent_checksum_address,
        )["value"]
        return (FixedPoint(scaled_value=agent_eth_balance), FixedPoint(scaled_value=agent_base_balance))

    def get_max_long(self, budget: FixedPoint) -> FixedPoint:
        """Get the maximum allowable long for the given Hyperdrive pool and agent budget.

        Arguments
        ---------
        budget: FixedPoint
            How much money the agent is able to spend

        Returns
        -------
        FixedPoint
            The maximum long as a FixedPoint representation of a Solidity uint256 value.
        """
        # pylint: disable=no-member
        pool_config_str = PoolConfig(
            base_token=self._contract_pool_config["baseToken"],
            initial_share_price=str(self._contract_pool_config["initialSharePrice"]),
            minimum_share_reserves=str(self._contract_pool_config["minimumShareReserves"]),
            position_duration=str(self._contract_pool_config["positionDuration"]),
            checkpoint_duration=str(self._contract_pool_config["checkpointDuration"]),
            time_stretch=str(self._contract_pool_config["timeStretch"]),
            governance=self._contract_pool_config["governance"],
            fee_collector=self._contract_pool_config["feeCollector"],
            fees=Fees(
                curve=str(self._contract_pool_config["fees"][0]),
                flat=str(self._contract_pool_config["fees"][1]),
                governance=str(self._contract_pool_config["fees"][2]),
            ),
            oracle_size=str(self._contract_pool_config["oracleSize"]),
            update_gap=str(self._contract_pool_config["updateGap"]),
        )
        pool_info_str = PoolInfo(
            share_reserves=str(self._contract_pool_info["shareReserves"]),
            bond_reserves=str(self._contract_pool_info["bondReserves"]),
            lp_total_supply=str(self._contract_pool_info["lpTotalSupply"]),
            share_price=str(self._contract_pool_info["sharePrice"]),
            longs_outstanding=str(self._contract_pool_info["longsOutstanding"]),
            long_average_maturity_time=str(self._contract_pool_info["longAverageMaturityTime"]),
            shorts_outstanding=str(self._contract_pool_info["shortsOutstanding"]),
            short_average_maturity_time=str(self._contract_pool_info["shortAverageMaturityTime"]),
            short_base_volume="0",  # TODO: remove this from Pyperdrive
            withdrawal_shares_ready_to_withdraw=str(self._contract_pool_info["withdrawalSharesReadyToWithdraw"]),
            withdrawal_shares_proceeds=str(self._contract_pool_info["withdrawalSharesProceeds"]),
            lp_share_price=str(self._contract_pool_info["lpSharePrice"]),
            long_exposure=str(self._contract_pool_info["longExposure"]),
        )
        max_long = pyperdrive.get_max_long(
            pool_config_str,
            pool_info_str,
            str(budget.scaled_value),
            checkpoint_exposure=str(self.latest_checkpoint["longExposure"].scaled_value),
            maybe_max_iterations=None,
        )
        return FixedPoint(max_long)

    def get_max_short(self, budget: FixedPoint) -> FixedPoint:
        """Get the maximum allowable short for the given Hyperdrive pool and agent budget.

        Arguments
        ---------
        budget: FixedPoint
            How much money the agent is able to spend

        Returns
        -------
        FixedPoint
            The maximum long as a FixedPoint representation of a Solidity uint256 value.
        """
        # pylint: disable=no-member
        pool_config_str = PoolConfig(
            base_token=self._contract_pool_config["baseToken"],
            initial_share_price=str(self._contract_pool_config["initialSharePrice"]),
            minimum_share_reserves=str(self._contract_pool_config["minimumShareReserves"]),
            position_duration=str(self._contract_pool_config["positionDuration"]),
            checkpoint_duration=str(self._contract_pool_config["checkpointDuration"]),
            time_stretch=str(self._contract_pool_config["timeStretch"]),
            governance=self._contract_pool_config["governance"],
            fee_collector=self._contract_pool_config["feeCollector"],
            fees=Fees(
                curve=str(self._contract_pool_config["fees"][0]),
                flat=str(self._contract_pool_config["fees"][1]),
                governance=str(self._contract_pool_config["fees"][2]),
            ),
            oracle_size=str(self._contract_pool_config["oracleSize"]),
            update_gap=str(self._contract_pool_config["updateGap"]),
        )
        pool_info_str = PoolInfo(
            share_reserves=str(self._contract_pool_info["shareReserves"]),
            bond_reserves=str(self._contract_pool_info["bondReserves"]),
            lp_total_supply=str(self._contract_pool_info["lpTotalSupply"]),
            share_price=str(self._contract_pool_info["sharePrice"]),
            longs_outstanding=str(self._contract_pool_info["longsOutstanding"]),
            long_average_maturity_time=str(self._contract_pool_info["longAverageMaturityTime"]),
            shorts_outstanding=str(self._contract_pool_info["shortsOutstanding"]),
            short_average_maturity_time=str(self._contract_pool_info["shortAverageMaturityTime"]),
            short_base_volume="0",  # TODO: remove this from Pyperdrive
            withdrawal_shares_ready_to_withdraw=str(self._contract_pool_info["withdrawalSharesReadyToWithdraw"]),
            withdrawal_shares_proceeds=str(self._contract_pool_info["withdrawalSharesProceeds"]),
            lp_share_price=str(self._contract_pool_info["lpSharePrice"]),
            long_exposure=str(self._contract_pool_info["longExposure"]),
        )
        max_short = pyperdrive.get_max_short(
            pool_config_str,
            pool_info_str,
            str(budget.scaled_value),
            pool_info_str.share_price,
            maybe_conservative_price=None,
            maybe_max_iterations=None,
        )
        return FixedPoint(max_short)

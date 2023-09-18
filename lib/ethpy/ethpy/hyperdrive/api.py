"""High-level interface for the Hyperdrive market"""
from __future__ import annotations

from typing import Any

import eth_utils
import pyperdrive
from eth_account.signers.local import LocalAccount
from eth_typing import URI, BlockNumber
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

from .get_web3_and_hyperdrive_contracts import get_web3_and_hyperdrive_contracts
from .interface import get_hyperdrive_config, get_hyperdrive_pool_info, get_hyperdrive_checkpoint_info, parse_logs
from .receipt_breakdown import ReceiptBreakdown


class HyperdriveInterface:
    """End-point api for interfacing with Hyperdrive"""

    def __init__(
        self,
        eth_config: EthConfig | None = None,
        *,  # kw-args only from here forward
        artifacts: str | URI | HyperdriveAddresses | None = None,
        rpc_uri: str | URI | None = None,
        abi_dir: str | None = None,
    ) -> None:
        """The Hyperdrive API can be initialized with either an EthConfig,
        or strings corresponding to the required URIs and directories.

        ## TODO: Write out options for initializing HyperdriveInterface
            ## or: PR to fix this to happen behind the scenes in EthConfig
            ## or: Make an issue to fix EthConfig so that it handles all of this optional argument bullshit
        ## TODO: Change pyperdrive interface to take str OR python FixedPoint objs; use FixedPoint here.
        ## TODO: Add cached checkpoint & use that in get_max_long
        """
        if all([eth_config is None, artifacts is None, rpc_uri is None, abi_dir is None]):
            eth_config = build_eth_config()
        if eth_config is None:
            if artifacts is None or rpc_uri is None or abi_dir is None:
                raise AssertionError("if eth_config is None, then all of the remaining arguments must be set.")
            if isinstance(artifacts, HyperdriveAddresses):
                self.config = EthConfig("Not used", rpc_uri, abi_dir)
                addresses_arg = artifacts
            else:  # str or URI
                self.config = EthConfig(artifacts, rpc_uri, abi_dir)
                addresses_arg = None
        if eth_config is not None:
            if not all([artifacts is None, rpc_uri is None, abi_dir is None]):
                raise AssertionError("if eth_config is not None, then none of the remaining arguments can be set.")
            self.config = eth_config
        self.web3, self.base_token_contract, self.hyperdrive_contract = get_web3_and_hyperdrive_contracts(
            self.config, addresses_arg
        )
        self.pool_config = get_hyperdrive_config(self.hyperdrive_contract)
        self._pool_info = get_hyperdrive_pool_info(self.web3, self.hyperdrive_contract, self.current_block_number)
        self._latest_checkpoint = get_hyperdrive_checkpoint_info(self.web3, self.hyperdrive_contract, self.current_block_number)
        self.last_state_block = self.web3.eth.get_block("latest")

    @property
    def pool_info(self):
        """Returns the current pool state info"""
        if self.current_block > self.last_state_block:
            self.last_state_block = self.current_block
            setattr(
                self,
                "_pool_info",
                get_hyperdrive_pool_info(self.web3, self.hyperdrive_contract, self.current_block_number),
            )
        return self._pool_info
    
    @property
    def latest_checkpoint(self):

    @property
    def current_block(self) -> BlockData:
        """The current block number"""
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
            base_token=str(self.pool_config["base_token"]),
            initial_share_price=str(self.pool_config["initial_share_price"]),
            minimum_share_reserves=str(self.pool_config["minimum_share_reserves"]),
            position_duration=str(self.pool_config["position_duration"]),
            checkpoint_duration=str(self.pool_config["checkpoint_duration"]),
            time_stretch=str(self.pool_config["time_stretch"]),
            governance=str(self.pool_config["governance"]),
            fee_collector=str(self.pool_config["fee_collector"]),
            fees=Fees(
                curve=str(self.pool_config["fees"]["curve"]),
                flat=str(self.pool_config["fees"]["flat"]),
                governance=str(self.pool_config["fees"]["governance"]),
            ),
            oracle_size=str(self.pool_config["oracle_size"]),
            update_gap=str(self.pool_config["update_gap"]),
        )
        pool_info_str = PoolInfo(
            share_reserves=str(self.pool_info["share_reserves"]),
            bond_reserves=str(self.pool_info["bond_reserves"]),
            lp_total_supply=str(self.pool_info["lp_total_supply"]),
            share_price=str(self.pool_info["share_price"]),
            longs_outstanding=str(self.pool_info["longs_outstanding"]),
            long_average_maturity_time=str(self.pool_info["long_average_maturity_time"]),
            shorts_outstanding=str(self.pool_info["shorts_outstanding"]),
            short_average_maturity_time=str(self.pool_info["short_average_maturity_time"]),
            short_base_volume=str(self.pool_info["short_base_volume"]),
            withdrawal_shares_ready_to_withdraw=str(self.pool_info["withdrawal_shares_ready_to_withdraw"]),
            withdrawal_shares_proceeds=str(self.pool_info["withdrawal_shares_proceeds"]),
            lp_share_price=str(self.pool_info["lp_share_price"]),
            long_exposure=str(self.pool_info["long_exposure"]),
        )
        spot_price = pyperdrive.get_spot_price(pool_config_str, pool_info_str)
        return FixedPoint(spot_price)

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
        min_output = 0
        as_underlying = True
        fn_args = (
            int(maturity_time),
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
                int(maturity_time),
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

    async def async_close_short(
        self,
        agent: LocalAccount,
        trade_amount: FixedPoint,
        maturity_time: FixedPoint,
        slippage_tolerance: FixedPoint | None = None,
    ) -> ReceiptBreakdown:
        """Contract call to close a short position.

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
        min_output = 0
        as_underlying = True
        fn_args = (
            int(maturity_time),
            trade_amount,
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
            fn_args = (int(maturity_time), trade_amount, min_output, agent_checksum_address, as_underlying)
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
        fn_args = (trade_amount, min_apr, max_apr, agent_checksum_address, as_underlying)
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
        fn_args = (trade_amount, min_output, agent_checksum_address, as_underlying)
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
        min_output = FixedPoint(1)
        as_underlying = True
        fn_args = (trade_amount, min_output.scaled_value, agent_checksum_address, as_underlying)
        tx_receipt = await async_smart_contract_transact(
            self.web3, self.hyperdrive_contract, agent, "redeemWithdrawalShares", *fn_args
        )
        trade_result = parse_logs(tx_receipt, self.hyperdrive_contract, "redeemWithdrawalShares")
        return trade_result

    def balance_of(self, agent: LocalAccount) -> tuple[FixedPoint]:
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
        # TODO: automate acquision of current_exposure inside of pyperdrive
        pool_config_str = PoolConfig(
            base_token=str(self.pool_config["base_token"]),
            initial_share_price=str(self.pool_config["initial_share_price"]),
            minimum_share_reserves=str(self.pool_config["minimum_share_reserves"]),
            position_duration=str(self.pool_config["position_duration"]),
            checkpoint_duration=str(self.pool_config["checkpoint_duration"]),
            time_stretch=str(self.pool_config["time_stretch"]),
            governance=str(self.pool_config["governance"]),
            fee_collector=str(self.pool_config["fee_collector"]),
            fees=Fees(
                curve=str(self.pool_config["fees"]["curve"]),
                flat=str(self.pool_config["fees"]["flat"]),
                governance=str(self.pool_config["fees"]["governance"]),
            ),
            oracle_size=str(self.pool_config["oracle_size"]),
            update_gap=str(self.pool_config["update_gap"]),
        )
        pool_info_str = PoolInfo(
            share_reserves=str(self.pool_info["share_reserves"]),
            bond_reserves=str(self.pool_info["bond_reserves"]),
            lp_total_supply=str(self.pool_info["lp_total_supply"]),
            share_price=str(self.pool_info["share_price"]),
            longs_outstanding=str(self.pool_info["longs_outstanding"]),
            long_average_maturity_time=str(self.pool_info["long_average_maturity_time"]),
            shorts_outstanding=str(self.pool_info["shorts_outstanding"]),
            short_average_maturity_time=str(self.pool_info["short_average_maturity_time"]),
            short_base_volume=str(self.pool_info["short_base_volume"]),
            withdrawal_shares_ready_to_withdraw=str(self.pool_info["withdrawal_shares_ready_to_withdraw"]),
            withdrawal_shares_proceeds=str(self.pool_info["withdrawal_shares_proceeds"]),
            lp_share_price=str(self.pool_info["lp_share_price"]),
            long_exposure=str(self.pool_info["long_exposure"]),
        )
        max_long = pyperdrive.get_max_long(pool_config_str, pool_info_str, str(budget), checkpoint_exposure="0")
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
            base_token=str(self.pool_config["base_token"]),
            initial_share_price=str(self.pool_config["initial_share_price"]),
            minimum_share_reserves=str(self.pool_config["minimum_share_reserves"]),
            position_duration=str(self.pool_config["position_duration"]),
            checkpoint_duration=str(self.pool_config["checkpoint_duration"]),
            time_stretch=str(self.pool_config["time_stretch"]),
            governance=str(self.pool_config["governance"]),
            fee_collector=str(self.pool_config["fee_collector"]),
            fees=Fees(
                curve=str(self.pool_config["fees"]["curve"]),
                flat=str(self.pool_config["fees"]["flat"]),
                governance=str(self.pool_config["fees"]["governance"]),
            ),
            oracle_size=str(self.pool_config["oracle_size"]),
            update_gap=str(self.pool_config["update_gap"]),
        )
        pool_info_str = PoolInfo(
            share_reserves=str(self.pool_info["share_reserves"]),
            bond_reserves=str(self.pool_info["bond_reserves"]),
            lp_total_supply=str(self.pool_info["lp_total_supply"]),
            share_price=str(self.pool_info["share_price"]),
            longs_outstanding=str(self.pool_info["longs_outstanding"]),
            long_average_maturity_time=str(self.pool_info["long_average_maturity_time"]),
            shorts_outstanding=str(self.pool_info["shorts_outstanding"]),
            short_average_maturity_time=str(self.pool_info["short_average_maturity_time"]),
            short_base_volume=str(self.pool_info["short_base_volume"]),
            withdrawal_shares_ready_to_withdraw=str(self.pool_info["withdrawal_shares_ready_to_withdraw"]),
            withdrawal_shares_proceeds=str(self.pool_info["withdrawal_shares_proceeds"]),
            lp_share_price=str(self.pool_info["lp_share_price"]),
            long_exposure=str(self.pool_info["long_exposure"]),
        )
        max_short = pyperdrive.get_max_short(pool_config_str, pool_info_str, str(budget), pool_info_str.share_price)
        return FixedPoint(max_short)

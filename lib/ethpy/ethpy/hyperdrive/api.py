"""High-level interface for the Hyperdrive market."""
from __future__ import annotations

import copy
import os
from datetime import datetime
from typing import Any

import eth_utils
import pyperdrive
from eth_account.signers.local import LocalAccount
from eth_typing import BlockNumber
from ethpy import EthConfig, build_eth_config
from ethpy.base import (BaseInterface, async_smart_contract_transact,
                        get_account_balance,
                        initialize_web3_with_http_provider, load_all_abis,
                        smart_contract_preview_transaction,
                        smart_contract_read)
from fixedpointmath import FixedPoint
from pyperdrive.types import Fees, PoolConfig, PoolInfo
from web3 import Web3
from web3.contract.contract import Contract
from web3.types import BlockData, Nonce, Timestamp

from .addresses import HyperdriveAddresses, fetch_hyperdrive_address_from_uri
from .interface import (get_hyperdrive_checkpoint, get_hyperdrive_pool_config,
                        get_hyperdrive_pool_info, parse_logs,
                        process_hyperdrive_checkpoint,
                        process_hyperdrive_pool_config,
                        process_hyperdrive_pool_info)
from .receipt_breakdown import ReceiptBreakdown

# known issue where class properties aren't recognized as subscriptable
# https://github.com/pylint-dev/pylint/issues/5699
# pylint: disable=unsubscriptable-object


class HyperdriveInterface(BaseInterface[HyperdriveAddresses]):
    """End-point api for interfacing with Hyperdrive."""

    # TODO: we expect to have many instance attributes & methods since this is a large API
    # although we should still break this up into a folder of files
    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-many-public-methods

    def __init__(
        self,
        eth_config: EthConfig | None = None,
        addresses: HyperdriveAddresses | None = None,
        web3: Web3 | None = None,
    ) -> None:
        """The HyperdriveInterface API.

        HyperdriveInterface requires an EthConfig to initialize.
        If the user does not provide one, then it is constructed from environment variables.
        The user can optionally include an `artifacts` HyperdriveAddresses object.
        In this case, the `eth_config.artifacts_uri` variable is not used,
        and these Addresses are used instead.

        .. todo::
            Change pyperdrive interface to take str OR python FixedPoint objs;
            use FixedPoint here.
        """
        if eth_config is None:
            eth_config = build_eth_config()
        self.config = eth_config
        if addresses is None:
            addresses = fetch_hyperdrive_address_from_uri(os.path.join(eth_config.artifacts_uri, "addresses.json"))
        if web3 is None:
            web3 = initialize_web3_with_http_provider(eth_config.rpc_uri, reset_provider=False)
        self.web3 = web3
        abis = load_all_abis(eth_config.abi_dir)
        # set up the ERC20 contract for minting base tokens
        self.base_token_contract: Contract = web3.eth.contract(
            abi=abis["ERC20Mintable"], address=web3.to_checksum_address(addresses.base_token)
        )
        # set up hyperdrive contract
        self.hyperdrive_contract: Contract = web3.eth.contract(
            abi=abis["IHyperdrive"], address=web3.to_checksum_address(addresses.mock_hyperdrive)
        )
        self.last_state_block_number = copy.copy(self.current_block_number)
        # get yield (variable rate) pool contract
        # TODO: In the future we want to switch to a single IERC4626Hyperdrive ABI
        data_provider_contract: Contract = web3.eth.contract(
            abi=abis["ERC4626DataProvider"], address=web3.to_checksum_address(addresses.mock_hyperdrive)
        )
        yield_address = smart_contract_read(data_provider_contract, "pool")["value"]
        self.yield_contract: Contract = web3.eth.contract(
            abi=abis["MockERC4626"], address=web3.to_checksum_address(yield_address)
        )
        # pool config is static
        self._contract_pool_config = get_hyperdrive_pool_config(self.hyperdrive_contract)
        self.pool_config = process_hyperdrive_pool_config(
            copy.deepcopy(self._contract_pool_config), self.hyperdrive_contract.address
        )
        # the following attributes will change when trades occur
        self._contract_pool_info: dict[str, Any] = {}
        self._pool_info: dict[str, Any] = {}
        self._contract_latest_checkpoint: dict[str, int] = {}
        self._latest_checkpoint: dict[str, Any] = {}
        # fill in initial cache
        self._ensure_current_state(override=True)
        super().__init__(eth_config, addresses)

    @property
    def pool_info(self) -> dict[str, Any]:
        """Returns the current pool state info."""
        self._ensure_current_state()
        return self._pool_info

    @property
    def latest_checkpoint(self) -> dict[str, Any]:
        """Returns the latest checkpoint info."""
        self._ensure_current_state()
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
    def position_duration_in_years(self) -> FixedPoint:
        """Returns the pool config position duration as a fraction of a year.

        This "annualized" time value is used in some calculations, such as the Fixed APR.
        """
        return (
            FixedPoint(self.pool_config["positionDuration"])
            / FixedPoint(60)
            / FixedPoint(60)
            / FixedPoint(24)
            / FixedPoint(365)
        )

    @property
    def fixed_rate(self) -> FixedPoint:
        """Returns the market fixed rate.

        Follows the formula:

        .. math::
            r = ((1/p)-1)/t = (1-p)/(pt)
        """
        return (FixedPoint(1) - self.spot_price) / (self.spot_price * self.position_duration_in_years)

    @property
    def variable_rate(self) -> FixedPoint:
        """Returns the market variable rate."""
        rate = smart_contract_read(self.yield_contract, "getRate")["value"]
        return FixedPoint(scaled_value=rate)

    @property
    def seconds_since_latest_checkpoint(self) -> int:
        """Return the amount of seconds that have passed since the latest checkpoint.
        The time is rounded to the nearest second.
        """
        self._ensure_current_state()
        latest_checkpoint_datetime: datetime = self.latest_checkpoint["timestamp"]
        current_block_datetime = datetime.fromtimestamp(int(self.current_block_time))
        return int(round((current_block_datetime - latest_checkpoint_datetime).total_seconds()))

    @property
    def spot_price(self) -> FixedPoint:
        """Get the current Hyperdrive pool spot price.

        Returns
        -------
        FixedPoint
            The current spot price.
        """
        self._ensure_current_state()
        pool_config_str = self._serialized_pool_config()
        pool_info_str = self._serialized_pool_info()
        spot_price = pyperdrive.get_spot_price(pool_config_str, pool_info_str)  # pylint: disable=no-member
        return FixedPoint(scaled_value=int(spot_price))

    def get_out_for_in(
        self,
        amount_in: FixedPoint,
        shares_in: bool,
    ) -> FixedPoint:
        """Gets the amount of an asset for a given amount in of the other.

        Arguments
        ---------
        amount_in : FixedPoint
            The aount in.
        shares_in : bool
            True if the asset in is shares, False if it is bonds.

        Returns
        -------
        FixedPoint
            The aount out.
        """
        pool_config_str = self._serialized_pool_config()
        pool_info_str = self._serialized_pool_info()
        out_for_in = pyperdrive.get_out_for_in(pool_config_str, pool_info_str, str(amount_in.scaled_value), shares_in) # pylint: disable=no-member
        return FixedPoint(scaled_value=int(out_for_in))

    def get_in_for_out(
        self,
        amount_out: FixedPoint,
        shares_out: bool,
    ) -> FixedPoint:
        """Gets the amount of an asset for a given amount out of the other.

        Arguments
        ---------
        amount_out : FixedPoint
            The aount out.
        shares_out : bool
            True if the asset out is shares, False if it is bonds.

        Returns
        -------
        FixedPoint
            The aount in.
        """
        pool_config_str = self._serialized_pool_config()
        pool_info_str = self._serialized_pool_info()
        in_for_out = pyperdrive.get_in_for_out(pool_config_str, pool_info_str, str(amount_out.scaled_value), shares_out) # pylint: disable=no-member
        return FixedPoint(scaled_value=int(in_for_out))


    def _serialized_pool_config(self) -> PoolConfig:
        pool_config_str = PoolConfig(
            baseToken=self._contract_pool_config["baseToken"],
            initialSharePrice=str(self._contract_pool_config["initialSharePrice"]),
            minimumShareReserves=str(self._contract_pool_config["minimumShareReserves"]),
            minimumTransactionAmount=str(self._contract_pool_config["minimumTransactionAmount"]),
            positionDuration=str(self._contract_pool_config["positionDuration"]),
            checkpointDuration=str(self._contract_pool_config["checkpointDuration"]),
            timeStretch=str(self._contract_pool_config["timeStretch"]),
            governance=self._contract_pool_config["governance"],
            feeCollector=self._contract_pool_config["feeCollector"],
            Fees=Fees(
                curve=str(self._contract_pool_config["fees"][0]),
                flat=str(self._contract_pool_config["fees"][1]),
                governance=str(self._contract_pool_config["fees"][2]),
            ),
            oracleSize=str(self._contract_pool_config["oracleSize"]),
            updateGap=str(self._contract_pool_config["updateGap"]),
        )
        return pool_config_str

    def _serialized_pool_info(self) -> PoolInfo:
        pool_info_str = PoolInfo(
            shareReserves=str(self._contract_pool_info["shareReserves"]),
            shareAdjustment=str(self._contract_pool_info["shareAdjustment"]),
            bondReserves=str(self._contract_pool_info["bondReserves"]),
            lpTotalSupply=str(self._contract_pool_info["lpTotalSupply"]),
            sharePrice=str(self._contract_pool_info["sharePrice"]),
            longsOutstanding=str(self._contract_pool_info["longsOutstanding"]),
            longAverageMaturityTime=str(self._contract_pool_info["longAverageMaturityTime"]),
            shortsOutstanding=str(self._contract_pool_info["shortsOutstanding"]),
            shortAverageMaturityTime=str(self._contract_pool_info["shortAverageMaturityTime"]),
            withdrawalSharesReadyToWithdraw=str(self._contract_pool_info["withdrawalSharesReadyToWithdraw"]),
            withdrawalSharesProceeds=str(self._contract_pool_info["withdrawalSharesProceeds"]),
            lpSharePrice=str(self._contract_pool_info["lpSharePrice"]),
            longExposure=str(self._contract_pool_info["longExposure"]),
        )
        return pool_info_str


    def _ensure_current_state(self, override: bool = False) -> None:
        """Update the cached pool info and latest checkpoint if needed.

        Attributes
        ----------
        override : bool
            If True, then reset the variables even if it is not needed.

        """
        if self.current_block_number > self.last_state_block_number or override:
            self.last_state_block_number = copy.copy(self.current_block_number)
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
                copy.deepcopy(self._contract_latest_checkpoint),
                self.web3,
                self.current_block_number,
            )


    def bonds_given_shares_and_rate(self, target_rate: FixedPoint) -> FixedPoint:
        r"""Returns the bond reserves for the market share reserves
        and a given fixed rate.


        The calculation is based on the formula: .. math::
            mu * (z - zeta) * (1 + apr * t) ** (1 / tau)

        Arguments
        ---------
        target_rate : FixedPoint
            The target apr for which to calculate the bond reserves given the pools current share
            reserves.
        """

        mu: FixedPoint = self.pool_config["initialSharePrice"]
        z_minus_zeta: FixedPoint = self.pool_info["shareReserves"] - self.pool_info["shareAdjustment"]
        t = self.position_duration_in_years
        one_over_tau: FixedPoint = self.pool_config["timeStretch"]
        adjusted_apr = (FixedPoint("1") + target_rate*t)

        return mu * z_minus_zeta * adjusted_apr ** one_over_tau


    async def async_open_long(
        self,
        agent: LocalAccount,
        trade_amount: FixedPoint,
        slippage_tolerance: FixedPoint | None = None,
        nonce: Nonce | None = None,
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
        nonce: Nonce | None
            An optional explicit nonce to set with the transaction

        Returns
        -------
        ReceiptBreakdown
            A dataclass containing the maturity time and the absolute values for token quantities changed
        """
        agent_checksum_address = Web3.to_checksum_address(agent.address)
        # min_share_price : int
        #   Minium share price at which to open the long.
        #   This allows traders to protect themselves from opening a long in
        #   a checkpoint where negative interest has accrued.
        min_share_price = 0  # TODO: give the user access to this parameter
        min_output = 0  # TODO: give the user access to this parameter
        as_underlying = True
        fn_args = (
            trade_amount.scaled_value,
            min_output,
            min_share_price,
            agent_checksum_address,
            as_underlying,
        )
        if slippage_tolerance is not None:
            preview_result = smart_contract_preview_transaction(
                self.hyperdrive_contract, agent_checksum_address, "openLong", *fn_args
            )
            min_output = (
                FixedPoint(scaled_value=preview_result["bondProceeds"]) * (FixedPoint(1) - slippage_tolerance)
            ).scaled_value
            fn_args = (
                trade_amount.scaled_value,
                min_output,
                min_share_price,
                agent_checksum_address,
                as_underlying,
            )
        tx_receipt = await async_smart_contract_transact(
            self.web3, self.hyperdrive_contract, agent, "openLong", *fn_args, nonce=nonce
        )
        trade_result = parse_logs(tx_receipt, self.hyperdrive_contract, "openLong")
        return trade_result

    # pylint: disable=too-many-arguments
    async def async_close_long(
        self,
        agent: LocalAccount,
        trade_amount: FixedPoint,
        maturity_time: int,
        slippage_tolerance: FixedPoint | None = None,
        nonce: Nonce | None = None,
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
        nonce: Nonce | None
            An optional explicit nonce to set with the transaction

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
            self.web3, self.hyperdrive_contract, agent, "closeLong", *fn_args, nonce=nonce
        )
        trade_result = parse_logs(tx_receipt, self.hyperdrive_contract, "closeLong")
        return trade_result

    async def async_open_short(
        self,
        agent: LocalAccount,
        trade_amount: FixedPoint,
        slippage_tolerance: FixedPoint | None = None,
        nonce: Nonce | None = None,
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
        nonce: Nonce | None
            An optional explicit nonce to set with the transaction

        Returns
        -------
        ReceiptBreakdown
            A dataclass containing the maturity time and the absolute values for token quantities changed
        """
        agent_checksum_address = Web3.to_checksum_address(agent.address)
        as_underlying = True
        max_deposit = int(eth_utils.currency.MAX_WEI)
        # min_share_price : int
        #   Minium share price at which to open the short.
        #   This allows traders to protect themselves from opening a long in
        #   a checkpoint where negative interest has accrued.
        min_share_price = 0  # TODO: give the user access to this parameter
        fn_args = (
            trade_amount.scaled_value,
            max_deposit,
            min_share_price,
            agent_checksum_address,
            as_underlying,
        )
        if slippage_tolerance:
            preview_result = smart_contract_preview_transaction(
                self.hyperdrive_contract, agent_checksum_address, "openShort", *fn_args
            )
            max_deposit = (
                FixedPoint(scaled_value=preview_result["traderDeposit"]) * (FixedPoint(1) + slippage_tolerance)
            ).scaled_value
        fn_args = (
            trade_amount.scaled_value,
            max_deposit,
            min_share_price,
            agent_checksum_address,
            as_underlying,
        )
        tx_receipt = await async_smart_contract_transact(
            self.web3, self.hyperdrive_contract, agent, "openShort", *fn_args, nonce=nonce
        )
        trade_result = parse_logs(tx_receipt, self.hyperdrive_contract, "openShort")
        return trade_result

    # pylint: disable=too-many-arguments
    async def async_close_short(
        self,
        agent: LocalAccount,
        trade_amount: FixedPoint,
        maturity_time: int,
        slippage_tolerance: FixedPoint | None = None,
        nonce: Nonce | None = None,
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
        nonce: Nonce | None
            An optional explicit nonce to set with the transaction

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
            fn_args = (
                maturity_time,
                trade_amount.scaled_value,
                min_output,
                agent_checksum_address,
                as_underlying,
            )
        tx_receipt = await async_smart_contract_transact(
            self.web3, self.hyperdrive_contract, agent, "closeShort", *fn_args, nonce=nonce
        )
        trade_result = parse_logs(tx_receipt, self.hyperdrive_contract, "closeShort")
        return trade_result

    # pylint: disable=too-many-arguments
    async def async_add_liquidity(
        self,
        agent: LocalAccount,
        trade_amount: FixedPoint,
        min_apr: FixedPoint,
        max_apr: FixedPoint,
        nonce: Nonce | None = None,
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
        nonce: Nonce | None
            An optional explicit nonce to set with the transaction

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
            self.web3, self.hyperdrive_contract, agent, "addLiquidity", *fn_args, nonce=nonce
        )
        trade_result = parse_logs(tx_receipt, self.hyperdrive_contract, "addLiquidity")
        return trade_result

    async def async_remove_liquidity(
        self,
        agent: LocalAccount,
        trade_amount: FixedPoint,
        nonce: Nonce | None = None,
    ) -> ReceiptBreakdown:
        """Contract call to remove liquidity from the Hyperdrive pool.

        Arguments
        ---------
        agent: LocalAccount
            The account for the agent that is executing and signing the trade transaction.
        trade_amount: FixedPoint
            The size of the position, in base.
        nonce: Nonce | None
            An optional explicit nonce to set with the transaction

        Returns
        -------
        ReceiptBreakdown
            A dataclass containing the absolute values for token quantities changed
        """
        agent_checksum_address = Web3.to_checksum_address(agent.address)
        min_output = 0
        as_underlying = True
        fn_args = (
            trade_amount.scaled_value,
            min_output,
            agent_checksum_address,
            as_underlying,
        )
        tx_receipt = await async_smart_contract_transact(
            self.web3, self.hyperdrive_contract, agent, "removeLiquidity", *fn_args, nonce=nonce
        )
        trade_result = parse_logs(tx_receipt, self.hyperdrive_contract, "removeLiquidity")
        return trade_result

    async def async_redeem_withdraw_shares(
        self,
        agent: LocalAccount,
        trade_amount: FixedPoint,
        nonce: Nonce | None = None,
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
        nonce: Nonce | None
            An optional explicit nonce to set with the transaction

        Returns
        -------
        ReceiptBreakdown
            A dataclass containing the absolute values for token quantities changed
        """
        # for now, assume an underlying vault share price of at least 1, should be higher by a bit
        agent_checksum_address = Web3.to_checksum_address(agent.address)
        min_output = FixedPoint(scaled_value=1)
        as_underlying = True
        fn_args = (
            trade_amount.scaled_value,
            min_output.scaled_value,
            agent_checksum_address,
            as_underlying,
        )
        tx_receipt = await async_smart_contract_transact(
            self.web3, self.hyperdrive_contract, agent, "redeemWithdrawalShares", *fn_args, nonce=nonce
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
        return (
            FixedPoint(scaled_value=agent_eth_balance),
            FixedPoint(scaled_value=agent_base_balance),
        )

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
        self._ensure_current_state()
        pool_config_str = PoolConfig(
            baseToken=self._contract_pool_config["baseToken"],
            initialSharePrice=str(self._contract_pool_config["initialSharePrice"]),
            minimumShareReserves=str(self._contract_pool_config["minimumShareReserves"]),
            minimumTransactionAmount=str(self._contract_pool_config["minimumTransactionAmount"]),
            positionDuration=str(self._contract_pool_config["positionDuration"]),
            checkpointDuration=str(self._contract_pool_config["checkpointDuration"]),
            timeStretch=str(self._contract_pool_config["timeStretch"]),
            governance=self._contract_pool_config["governance"],
            feeCollector=self._contract_pool_config["feeCollector"],
            Fees=Fees(
                curve=str(self._contract_pool_config["fees"][0]),
                flat=str(self._contract_pool_config["fees"][1]),
                governance=str(self._contract_pool_config["fees"][2]),
            ),
            oracleSize=str(self._contract_pool_config["oracleSize"]),
            updateGap=str(self._contract_pool_config["updateGap"]),
        )
        pool_info_str = PoolInfo(
            shareReserves=str(self._contract_pool_info["shareReserves"]),
            shareAdjustment=str(self._contract_pool_info["shareAdjustment"]),
            bondReserves=str(self._contract_pool_info["bondReserves"]),
            lpTotalSupply=str(self._contract_pool_info["lpTotalSupply"]),
            sharePrice=str(self._contract_pool_info["sharePrice"]),
            longsOutstanding=str(self._contract_pool_info["longsOutstanding"]),
            longAverageMaturityTime=str(self._contract_pool_info["longAverageMaturityTime"]),
            shortsOutstanding=str(self._contract_pool_info["shortsOutstanding"]),
            shortAverageMaturityTime=str(self._contract_pool_info["shortAverageMaturityTime"]),
            withdrawalSharesReadyToWithdraw=str(self._contract_pool_info["withdrawalSharesReadyToWithdraw"]),
            withdrawalSharesProceeds=str(self._contract_pool_info["withdrawalSharesProceeds"]),
            lpSharePrice=str(self._contract_pool_info["lpSharePrice"]),
            longExposure=str(self._contract_pool_info["longExposure"]),
        )
        # pylint: disable=no-member
        max_long = pyperdrive.get_max_long(
            pool_config_str,
            pool_info_str,
            str(budget.scaled_value),
            checkpoint_exposure=str(self.latest_checkpoint["longExposure"].scaled_value),
            maybe_max_iterations=None,
        )
        return FixedPoint(scaled_value=int(max_long))

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
        self._ensure_current_state()
        pool_config_str = PoolConfig(
            baseToken=self._contract_pool_config["baseToken"],
            initialSharePrice=str(self._contract_pool_config["initialSharePrice"]),
            minimumShareReserves=str(self._contract_pool_config["minimumShareReserves"]),
            minimumTransactionAmount=str(self._contract_pool_config["minimumTransactionAmount"]),
            positionDuration=str(self._contract_pool_config["positionDuration"]),
            checkpointDuration=str(self._contract_pool_config["checkpointDuration"]),
            timeStretch=str(self._contract_pool_config["timeStretch"]),
            governance=self._contract_pool_config["governance"],
            feeCollector=self._contract_pool_config["feeCollector"],
            Fees=Fees(
                curve=str(self._contract_pool_config["fees"][0]),
                flat=str(self._contract_pool_config["fees"][1]),
                governance=str(self._contract_pool_config["fees"][2]),
            ),
            oracleSize=str(self._contract_pool_config["oracleSize"]),
            updateGap=str(self._contract_pool_config["updateGap"]),
        )
        pool_info_str = PoolInfo(
            shareReserves=str(self._contract_pool_info["shareReserves"]),
            shareAdjustment=str(self._contract_pool_info["shareAdjustment"]),
            bondReserves=str(self._contract_pool_info["bondReserves"]),
            lpTotalSupply=str(self._contract_pool_info["lpTotalSupply"]),
            sharePrice=str(self._contract_pool_info["sharePrice"]),
            longsOutstanding=str(self._contract_pool_info["longsOutstanding"]),
            longAverageMaturityTime=str(self._contract_pool_info["longAverageMaturityTime"]),
            shortsOutstanding=str(self._contract_pool_info["shortsOutstanding"]),
            shortAverageMaturityTime=str(self._contract_pool_info["shortAverageMaturityTime"]),
            withdrawalSharesReadyToWithdraw=str(self._contract_pool_info["withdrawalSharesReadyToWithdraw"]),
            withdrawalSharesProceeds=str(self._contract_pool_info["withdrawalSharesProceeds"]),
            lpSharePrice=str(self._contract_pool_info["lpSharePrice"]),
            longExposure=str(self._contract_pool_info["longExposure"]),
        )
        # pylint: disable=no-member
        max_short = pyperdrive.get_max_short(
            pool_config_str,
            pool_info_str,
            str(budget.scaled_value),
            pool_info_str.sharePrice,
            checkpoint_exposure=str(self.latest_checkpoint["longExposure"].scaled_value),
            maybe_conservative_price=None,
            maybe_max_iterations=None,
        )
        return FixedPoint(scaled_value=int(max_short))

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
from fixedpointmath import FixedPoint
from pyperdrive.types import Fees, PoolConfig, PoolInfo
from web3 import Web3
from web3.contract.contract import Contract
from web3.types import BlockData, Timestamp

from ethpy import EthConfig, build_eth_config
from ethpy.base import (
    BaseInterface,
    async_smart_contract_transact,
    get_account_balance,
    initialize_web3_with_http_provider,
    load_all_abis,
    smart_contract_preview_transaction,
    smart_contract_read,
)

from .addresses import HyperdriveAddresses, fetch_hyperdrive_address_from_uri
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
        """Initialize the HyperdriveInterface API.

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
    def variable_rate(self) -> None:
        """Returns the market variable rate.

        .. todo::
            - Need the address for the yield source (e.g. MockERC4626)
            - then should be able to do a contract read call (e.g. getRate)
            issue #913
        """
        return None

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
        pool_config_str = self._stringify_pool_config(self._contract_pool_config)
        pool_info_str = self._stringify_pool_info(self._contract_pool_info)
        spot_price = pyperdrive.get_spot_price(pool_config_str, pool_info_str)  # pylint: disable=no-member
        return FixedPoint(scaled_value=int(spot_price))

    def _stringify_pool_config(self, pool_config_dict: dict[str, Any]) -> PoolConfig:
        return PoolConfig(
            baseToken=pool_config_dict["baseToken"],
            initialSharePrice=str(pool_config_dict["initialSharePrice"]),
            minimumShareReserves=str(pool_config_dict["minimumShareReserves"]),
            minimumTransactionAmount=str(pool_config_dict["minimumTransactionAmount"]),
            positionDuration=str(pool_config_dict["positionDuration"]),
            checkpointDuration=str(pool_config_dict["checkpointDuration"]),
            timeStretch=str(pool_config_dict["timeStretch"]),
            governance=pool_config_dict["governance"],
            feeCollector=pool_config_dict["feeCollector"],
            Fees=Fees(
                curve=str(pool_config_dict["fees"][0]),
                flat=str(pool_config_dict["fees"][1]),
                governance=str(pool_config_dict["fees"][2]),
            ),
            oracleSize=str(pool_config_dict["oracleSize"]),
            updateGap=str(pool_config_dict["updateGap"]),
        )

    def _stringify_pool_info(self, pool_info_dict: dict[str, Any]) -> PoolInfo:
        return PoolInfo(
            shareReserves=str(pool_info_dict["shareReserves"]),
            shareAdjustment=str(pool_info_dict["shareAdjustment"]),
            bondReserves=str(pool_info_dict["bondReserves"]),
            lpTotalSupply=str(pool_info_dict["lpTotalSupply"]),
            sharePrice=str(pool_info_dict["sharePrice"]),
            longsOutstanding=str(pool_info_dict["longsOutstanding"]),
            longAverageMaturityTime=str(pool_info_dict["longAverageMaturityTime"]),
            shortsOutstanding=str(pool_info_dict["shortsOutstanding"]),
            shortAverageMaturityTime=str(pool_info_dict["shortAverageMaturityTime"]),
            withdrawalSharesReadyToWithdraw=str(pool_info_dict["withdrawalSharesReadyToWithdraw"]),
            withdrawalSharesProceeds=str(pool_info_dict["withdrawalSharesProceeds"]),
            lpSharePrice=str(pool_info_dict["lpSharePrice"]),
            longExposure=str(pool_info_dict["longExposure"]),
        )

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
        r"""Return the bond reserves for the market share reserves and a given fixed rate.

        .. math::
            r = ((1/p)-1)/t //
            p = ((\mu z) / y)**(t) //
            y = \mu z p**((p r)/(p - 1))
        """
        return (
            self.pool_config["initialSharePrice"]
            * self.pool_info["shareReserves"]
            * self.spot_price ** ((self.spot_price * target_rate) / (self.spot_price - 1))
        )

    async def async_open_long(
        self,
        agent: LocalAccount,
        trade_amount: FixedPoint,
        slippage_tolerance: FixedPoint | None = None,
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
            fn_args = (
                maturity_time,
                trade_amount.scaled_value,
                min_output,
                agent_checksum_address,
                as_underlying,
            )
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
        fn_args = (
            trade_amount.scaled_value,
            min_output,
            agent_checksum_address,
            as_underlying,
        )
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
        fn_args = (
            trade_amount.scaled_value,
            min_output.scaled_value,
            agent_checksum_address,
            as_underlying,
        )
        tx_receipt = await async_smart_contract_transact(
            self.web3,
            self.hyperdrive_contract,
            agent,
            "redeemWithdrawalShares",
            *fn_args,
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
        pool_config_str = self._stringify_pool_config(self._contract_pool_config)
        pool_info_str = self._stringify_pool_info(self._contract_pool_info)
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
        pool_config_str = self._stringify_pool_config(self._contract_pool_config)
        pool_info_str = self._stringify_pool_info(self._contract_pool_info)
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

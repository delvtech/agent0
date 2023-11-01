"""High-level interface for the Hyperdrive market."""
from __future__ import annotations

import copy
import os
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, cast

from ethpy import build_eth_config
from ethpy.base import (
    BaseInterface,
    initialize_web3_with_http_provider,
    load_all_abis,
    smart_contract_read,
)
from ethpy.hyperdrive.addresses import (
    HyperdriveAddresses,
    fetch_hyperdrive_address_from_uri,
)
from ethpy.hyperdrive.interface import (
    convert_hyperdrive_checkpoint_types,
    convert_hyperdrive_pool_config_types,
    convert_hyperdrive_pool_info_types,
    get_hyperdrive_checkpoint,
    get_hyperdrive_pool_config,
    get_hyperdrive_pool_info,
    process_hyperdrive_checkpoint,
    process_hyperdrive_pool_config,
    process_hyperdrive_pool_info,
)
from web3.types import BlockIdentifier, Timestamp

from ._block_getters import _get_block, _get_block_number, _get_block_time
from ._contract_calls import (
    _async_add_liquidity,
    _async_close_long,
    _async_close_short,
    _async_open_long,
    _async_open_short,
    _async_redeem_withdraw_shares,
    _async_remove_liquidity,
    _get_eth_base_balances,
    _get_variable_rate,
    _get_vault_shares,
)
from ._mock_contract import (
    _calc_bonds_given_shares_and_rate,
    _calc_effective_share_reserves,
    _calc_fees_out_given_bonds_in,
    _calc_fees_out_given_shares_in,
    _calc_fixed_rate,
    _calc_in_for_out,
    _calc_long_amount,
    _calc_max_long,
    _calc_max_short,
    _calc_out_for_in,
    _calc_position_duration_in_years,
    _calc_short_deposit,
    _calc_spot_price,
)

# We expect to have many instance attributes & public methods since this is a large API.
# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-public-methods
# We only worry about protected access for anyone outside of this folder
# pylint: disable=protected-access


if TYPE_CHECKING:
    from typing import Any

    from eth_account.signers.local import LocalAccount
    from eth_typing import BlockNumber
    from ethpy import EthConfig
    from fixedpointmath import FixedPoint
    from web3 import Web3
    from web3.contract.contract import Contract
    from web3.types import BlockData, Nonce

    from ..receipt_breakdown import ReceiptBreakdown


@dataclass
class Checkpoint:
    """Checkpoint struct."""

    share_price: int
    long_exposure: int


@dataclass
class Fees:
    """Fees struct."""

    curve: FixedPoint
    flat: FixedPoint
    governance: FixedPoint


@dataclass
class PoolConfig:
    """PoolConfig struct."""

    base_token: str
    initial_share_price: FixedPoint
    minimum_share_reserves: FixedPoint
    minimum_transaction_amount: FixedPoint
    position_duration: int
    checkpoint_duration: int
    time_stretch: FixedPoint
    governance: str
    fee_collector: str
    fees: dict | Fees
    oracle_size: int
    update_gap: int

    def __post_init__(self):
        if isinstance(self.fees, dict):
            self.fees: Fees = Fees(**self.fees)


@dataclass
class PoolInfo:
    """PoolInfo struct."""

    share_reserves: FixedPoint
    share_adjustment: FixedPoint
    bond_reserves: FixedPoint
    lp_total_supply: FixedPoint
    share_price: FixedPoint
    longs_outstanding: FixedPoint
    long_average_maturity_time: FixedPoint
    shorts_outstanding: FixedPoint
    short_average_maturity_time: FixedPoint
    withdrawal_shares_ready_to_withdraw: FixedPoint
    withdrawal_shares_proceeds: FixedPoint
    lp_share_price: FixedPoint
    long_exposure: FixedPoint


@dataclass
class PoolState:
    r"""A collection of stateful variables for a deployed Hyperdrive contract."""
    hyperdrive_interface: HyperdriveInterface
    block_identifier: BlockIdentifier = cast(BlockIdentifier, "latest")

    def __post_init__(self):
        self.block = self.hyperdrive_interface.get_block(self.block_identifier)
        self.block_number = _get_block_number(self.block)
        self.block_time = _get_block_time(self.block)
        self.contract_pool_config = get_hyperdrive_pool_config(
            self.hyperdrive_interface.hyperdrive_contract
        )
        # TODO: Get the rest of the extra process pool config values as extra attributes
        self.pool_config = PoolConfig(
            **convert_hyperdrive_pool_config_types(self.contract_pool_config)
        )
        self.contract_pool_info = get_hyperdrive_pool_info(
            self.hyperdrive_interface.hyperdrive_contract, self.block_number
        )
        # TODO: Get the rest of the extra process pool info values as extra attributes
        self.pool_info = PoolInfo(
            **convert_hyperdrive_pool_info_types(self.contract_pool_info)
        )
        self.contract_checkpoint = get_hyperdrive_checkpoint(
            self.hyperdrive_interface.hyperdrive_contract,
            self.hyperdrive_interface.calc_checkpoint_id(self.block_time),
        )
        self.checkpoint = Checkpoint(
            **convert_hyperdrive_checkpoint_types(self.contract_checkpoint)
        )


class HyperdriveInterface(BaseInterface[HyperdriveAddresses]):
    """End-point api for interfacing with Hyperdrive."""

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
        In this case, the `eth_config.artifacts_uri` variable is not used, and these Addresses are used instead.
        """
        if eth_config is None:
            eth_config = build_eth_config()
        self.config = eth_config
        if addresses is None:
            addresses = fetch_hyperdrive_address_from_uri(
                os.path.join(eth_config.artifacts_uri, "addresses.json")
            )
        if web3 is None:
            web3 = initialize_web3_with_http_provider(
                eth_config.rpc_uri, reset_provider=False
            )
        self.web3 = web3
        abis = load_all_abis(eth_config.abi_dir)
        # set up the ERC20 contract for minting base tokens
        self.base_token_contract: Contract = web3.eth.contract(
            abi=abis["ERC20Mintable"],
            address=web3.to_checksum_address(addresses.base_token),
        )
        # set up hyperdrive contract
        self.hyperdrive_contract: Contract = web3.eth.contract(
            abi=abis["IHyperdrive"],
            address=web3.to_checksum_address(addresses.mock_hyperdrive),
        )
        self.last_state_block_number = copy.copy(self.current_block_number)
        # get yield (variable rate) pool contract
        # TODO: In the future we want to switch to a single IERC4626Hyperdrive ABI
        data_provider_contract: Contract = web3.eth.contract(
            abi=abis["ERC4626DataProvider"],
            address=web3.to_checksum_address(addresses.mock_hyperdrive),
        )
        self.yield_address = smart_contract_read(data_provider_contract, "pool")[
            "value"
        ]
        self.yield_contract: Contract = web3.eth.contract(
            abi=abis["MockERC4626"],
            address=web3.to_checksum_address(self.yield_address),
        )
        # pool config is static
        self._contract_pool_config = get_hyperdrive_pool_config(
            self.hyperdrive_contract
        )
        # TODO process functions should not adjust state
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

    def get_hyperdrive_state(self, block_identifier: BlockIdentifier | None = None):
        """Get the hyperdrive pool and block state, given a block identifier"""
        if block_identifier is None:
            block_identifier = cast(BlockIdentifier, "latest")
        return PoolState(self, block_identifier)

    @property
    def current_pool_info(self) -> dict[str, Any]:
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
        return _get_block(self, "latest")

    @property
    def current_block_number(self) -> BlockNumber:
        """The current block number."""
        return _get_block_number(self.current_block)

    @property
    def current_block_time(self) -> Timestamp:
        """The current block timestamp."""
        return _get_block_time(self.current_block)

    @property
    def position_duration_in_years(self) -> FixedPoint:
        """Returns the pool config position duration as a fraction of a year.

        This "annualized" time value is used in some calculations, such as the Fixed APR.
        """
        return _calc_position_duration_in_years(self)

    @property
    def fixed_rate(self) -> FixedPoint:
        """Returns the market fixed rate.

        Follows the formula:

        .. math::
            r = ((1 / p) - 1) / t = (1 - p) / (p * t)
        """
        return _calc_fixed_rate(self)

    @property
    def variable_rate(self) -> FixedPoint:
        """Returns the market variable rate."""
        return _get_variable_rate(self)

    @property
    def seconds_since_latest_checkpoint(self) -> int:
        """Return the amount of seconds that have passed since the latest checkpoint.
        The time is rounded to the nearest second.
        """
        self._ensure_current_state()
        latest_checkpoint_datetime: datetime = self.latest_checkpoint["timestamp"]
        current_block_datetime = datetime.fromtimestamp(int(self.current_block_time))
        return int(
            round((current_block_datetime - latest_checkpoint_datetime).total_seconds())
        )

    @property
    def spot_price(self) -> FixedPoint:
        """Get the current Hyperdrive pool spot price.

        Returns
        -------
        FixedPoint
            The current spot price.
        """
        self._ensure_current_state()
        return _calc_spot_price(self)

    @property
    def vault_shares(self) -> FixedPoint:
        """Get the balance of vault shares that Hyperdrive has."""
        return _get_vault_shares(self)

    @property
    def effective_share_reserves(self) -> FixedPoint:
        """Get the adjusted share reserves for the current Hyperdrive pool."""
        self._ensure_current_state()
        return _calc_effective_share_reserves(self)

    def _ensure_current_state(self, override: bool = False) -> None:
        """Update the cached pool info and latest checkpoint if needed.

        Attributes
        ----------
        override : bool
            If True, then reset the variables even if it is not needed.

        """
        if self.current_block_number > self.last_state_block_number or override:
            self.last_state_block_number = copy.copy(self.current_block_number)
            self._contract_pool_info = get_hyperdrive_pool_info(
                self.hyperdrive_contract, self.current_block_number
            )
            # TODO process functions should not adjust state
            self._pool_info = process_hyperdrive_pool_info(
                copy.deepcopy(self._contract_pool_info),
                self.web3,
                self.hyperdrive_contract,
                self.current_block_number,
            )
            self._contract_latest_checkpoint = get_hyperdrive_checkpoint(
                self.hyperdrive_contract,
                self.calc_checkpoint_id(self.current_block_time),
            )
            # TODO process functions should not adjust state
            self._latest_checkpoint = process_hyperdrive_checkpoint(
                copy.deepcopy(self._contract_latest_checkpoint),
                self.web3,
                self.current_block_number,
            )

    def get_block(self, block_identifier: BlockIdentifier) -> BlockData:
        """Get the block for a given identifier."""
        return _get_block(self, block_identifier)

    def get_block_number(self, block_identifier: BlockIdentifier) -> BlockNumber:
        """Get the block number for a given identifier."""
        return _get_block_number(_get_block(self, block_identifier))

    def calc_checkpoint_id(self, block_timestamp: Timestamp) -> Timestamp:
        """Get the Checkpoint ID for a given timestamp.

        Arguments
        ---------
        block_timestamp: int
            A timestamp for any block. Use the latest block to get the current checkpoint id,
            or a specific timestamp of a transaction's block if getting the checkpoint id for that transaction.

        Returns
        -------
        int
            The checkpoint id, which can be used as an argument for the Hyperdrive getCheckpoint function.
        """
        latest_checkpoint_timestamp = block_timestamp - (
            block_timestamp % self.pool_config["checkpointDuration"]
        )
        return cast(Timestamp, latest_checkpoint_timestamp)

    def get_eth_base_balances(
        self, agent: LocalAccount
    ) -> tuple[FixedPoint, FixedPoint]:
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
        return _get_eth_base_balances(self, agent)

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
        return await _async_open_long(
            self, agent, trade_amount, slippage_tolerance, nonce
        )

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
        return await _async_close_long(
            self, agent, trade_amount, maturity_time, slippage_tolerance, nonce
        )

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
        return await _async_open_short(
            self, agent, trade_amount, slippage_tolerance, nonce
        )

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
        return await _async_close_short(
            self, agent, trade_amount, maturity_time, slippage_tolerance, nonce
        )

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
        return await _async_add_liquidity(
            self, agent, trade_amount, min_apr, max_apr, nonce
        )

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
        return await _async_remove_liquidity(self, agent, trade_amount, nonce)

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
        return await _async_redeem_withdraw_shares(self, agent, trade_amount, nonce)

    def calc_open_long(self, base_amount: FixedPoint) -> FixedPoint:
        """Calculate the long amount that will be opened for a given base amount after fees.

        Arguments
        ---------
        base_amount : FixedPoint
            The amount to spend, in base.

        Returns
        -------
        long_amount : FixedPoint
            The amount of bonds purchased.
        """
        return _calc_long_amount(self, base_amount)

    def calc_open_short(self, short_amount: FixedPoint) -> FixedPoint:
        """Calculate the amount of base the trader will need to deposit for a short of a given size.

        Arguments
        ---------
        short_amount : FixedPoint
            The amount to of bonds to short.

        Returns
        -------
        short_amount : FixedPoint
            The amount of base required to short the bonds (aka the "max loss").
        """
        return _calc_short_deposit(
            self, short_amount, self.spot_price, self.current_pool_info["sharePrice"]
        )

    def calc_out_for_in(
        self,
        amount_in: FixedPoint,
        shares_in: bool,
    ) -> FixedPoint:
        """Calculate the amount of an asset for a given amount in of the other.

        Arguments
        ---------
        amount_in : FixedPoint
            The amount in.
        shares_in : bool
            True if the asset in is shares, False if it is bonds.

        Returns
        -------
        FixedPoint
            The amount out.
        """
        return _calc_out_for_in(self, amount_in, shares_in)

    def calc_in_for_out(
        self,
        amount_out: FixedPoint,
        shares_out: bool,
    ) -> FixedPoint:
        """Calculate the amount of an asset for a given amount out of the other.

        Arguments
        ---------
        amount_out : FixedPoint
            The amount out.
        shares_out : bool
            True if the asset out is shares, False if it is bonds.

        Returns
        -------
        FixedPoint
            The amount in.
        """
        return _calc_in_for_out(self, amount_out, shares_out)

    def calc_fees_out_given_bonds_in(
        self, bonds_in: FixedPoint, maturity_time: int | None = None
    ) -> tuple[FixedPoint, FixedPoint, FixedPoint]:
        """Calculates the fees that go to the LPs and governance.

        Implements the formula:
            curve_fee = ((1 - p) * phi_curve * d_y * t)/c
            gov_fee = curve_fee * phi_gov
            flat_fee = (d_y * (1 - t) * phi_flat) / c

        Arguments
        ---------
        bonds_in : FixedPoint
            The amount of bonds in.
        interface : HyperdriveInterface
            The API interface object.
        maturity_time : int, optional
            The maturity timestamp of the open position, in epoch seconds.

        Returns
        -------
        tuple[FixedPoint, FixedPoint, FixedPoint] consisting of:
            curve_fee : FixedPoint
                Curve fee, in shares.
            flat_fee : FixedPoint
                Flat fee, in shares.
            gov_fee : FixedPoint
                Governance fee, in shares.
        """
        return _calc_fees_out_given_bonds_in(self, bonds_in, maturity_time)

    def calc_fees_out_given_shares_in(
        self, shares_in: FixedPoint, maturity_time: int | None = None
    ) -> tuple[FixedPoint, FixedPoint, FixedPoint]:
        """Calculates the fees that go to the LPs and governance.

        Implements the formula:
            curve_fee = ((1 / p) - 1) * phi_curve * c * dz
            gov_fee = shares * phi_gov
            flat_fee = (d_y * (1 - t) * phi_flat) / c

        Arguments
        ---------
        bonds_in : FixedPoint
            The amount of bonds in.
        interface : HyperdriveInterface
            The API interface object.
        maturity_time : int, optional
            The maturity timestamp of the open position, in epoch seconds.

        Returns
        -------
        tuple[FixedPoint, FixedPoint, FixedPoint] consisting of:
            curve_fee : FixedPoint
                Curve fee, in shares.
            flat_fee : FixedPoint
                Flat fee, in shares.
            gov_fee : FixedPoint
                Governance fee, in shares.
        """
        return _calc_fees_out_given_shares_in(self, shares_in, maturity_time)

    def calc_bonds_given_shares_and_rate(
        self, target_rate: FixedPoint, target_shares: FixedPoint | None = None
    ) -> FixedPoint:
        r"""Returns the bond reserves for the market share reserves
        and a given fixed rate.


        The calculation is based on the formula:

        .. math::
            mu * (z - zeta) * (1 + apr * t) ** (1 / tau)

        Arguments
        ---------
        target_rate : FixedPoint
            The target apr for which to calculate the bond reserves given the pools current share reserves.
        target_shares : FixedPoint, optional
            The target share reserves for the pool

        .. todo::
            This function name matches the Rust implementation, but is not preferred because
            "given_*" is in the wrong order and can be inferred from arguments.
            Need to fix it from the bottom up.
        """
        return _calc_bonds_given_shares_and_rate(self, target_rate, target_shares)

    def calc_max_long(self, budget: FixedPoint) -> FixedPoint:
        """Calculate the maximum allowable long for the given Hyperdrive pool and agent budget.

        Arguments
        ---------
        budget: FixedPoint
            How much money the agent is able to spend, in base.

        Returns
        -------
        FixedPoint
            The maximum long, in units of base.
        """
        return _calc_max_long(self, budget)

    def calc_max_short(self, budget: FixedPoint) -> FixedPoint:
        """Calculate the maximum allowable short for the given Hyperdrive pool and agent budget.

        Arguments
        ---------
        budget: FixedPoint
            How much money the agent is able to spend, in base.

        Returns
        -------
        FixedPoint
            The maximum short, in units of base.
        """
        return _calc_max_short(self, budget)

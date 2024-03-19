"""High-level interface for a Hyperdrive pool."""

from __future__ import annotations

import copy
import os
from typing import TYPE_CHECKING, cast

from eth_account import Account
from fixedpointmath import FixedPoint
from web3.types import BlockData, BlockIdentifier, Timestamp

from agent0.ethpy import build_eth_config
from agent0.ethpy.base import initialize_web3_with_http_provider
from agent0.ethpy.hyperdrive.addresses import HyperdriveAddresses, fetch_hyperdrive_address_from_uri
from agent0.ethpy.hyperdrive.deploy import DeployedHyperdrivePool
from agent0.ethpy.hyperdrive.state import PoolState
from agent0.ethpy.hyperdrive.transactions import (
    get_hyperdrive_checkpoint,
    get_hyperdrive_checkpoint_exposure,
    get_hyperdrive_pool_config,
    get_hyperdrive_pool_info,
)
from agent0.hypertypes import (
    CheckpointFP,
    ERC20MintableContract,
    HyperdriveFactoryContract,
    IERC4626HyperdriveContract,
    MockERC4626Contract,
)

from ._block_getters import _get_block, _get_block_number, _get_block_time
from ._contract_calls import (
    _get_eth_base_balances,
    _get_gov_fees_accrued,
    _get_hyperdrive_base_balance,
    _get_hyperdrive_eth_balance,
    _get_total_supply_withdrawal_shares,
    _get_variable_rate,
    _get_vault_shares,
)
from ._mock_contract import (
    _calc_bonds_given_shares_and_rate,
    _calc_bonds_out_given_shares_in_down,
    _calc_checkpoint_id,
    _calc_close_long,
    _calc_close_short,
    _calc_effective_share_reserves,
    _calc_fees_out_given_bonds_in,
    _calc_fees_out_given_shares_in,
    _calc_fixed_rate,
    _calc_max_long,
    _calc_max_short,
    _calc_open_long,
    _calc_open_short,
    _calc_position_duration_in_years,
    _calc_present_value,
    _calc_shares_in_given_bonds_out_down,
    _calc_shares_in_given_bonds_out_up,
    _calc_shares_out_given_bonds_in_down,
    _calc_spot_price,
    _calc_time_stretch,
)

# We expect to have many instance attributes & public methods since this is a large API.
# pylint: disable=too-many-lines
# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-public-methods
# pylint: disable=too-many-arguments
# We only worry about protected access for anyone outside of this folder.
# pylint: disable=protected-access


if TYPE_CHECKING:
    from eth_account.signers.local import LocalAccount
    from eth_typing import BlockNumber
    from web3 import Web3

    from agent0.ethpy import EthConfig


class HyperdriveReadInterface:
    """Read-only end-point API for interfacing with a deployed Hyperdrive pool."""

    _deployed_hyperdrive_pool: DeployedHyperdrivePool | None = None

    def __init__(
        self,
        eth_config: EthConfig | None = None,
        addresses: HyperdriveAddresses | None = None,
        web3: Web3 | None = None,
        read_retry_count: int | None = None,
    ) -> None:
        """The HyperdriveReadInterface API. This is the primary endpoint for
        users to simulate transactions on Hyperdrive smart contracts.

        Arguments
        ---------
        eth_config: EthConfig, optional
            Configuration dataclass for the ethereum environment.
            If given, then it is constructed from environment variables.
        addresses: HyperdriveAddresses, optional
            This is a dataclass containing addresses for deployed hyperdrive and base token contracts.
            If given, then the `eth_config.artifacts_uri` variable is not used, and these Addresses are used instead.
            If not given, then addresses is constructed from the `addresses.json` file at `eth_config.artifacts_uri`.
        web3: Web3, optional
            web3 provider object, optional
            If given, a web3 object is constructed using the `eth_config.rpc_uri` as the http provider.
        read_retry_count: int | None, optional
            The number of times to retry the read call if it fails. Defaults to 5.
        """
        # Handle defaults for config and addresses.
        self.eth_config: EthConfig = build_eth_config() if eth_config is None else eth_config
        if addresses is None:
            addresses = fetch_hyperdrive_address_from_uri(os.path.join(self.eth_config.artifacts_uri, "addresses.json"))
        self.addresses: HyperdriveAddresses = addresses
        # Setup provider for communicating with the chain.
        if web3 is None:
            web3 = initialize_web3_with_http_provider(self.eth_config.rpc_uri, reset_provider=False)
        self.web3 = web3
        # Setup the ERC20 contract for minting base tokens.
        self.base_token_contract: ERC20MintableContract = ERC20MintableContract.factory(w3=self.web3)(
            web3.to_checksum_address(self.addresses.base_token)
        )
        # Setup Hyperdrive, Yield (variable rate), and Hyperdrive Factory contracts.
        self.hyperdrive_contract: IERC4626HyperdriveContract = IERC4626HyperdriveContract.factory(w3=self.web3)(
            web3.to_checksum_address(self.addresses.erc4626_hyperdrive)
        )
        self.yield_address = self.hyperdrive_contract.functions.vault().call()
        self.yield_contract: MockERC4626Contract = MockERC4626Contract.factory(w3=self.web3)(
            address=web3.to_checksum_address(self.yield_address)
        )
        self.hyperdrive_factory_contract: HyperdriveFactoryContract = HyperdriveFactoryContract.factory(w3=self.web3)(
            web3.to_checksum_address(self.addresses.factory)
        )
        # Fill in the initial state cache.
        self._current_pool_state = self.get_hyperdrive_state()
        self.last_state_block_number = copy.copy(self._current_pool_state.block_number)
        self.pool_config = self._current_pool_state.pool_config
        # Set the retry count for contract calls using the interface when previewing/transacting
        # TODO these parameters are currently only used for trades against hyperdrive
        # and uses defaults for other smart_contract_read functions, e.g., get_pool_info.
        self.read_retry_count = read_retry_count
        self._deployed_hyperdrive_pool = self._create_deployed_hyperdrive_pool()

    def _create_deployed_hyperdrive_pool(self) -> DeployedHyperdrivePool:
        return DeployedHyperdrivePool(
            web3=self.web3,
            deploy_account=Account().from_key("0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"),
            hyperdrive_contract_addresses=self.addresses,
            hyperdrive_contract=self.hyperdrive_contract,
            hyperdrive_factory_contract=self.hyperdrive_factory_contract,
            base_token_contract=self.base_token_contract,
            deploy_block_number=0,  # don't have access to this here, use at your own risk
        )

    @property
    def deployed_hyperdrive_pool(self) -> DeployedHyperdrivePool:
        """Retrieve the deployed hyperdrive pool to which the interface is connected."""
        if self._deployed_hyperdrive_pool is None:
            self._deployed_hyperdrive_pool = self._create_deployed_hyperdrive_pool()
        return self._deployed_hyperdrive_pool

    @property
    def current_pool_state(self) -> PoolState:
        """The current state of the pool.

        Each time this is accessed we use an RPC to check that the pool state is synced with the current block.
        """
        _ = self._ensure_current_state()
        return self._current_pool_state

    def _ensure_current_state(self) -> bool:
        """Update the cached pool info and latest checkpoint if needed.

        Returns
        -------
        bool
            True if the state was updated.
        """
        current_block = self.get_current_block()
        current_block_number = self.get_block_number(current_block)
        if current_block_number > self.last_state_block_number:
            self._current_pool_state = self.get_hyperdrive_state(current_block)
            self.last_state_block_number = current_block_number
            return True
        return False

    def get_current_block(self) -> BlockData:
        """Use an RPC to get the current block.

        Returns
        -------
        BlockData
            A web3py dataclass containing information about the latest mined block.
        """
        return self.get_block("latest")

    def get_block(self, block_identifier: BlockIdentifier) -> BlockData:
        """Use an RPC to get the block for the provided identifier.

        Delegates to eth_getBlockByNumber if block_identifier is an integer or
        one of the predefined block parameters 'latest', 'earliest', 'pending', 'safe', 'finalized'.
        Otherwise delegates to eth_getBlockByHash.
        Throws BlockNotFound error if the block is not found.

        Arguments
        ---------
        block_identifier: BlockIdentifier
            Any one of the web3py types: [BlockParams, BlockNumber, Hash32, HexStr, HexBytes, int].

        Returns
        -------
        BlockData
            A web3py dataclass containing block information.
        """
        return _get_block(self, block_identifier)

    def get_block_number(self, block: BlockData) -> BlockNumber:
        """Use an RPC to get the number for the provided block.

        Arguments
        ---------
        block: BlockData
            A web3py dataclass for storing block information.

        Returns
        -------
        BlockNumber
            The number for the corresponding block.
        """
        return _get_block_number(block)

    def get_block_timestamp(self, block: BlockData) -> Timestamp:
        """Use an RPC to get the time for the provided block.

        Arguments
        ---------
        block: BlockData
            A web3py dataclass for storing block information.

        Returns
        -------
        Timestamp
            The integer timestamp, in seconds, for the corresponding block.
        """
        return _get_block_time(block)

    def get_hyperdrive_state(self, block: BlockData | None = None) -> PoolState:
        """Use RPCs and contract calls to get the Hyperdrive pool and block state, given a block identifier.

        Arguments
        ---------
        block: BlockData, optional
            A web3py dataclass for storing block information.
            Defaults to the latest block.

        Returns
        -------
        PoolState
            A dataclass containing PoolInfo, PoolConfig, Checkpoint, and Block
            information that is synced to a given block number.
        """
        if block is None:
            block_identifier = cast(BlockIdentifier, "latest")
            block = self.get_block(block_identifier)
        block_number = self.get_block_number(block)
        pool_config = get_hyperdrive_pool_config(self.hyperdrive_contract)
        pool_info = get_hyperdrive_pool_info(self.hyperdrive_contract, block_number)
        checkpoint_time = self.calc_checkpoint_id(pool_config.checkpoint_duration, self.get_block_timestamp(block))
        checkpoint = get_hyperdrive_checkpoint(self.hyperdrive_contract, checkpoint_time)
        exposure = get_hyperdrive_checkpoint_exposure(self.hyperdrive_contract, checkpoint_time)
        variable_rate = self.get_variable_rate(block_number)
        vault_shares = self.get_vault_shares(block_number)
        total_supply_withdrawal_shares = self.get_total_supply_withdrawal_shares(block_number)
        hyperdrive_base_balance = self.get_hyperdrive_base_balance(block_number)
        hyperdrive_eth_balance = self.get_hyperdrive_eth_balance()
        gov_fees_accrued = self.get_gov_fees_accrued(block_number)
        return PoolState(
            block=block,
            pool_config=pool_config,
            pool_info=pool_info,
            checkpoint_time=checkpoint_time,
            checkpoint=checkpoint,
            exposure=exposure,
            variable_rate=variable_rate,
            vault_shares=vault_shares,
            total_supply_withdrawal_shares=total_supply_withdrawal_shares,
            hyperdrive_base_balance=hyperdrive_base_balance,
            hyperdrive_eth_balance=hyperdrive_eth_balance,
            gov_fees_accrued=gov_fees_accrued,
        )

    def get_checkpoint(self, checkpoint_time: Timestamp) -> CheckpointFP:
        """Use an RPC to get the checkpoint info for the Hyperdrive contract for a given checkpoint_time index.

        Arguments
        ---------
        checkpoint_time: Timestamp
            The block timestamp that indexes the checkpoint to get.

        Returns
        -------
        CheckpointFP
            The dataclass containing the checkpoint info in fixed point
        """
        return get_hyperdrive_checkpoint(self.hyperdrive_contract, checkpoint_time)

    def get_total_supply_withdrawal_shares(self, block_number: BlockNumber | None) -> FixedPoint:
        """Use an RPC to get the total supply of withdrawal shares in the pool at the given block.

        Arguments
        ---------
        block_number: BlockNumber, optional
            The number for any minted block.
            If not given, the latest block number is used.

        Returns
        -------
        FixedPoint
            The quantity of withdrawal shares available in the Hyperdrive pool.
        """
        if block_number is None:
            block_number = self.get_block_number(self.get_current_block())
        return _get_total_supply_withdrawal_shares(self.hyperdrive_contract, block_number)

    def get_vault_shares(self, block_number: BlockNumber | None) -> FixedPoint:
        """Use an RPC to get the balance of shares that the Hyperdrive pool has in the underlying yield source.

        Arguments
        ---------
        block_number: BlockNumber, optional
            The number for any minted block.
            Defaults to the current block number.

        Returns
        -------
        FixedPoint
            The quantity of vault shares for the yield source at the provided block.
        """
        if block_number is None:
            block_number = self.get_block_number(self.get_current_block())
        return _get_vault_shares(self.yield_contract, self.hyperdrive_contract, block_number)

    def get_idle_shares(self, block_number: BlockNumber | None) -> FixedPoint:
        """Get the balance of idle shares that the Hyperdrive pool has.

        Arguments
        ---------
        block_number: BlockNumber, optional
            The number for any minted block.
            Defaults to the current block number.

        Returns
        -------
        FixedPoint
            The quantity of vault shares for the yield source at the provided block.
        """
        if block_number is None:
            block_number = self.get_block_number(self.get_current_block())
        pool_state = self.current_pool_state
        long_exposure_shares = self.current_pool_state.pool_info.long_exposure / pool_state.pool_info.vault_share_price
        idle_shares = (
            pool_state.pool_info.share_reserves - long_exposure_shares - pool_state.pool_config.minimum_share_reserves
        )
        return idle_shares

    def get_variable_rate(self, block_number: BlockNumber | None = None) -> FixedPoint:
        """Use an RPC to get the yield source variable rate.

        Arguments
        ---------
        block_number: BlockNumber, optional
            The number for any minted block.
            Defaults to the current block number.

        Returns
        -------
        FixedPoint
            The variable rate for the yield source at the provided block.
        """
        if block_number is None:
            block_number = self.get_block_number(self.get_current_block())
        return _get_variable_rate(self.yield_contract, block_number)

    def get_eth_base_balances(self, agent: LocalAccount) -> tuple[FixedPoint, FixedPoint]:
        """Use an RPC to get the agent's balance on the Base & Hyperdrive contracts.

        Arguments
        ---------
        agent: LocalAccount
            The account for the agent that is executing and signing the trade transaction.

        Returns
        -------
        tuple[FixedPoint]
            A tuple containing the [agent_eth_balance, agent_base_balance].
        """
        return _get_eth_base_balances(self, agent)

    def get_hyperdrive_eth_balance(self) -> FixedPoint:
        """Get the current Hyperdrive eth balance from an RPC.

        Returns
        -------
        FixedPoint
            The eth on the chain.
        """
        return _get_hyperdrive_eth_balance(self.web3, self.hyperdrive_contract.address)

    def get_hyperdrive_base_balance(self, block_number: BlockNumber | None = None) -> FixedPoint:
        """Get the current Hyperdrive balance in the base contract.

        Arguments
        ---------
        block_number: BlockNumber, optional
            The number for any minted block.
            Defaults to the current block number.

        Returns
        -------
        FixedPoint
            The result of base_token_contract.balanceOf(hypedrive_address).
        """
        return _get_hyperdrive_base_balance(self.base_token_contract, self.hyperdrive_contract, block_number)

    def get_gov_fees_accrued(self, block_number: BlockNumber | None = None) -> FixedPoint:
        """Get the current amount of Uncollected Governance Fees in the Hyperdrive contract.

        Arguments
        ---------
        block_number: BlockNumber, optional
            The number for any minted block.
            Defaults to the current block number.

        Returns
        -------
        FixedPoint
            The result of hyperdrive_contract.functions.getUncollectedGovernanceFees
        """
        return _get_gov_fees_accrued(self.hyperdrive_contract, block_number)

    def calc_position_duration_in_years(self, pool_state: PoolState | None = None) -> FixedPoint:
        """Returns the pool config position duration as a fraction of a year.

        This "annualized" time value is used in some calculations, such as the Fixed APR.
        The function does not perform contract calls, but instead relies on the Hyperdrive-rust sdk
        to simulate the contract outputs.

        Arguments
        ---------
        pool_state: PoolState, optional
            The state of the pool, which includes block details, pool config, and pool info.
            If not given, use the current pool state.

        Returns
        -------
        FixedPoint
            The annualized position duration
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_position_duration_in_years(pool_state)

    def calc_time_stretch(self, target_rate: FixedPoint, target_position_duration: FixedPoint) -> FixedPoint:
        """Returns the time stretch parameter given a target fixed rate and position duration.

        Arguments
        ---------
        target_rate: FixedPoint
            The fixed rate that the Hyperdrive pool will be initialized with.
        target_position_duration: FixedPoint
            The position duration that the Hyperdrive pool will be initialized with.

        Returns
        -------
        FixedPoint
            The time stretch constant.
        """
        return _calc_time_stretch(target_rate, target_position_duration)

    def calc_checkpoint_id(
        self, checkpoint_duration: int | None = None, block_timestamp: Timestamp | None = None
    ) -> Timestamp:
        """Calculate the Checkpoint ID for a given timestamp.

        The function does not perform contract calls, but instead relies on the Hyperdrive-rust sdk
        to simulate the contract outputs.

        Arguments
        ---------
        checkpoint_duration: int, optional
            The time, in seconds, between checkpoints.
            Defaults to the current pool's checkpoint duration.
        block_timestamp: Timestamp, optional
            A timestamp for any block. Use the latest block to get the current checkpoint id,
            or a specific timestamp of a transaction's block if getting the checkpoint id for that transaction.
            Defaults to the current block timestamp.

        Returns
        -------
        int
            The checkpoint id, in units of seconds,
            which represents the time of the last checkpoint.
        """
        if checkpoint_duration is None:
            checkpoint_duration = self.pool_config.checkpoint_duration
        if block_timestamp is None:
            block_timestamp = self.current_pool_state.block_time
        return _calc_checkpoint_id(checkpoint_duration, block_timestamp)

    def calc_fixed_rate(self, pool_state: PoolState | None = None) -> FixedPoint:
        r"""Calculate the fixed rate for a given pool state.

        The function does not perform contract calls, but instead relies on the Hyperdrive-rust sdk
        to simulate the contract outputs. The simulation follows the formula:

        .. math::
            r = ((1 / p) - 1) / t = (1 - p) / (p * t)

        Arguments
        ---------
        pool_state: PoolState, optional
            The state of the pool, which includes block details, pool config, and pool info.
            If not given, use the current pool state.

        Returns
        -------
        FixedPoint
            The fixed rate apr for the Hyperdrive pool state.
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_fixed_rate(pool_state)

    def calc_spot_price(self, pool_state: PoolState | None = None) -> FixedPoint:
        """Calculate the spot price for a given Hyperdrive pool.

        The function does not perform contract calls, but instead relies on the Hyperdrive-rust sdk
        to simulate the contract outputs.

        Arguments
        ---------
        pool_state: PoolState, optional
            The state of the pool, which includes block details, pool config, and pool info.
            If not given, use the current pool state.

        Returns
        -------
        FixedPoint
            The spot price for the Hyperdrive pool state.
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_spot_price(pool_state)

    def calc_effective_share_reserves(self, pool_state: PoolState | None = None) -> FixedPoint:
        """Calculate the adjusted share reserves for a given Hyperdrive pool.

        The function does not perform contract calls, but instead relies on the Hyperdrive-rust sdk
        to simulate the contract outputs.

        Arguments
        ---------
        pool_state: PoolState, optional
            The state of the pool, which includes block details, pool config, and pool info.
            If not given, use the current pool state.

        Returns
        -------
        FixedPoint
            The effective (aka zeta-adjusted) share reserves.
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_effective_share_reserves(pool_state)

    def calc_open_long(self, base_amount: FixedPoint, pool_state: PoolState | None = None) -> FixedPoint:
        """Calculate the long amount that will be opened for a given base amount after fees.

        The function does not perform contract calls, but instead relies on the Hyperdrive-rust sdk
        to simulate the contract outputs.

        Arguments
        ---------
        base_amount: FixedPoint
            The amount to spend, in base.
        pool_state: PoolState, optional
            The state of the pool, which includes block details, pool config, and pool info.
            If not given, use the current pool state.

        Returns
        -------
        FixedPoint
            The amount of bonds purchased.
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_open_long(pool_state, base_amount)

    def calc_close_long(
        self, bond_amount: FixedPoint, normalized_time_remaining: FixedPoint, pool_state: PoolState | None = None
    ) -> FixedPoint:
        """Calculates the amount of shares that will be returned after fees for closing a long.

        Arguments
        ---------
        bond_amount: FixedPoint
            The amount of bonds to sell.
        normalized_time_remaining: FixedPoint
            The time remaining before the long reaches maturity,
            normalized such that 1 is at opening and 0 is at maturity.
        pool_state: PoolState, optional
            The state of the pool, which includes block details, pool config, and pool info.
            If not given, use the current pool state.

        Returns
        -------
        FixedPoint
            The amount of shares returned.
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_close_long(pool_state, bond_amount, normalized_time_remaining)

    def calc_open_short(self, bond_amount: FixedPoint, pool_state: PoolState | None = None) -> FixedPoint:
        """Calculate the amount of base the trader will need to deposit for a short of a given size, after fees.

        The function does not perform contract calls, but instead relies on the Hyperdrive-rust sdk
        to simulate the contract outputs.

        Arguments
        ---------
        bond_amount: FixedPoint
            The amount to of bonds to short.
        pool_state: PoolState, optional
            The state of the pool, which includes block details, pool config, and pool info.
            If not given, use the current pool state.

        Returns
        -------
        FixedPoint
            The amount of base required to short the bonds (aka the "max loss").
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_open_short(
            pool_state, bond_amount, _calc_spot_price(pool_state), pool_state.pool_info.vault_share_price
        )

    def calc_close_short(
        self,
        bond_amount: FixedPoint,
        open_vault_share_price: FixedPoint,
        close_vault_share_price: FixedPoint,
        normalized_time_remaining: FixedPoint,
        pool_state: PoolState | None = None,
    ) -> FixedPoint:
        """Gets the amount of shares the trader will receive from closing a short.

        Arguments
        ---------
        bond_amount: FixedPoint
            The amount to of bonds provided.
        open_vault_share_price: FixedPoint
            The checkpoint share price when the short was opened.
        close_vault_share_price: FixedPoint
            The share price when the short was closed.
            If the short isn't mature, this is the current share price.
            If the short is mature, this is the share price of the maturity checkpoint.
        normalized_time_remaining: FixedPoint
            The time remaining before the short reaches maturity,
            normalized such that 1 is at opening and 0 is at maturity.
        pool_state: PoolState, optional
            The state of the pool, which includes block details, pool config, and pool info.
            If not given, use the current pool state.

        Returns
        -------
        FixedPoint
            The amount of shares the trader will receive for closing the short.
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_close_short(
            pool_state, bond_amount, open_vault_share_price, close_vault_share_price, normalized_time_remaining
        )

    def calc_bonds_out_given_shares_in_down(
        self, amount_in: FixedPoint, pool_state: PoolState | None = None
    ) -> FixedPoint:
        """Calculates the amount of bonds a user will receive from the pool by
        providing a specified amount of shares. We underestimate the amount of
        bonds. The amount returned is before fees are applied.

        The function does not perform contract calls, but instead relies on the Hyperdrive-rust sdk
        to simulate the contract outputs.

        Arguments
        ---------
        amount_in: FixedPoint
            The amount of shares going into the pool.
        pool_state: PoolState, optional
            The state of the pool, which includes block details, pool config, and pool info.
            If not given, use the current pool state.

        Returns
        -------
        FixedPoint
            The amount of bonds out.
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_bonds_out_given_shares_in_down(pool_state, amount_in)

    def calc_shares_in_given_bonds_out_up(
        self, amount_in: FixedPoint, pool_state: PoolState | None = None
    ) -> FixedPoint:
        """Calculates the amount of shares a user must provide the pool to receive
        a specified amount of bonds. We overestimate the amount of shares in.
        The amount returned is before fees are applied.

        The function does not perform contract calls, but instead relies on the Hyperdrive-rust sdk
        to simulate the contract outputs.

        Arguments
        ---------
        amount_in: FixedPoint
            The amount of bonds to target.
        pool_state: PoolState, optional
            The state of the pool, which includes block details, pool config, and pool info.
            If not given, use the current pool state.

        Returns
        -------
        FixedPoint
            The amount of shares in to reach the target.
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_shares_in_given_bonds_out_up(pool_state, amount_in)

    def calc_shares_in_given_bonds_out_down(
        self, amount_in: FixedPoint, pool_state: PoolState | None = None
    ) -> FixedPoint:
        """Calculates the amount of shares a user must provide the pool to receive
        a specified amount of bonds. We underestimate the amount of shares in.
        The amount returned is before fees are applied.

        The function does not perform contract calls, but instead relies on the Hyperdrive-rust sdk
        to simulate the contract outputs.

        Arguments
        ---------
        amount_in: FixedPoint
            The amount of bonds to target.
        pool_state: PoolState, optional
            The state of the pool, which includes block details, pool config, and pool info.
            If not provided, use the current pool state.

        Returns
        -------
        FixedPoint
            The amount of shares in to reach the target.
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_shares_in_given_bonds_out_down(pool_state, amount_in)

    def calc_shares_out_given_bonds_in_down(
        self, amount_in: FixedPoint, pool_state: PoolState | None = None
    ) -> FixedPoint:
        """Calculates the amount of shares a user will receive from the pool by
        providing a specified amount of bonds. We underestimate the amount of
        shares out. The amount returned is before fees are applied.

        The function does not perform contract calls, but instead relies on the Hyperdrive-rust sdk
        to simulate the contract outputs.

        Arguments
        ---------
        amount_in: FixedPoint
            The amount of bonds in.
        pool_state: PoolState, optional
            The state of the pool, which includes block details, pool config, and pool info.
            If not provided, use the current pool state.

        Returns
        -------
        FixedPoint
            The amount of shares out.
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_shares_out_given_bonds_in_down(pool_state, amount_in)

    def calc_fees_out_given_bonds_in(
        self, bonds_in: FixedPoint, maturity_time: int | None = None, pool_state: PoolState | None = None
    ) -> tuple[FixedPoint, FixedPoint, FixedPoint]:
        r"""Calculates the fees that would be deducted for an amount of bonds entering the pool.

        The function does not perform contract calls, but instead relies on the Hyperdrive-rust sdk
        to simulate the contract outputs. It implements the formula:

        .. math::
            \begin{align*}
                &\text{curve_fee} = \frac{(1 - p) * \phi_{\text{curve}} * d_y * t}{c}
                &\text{gov_fee} = \text{curve_fee} * \phi_{\text{gov}}
                &\text{flat_fee} = \frac{d_y * (1 - t) * \phi_{\text{flat}}}{c}
            \end{align*}

        Arguments
        ---------
        bonds_in: FixedPoint
            The amount of bonds being added to the pool.
        maturity_time: int, optional
            The maturity timestamp of the open position, in epoch seconds.
        pool_state: PoolState, optional
            The state of the pool, which includes block details, pool config, and pool info.
            If not given, use the current pool state.

        Returns
        -------
        tuple[FixedPoint, FixedPoint, FixedPoint]
            curve_fee: FixedPoint
                Curve fee, in shares.
            flat_fee: FixedPoint
                Flat fee, in shares.
            gov_fee: FixedPoint
                Governance fee, in shares.
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_fees_out_given_bonds_in(pool_state, bonds_in, maturity_time)

    def calc_fees_out_given_shares_in(
        self, shares_in: FixedPoint, maturity_time: int | None = None, pool_state: PoolState | None = None
    ) -> tuple[FixedPoint, FixedPoint, FixedPoint]:
        r"""Calculates the fees that go to the LPs and governance.

        The function does not perform contract calls, but instead relies on the Hyperdrive-rust sdk
        to simulate the contract outputs. It implements the formula:

        .. math::
            \begin{align*}
                &\text{curve_fee} = ((1 / p) - 1) * \phi_{\text{curve}} * c * dz
                &\text{gov_fee} = \text{shares} * \phi_{\text{gov}}
                &\text{flat_fee} = \frac{d_y * (1 - t) * \phi_{\text{flat}}}{c}
            \end{align*}

        Arguments
        ---------
        shares_in: FixedPoint
            The amount of shares being added to the pool.
        maturity_time: int, optional
            The maturity timestamp of the open position, in epoch seconds.
        pool_state: PoolState, optional
            The state of the pool, which includes block details, pool config, and pool info.
            If not given, use the current pool state.

        Returns
        -------
        tuple[FixedPoint, FixedPoint, FixedPoint]
            curve_fee: FixedPoint
                Curve fee, in shares.
            flat_fee: FixedPoint
                Flat fee, in shares.
            gov_fee: FixedPoint
                Governance fee, in shares.
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_fees_out_given_shares_in(pool_state, shares_in, maturity_time)

    def calc_bonds_given_shares_and_rate(
        self, target_rate: FixedPoint, target_shares: FixedPoint | None = None, pool_state: PoolState | None = None
    ) -> FixedPoint:
        r"""Returns the bond reserves for the market share reserves
        and a given fixed rate.

        The function does not perform contract calls, but instead relies on the Hyperdrive-rust sdk
        to simulate the contract outputs. The calculation is based on the formula:

        .. math::
            \mu * (z - \zeta) * (1 + \text{apr} * t)^{1 / \tau}

        .. todo::
            This function name matches the Rust implementation, but is not preferred because
            "given_shares_and_rate" is in the wrong order (should be rate_and_shares) according to arguments
            and really "given_*" could be removed because it can be inferred from arguments.
            Need to fix it from the bottom up.

        Arguments
        ---------
        target_rate: FixedPoint
            The target apr for which to calculate the bond reserves given the pools current share reserves.
        target_shares: FixedPoint, optional
            The target share reserves for the pool
        pool_state: PoolState, optional
            The state of the pool, which includes block details, pool config, and pool info.
            If not given, use the current pool state.

        Returns
        -------
        FixedPoint
            The output bonds.
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_bonds_given_shares_and_rate(pool_state, target_rate, target_shares)

    def calc_max_long(self, budget: FixedPoint, pool_state: PoolState | None = None) -> FixedPoint:
        """Calculate the maximum allowable long for the given Hyperdrive pool and agent budget.

        The function does not perform contract calls, but instead relies on the Hyperdrive-rust sdk
        to simulate the contract outputs.

        Arguments
        ---------
        budget: FixedPoint
            How much money the agent is able to spend, in base.
        pool_state: PoolState, optional
            The state of the pool, which includes block details, pool config, and pool info.
            If not given, use the current pool state.

        Returns
        -------
        FixedPoint
            The maximum long, in units of base.
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_max_long(pool_state, budget)

    def calc_max_short(self, budget: FixedPoint, pool_state: PoolState | None = None) -> FixedPoint:
        """Calculate the maximum allowable short for the given Hyperdrive pool and agent budget.

        The function does not perform contract calls, but instead relies on the Hyperdrive-rust sdk
        to simulate the contract outputs.

        Arguments
        ---------
        budget: FixedPoint
            How much money the agent is able to spend, in base.
        pool_state: PoolState, optional
            The state of the pool, which includes block details, pool config, and pool info.
            If not given, use the current pool state.

        Returns
        -------
        FixedPoint
            The maximum short, in units of bonds.
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_max_short(pool_state, budget)

    def calc_present_value(self, pool_state: PoolState | None = None) -> FixedPoint:
        """Calculates the present value of LPs capital in the pool.

        Arguments
        ---------
        pool_state: PoolState, optional
            The state of the pool, which includes block details, pool config, and pool info.
            If not given, use the current pool state.

        Returns
        -------
        FixedPoint
            The present value of all LP capital in the pool.
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_present_value(pool_state, pool_state.block_time)

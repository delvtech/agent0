"""High-level interface for a Hyperdrive pool."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

from fixedpointmath import FixedPoint
from web3.exceptions import BadFunctionCallOutput, ContractLogicError
from web3.types import BlockData, BlockIdentifier, Timestamp

from agent0.ethpy.base import initialize_web3_with_http_provider
from agent0.ethpy.hyperdrive.get_expected_hyperdrive_version import get_expected_hyperdrive_version
from agent0.ethpy.hyperdrive.state import PoolState
from agent0.ethpy.hyperdrive.transactions import (
    get_hyperdrive_checkpoint,
    get_hyperdrive_checkpoint_exposure,
    get_hyperdrive_pool_config,
    get_hyperdrive_pool_info,
)
from agent0.hypertypes import CheckpointFP, ERC20MintableContract, IHyperdriveContract, MockERC4626Contract

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
    _calc_checkpoint_timestamp,
    _calc_close_long,
    _calc_close_short,
    _calc_effective_share_reserves,
    _calc_idle_share_reserves_in_base,
    _calc_max_long,
    _calc_max_short,
    _calc_max_spot_price,
    _calc_open_long,
    _calc_open_short,
    _calc_pool_deltas_after_open_long,
    _calc_pool_deltas_after_open_short,
    _calc_position_duration_in_years,
    _calc_present_value,
    _calc_shares_in_given_bonds_out_down,
    _calc_shares_in_given_bonds_out_up,
    _calc_shares_out_given_bonds_in_down,
    _calc_solvency,
    _calc_spot_price,
    _calc_spot_price_after_long,
    _calc_spot_price_after_short,
    _calc_spot_rate,
    _calc_spot_rate_after_long,
    _calc_targeted_long,
    _calc_time_stretch,
)

AGENT0_SIGNATURE = bytes.fromhex("a0")

if TYPE_CHECKING:
    from eth_account.signers.local import LocalAccount
    from eth_typing import BlockNumber, ChecksumAddress
    from web3 import Web3

# We expect to have many instance attributes & public methods since this is a large API.
# pylint: disable=too-many-lines
# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-public-methods
# pylint: disable=too-many-arguments
# ruff: noqa: PLR0913
# We only worry about protected access for anyone outside of this folder.
# pylint: disable=protected-access


class HyperdriveReadInterface:
    """Read-only end-point API for interfacing with a deployed Hyperdrive pool."""

    def __init__(
        self,
        hyperdrive_address: ChecksumAddress,
        rpc_uri: str | None = None,
        web3: Web3 | None = None,
        read_retry_count: int | None = None,
        txn_receipt_timeout: float | None = None,
        txn_signature: bytes | None = None,
    ) -> None:
        """Initialize the HyperdriveReadInterface API.

        This is the primary endpoint for users to simulate transactions on Hyperdrive smart contracts.

        Arguments
        ---------
        hyperdrive_address: ChecksumAddress
            This is a contract address for a deployed hyperdrive.
        rpc_uri: str, optional
            The URI to initialize the web3 provider. Not used if web3 is provided.
        web3: Web3, optional
            web3 provider object, optional
            If not given, a web3 object is constructed using the `rpc_uri` as the http provider.
        read_retry_count: int | None, optional
            The number of times to retry the read call if it fails. Defaults to 5.
        txn_receipt_timeout: float | None, optional
            The timeout for waiting for a transaction receipt in seconds. Defaults to 120.
        txn_signature: bytes | None, optional
            The signature for transactions. Defaults to `0xa0`.
        """
        if txn_signature is None:
            self.txn_signature = AGENT0_SIGNATURE
        else:
            self.txn_signature = txn_signature

        # Handle defaults for config and addresses.
        self.hyperdrive_address = hyperdrive_address

        # Setup provider for communicating with the chain.
        if web3 is None and rpc_uri is None:
            raise ValueError("Must provide either `web3` or `rpc_uri`")
        if web3 is None:
            assert rpc_uri is not None
            web3 = initialize_web3_with_http_provider(rpc_uri, reset_provider=False)
        self.web3 = web3

        # Setup Hyperdrive contract
        self.hyperdrive_contract: IHyperdriveContract = IHyperdriveContract.factory(w3=self.web3)(
            web3.to_checksum_address(self.hyperdrive_address)
        )

        # Check version here to ensure the contract is the correct version
        hyperdrive_version = self.hyperdrive_contract.functions.version().call()
        expected_version = get_expected_hyperdrive_version()
        if hyperdrive_version not in expected_version:
            raise ValueError(
                f"Hyperdrive address {self.hyperdrive_address} is version {hyperdrive_version}, "
                f"does not match one of the expected versions {expected_version}"
            )

        # We get the yield address and contract from the pool config
        self.pool_config = get_hyperdrive_pool_config(self.hyperdrive_contract)
        base_token_contract_address = self.pool_config.base_token
        vault_shares_token_address = self.pool_config.vault_shares_token

        # TODO Although the underlying function might not be a MockERC4626Contract,
        # the pypechain contract factory happily accepts any address and exposes
        # all functions from that contract. The code will only break if we try to
        # call a non-existent function on the underlying contract address.
        self.vault_shares_token_contract: MockERC4626Contract = MockERC4626Contract.factory(w3=self.web3)(
            address=web3.to_checksum_address(vault_shares_token_address)
        )

        # Agent0 doesn't support eth as base, so if it is, we use the yield token as the base, and
        # calls to trades will use "as_base=False"
        if base_token_contract_address == "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE":
            self.base_is_eth = True
            # If the base token is eth, we use the yield token as the base token (e.g., steth)
            # and pass in "as_base=False" to the contract calls.
            # This simplifies accounting to have only one base token for steth.
            # The alternative of having eth as base token requires keeping track of both
            # tokens in order to support `removeLiquidity`, as we can't remove liquidity into
            # eth.
            base_token_contract_address = vault_shares_token_address
        else:
            self.base_is_eth = False

        self.base_token_contract: ERC20MintableContract = ERC20MintableContract.factory(w3=self.web3)(
            web3.to_checksum_address(base_token_contract_address)
        )

        # Set the retry count for contract calls using the interface when previewing/transacting
        # TODO these parameters are currently only used for trades against hyperdrive
        # and uses defaults for other smart_contract_read functions, e.g., get_pool_info.
        self.read_retry_count = read_retry_count
        self.txn_receipt_timeout = txn_receipt_timeout

        # Lazily fill in state cache
        self._current_pool_state = None
        self.last_state_block_number = -1

    @property
    def current_pool_state(self) -> PoolState:
        """The current state of the pool.

        Each time this is accessed we use an RPC to check that the pool state is synced with the current block.
        """
        _ = self._ensure_current_state()
        assert self._current_pool_state is not None
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
        pool_info = get_hyperdrive_pool_info(self.hyperdrive_contract, block_number)
        checkpoint_time = self.calc_checkpoint_id(self.pool_config.checkpoint_duration, self.get_block_timestamp(block))
        checkpoint = get_hyperdrive_checkpoint(self.hyperdrive_contract, checkpoint_time, block_number)
        exposure = get_hyperdrive_checkpoint_exposure(self.hyperdrive_contract, checkpoint_time, block_number)

        try:
            variable_rate = self.get_variable_rate(block_number)
        except BadFunctionCallOutput:
            logging.warning(
                "Underlying yield contract has no `getRate` function, setting `state.variable_rate` as `None`."
            )
            variable_rate = None
        # Some contracts throw a logic error
        except ContractLogicError:
            logging.warning(
                "Underlying yield contract reverted `getRate` function, setting `state.variable_rate` as `None`."
            )
            variable_rate = None

        vault_shares = self.get_vault_shares(block_number)
        total_supply_withdrawal_shares = self.get_total_supply_withdrawal_shares(block_number)
        hyperdrive_base_balance = self.get_hyperdrive_base_balance(block_number)
        hyperdrive_eth_balance = self.get_hyperdrive_eth_balance()
        gov_fees_accrued = self.get_gov_fees_accrued(block_number)
        return PoolState(
            block=block,
            pool_config=self.pool_config,
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

    def get_checkpoint(self, checkpoint_time: Timestamp, block_number: BlockNumber | None = None) -> CheckpointFP:
        """Use an RPC to get the checkpoint info for the Hyperdrive contract for a given checkpoint_time index.

        Arguments
        ---------
        checkpoint_time: Timestamp
            The block timestamp that indexes the checkpoint to get.
        block_number: BlockNumber, optional
            The number for any minted block.
            If not given, the latest block number is used.

        Returns
        -------
        CheckpointFP
            The dataclass containing the checkpoint info in fixed point
        """
        if block_number is None:
            block_number = self.get_block_number(self.get_current_block())
        return get_hyperdrive_checkpoint(self.hyperdrive_contract, checkpoint_time, block_number)

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
        return _get_vault_shares(self.vault_shares_token_contract, self.hyperdrive_contract, block_number)

    def get_idle_shares(self, pool_state: PoolState | None) -> FixedPoint:
        """Get the balance of idle shares that the Hyperdrive pool has.

        Arguments
        ---------
        pool_state: PoolState | None, optional
            The state of the pool, which includes block details, pool config, and pool info.
            If not given, use the current pool state.

        Returns
        -------
        FixedPoint
            The quantity of vault shares for the yield source at the provided block.
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        long_exposure_shares = pool_state.pool_info.long_exposure / pool_state.pool_info.vault_share_price
        idle_shares = (
            pool_state.pool_info.share_reserves - long_exposure_shares - pool_state.pool_config.minimum_share_reserves
        )
        return idle_shares

    def get_variable_rate(self, block_number: BlockNumber | None = None) -> FixedPoint:
        """Use an RPC to get the yield source variable rate.

        .. note:: This function assumes there exists an underlying `getRate` function in the contract.
        This call will fail if the deployed yield contract doesn't have a `getRate` function.

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
        return _get_variable_rate(self.vault_shares_token_contract, block_number)

    def get_standardized_variable_rate(self, time_range: int = 604800) -> FixedPoint:
        """Get a standardized variable rate using vault share prices from checkpoints in the last `time_range` seconds.

        .. note:: This function will throw an error if the pool was deployed within the last `time_range` seconds.

        Arguments
        ---------
        time_range: int
            The time range (in seconds) to use to calculate the variable rate to look for checkpoints.

        Returns
        -------
        FixedPoint
            The standardized variable rate.
        """
        # Get the vault share price of the checkpoint in the past `time_range`
        current_block = self.current_pool_state.block
        current_block_time = self.get_block_timestamp(current_block)
        start_checkpoint_id = self.calc_checkpoint_id(block_timestamp=Timestamp(current_block_time - time_range))
        start_vault_share_price = self.get_checkpoint(start_checkpoint_id).vault_share_price

        # Vault share price is 0 if checkpoint doesn't exist
        # This happens if the pool was deployed within the past `time_range`
        if start_vault_share_price == FixedPoint(0):
            raise ValueError("Checkpoint doesn't exist for the given time range.")

        # We can also get the current vault share price instead of getting it from the latest checkpoint
        current_checkpoint_id = self.calc_checkpoint_id(block_timestamp=current_block_time)
        current_vault_share_price = self.get_checkpoint(current_checkpoint_id).vault_share_price
        # If the current checkpoint doesn't exist (due to checkpoint not being made yet),
        # we use the current vault share price
        if current_vault_share_price == FixedPoint(0):
            current_vault_share_price = self.current_pool_state.pool_info.vault_share_price

        rate_of_return = (current_vault_share_price - start_vault_share_price) / start_vault_share_price
        # Annualized the rate of return
        annualized_rate_of_return = rate_of_return * FixedPoint(60 * 60 * 24 * 365) / FixedPoint(time_range)
        return annualized_rate_of_return

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
        return _get_hyperdrive_eth_balance(self, self.web3, self.hyperdrive_contract.address)

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
            The result of base_token_contract.balanceOf(hyperdrive_address).
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
        """Return the pool config position duration as a fraction of a year.

        This "annualized" time value is used in some calculations, such as the Fixed APR.
        The function does not perform contract calls, but instead relies on the Hyperdrive-rust api
        to simulate the contract outputs.

        Arguments
        ---------
        pool_state: PoolState | None, optional
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
        """Return the time stretch parameter given a target fixed rate and position duration.

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

    def calc_checkpoint_timestamp(self, time: int | Timestamp, pool_state: PoolState | None = None) -> Timestamp:
        """Converts a timestamp to the checkpoint timestamp that it corresponds to.

        Arguments
        ---------
        time: int | Timestamp
            Any timestamp (in seconds) before or at the present.
        pool_state: PoolState | None, optional
            The state of the pool, which includes block details, pool config, and pool info.
            If not given, use the current pool state.

        Returns
        -------
        Timestamp
            The checkpoint timestamp.
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_checkpoint_timestamp(pool_state, int(time))

    def calc_checkpoint_id(
        self, checkpoint_duration: int | None = None, block_timestamp: Timestamp | None = None
    ) -> Timestamp:
        """Calculate the Checkpoint ID for a given timestamp.

        The function does not perform contract calls, but instead relies on the Hyperdrive-rust api
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

    def calc_spot_rate(self, pool_state: PoolState | None = None) -> FixedPoint:
        r"""Calculate the spot fixed rate for a given pool state.

        The function does not perform contract calls, but instead relies on the Hyperdrive-rust api
        to simulate the contract outputs. The simulation follows the formula:

        .. math::
            r = ((1 / p) - 1) / t = (1 - p) / (p * t)

        Arguments
        ---------
        pool_state: PoolState | None, optional
            The state of the pool, which includes block details, pool config, and pool info.
            If not given, use the current pool state.

        Returns
        -------
        FixedPoint
            The fixed rate apr for the Hyperdrive pool state.
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_spot_rate(pool_state)

    def calc_spot_price(self, pool_state: PoolState | None = None) -> FixedPoint:
        """Calculate the spot price for a given Hyperdrive pool.

        The function does not perform contract calls, but instead relies on the Hyperdrive-rust api
        to simulate the contract outputs.

        Arguments
        ---------
        pool_state: PoolState | None, optional
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

    def calc_max_spot_price(self, pool_state: PoolState | None = None) -> FixedPoint:
        """Get the pool's max spot price.

        Arguments
        ---------
        pool_state: PoolState | None, optional
            The state of the pool, which includes block details, pool config, and pool info.
            If not given, use the current pool state.

        Returns
        -------
        FixedPoint
            The pool's maximum achievable spot price.
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_max_spot_price(pool_state)

    def calc_effective_share_reserves(self, pool_state: PoolState | None = None) -> FixedPoint:
        """Calculate the adjusted share reserves for a given Hyperdrive pool.

        The function does not perform contract calls, but instead relies on the Hyperdrive-rust api
        to simulate the contract outputs.

        Arguments
        ---------
        pool_state: PoolState | None, optional
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

    def calc_idle_share_reserves_in_base(self, pool_state: PoolState | None = None) -> FixedPoint:
        """Calculates the idle share reserves in base of the pool.

        Arguments
        ---------
        pool_state: PoolState | None, optional
            The state of the pool, which includes block details, pool config, and pool info.
            If not given, use the current pool state.

        Returns
        -------
        FixedPoint
            The pool's idle share reserves in base.
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_idle_share_reserves_in_base(pool_state)

    def calc_bonds_given_shares_and_rate(
        self, target_rate: FixedPoint, target_shares: FixedPoint | None = None, pool_state: PoolState | None = None
    ) -> FixedPoint:
        r"""Return the bond reserves for the market share reserves and a given fixed rate.

        The function does not perform contract calls, but instead relies on the Hyperdrive-rust api
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
        pool_state: PoolState | None, optional
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

    def calc_open_long(self, base_amount: FixedPoint, pool_state: PoolState | None = None) -> FixedPoint:
        """Calculate the long amount that will be opened for a given base amount after fees.

        The function does not perform contract calls, but instead relies on the Hyperdrive-rust api
        to simulate the contract outputs.

        Arguments
        ---------
        base_amount: FixedPoint
            The amount to spend, in base.
        pool_state: PoolState | None, optional
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

    def calc_pool_deltas_after_open_long(
        self, base_amount: FixedPoint, pool_state: PoolState | None = None
    ) -> FixedPoint:
        """Calculate the bond deltas to be applied to the pool after opening a long.

        Arguments
        ---------
        base_amount: FixedPoint
            The amount of base used to open a long.
        pool_state: PoolState | None, optional
            The state of the pool, which includes block details, pool config, and pool info.
            If not given, use the current pool state.

        Returns
        -------
        FixedPoint
            The amount of bonds to remove from the pool reserves.
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_pool_deltas_after_open_long(pool_state, base_amount)

    def calc_spot_price_after_long(
        self, base_amount: FixedPoint, bond_amount: FixedPoint | None = None, pool_state: PoolState | None = None
    ) -> FixedPoint:
        """Calculate the spot price for a given Hyperdrive pool after a long is opened for `base_amount`.

        The function does not perform contract calls, but instead relies on the Hyperdrive-rust api
        to simulate the contract outputs.

        Arguments
        ---------
        base_amount: FixedPoint
            The amount of base provided for the long.
        bond_amount: FixedPoint | None, optional
            The amount of bonds that would be purchased by the long.
            The default is to use whatever is returned by `calc_open_long(base_amount)`.
        pool_state: PoolState | None, optional
            The state of the pool, which includes block details, pool config, and pool info.
            If not given, use the current pool state.

        Returns
        -------
        FixedPoint
            The spot price for the Hyperdrive pool state.
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_spot_price_after_long(pool_state, base_amount, bond_amount)

    def calc_spot_rate_after_long(
        self, base_amount: FixedPoint, bond_amount: FixedPoint | None = None, pool_state: PoolState | None = None
    ) -> FixedPoint:
        """Calculate the spot rate for a given Hyperdrive pool after a long is opened for `base_amount`.

        The function does not perform contract calls, but instead relies on the Hyperdrive-rust api
        to simulate the contract outputs.

        Arguments
        ---------
        base_amount: FixedPoint
            The amount of base provided for the long.
        bond_amount: FixedPoint | None, optional
            The amount of bonds that would be purchased by the long.
            The default is to use whatever is returned by `calc_open_long(base_amount)`.
        pool_state: PoolState | None, optional
            The state of the pool, which includes block details, pool config, and pool info.
            If not given, use the current pool state.

        Returns
        -------
        FixedPoint
            The spot rate for the Hyperdrive pool state.
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_spot_rate_after_long(pool_state, base_amount, bond_amount)

    def calc_max_long(self, budget: FixedPoint, pool_state: PoolState | None = None) -> FixedPoint:
        """Calculate the maximum allowable long for the given Hyperdrive pool and agent budget.

        The function does not perform contract calls, but instead relies on the Hyperdrive-rust api
        to simulate the contract outputs.

        Arguments
        ---------
        budget: FixedPoint
            How much money the agent is able to spend, in base.
        pool_state: PoolState | None, optional
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

    def calc_close_long(
        self, bond_amount: FixedPoint, maturity_time: int, pool_state: PoolState | None = None
    ) -> FixedPoint:
        """Calculate the amount of shares that will be returned after fees for closing a long.

        Arguments
        ---------
        bond_amount: FixedPoint
            The amount of bonds to sell.
        maturity_time: int
            The maturity time of the bond.
        pool_state: PoolState | None, optional
            The state of the pool, which includes block details, pool config, and pool info.
            If not given, use the current pool state.

        Returns
        -------
        FixedPoint
            The amount of shares returned.
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_close_long(pool_state, bond_amount, maturity_time, int(pool_state.block_time))

    def calc_targeted_long(
        self,
        budget: FixedPoint,
        target_rate: FixedPoint,
        max_iterations: int | None = None,
        allowable_error: FixedPoint | None = None,
        pool_state: PoolState | None = None,
    ) -> FixedPoint:
        """Calculate the amount of bonds that can be purchased for the given budget.

        Arguments
        ---------
        budget: FixedPont
            The account budget in base for making a long.
        target_rate: FixedPoint
            The target fixed rate.
        max_iterations: int | None, optional
            The number of iterations to use for the Newtonian method.
            Defaults to 7.
        allowable_error: FixedPoint | None, optional
            The amount of error supported for reaching the target rate.
            Defaults to 1e-4.
        pool_state: PoolState | None, optional
            The state of the pool, which includes block details, pool config, and pool info.
            If not given, use the current pool state.

        Returns
        -------
        FixedPoint
            The amount of shares returned.
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_targeted_long(pool_state, budget, target_rate, max_iterations, allowable_error)

    def calc_open_short(self, bond_amount: FixedPoint, pool_state: PoolState | None = None) -> FixedPoint:
        """Calculate the amount of base the trader will need to deposit for a short of a given size, after fees.

        The function does not perform contract calls, but instead relies on the Hyperdrive-rust api
        to simulate the contract outputs.

        Arguments
        ---------
        bond_amount: FixedPoint
            The amount to of bonds to short.
        pool_state: PoolState | None, optional
            The state of the pool, which includes block details, pool config, and pool info.
            If not given, use the current pool state.

        Returns
        -------
        FixedPoint
            The amount of base required to short the bonds (aka the "max loss").
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_open_short(pool_state, bond_amount, pool_state.pool_info.vault_share_price)

    def calc_pool_deltas_after_open_short(
        self, bond_amount: FixedPoint, pool_state: PoolState | None = None
    ) -> FixedPoint:
        """Calculate the amount of shares the pool will add after opening a short.

        Arguments
        ---------
        bond_amount: FixedPoint
            The amount to of bonds to short.
        pool_state: PoolState | None, optional
            The state of the pool, which includes block details, pool config, and pool info.
            If not given, use the current pool state.

        Returns
        -------
        FixedPoint
            The amount of base to add to the pool share reserves.
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_pool_deltas_after_open_short(pool_state, bond_amount)

    def calc_spot_price_after_short(
        self, bond_amount: FixedPoint, base_amount: FixedPoint | None = None, pool_state: PoolState | None = None
    ) -> FixedPoint:
        """Calculate the spot price for a given Hyperdrive pool after a short is opened for `base_amount`.

        The function does not perform contract calls, but instead relies on the Hyperdrive-rust api
        to simulate the contract outputs.

        Arguments
        ---------
        bond_amount: FixedPoint
            The amount that woud be used to open a short.
        base_amount: FixedPoint | None, optional
            The amount of base provided for the short.
            The default is to use whatever is returned by `calc_open_short(bond_amount)`.
        pool_state: PoolState | None, optional
            The state of the pool, which includes block details, pool config, and pool info.
            If not given, use the current pool state.

        Returns
        -------
        FixedPoint
            The spot price for the Hyperdrive pool state.
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_spot_price_after_short(pool_state, bond_amount, base_amount)

    def calc_max_short(self, budget: FixedPoint, pool_state: PoolState | None = None) -> FixedPoint:
        """Calculate the maximum allowable short for the given Hyperdrive pool and agent budget.

        The function does not perform contract calls, but instead relies on the Hyperdrive-rust api
        to simulate the contract outputs.

        Arguments
        ---------
        budget: FixedPoint
            How much money the agent is able to spend, in base.
        pool_state: PoolState | None, optional
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

    def calc_close_short(
        self,
        bond_amount: FixedPoint,
        open_vault_share_price: FixedPoint,
        close_vault_share_price: FixedPoint,
        maturity_time: int,
        pool_state: PoolState | None = None,
    ) -> FixedPoint:
        """Get the amount of shares the trader will receive from closing a short.

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
        maturity_time: int
            The maturity time of the short.
        pool_state: PoolState | None, optional
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
            pool_state, bond_amount, open_vault_share_price, close_vault_share_price, maturity_time
        )

    def calc_present_value(self, pool_state: PoolState | None = None) -> FixedPoint:
        """Calculate the present value of LPs capital in the pool.

        Arguments
        ---------
        pool_state: PoolState | None, optional
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

    def calc_solvency(self, pool_state: PoolState | None = None) -> FixedPoint:
        """Calculate the pool's solvency.

        Arguments
        ---------
        pool_state: PoolState | None, optional
            The state of the pool, which includes block details, pool config, and pool info.
            If not given, use the current pool state.

        Returns
        -------
        FixedPoint
            solvency = share_reserves - long_exposure / vault_share_price - minimum_share_reserves
        """
        if pool_state is None:
            pool_state = self.current_pool_state
        return _calc_solvency(pool_state)

    def calc_bonds_out_given_shares_in_down(
        self, amount_in: FixedPoint, pool_state: PoolState | None = None
    ) -> FixedPoint:
        """Calculate the amount of bonds a user will receive from the pool by providing a specified amount of shares.

        We underestimate the amount of bonds. The amount returned is before fees are applied.
        The function does not perform contract calls, but instead relies on the Hyperdrive-rust api
        to simulate the contract outputs.

        Arguments
        ---------
        amount_in: FixedPoint
            The amount of shares going into the pool.
        pool_state: PoolState | None, optional
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
        """Calculate the amount of shares a user must provide the pool to receive a specified amount of bonds.

        We overestimate the amount of shares in. The amount returned is before fees are applied.
        The function does not perform contract calls, but instead relies on the Hyperdrive-rust api
        to simulate the contract outputs.

        Arguments
        ---------
        amount_in: FixedPoint
            The amount of bonds to target.
        pool_state: PoolState | None, optional
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
        """Calculate the amount of shares a user must provide the pool to receive a specified amount of bonds.

        We underestimate the amount of shares in. The amount returned is before fees are applied.
        The function does not perform contract calls, but instead relies on the Hyperdrive-rust api
        to simulate the contract outputs.

        Arguments
        ---------
        amount_in: FixedPoint
            The amount of bonds to target.
        pool_state: PoolState | None, optional
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
        """Calculate the amount of shares a user will receive from the pool by providing a specified amount of bonds.

        We underestimate the amount of shares out. The amount returned is before fees are applied.
        The function does not perform contract calls, but instead relies on the Hyperdrive-rust api
        to simulate the contract outputs.

        Arguments
        ---------
        amount_in: FixedPoint
            The amount of bonds in.
        pool_state: PoolState | None, optional
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

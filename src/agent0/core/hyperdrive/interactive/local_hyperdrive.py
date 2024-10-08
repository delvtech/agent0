"""Defines the interactive hyperdrive class that encapsulates a hyperdrive pool."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Sequence

import pandas as pd
from eth_typing import BlockNumber, ChecksumAddress
from fixedpointmath import FixedPoint
from hyperdrivetypes import CreateCheckpointEventFP
from hyperdrivetypes.types.HyperdriveFactoryTypes import FactoryConfig
from hyperdrivetypes.types.IHyperdriveTypes import Fees, PoolDeployConfig
from web3 import Web3

from agent0.chainsync.analysis import fill_pnl_values
from agent0.chainsync.db.hyperdrive import (
    get_checkpoint_info,
    get_pool_config,
    get_pool_info,
    get_position_snapshot,
    get_total_pnl_over_time,
    get_trade_events,
)
from agent0.chainsync.exec import acquire_data, analyze_data
from agent0.ethpy.hyperdrive import (
    DeployedHyperdriveFactory,
    DeployedHyperdrivePool,
    HyperdriveDeployType,
    deploy_base_and_vault,
    deploy_hyperdrive_factory,
    deploy_hyperdrive_from_factory,
)

from .hyperdrive import Hyperdrive

if TYPE_CHECKING:
    from .chain import Chain
    from .local_chain import LocalChain

# Is very thorough module.
# pylint: disable=too-many-lines
# pylint: disable=protected-access
# pylint: disable=too-many-instance-attributes


class LocalHyperdrive(Hyperdrive):
    """Interactive Hyperdrive class that supports an interactive interface for running tests and experiments."""

    # We add a link to the `DeployType` here for access from this hyperdrive object,
    # e.g., `LocalHyperdrive.DeployType.ERC4626`
    DeployType = HyperdriveDeployType

    @dataclass(kw_only=True)
    class Config(Hyperdrive.Config):
        """The configuration for the local hyperdrive pool."""

        # Environment variables
        data_pipeline_timeout: int = 60
        """The timeout for the data pipeline. Defaults to 60 seconds."""

        # Initial pool variables
        initial_liquidity: FixedPoint = FixedPoint(100_000_000)
        """The amount of money to be provided by the `deploy_account` for initial pool liquidity."""
        initial_variable_rate: FixedPoint = FixedPoint("0.05")
        """The starting variable rate for an underlying yield source."""
        initial_fixed_apr: FixedPoint = FixedPoint("0.05")
        """The fixed rate of the pool on initialization."""
        initial_time_stretch_apr: FixedPoint = FixedPoint("0.05")
        """The rate to target for the time stretch."""

        # Factory Deploy Config variables
        # We match defaults here from the deploy script in hyperdrive
        # except for fees, where we span the full range to allow for testing
        factory_checkpoint_duration_resolution: int = 60 * 60  # 1 hour
        """The resolution for checkpoint durations."""
        factory_min_checkpoint_duration: int = 60 * 60  # 1 hour
        """The factory's minimum checkpoint duration."""
        factory_max_checkpoint_duration: int = 60 * 60 * 24  # 1 day
        """The factory's maximum checkpoint duration."""
        factory_min_position_duration: int = 60 * 60 * 24  # 1 day
        """The factory's minimum position duration."""
        factory_max_position_duration: int = 60 * 60 * 24 * 365 * 10  # 10 year
        """The factory's maximum position duration."""
        factory_min_circuit_breaker_delta: FixedPoint = FixedPoint("0.15")
        """The factory's minimum circuit breaker delta."""
        factory_max_circuit_breaker_delta: FixedPoint = FixedPoint("2")
        """The factory's maximum circuit breaker delta."""
        factory_min_fixed_apr: FixedPoint = FixedPoint("0.01")  # 1%
        """The factory's minimum fixed APR."""
        factory_max_fixed_apr: FixedPoint = FixedPoint("0.5")  # 50%
        """The factory's maximum fixed APR."""
        factory_min_time_stretch_apr: FixedPoint = FixedPoint("0.01")  # 1%
        """The factory's minimum time stretch rate."""
        factory_max_time_stretch_apr: FixedPoint = FixedPoint("0.5")  # 50%
        """The factory's maximum time stretch rate."""
        factory_min_curve_fee: FixedPoint = FixedPoint("0")
        """The lower bound on the curve fee that governance can set."""
        factory_min_flat_fee: FixedPoint = FixedPoint("0")
        """The lower bound on the flat fee that governance can set."""
        factory_min_governance_lp_fee: FixedPoint = FixedPoint("0")
        """The lower bound on the governance lp fee that governance can set."""
        factory_min_governance_zombie_fee: FixedPoint = FixedPoint("0")
        """The lower bound on the governance zombie fee that governance can set."""
        factory_max_curve_fee: FixedPoint = FixedPoint("1")
        """The upper bound on the curve fee that governance can set."""
        factory_max_flat_fee: FixedPoint = FixedPoint("1")
        """The upper bound on the flat fee that governance can set."""
        factory_max_governance_lp_fee: FixedPoint = FixedPoint("1")
        """The upper bound on the governance lp fee that governance can set."""
        factory_max_governance_zombie_fee: FixedPoint = FixedPoint("1")
        """The upper bound on the governance zombie fee that governance can set."""

        # Pool Deploy Config variables
        deploy_type: HyperdriveDeployType = HyperdriveDeployType.ERC4626
        """The type of deployment to use. If not specified, it will default to ERC4626."""
        minimum_share_reserves: FixedPoint | None = None
        """The minimum share reserves."""
        minimum_transaction_amount: FixedPoint = FixedPoint("0.001")
        """The minimum amount of tokens that a position can be opened or closed with."""
        circuit_breaker_delta: FixedPoint = FixedPoint(2)
        """
        The circuit breaker delta defines the maximum delta between the last checkpoint's
        weighted spot rate and the current spot rate to allow an LP to add liquidity.
        """
        position_duration: int = 604_800  # 1 week
        """The duration of a position prior to maturity (in seconds)."""
        checkpoint_duration: int = 3_600  # 1 hour
        """The duration of a checkpoint (in seconds)."""
        curve_fee: FixedPoint = FixedPoint("0.01")  # 1%
        """The LP fee applied to the curve portion of a trade."""
        # 0.05% APR. Here, we divide by 52 because the position duration is 1 week
        # TODO do we want to default to 0.05% APR always? so we divide by position duration
        # Maybe we just define the flat fee in terms of APR and do math under the hood to set
        # the flat fee parameter
        flat_fee: FixedPoint = FixedPoint(scaled_value=int(FixedPoint("0.0005").scaled_value / 52))
        """The LP fee applied to the flat portion of a trade in annualized rates."""
        governance_lp_fee: FixedPoint = FixedPoint("0.15")  # 15%
        """The portion of the LP fee that goes to governance."""
        governance_zombie_fee: FixedPoint = FixedPoint("0.03")  # 3%
        """
        The portion of the zombie interest that is given to governance as a fee.
        The portion of the zombie interest that will go to LPs is 1 - governance_zombie_fee.
        """

        def __post_init__(self):
            if self.checkpoint_duration > self.position_duration:
                raise ValueError("Checkpoint duration must be less than or equal to position duration")
            if self.position_duration % self.checkpoint_duration != 0:
                raise ValueError("Position duration must be a multiple of checkpoint duration")
            # Set defaults for minimum share reserves based on deploy type
            if self.minimum_share_reserves is None:
                match self.deploy_type:
                    case HyperdriveDeployType.STETH:
                        self.minimum_share_reserves = FixedPoint("0.001")
                    case _:
                        self.minimum_share_reserves = FixedPoint("10")

            # Steth deployment minimum share reserves and minimum transaction amount must be 0.001
            # in the steth deployer coordinator.
            # Adding useful error message here
            if self.deploy_type == HyperdriveDeployType.STETH and self.minimum_share_reserves != FixedPoint("0.001"):
                raise ValueError("Minimum share reserves must be 0.001 for steth deployment")

            if self.deploy_type == HyperdriveDeployType.STETH and self.minimum_transaction_amount != FixedPoint(
                "0.001"
            ):
                raise ValueError("Minimum transaction amount must be 0.001 for steth deployment")

        @property
        def _factory_min_fees(self) -> Fees:
            return Fees(
                curve=self.factory_min_curve_fee.scaled_value,
                flat=self.factory_min_flat_fee.scaled_value,
                governanceLP=self.factory_min_governance_lp_fee.scaled_value,
                governanceZombie=self.factory_min_governance_zombie_fee.scaled_value,
            )

        @property
        def _factory_max_fees(self) -> Fees:
            return Fees(
                curve=self.factory_max_curve_fee.scaled_value,
                flat=self.factory_max_flat_fee.scaled_value,
                governanceLP=self.factory_max_governance_lp_fee.scaled_value,
                governanceZombie=self.factory_max_governance_zombie_fee.scaled_value,
            )

        @property
        def _fees(self) -> Fees:
            return Fees(
                curve=self.curve_fee.scaled_value,
                flat=self.flat_fee.scaled_value,
                governanceLP=self.governance_lp_fee.scaled_value,
                governanceZombie=self.governance_zombie_fee.scaled_value,
            )

    # Pretty print for this class
    def __str__(self) -> str:
        return f"Local Hyperdrive Pool {self.name} at chain address {self.hyperdrive_address}"

    @classmethod
    def get_hyperdrive_pools_from_registry(
        cls,
        chain: Chain,
        registry_address: str,
    ) -> Sequence[LocalHyperdrive]:
        """Gather deployed Hyperdrive pool addresses.

        Arguments
        ---------
        chain: Chain
            The Chain object connected to a chain.
        registry_address: str
            The address of the Hyperdrive registry contract.

        Returns
        -------
        Sequence[LocalHyperdrive]
            The hyperdrive objects for all registered pools
        """

        # Explicit type check to ensure chain is not LocalChain
        if not chain.is_local_chain:
            raise TypeError(
                "Cannot use `LocalHyperdrive` function on `Chain` object. "
                "Use `Hyperdrive.get_hyperdrive_pools_from_registry` instead."
            )

        hyperdrive_addresses = cls.get_hyperdrive_addresses_from_registry(chain, registry_address)
        if len(hyperdrive_addresses) == 0:
            raise ValueError("Registry does not have any hyperdrive pools registered.")
        # Generate hyperdrive pool objects here
        registered_pools = []
        for hyperdrive_name, hyperdrive_address in hyperdrive_addresses.items():
            registered_pools.append(
                LocalHyperdrive(
                    # Chain is guaranteed to be LocalChain here,
                    # (from the `chain.is_local_chain` check above)
                    # but we want to avoid importing it.
                    chain,  # type: ignore
                    # We don't deploy since we're expecting to get existing pools from the registry
                    deploy=False,
                    hyperdrive_address=hyperdrive_address,
                    name=hyperdrive_name,
                )
            )

        return registered_pools

    def __init__(
        self,
        chain: LocalChain,
        config: Config | None = None,
        name: str | None = None,
        deploy: bool = True,
        hyperdrive_address: ChecksumAddress | str | None = None,
        backfill_data_start_block: int | None = None,
    ):
        """Constructor for the interactive hyperdrive agent.

        Arguments
        ---------
        chain: LocalChain
            The local chain object to launch hyperdrive on.
        hyperdrive_address: ChecksumAddress | str | None, optional
            The address of the hyperdrive contract to connect to if `deploy` is False.
            Defaults to deploying a new hyperdrive.
        config: Config | None
            The configuration for the initial pool configuration.
        name: str | None, optional
            The logical name of the pool.
        deploy: bool, optional
            If True, will deploy a new hyperdrive contract.
            If False, will connect to an existing hyperdrive contract (in cases of forking)
        backfill_data_start_block: int | None, optional
            In the case of attaching to an existing hyperdrive contract from a fork with `deploy = False`,
            this parameter controls the block to start backfilling the data from.
            The default is to not backfill and start from the current block.
            0 means backfill from the earliest time possible (i.e., when the pool was deployed).
            Otherwise, will backfill from the provided block number.
            NOTE: backfilling can be slow.
        """
        # pylint: disable=too-many-branches
        # pylint: disable=too-many-arguments
        # pylint: disable=too-many-positional-arguments

        # We don't call super's init since we do specific type checking
        # in Hyperdrive's init. Instead, we call _initialize
        # pylint: disable=super-init-not-called

        if config is None:
            self.config = self.Config()
        else:
            self.config = config

        # Deploys a hyperdrive factory + pool on the chain
        self._deployed_hyperdrive_factory = None
        self._deployed_hyperdrive_pool = None
        if deploy:
            if hyperdrive_address is not None:
                raise ValueError("Cannot specify a hyperdrive address if deploying a Hyperdrive contract.")
            (self._deployed_hyperdrive_factory, self._deployed_hyperdrive_pool) = self._deploy_hyperdrive(
                self.config, chain
            )
            hyperdrive_address = self._deployed_hyperdrive_pool.hyperdrive_contract.address

        else:
            if hyperdrive_address is None:
                raise ValueError("Must specify a hyperdrive address if not deploying a Hyperdrive contract.")

        if isinstance(hyperdrive_address, str):
            hyperdrive_address = Web3.to_checksum_address(hyperdrive_address)

        self._initialize(chain, hyperdrive_address, name)

        self.calc_pnl = self.chain.config.calc_pnl

        # At this point, we've deployed hyperdrive, so we want to save the block where it was deployed
        # for the data pipeline
        self._deploy_block_number = self.interface.get_deploy_block()

        if deploy:
            # If we're deploying, we expect the deploy block to be set
            if self._deploy_block_number is None:
                raise AssertionError("Expected deploy event not found")
            self._data_start_block = self._deploy_block_number
            self._analysis_start_block = self._deploy_block_number
        else:
            if backfill_data_start_block is None:
                self._data_start_block = chain.block_number()
            else:
                if self._deploy_block_number is None:
                    self._data_start_block = backfill_data_start_block
                else:
                    self._data_start_block = max(self._deploy_block_number, backfill_data_start_block)
            # Always start analysis at the current block
            self._analysis_start_block = chain.block_number()

        # Add this pool to the chain bookkeeping for snapshots
        chain._add_deployed_pool_to_bookkeeping(self)
        self.chain = chain

        # Run the data pipeline in background threads if experimental mode
        self.data_pipeline_timeout = self.config.data_pipeline_timeout

        if backfill_data_start_block is not None:
            logging.info("Backfilling data from block %s to %s", self._data_start_block, chain.block_number())
            # If this is set, we ignore manual sync and always sync the database
            self.sync_database(progress_bar=True, force_backfill=True, force_init=True)
        else:
            # Otherwise, we do this lazily if manual sync is on
            self._maybe_run_blocking_data_pipeline(force_init=True)

    def sync_database(
        self,
        start_block: int | None = None,
        progress_bar: bool = False,
        force_backfill: bool = False,
        force_init: bool = False,
    ) -> None:
        """Explicitly syncs the database with the chain.
        This function doesn't need to be explicitly called if `manual_database_sync = False`.

        The database itself will determine how to append new data to ensure non-duplicated data.
        We call this function with a start block if we want to skip intermediate blocks.
        Subsequent calls after can again be `self._deploy_block_number` as long as the
        call with skipping blocks wrote a row, as the data pipeline checks the latest
        block entry and starts from there.

        TODO these functions are not thread safe, need to fix if we expose async functions

        Arguments
        ---------
        start_block: int | None, optional
            The block number to start syncing from. Only used if we want to skip blocks in the database.
            Defaults to ensuring all blocks are synced.
        progress_bar: bool, optional
            If True, will show a progress bar.
        force_backfill: bool, optional
            If True, will force backfilling pool info data. Otherwise will look for
            `chain.config.backfill_pool_info` in the chain config.
        force_init: bool, optional
            If True, will explicitly initialize the database with this pool's info.
        """
        if start_block is None:
            data_start_block = self._data_start_block
            analysis_start_block = self._analysis_start_block
        else:
            data_start_block = start_block
            analysis_start_block = start_block

        if force_backfill:
            backfill = True
        else:
            backfill = self.chain.config.backfill_pool_info

        acquire_data(
            start_block=data_start_block,
            interfaces=[self.interface],
            db_session=self.chain.db_session,
            exit_on_catch_up=True,
            suppress_logs=True,
            progress_bar=progress_bar,
            backfill=backfill,
            force_init=force_init,
        )
        analyze_data(
            start_block=analysis_start_block,
            interfaces=[self.interface],
            db_session=self.chain.db_session,
            exit_on_catch_up=True,
            suppress_logs=True,
            calc_pnl=self.calc_pnl,
        )

    def _maybe_run_blocking_data_pipeline(
        self, start_block: int | None = None, progress_bar: bool = False, force_init: bool = False
    ) -> None:
        # Checks the chain config to see if manual sync is on. Noop if it is.
        if not self.chain.config.manual_database_sync:
            self.sync_database(start_block, progress_bar, force_init=force_init)

    # We overwrite these dunder methods to allow this object to be used as a dictionary key
    # This is used to allow chain's `advance_time` function to return this object as a key.
    def __hash__(self):
        """We use a combination of the chain's rpc uri and the hyperdrive contract address as the hash."""
        return hash((self.chain.rpc_uri, self.hyperdrive_address))

    def __eq__(self, other):
        return (self.chain.rpc_uri, self.hyperdrive_address) == (
            other.chain.rpc_uri,
            other.hyperdrive_address,
        )

    def _deploy_hyperdrive(
        self, config: Config, chain: LocalChain
    ) -> tuple[DeployedHyperdriveFactory, DeployedHyperdrivePool]:
        # sanity check (also for type checking), should get set in __post_init__
        assert config.minimum_share_reserves is not None
        factory_deploy_config = FactoryConfig(
            governance="",  # will be determined in the deploy function
            deployerCoordinatorManager="",  # will be determined in the deploy function
            hyperdriveGovernance="",  # will be determined in the deploy function
            defaultPausers=[],  # We don't support pausers when we deploy
            feeCollector="",  # will be determined in the deploy function
            sweepCollector="",  # will be determined in the deploy function
            checkpointRewarder="",  # will be determined in the deploy function
            checkpointDurationResolution=config.factory_checkpoint_duration_resolution,
            minCheckpointDuration=config.factory_min_checkpoint_duration,
            maxCheckpointDuration=config.factory_max_checkpoint_duration,
            minPositionDuration=config.factory_min_position_duration,
            maxPositionDuration=config.factory_max_position_duration,
            minCircuitBreakerDelta=config.factory_min_circuit_breaker_delta.scaled_value,
            maxCircuitBreakerDelta=config.factory_max_circuit_breaker_delta.scaled_value,
            minFixedAPR=config.factory_min_fixed_apr.scaled_value,
            maxFixedAPR=config.factory_max_fixed_apr.scaled_value,
            minTimeStretchAPR=config.factory_min_time_stretch_apr.scaled_value,
            maxTimeStretchAPR=config.factory_max_time_stretch_apr.scaled_value,
            minFees=config._factory_min_fees,  # pylint: disable=protected-access
            maxFees=config._factory_max_fees,  # pylint: disable=protected-access
            linkerFactory="",  # will be determined in the deploy function
            linkerCodeHash=bytes(),  # will be determined in the deploy function
        )

        pool_deploy_config = PoolDeployConfig(
            baseToken="",  # will be determined in the deploy function
            vaultSharesToken="",  # will be determined in the deploy function
            linkerFactory="",  # will be determined in the deploy function
            linkerCodeHash=bytes(),  # will be determined in the deploy function
            minimumShareReserves=config.minimum_share_reserves.scaled_value,
            minimumTransactionAmount=config.minimum_transaction_amount.scaled_value,
            circuitBreakerDelta=config.circuit_breaker_delta.scaled_value,
            positionDuration=config.position_duration,
            checkpointDuration=config.checkpoint_duration,
            timeStretch=0,
            governance="",  # will be determined in the deploy function
            feeCollector="",  # will be determined in the deploy function
            sweepCollector="",  # will be determined in the deploy function
            checkpointRewarder="",  # will be determined in the deploy function
            fees=config._fees,  # pylint: disable=protected-access
        )

        # TODO move deploying factory to be part of a parent, where deploying hyperdrive
        # only uses the factory
        deployed_base_and_vault = deploy_base_and_vault(
            chain._web3,
            config.deploy_type,
            chain.get_deployer_account(),
            config.initial_variable_rate,
        )

        deployed_hyperdrive_factory = deploy_hyperdrive_factory(
            chain._web3,
            chain.get_deployer_account(),
            deployed_base_and_vault,
            config.deploy_type,
            factory_deploy_config,
        )

        deployed_hyperdrive_pool = deploy_hyperdrive_from_factory(
            chain._web3,
            chain.get_deployer_account(),
            deployed_base_and_vault,
            deployed_hyperdrive_factory,
            config.deploy_type,
            config.initial_liquidity,
            config.initial_fixed_apr,
            config.initial_time_stretch_apr,
            pool_deploy_config,
        )
        return (deployed_hyperdrive_factory, deployed_hyperdrive_pool)

    def set_variable_rate(self, variable_rate: FixedPoint) -> None:
        """Sets the underlying variable rate for this pool.

        Arguments
        ---------
        variable_rate: FixedPoint
            The new variable rate for the pool.
        """
        self.interface.set_variable_rate(self.chain.get_deployer_account(), variable_rate)
        # Setting the variable rate mines a block, so we run data pipeline here
        self._maybe_run_blocking_data_pipeline()

    def _create_checkpoint(
        self,
        checkpoint_time: int | None = None,
        check_if_exists: bool = True,
        gas_limit: int | None = None,
    ) -> CreateCheckpointEventFP | None:
        """Internal function without safeguard checks for creating a checkpoint.
        Creating checkpoints is called by the chain's `advance_time`.
        """
        if checkpoint_time is None:
            block_timestamp = self.interface.get_block_timestamp(self.interface.get_current_block())
            checkpoint_time = self.interface.calc_checkpoint_id(
                self.interface.pool_config.checkpoint_duration, block_timestamp
            )

        if check_if_exists:
            checkpoint = self.interface.hyperdrive_contract.functions.getCheckpoint(checkpoint_time).call()
            # If it exists, don't create a checkpoint and return None.
            if checkpoint.vaultSharePrice > 0:
                return None

        try:
            checkpoint_event = self.interface.create_checkpoint(
                self.chain.get_deployer_account(),
                checkpoint_time=checkpoint_time,
                gas_limit=gas_limit,
            )
        except AssertionError as exc:
            # Adding additional context to the "Transaction receipt has no logs" error
            raise ValueError("Failed to create checkpoint, does the checkpoint already exist?") from exc
        # We don't call `_build_event_obj_from_tx_receipt` here because
        # it's based on the enum of `HyperdriveActionType`, which creating
        # a checkpoint isn't a trade result
        return checkpoint_event

    ### Database methods
    # These methods expose the underlying chainsync getter methods with minimal processing
    # TODO expand in docstrings the columns of the output dataframe

    def get_pool_config(self, coerce_float: bool = False) -> pd.Series:
        """Get the pool config and returns as a pandas series.

        Arguments
        ---------
        coerce_float: bool
            If True, will coerce underlying Decimals to floats.

        Returns
        -------
        pd.Series
            A pandas series that consists of the deployed pool config.
        """
        # Underlying function returns a dataframe, but this is assuming there's a single
        # pool config for this object.
        if self.chain.db_session is None:
            raise ValueError("Function requires postgres.")
        pool_config = get_pool_config(self.chain.db_session, coerce_float=coerce_float)
        if len(pool_config) == 0:
            raise ValueError("Pool config doesn't exist in the db.")
        return pool_config.iloc[0]

    def get_pool_info(self, coerce_float: bool = False) -> pd.DataFrame:
        """Get the pool info (and additional info) per block and returns as a pandas dataframe.

        Arguments
        ---------
        coerce_float: bool
            If True, will coerce underlying Decimals to floats.

        Returns
        -------
        pd.Dataframe
            A pandas dataframe that consists of the pool info per block.
        """
        if self.chain.db_session is None:
            raise ValueError("Function requires postgres.")
        pool_info = get_pool_info(self.chain.db_session, coerce_float=coerce_float).drop("id", axis=1)
        return pool_info

    def get_checkpoint_info(self, coerce_float: bool = False) -> pd.DataFrame:
        """Get the previous checkpoint infos per block and returns as a pandas dataframe.

        Arguments
        ---------
        coerce_float: bool
            If True, will coerce underlying Decimals to floats.

        Returns
        -------
        pd.Dataframe
            A pandas dataframe that consists of previous checkpoints made on this pool.
        """
        if self.chain.db_session is None:
            raise ValueError("Function requires postgres.")
        return get_checkpoint_info(
            self.chain.db_session, hyperdrive_address=self.hyperdrive_address, coerce_float=coerce_float
        )

    def get_positions(
        self,
        show_closed_positions: bool = False,
        calc_pnl: bool = False,
        coerce_float: bool = False,
    ) -> pd.DataFrame:
        """Gets all current positions of this pool and their corresponding pnl
        and returns as a pandas dataframe.

        This function only exists in local hyperdrive as only sim pool keeps track
        of all positions of all wallets.

        Arguments
        ---------
        show_closed_positions: bool, optional
            Whether to show positions closed positions (i.e., positions with zero balance). Defaults to False.
            When False, will only return currently open positions. Useful for gathering currently open positions.
            When True, will also return any closed positions. Useful for calculating overall pnl of all positions.
            Defaults to False.
        calc_pnl: bool, optional
            If the chain config's `calc_pnl` flag is False, passing in `calc_pnl=True` to this function allows for
            a one-off pnl calculation for the current positions. Ignored if the chain's `calc_pnl` flag is set to True,
            as every position snapshot will return pnl information.
        coerce_float: bool
            If True, will coerce underlying Decimals to floats.
            Defaults to False.

        Returns
        -------
        pd.Dataframe
            A dataframe consisting of currently open positions and their corresponding pnl.
        """
        if self.chain.db_session is None:
            raise ValueError("Function requires postgres.")
        position_snapshot = get_position_snapshot(
            self.chain.db_session,
            hyperdrive_address=self.interface.hyperdrive_address,
            latest_entry=True,
            coerce_float=coerce_float,
        ).drop("id", axis=1)
        if not show_closed_positions:
            position_snapshot = position_snapshot[position_snapshot["token_balance"] != 0].reset_index(drop=True)

        # If the config's calc_pnl is not set, but we pass in `calc_pnl = True` to this function,
        # we do a one off calculation to get the pnl here.
        if not self.calc_pnl and calc_pnl:
            position_snapshot = fill_pnl_values(
                position_snapshot,
                self.chain.db_session,
                self.interface,
                coerce_float=coerce_float,
            )

        # Add usernames
        position_snapshot = self.chain._add_username_to_dataframe(position_snapshot, "wallet_address")
        # Add logical name for pool
        position_snapshot = self.chain._add_hyperdrive_name_to_dataframe(position_snapshot, "hyperdrive_address")
        return position_snapshot

    def get_historical_positions(self, coerce_float: bool = False) -> pd.DataFrame:
        """Gets the history of all positions over time and their corresponding pnl
        and returns as a pandas dataframe.

        Arguments
        ---------
        coerce_float: bool
            If True, will coerce underlying Decimals to floats.

        Returns
        -------
        pd.Dataframe
            A dataframe consisting of positions over time and their corresponding pnl.
        """
        if self.chain.db_session is None:
            raise ValueError("Function requires postgres.")
        # TODO add logical name for pool
        position_snapshot = get_position_snapshot(
            self.chain.db_session, hyperdrive_address=self.interface.hyperdrive_address, coerce_float=coerce_float
        ).drop("id", axis=1)
        # Add usernames
        position_snapshot = self.chain._add_username_to_dataframe(position_snapshot, "wallet_address")
        position_snapshot = self.chain._add_hyperdrive_name_to_dataframe(position_snapshot, "hyperdrive_address")
        return position_snapshot

    def get_trade_events(self, all_token_deltas: bool = False, coerce_float: bool = False) -> pd.DataFrame:
        """Gets the ticker history of all trades and the corresponding token deltas for each trade.

        Arguments
        ---------
        all_token_deltas: bool
            When removing liquidity that results in withdrawal shares, the events table returns
            two entries for this transaction to keep track of token deltas (one for lp tokens and
            one for withdrawal shares). If this flag is true, will return all entries in the table,
            which is useful for calculating token positions. If false, will drop the duplicate
            withdrawal share entry (useful for returning a ticker).
        coerce_float: bool
            If True, will coerce underlying Decimals to floats.

        Returns
        -------
        pd.Dataframe
            A dataframe of trade events.
        """
        if self.chain.db_session is None:
            raise ValueError("Function requires postgres.")
        # TODO add timestamp back in
        out = get_trade_events(
            self.chain.db_session,
            hyperdrive_address=self.interface.hyperdrive_address,
            all_token_deltas=all_token_deltas,
            coerce_float=coerce_float,
        ).drop("id", axis=1)
        out = self.chain._add_username_to_dataframe(out, "wallet_address")
        out = self.chain._add_hyperdrive_name_to_dataframe(out, "hyperdrive_address")
        return out

    def get_historical_pnl(self, coerce_float: bool = False) -> pd.DataFrame:
        """Gets total pnl for each wallet for each block, aggregated across all open positions.

        Arguments
        ---------
        coerce_float: bool
            If True, will coerce underlying Decimals to floats.

        Returns
        -------
        pd.Dataframe
            A dataframe of aggregated wallet pnl per block
        """
        if self.chain.db_session is None:
            raise ValueError("Function requires postgres.")
        out = get_total_pnl_over_time(self.chain.db_session, coerce_float=coerce_float)
        out = self.chain._add_username_to_dataframe(out, "wallet_address")
        return out

    ################
    # Bookkeeping
    ################

    def _reinit_state_after_load_snapshot(self) -> None:
        """After loading a snapshot, we need to re-initialize the state the internal
        variables of the interactive hyperdrive.
        1. Wipe the cache from the hyperdrive interface.
        2. Load all agent's wallets from the db.
        """
        # Set internal state block number to 0 to enusre it updates
        self.interface.last_state_block_number = BlockNumber(0)
        # Clear the read interface cache
        self.interface._read_interface = None

    def _sync_events(self) -> None:
        # Making sure this function isn't called in local_hyperdrive
        raise NotImplementedError

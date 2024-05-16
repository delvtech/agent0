"""Defines the interactive hyperdrive class that encapsulates a hyperdrive pool."""

from __future__ import annotations

import logging
import os
import pathlib
import subprocess
import time
from dataclasses import asdict, dataclass
from threading import Thread
from typing import Literal, Type, overload

import dill
import pandas as pd
from eth_account.account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import BlockNumber, ChecksumAddress
from fixedpointmath import FixedPoint
from IPython.display import IFrame

from agent0.chainsync.db.base import add_addr_to_username
from agent0.chainsync.db.hyperdrive import (
    get_checkpoint_info,
    get_pool_config,
    get_pool_info,
    get_position_snapshot,
    get_total_pnl_over_time,
    get_trade_events,
)
from agent0.chainsync.exec import acquire_data, analyze_data
from agent0.core.base.make_key import make_private_key
from agent0.core.hyperdrive import HyperdrivePolicyAgent, TradeResult, TradeStatus
from agent0.core.hyperdrive.crash_report import get_anvil_state_dump
from agent0.core.hyperdrive.policies import HyperdriveBasePolicy
from agent0.ethpy.hyperdrive import (
    AssetIdPrefix,
    DeployedHyperdrivePool,
    ReceiptBreakdown,
    deploy_hyperdrive_from_factory,
    encode_asset_id,
)
from agent0.hypertypes import FactoryConfig, Fees, PoolDeployConfig

from .event_types import (
    AddLiquidity,
    CloseLong,
    CloseShort,
    CreateCheckpoint,
    OpenLong,
    OpenShort,
    RedeemWithdrawalShares,
    RemoveLiquidity,
)
from .hyperdrive import Hyperdrive
from .local_chain import LocalChain
from .local_hyperdrive_agent import LocalHyperdriveAgent

# Is very thorough module.
# pylint: disable=too-many-lines


class LocalHyperdrive(Hyperdrive):
    """Interactive Hyperdrive class that supports an interactive interface for running tests and experiments."""

    # Lots of attributes in config
    # pylint: disable=too-many-instance-attributes
    @dataclass(kw_only=True)
    class Config(Hyperdrive.Config):
        """The configuration for the local hyperdrive pool."""

        # Environment variables
        data_pipeline_timeout: int = 60
        """The timeout for the data pipeline. Defaults to 60 seconds."""
        crash_log_ticker: bool = False
        """Whether to log the trade ticker in crash reports. Defaults to False."""
        dashboard_port: int = 7777
        """The URL port for the deployed dashboard."""
        load_rng_on_snapshot: bool = True
        """
        If True, loading a snapshot also loads the RNG state of the underlying policy.
        This results in the same RNG state as when the snapshot was taken.
        If False, will use the existing RNG state before load.
        Defaults to False.
        """

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
        minimum_share_reserves: FixedPoint = FixedPoint(10)
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
            super().__post_init__()

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

    def __init__(self, chain: LocalChain, config: Config | None = None):
        """Constructor for the interactive hyperdrive agent.

        Arguments
        ---------
        chain: LocalChain
            The local chain object to launch hyperdrive on
        config: Config | None
            The configuration for the initial pool configuration
        """

        # We don't call super's init since we do specific type checking
        # in Hyperdrive's init. Instead, we call _initialize
        # pylint: disable=super-init-not-called

        if config is None:
            self.config = self.Config()
        else:
            self.config = config

        self.calc_pnl = self.config.calc_pnl

        # Deploys a hyperdrive factory + pool on the chain
        self._deployed_hyperdrive = self._deploy_hyperdrive(self.config, chain)

        self._initialize(chain, self.get_hyperdrive_address())

        # At this point, we've deployed hyperdrive, so we want to save the block where it was deployed
        # for the data pipeline
        self._deploy_block_number = self.interface.get_block_number(self.interface.get_current_block())

        # Add this pool to the chain bookkeeping for snapshots
        chain._add_deployed_pool_to_bookkeeping(self)
        self.chain = chain

        # We use this variable to control underlying threads when to exit.
        # When this varible is set to true, the underlying threads will exit.
        self._stop_threads = False
        self._data_thread: Thread | None = None
        self._analysis_thread: Thread | None = None

        # Run the data pipeline in background threads if experimental mode
        self.data_pipeline_timeout = self.config.data_pipeline_timeout

        self._run_blocking_data_pipeline()

        self.dashboard_subprocess: subprocess.Popen | None = None
        self._pool_agents: list[LocalHyperdriveAgent] = []

    def get_hyperdrive_address(self) -> ChecksumAddress:
        """Returns the hyperdrive addresses for this pool.

        Returns
        -------
        ChecksumAddress
            The hyperdrive addresses for this pool
        """
        # pylint: disable=protected-access
        return self._deployed_hyperdrive.hyperdrive_contract.address

    def _run_blocking_data_pipeline(self, start_block: int | None = None) -> None:
        # TODO these functions are not thread safe, need to fix if we expose async functions
        # Runs the data pipeline synchronously

        # We call this function with a start block if we want to skip intermediate blocks.
        # Subsequent calls after can again be `self._deploy_block_number` as long as the
        # call with skipping blocks wrote a row, as the data pipeline checks the latest
        # block entry and starts from there.
        if start_block is None:
            start_block = self._deploy_block_number

        acquire_data(
            start_block=start_block,  # Start block is the block hyperdrive was deployed
            interfaces=[self.interface],
            db_session=self.chain.db_session,
            exit_on_catch_up=True,
            suppress_logs=True,
        )
        analyze_data(
            start_block=start_block,
            interfaces=[self.interface],
            db_session=self.chain.db_session,
            exit_on_catch_up=True,
            suppress_logs=True,
            calc_pnl=self.calc_pnl,
        )

    def _cleanup(self):
        """Cleans up resources used by this object."""
        super()._cleanup()

        if self.dashboard_subprocess is not None:
            self.dashboard_subprocess.kill()
            self.dashboard_subprocess = None

    # We overwrite these dunder methods to allow this object to be used as a dictionary key
    # This is used to allow chain's `advance_time` function to return this object as a key.
    def __hash__(self):
        """We use a combination of the chain's rpc uri and the hyperdrive contract address as the hash."""
        return hash((self.chain.rpc_uri, self._deployed_hyperdrive.hyperdrive_contract.address))

    def __eq__(self, other):
        return (self.chain.rpc_uri, self._deployed_hyperdrive.hyperdrive_contract.address) == (
            other.chain.rpc_uri,
            other._deployed_hyperdrive.hyperdrive_contract.address,
        )

    def _deploy_hyperdrive(self, config: Config, chain: LocalChain) -> DeployedHyperdrivePool:
        # sanity check (also for type checking), should get set in __post_init__
        factory_deploy_config = FactoryConfig(
            governance="",  # will be determined in the deploy function
            deployerCoordinatorManager="",  # will be determined in the deploy function
            hyperdriveGovernance="",  # will be determined in the deploy function
            defaultPausers=[],  # We don't support pausers when we deploy
            feeCollector="",  # will be determined in the deploy function
            sweepCollector="",  # will be determined in the deploy function
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
            fees=config._fees,  # pylint: disable=protected-access
        )

        return deploy_hyperdrive_from_factory(
            chain.rpc_uri,
            chain.get_deployer_account_private_key(),
            config.initial_liquidity,
            config.initial_variable_rate,
            config.initial_fixed_apr,
            config.initial_time_stretch_apr,
            factory_deploy_config,
            pool_deploy_config,
        )

    def set_variable_rate(self, variable_rate: FixedPoint) -> None:
        """Sets the underlying variable rate for this pool.

        Arguments
        ---------
        variable_rate: FixedPoint
            The new variable rate for the pool.
        """
        self.interface.set_variable_rate(self._deployed_hyperdrive.deploy_account, variable_rate)
        # Setting the variable rate mines a block, so we run data pipeline here
        self._run_blocking_data_pipeline()

    def _create_checkpoint(
        self, checkpoint_time: int | None = None, check_if_exists: bool = True
    ) -> CreateCheckpoint | None:
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
            tx_receipt = self.interface.create_checkpoint(
                self._deployed_hyperdrive.deploy_account, checkpoint_time=checkpoint_time
            )
        except AssertionError as exc:
            # Adding additional context to the "Transaction receipt has no logs" error
            raise ValueError("Failed to create checkpoint, does the checkpoint already exist?") from exc
        # We don't call `_build_event_obj_from_tx_receipt` here because
        # it's based on the enum of `HyperdriveActionType`, which creating
        # a checkpoint isn't a trade result
        return CreateCheckpoint(
            checkpoint_time=tx_receipt.checkpoint_time,
            vault_share_price=tx_receipt.vault_share_price,
            checkpoint_vault_share_price=tx_receipt.checkpoint_vault_share_price,
            matured_shorts=tx_receipt.matured_shorts,
            matured_longs=tx_receipt.matured_longs,
            lp_share_price=tx_receipt.lp_share_price,
        )

    def init_agent(
        self,
        private_key: str | None = None,
        policy: Type[HyperdriveBasePolicy] | None = None,
        policy_config: HyperdriveBasePolicy.Config | None = None,
        name: str | None = None,
        base: FixedPoint | None = None,
        eth: FixedPoint | None = None,
    ) -> LocalHyperdriveAgent:
        """Initializes an agent with initial funding and a logical name.

        Arguments
        ---------
        private_key: str, optional
            The private key of the associated account. Default is auto-generated.
        policy: HyperdrivePolicy, optional
            An optional policy to attach to this agent.
        policy_config: HyperdrivePolicy, optional
            The configuration for the attached policy.
        base: FixedPoint | None, optional
            The amount of base to fund the agent with. Defaults to 0.
            If a private key is provided then the base amount is added to their previous balance.
        eth: FixedPoint | None, optional
            The amount of ETH to fund the agent with. Defaults to 0.
            If a private key is provided then the eth amount is added to their previous balance.
        name: str, optional
            The name of the agent. Defaults to the wallet address.

        Returns
        -------
        LocalHyperdriveAgent
            The agent object for a user to execute trades with.
        """
        # pylint: disable=too-many-arguments
        if self.chain._has_saved_snapshot:  # pylint: disable=protected-access
            logging.warning(
                "Adding new agent with existing snapshot. "
                "This object will no longer be valid if the snapshot is loaded."
            )
        if base is None:
            base = FixedPoint(0)
        if eth is None:
            eth = FixedPoint(0)
        # If the underlying policy's rng isn't set, we use the one from interactive hyperdrive
        if policy_config is not None and policy_config.rng is None and policy_config.rng_seed is None:
            policy_config.rng = self.config.rng
        out_agent = LocalHyperdriveAgent(
            base=base,
            eth=eth,
            name=name,
            pool=self,
            policy=policy,
            policy_config=policy_config,
            private_key=private_key,
        )
        self._pool_agents.append(out_agent)
        return out_agent

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
        pool_config = get_pool_config(self.chain.db_session, coerce_float=coerce_float)
        if len(pool_config) == 0:
            raise ValueError("Pool config doesn't exist in the db.")
        return pool_config.iloc[0]

    def get_pool_info(self, coerce_float: bool = False) -> pd.DataFrame:
        """Get the pool info (and additional info) per block and returns as a pandas dataframe.

        Arguments
        ---------
        add_analysis_columns: bool
            If True, will add additional analysis columns to the output dataframe.
        coerce_float: bool
            If True, will coerce underlying Decimals to floats.

        Returns
        -------
        pd.Dataframe
            A pandas dataframe that consists of the pool info per block.
        """
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
            A pandas dataframe that consists of previous checkpoints made.
        """
        return get_checkpoint_info(self.chain.db_session, coerce_float=coerce_float)

    def get_positions(self, show_zero_balance: bool = False, coerce_float: bool = False) -> pd.DataFrame:
        """Gets all current positions of this pool and their corresponding pnl
        and returns as a pandas dataframe.
        This function only exists in local hyperdrive as only sim pool keeps track
        of all positions of all wallets.

        Arguments
        ---------
        coerce_float: bool
            If True, will coerce underlying Decimals to floats.
        show_zero_balance: bool
            Whether to show positions with zero balance.
            When False, will only return currently open positions. Useful for gathering currently open positions.
            When True, will also return any closed positions. Useful for calculating overall pnl of all positions.

        Returns
        -------
        pd.Dataframe
            A dataframe consisting of currently open positions and their corresponding pnl.
        """
        # TODO add timestamp back in
        # TODO add logical name for pool
        position_snapshot = get_position_snapshot(
            self.chain.db_session,
            hyperdrive_address=self.interface.hyperdrive_address,
            start_block=-1,
            coerce_float=coerce_float,
        ).drop("id", axis=1)
        if not show_zero_balance:
            position_snapshot = position_snapshot[position_snapshot["token_balance"] != 0].reset_index(drop=True)
        # Add usernames
        out = self._add_username_to_dataframe(position_snapshot, "wallet_address")
        return out

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
        # TODO add timestamp back in
        # TODO add logical name for pool
        position_snapshot = get_position_snapshot(
            self.chain.db_session, hyperdrive_address=self.interface.hyperdrive_address, coerce_float=coerce_float
        ).drop("id", axis=1)
        # Add usernames
        out = self._add_username_to_dataframe(position_snapshot, "wallet_address")
        return out

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
        # TODO add timestamp back in
        out = get_trade_events(
            self.chain.db_session,
            hyperdrive_address=self.interface.hyperdrive_address,
            all_token_deltas=all_token_deltas,
            coerce_float=coerce_float,
        ).drop("id", axis=1)
        # TODO add pool name
        out = self._add_username_to_dataframe(out, "wallet_address")
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
        out = get_total_pnl_over_time(self.chain.db_session, coerce_float=coerce_float)
        out = self._add_username_to_dataframe(out, "wallet_address")
        return out

    def _get_dashboard_run_command(self, flags: list[str] | None = None) -> list[str]:
        """Returns the run command for launching a Streamlit dashboard.

        Arguments
        ---------
        flags: list[str] | None, optional
            List of streamlit flags to be added to the run command.
            Commands and arguments should be seperate entries, for example: ["--server.headless", "true"]
            Defaults to an empty list, which passes no flags.

        Returns
        -------
        str
            The streamlit run command string.
        """
        if flags is None:
            flags = []
        # In order to support this command in both notebooks and scripts, we reference
        # the path to the virtual environment relative to this file.
        base_dir = pathlib.Path(__file__).parent.parent.parent.parent.parent.parent.resolve()
        venv_dir = pathlib.Path(os.environ["VIRTUAL_ENV"])
        streamlit_path = str(venv_dir / "bin" / "streamlit")
        dashboard_path = str(base_dir / "src" / "agent0" / "chainsync" / "streamlit" / "Dashboard.py")
        dashboard_run_command = (
            [streamlit_path, "run"]
            + flags
            + [
                dashboard_path,
            ]
        )
        return dashboard_run_command

    def run_dashboard(self, blocking: bool = False) -> None:
        """Runs the streamlit dashboard in a subprocess connected to interactive hyperdrive.

        .. note::
            The interactive hyperdrive script must be in a paused state (before cleanup) for the dashboard to
            connect with the underlying database, otherwise `cleanup` and/or the main thread executed will kill the
            streamlit server. Passing ``blocking=True`` will block execution of the main
            script in this function until a keypress is registered.

        Arguments
        ---------
        blocking: bool
            If True, will block execution of the main script in this function until a keypress is registered.
            When in blocking mode, the server will be killed upon return of control to caller.
            If False, will clean up subprocess in cleanup.
        """

        dashboard_run_command = self._get_dashboard_run_command(
            flags=[
                "--server.port",
                str(self.config.dashboard_port),
                "--server.address",
                "localhost",
            ]
        )
        env = {key: str(val) for key, val in asdict(self.chain.postgres_config).items()}

        assert self.dashboard_subprocess is None
        # Since dashboard is a non-terminating process, we need to manually control its lifecycle
        self.dashboard_subprocess = subprocess.Popen(  # pylint: disable=consider-using-with
            dashboard_run_command,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )
        if blocking:
            input("Press any key to kill dashboard server.")
            self.dashboard_subprocess.kill()
            self.dashboard_subprocess = None

    def get_dashboard_iframe(self, width: int = 1000, height: int = 800) -> IFrame:
        """Embeds the streamlit dashboard into a Jupyter notebook as an IFrame.

        .. note::
            The interactive hyperdrive script must be in a paused state (before cleanup) for the dashboard to
            connect with the underlying database, otherwise `cleanup` and/or the main thread executed will kill the
            streamlit server. Passing ``blocking=True`` will block execution of the main
            script in this function until a keypress is registered.

        Arguments
        ---------
        width: int
            Width, in pixels, of the IFrame.
            Defaults to 1000.
        height: int
            Height, in pixels, of the IFrame.
            Defaults to 800.

        Returns
        -------
        IFrame
            An dashboard IFrame that can be shown in a Jupyter notebook with the `display` command.
        """
        dashboard_run_command = self._get_dashboard_run_command(
            flags=[
                "--server.headless",
                "true",
                "--server.port",
                str(self.config.dashboard_port),
                "--server.address",
                "localhost",
            ]
        )
        env = {key: str(val) for key, val in asdict(self.chain.postgres_config).items()}
        self.dashboard_subprocess = subprocess.Popen(  # pylint: disable=consider-using-with
            dashboard_run_command,
            env=env,
            # stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        network_url = f"http://localhost:{self.config.dashboard_port}"

        dashboard_iframe = IFrame(src=network_url, width=width, height=height)
        time.sleep(2)  # TODO: This is a hack, need to sleep to let the page load
        return dashboard_iframe

    ### Private agent methods ###

    def _init_local_agent(
        self,
        base: FixedPoint,
        eth: FixedPoint,
        name: str | None,
        policy: Type[HyperdriveBasePolicy] | None,
        policy_config: HyperdriveBasePolicy.Config | None,
        private_key: str | None = None,
    ) -> HyperdrivePolicyAgent:
        # We overwrite the base init agents with different parameters
        # pylint: disable=arguments-differ
        # pylint: disable=too-many-arguments
        agent_private_key = make_private_key() if private_key is None else private_key

        # Setting the budget to 0 here, we'll update the wallet from the chain
        if policy is None:
            if policy_config is None:
                policy_config = HyperdriveBasePolicy.Config(rng=self.config.rng)
            policy_obj = HyperdriveBasePolicy(policy_config)
        else:
            if policy_config is None:
                policy_config = policy.Config(rng=self.config.rng)
            policy_obj = policy(policy_config)

        # Setting the budget to 0 here, `_add_funds` will take care of updating the wallet
        agent = HyperdrivePolicyAgent(
            Account().from_key(agent_private_key), initial_budget=FixedPoint(0), policy=policy_obj
        )
        # Update wallet to agent's previous budget
        if private_key is not None:  # address already existed
            agent.wallet.balance.amount = self.interface.get_eth_base_balances(agent)[1]
            agent.wallet.lp_tokens = FixedPoint(
                scaled_value=self.interface.hyperdrive_contract.functions.balanceOf(
                    encode_asset_id(AssetIdPrefix.LP, 0),
                    agent.checksum_address,
                ).call()
            )
            agent.wallet.withdraw_shares = FixedPoint(
                scaled_value=self.interface.hyperdrive_contract.functions.balanceOf(
                    encode_asset_id(AssetIdPrefix.WITHDRAWAL_SHARE, 0),
                    agent.checksum_address,
                ).call()
            )
        # Fund agent
        if eth > 0 or base > 0:
            self._add_funds(agent, base, eth)

        # Establish max approval for the hyperdrive contract
        self._set_max_approval(agent)

        # Register the username if it was provided
        if name is not None:
            add_addr_to_username(name, [agent.address], self.chain.db_session)
        return agent

    def _sync_events(self, agent: HyperdrivePolicyAgent) -> None:
        # No need to sync in local hyperdrive, we sync when we run the data pipeline
        pass

    def _sync_snapshot(self, agent: HyperdrivePolicyAgent) -> None:
        # No need to sync in local hyperdrive, we sync when we run the data pipeline
        pass

    def _add_funds(
        self,
        agent: HyperdrivePolicyAgent,
        base: FixedPoint,
        eth: FixedPoint,
        signer_account: LocalAccount | None = None,
    ) -> None:
        # Adding funds default to the deploy account
        if signer_account is None:
            signer_account = self._deployed_hyperdrive.deploy_account

        super()._add_funds(agent, base, eth, signer_account=signer_account)

        # Adding funds mines a block, so we run data pipeline here
        self._run_blocking_data_pipeline()

    @overload
    def _handle_trade_result(
        self, trade_result: TradeResult, always_throw_exception: Literal[True]
    ) -> ReceiptBreakdown: ...

    @overload
    def _handle_trade_result(
        self, trade_result: TradeResult, always_throw_exception: Literal[False]
    ) -> ReceiptBreakdown | None: ...

    def _handle_trade_result(self, trade_result: TradeResult, always_throw_exception: bool) -> ReceiptBreakdown | None:
        # We add specific data to the trade result from interactive hyperdrive
        if trade_result.status == TradeStatus.FAIL:
            assert trade_result.exception is not None
            # TODO we likely want to explicitly check for slippage here and not
            # get anvil state dump if it's a slippage error and the user wants to
            # ignore slippage errors
            trade_result.anvil_state = get_anvil_state_dump(self.interface.web3)
            if self.config.crash_log_ticker:
                if trade_result.additional_info is None:
                    trade_result.additional_info = {"trade_events": self.get_trade_events()}
                else:
                    trade_result.additional_info["trade_events"] = self.get_trade_events()

        # This check is necessary for subclass overloading and typing,
        # as types are narrowed based on the literal `always_throw_exception`
        if always_throw_exception:
            return super()._handle_trade_result(trade_result, always_throw_exception)
        return super()._handle_trade_result(trade_result, always_throw_exception)

    def _open_long(self, agent: HyperdrivePolicyAgent, base: FixedPoint) -> OpenLong:
        out = super()._open_long(agent, base)
        self._run_blocking_data_pipeline()
        return out

    def _close_long(self, agent: HyperdrivePolicyAgent, maturity_time: int, bonds: FixedPoint) -> CloseLong:
        out = super()._close_long(agent, maturity_time, bonds)
        self._run_blocking_data_pipeline()
        return out

    def _open_short(self, agent: HyperdrivePolicyAgent, bonds: FixedPoint) -> OpenShort:
        out = super()._open_short(agent, bonds)
        self._run_blocking_data_pipeline()
        return out

    def _close_short(self, agent: HyperdrivePolicyAgent, maturity_time: int, bonds: FixedPoint) -> CloseShort:
        out = super()._close_short(agent, maturity_time, bonds)
        self._run_blocking_data_pipeline()
        return out

    def _add_liquidity(self, agent: HyperdrivePolicyAgent, base: FixedPoint) -> AddLiquidity:
        out = super()._add_liquidity(agent, base)
        self._run_blocking_data_pipeline()
        return out

    def _remove_liquidity(self, agent: HyperdrivePolicyAgent, shares: FixedPoint) -> RemoveLiquidity:
        out = super()._remove_liquidity(agent, shares)
        self._run_blocking_data_pipeline()
        return out

    def _redeem_withdraw_share(self, agent: HyperdrivePolicyAgent, shares: FixedPoint) -> RedeemWithdrawalShares:
        out = super()._redeem_withdraw_share(agent, shares)
        self._run_blocking_data_pipeline()
        return out

    def _execute_policy_action(
        self, agent: HyperdrivePolicyAgent
    ) -> list[OpenLong | OpenShort | CloseLong | CloseShort | AddLiquidity | RemoveLiquidity | RedeemWithdrawalShares]:
        out = super()._execute_policy_action(agent)
        self._run_blocking_data_pipeline()
        return out

    def _liquidate(
        self, agent: HyperdrivePolicyAgent, randomize: bool
    ) -> list[CloseLong | CloseShort | RemoveLiquidity | RedeemWithdrawalShares]:
        out = super()._liquidate(agent, randomize)
        self._run_blocking_data_pipeline()
        return out

    def _reinit_state_after_load_snapshot(self) -> None:
        """After loading a snapshot, we need to re-initialize the state the internal
        variables of the interactive hyperdrive.
        1. Wipe the cache from the hyperdrive interface.
        2. Load all agent's wallets from the db.
        """
        # Set internal state block number to 0 to enusre it updates
        self.interface.last_state_block_number = BlockNumber(0)

        # Load and set all agent wallets from the db
        for agent in self._pool_agents:
            agent.agent.wallet = self._get_wallet(agent.agent)

    def _save_agent_bookkeeping(self, save_dir: str) -> None:
        """Saves the policy state to file.

        Arguments
        ---------
        save_dir: str
            The directory to save the state to.
        """
        policy_file = save_dir + "/" + self.interface.hyperdrive_contract.address + "-agents.pkl"
        agents = [agent.checksum_address for agent in self._pool_agents]
        with open(policy_file, "wb") as file:
            # We use dill, as pickle can't store local objects
            dill.dump(agents, file, protocol=dill.HIGHEST_PROTOCOL)

    def _save_policy_state(self, save_dir: str) -> None:
        """Saves the policy state to file.

        Arguments
        ---------
        save_dir: str
            The directory to save the state to.
        """
        # The policy file is stored as <pool_hyperdrive_contract_address>-<agent_checksum_address>.pkl
        policy_file_prefix = save_dir + "/" + self.interface.hyperdrive_contract.address + "-"
        for agent in self._pool_agents:
            policy_file = policy_file_prefix + agent.checksum_address + ".pkl"
            with open(policy_file, "wb") as file:
                # We use dill, as pickle can't store local objects
                dill.dump(agent.agent.policy, file, protocol=dill.HIGHEST_PROTOCOL)

    def _load_agent_bookkeeping(self, load_dir: str) -> None:
        """Loads the list of agents from file.

        Arguments
        ---------
        load_dir: str
            The directory to load the state from.
        """
        policy_file = load_dir + "/" + self.interface.hyperdrive_contract.address + "-agents.pkl"
        with open(policy_file, "rb") as file:
            # We use dill, as pickle can't store local objects
            load_agents = dill.load(file)
        # Remove references of all agents added after snapshot
        # NOTE: existing agent objects initialized after snapshot will no longer be valid.
        self._pool_agents = [agent for agent in self._pool_agents if agent.checksum_address in load_agents]

    def _load_policy_state(self, load_dir: str) -> None:
        """Loads the policy state from file.

        Arguments
        ---------
        load_dir: str
            The directory to load the state from.
        """
        # The policy file is stored as <pool_hyperdrive_contract_address>-<agent_checksum_address>.pkl
        policy_file_prefix = load_dir + "/" + self.interface.hyperdrive_contract.address + "-"
        for agent in self._pool_agents:
            policy_file = policy_file_prefix + agent.checksum_address + ".pkl"
            with open(policy_file, "rb") as file:
                # If we don't load rng, we get the current RNG state and set it after loading
                rng = None
                if not self.config.load_rng_on_snapshot:
                    rng = agent.agent.policy.rng
                # We use dill, as pickle can't store local objects
                agent.agent.policy = dill.load(file)
                if not self.config.load_rng_on_snapshot:
                    # For type checking
                    assert rng is not None
                    agent.agent.policy.rng = rng

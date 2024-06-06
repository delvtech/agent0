"""The chain objects that encapsulates a chain."""

from __future__ import annotations

import logging
import os
import pathlib
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Type

import dill
from eth_account.account import Account
from eth_account.signers.local import LocalAccount
from fixedpointmath import FixedPoint
from IPython.display import IFrame
from web3.types import RPCEndpoint

from agent0.chainsync.db.hyperdrive.import_export_data import export_db_to_file, import_to_db
from agent0.core.hyperdrive.crash_report import get_anvil_state_dump
from agent0.core.hyperdrive.policies import HyperdriveBasePolicy

from .chain import Chain
from .event_types import CreateCheckpoint
from .local_hyperdrive import LocalHyperdrive
from .local_hyperdrive_agent import LocalHyperdriveAgent

if TYPE_CHECKING:
    from .hyperdrive import Hyperdrive


# pylint: disable=too-many-instance-attributes
# pylint: disable=protected-access


class LocalChain(Chain):
    """Launches a local anvil chain in a subprocess, along with a postgres container."""

    # Pylint is complaining that `load_state` is an abstract method, so we need to overwrite here.
    # However, `load_state` is just a function stub that needs to throw `NotImplementedError` if called.
    # pylint: disable=abstract-method

    @dataclass(kw_only=True)
    class Config(Chain.Config):
        """The configuration for the local chain object."""

        dashboard_port: int = 7777
        """The URL port for the deployed dashboard."""
        block_time: int | None = None
        """If None, mines per transaction. Otherwise mines every `block_time` seconds."""
        block_timestamp_interval: int | None = 12
        """Number of seconds to advance time for every mined block. Uses real time if None."""
        chain_host: str | None = None
        """The host to bind for the anvil chain. Defaults to `127.0.0.1`."""
        # TODO allow chain_port to be None to allow for automatically finding an open port within range.
        chain_port: int = 10_000
        """The port to bind for the anvil chain. Will fail if this port is being used."""
        chain_genesis_timestamp: int | None = None
        """The genesis timestamp (in epoch seconds) for the anvil chain. If None, uses the current time."""
        transaction_block_keeper: int = 10_000
        """The number of blocks to keep transaction records for. Undocumented in Anvil, we're being optimistic here."""
        snapshot_dir: str | None = None
        """
        The directory where the snapshot will be stored. 
        Defaults to `.interactive_state/snapshot/chain_<chain_port>`.
        """
        load_rng_on_snapshot: bool = True
        """
        If True, loading a snapshot also loads the RNG state of the underlying policy.
        This results in the same RNG state as when the snapshot was taken.
        If False, will use the existing RNG state before load.
        Defaults to False.
        """
        advance_time_create_checkpoint_retry_count: int | None = None
        """
        The number of times to retry creating checkpoints when advancing time.
        Defaults to no retries.
        """

        crash_log_ticker: bool = False
        """Whether to log the trade ticker in crash reports. Defaults to False."""

    def __init__(
        self,
        config: Config | None = None,
        fork_uri: str | None = None,
        fork_block_number: int | None = None,
    ):
        """Initialize the Chain class that connects to an existing chain.

        Also launch a postgres docker container for gathering data.

        Arguments
        ---------
        config: Config | None, optional
            The local chain configuration. Will use defaults if not provided.
        fork_uri: str | None, optional
            The URI of the fork to connect to. Will start a chain from scratch if not set.
        fork_block_number: int | None, optional
            The block number to fork at if fork_uri is set. Defaults to latest.
        """
        if config is None:
            config = self.Config()

        if config.chain_host is None:
            chain_host = "127.0.0.1"
        else:
            chain_host = config.chain_host

        anvil_launch_args = [
            "anvil",
            "--host",
            chain_host,
            "--port",
            str(config.chain_port),
            "--code-size-limit",
            "9999999999",
            "--transaction-block-keeper",
            str(config.transaction_block_keeper),
        ]
        if config.block_time is not None:
            anvil_launch_args.extend(("--block-time", str(config.block_time)))

        if config.chain_genesis_timestamp is not None:
            anvil_launch_args.extend(("--timestamp", str(config.chain_genesis_timestamp)))

        if fork_uri is not None:
            anvil_launch_args.extend(["--fork-url", fork_uri])
            if fork_block_number is not None:
                anvil_launch_args.extend(["--fork-block-number", str(fork_block_number)])

        # This process never stops, so we run this in the background and explicitly clean up later
        self.anvil_process = subprocess.Popen(  # pylint: disable=consider-using-with
            # Suppressing output of anvil
            anvil_launch_args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            close_fds=True,
        )

        # TODO HACK wait for anvil to start, ideally we would be looking for the output to stdout
        # Forking takes a bit longer to spin up, so we only sleep when forking
        if fork_uri is not None:
            time.sleep(2)

        super().__init__(f"http://127.0.0.1:{str(config.chain_port)}", config)

        # Snapshot bookkeeping
        # Put chain_id as a separate directory to avoid conflicts
        if config.snapshot_dir is None:
            self._snapshot_dir = Path(".interactive_state") / "snapshot" / ("chain_" + str(self.chain_id))
        else:
            self._snapshot_dir = Path(config.snapshot_dir)

        self._saved_snapshot_id: str
        self._has_saved_snapshot = False
        self._deployed_hyperdrive_pools: list[LocalHyperdrive] = []
        self._chain_agents: list[LocalHyperdriveAgent] = []

        # Ensure snapshot dir exists
        os.makedirs(self._snapshot_dir, exist_ok=True)

        if config.block_timestamp_interval is not None:
            self._set_block_timestamp_interval(config.block_timestamp_interval)

        self.config = config
        self.dashboard_subprocess: subprocess.Popen | None = None

        # TODO hack, wait for chain to init
        time.sleep(1)

    def cleanup(self):
        """Kills the subprocess in this class' destructor."""
        # Runs cleanup on all deployed pools
        try:
            if self.anvil_process is not None:
                if self.anvil_process.stdout is not None:
                    self.anvil_process.stdout.close()
                if self.anvil_process.stderr is not None:
                    self.anvil_process.stderr.close()
                self.anvil_process.terminate()
                self.anvil_process = None
        except Exception:  # pylint: disable=broad-except
            pass

        try:
            if self.dashboard_subprocess is not None:
                if self.dashboard_subprocess.stdout is not None:
                    self.dashboard_subprocess.stdout.close()
                if self.dashboard_subprocess.stderr is not None:
                    self.dashboard_subprocess.stderr.close()
                self.dashboard_subprocess.terminate()
                self.dashboard_subprocess = None
        except Exception:  # pylint: disable=broad-except
            pass

        super().cleanup()

    def get_deployer_account_private_key(self) -> str:
        """Get the private key of the deployer account.

        Returns
        -------
        str
            The private key for the deployer account.
        """
        # TODO this is the deployed account for anvil, get this programmatically
        return "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"

    def get_deployer_account(self) -> LocalAccount:
        """Get the public key of the deployer account.

        Returns
        -------
        src
            The public key for the deployer account.
        """
        return Account().from_key(self.get_deployer_account_private_key())

    def get_deployer_address(self) -> str:
        """Get the public key of the deployer account.

        Returns
        -------
        src
            The public key for the deployer account.
        """
        return self.get_deployer_account().address

    @property
    def is_local_chain(self) -> bool:
        """Returns if this object is a local chain."""
        return True

    ##########
    # Advance time functions
    ##########

    def _advance_chain_time(self, time_delta: int) -> None:
        # We explicitly set the next block timestamp to be exactly time_delta seconds
        # after the previous block. Hence, we first get the current block, followed by
        # an explicit set of the next block timestamp, followed by a mine.
        latest_blocktime = self._web3.eth.get_block("latest").get("timestamp", None)
        if latest_blocktime is None:
            raise AssertionError("The provided block has no timestamp")
        next_blocktime = latest_blocktime + time_delta
        response = self._web3.provider.make_request(method=RPCEndpoint("evm_mine"), params=[next_blocktime])

        # ensure response is valid
        if "result" not in response:
            raise KeyError("Response did not have a result.")

    def _set_block_timestamp_interval(self, timestamp_interval: int) -> None:
        response = self._web3.provider.make_request(
            method=RPCEndpoint("anvil_setBlockTimestampInterval"), params=[timestamp_interval]
        )
        # ensure response is valid
        if "result" not in response:
            raise KeyError("Response did not have a result.")

    # pylint: disable=too-many-branches
    def advance_time(
        self, time_delta: int | timedelta, create_checkpoints: bool = True
    ) -> dict[LocalHyperdrive, list[CreateCheckpoint]]:
        """Advance time for this chain using the `evm_mine` RPC call.

        This function looks at the timestamp of the current block, then
        mines a block explicitly setting the timestamp to the current block timestamp + time_delta.

        If create_checkpoints is True, it will also create intermediate when advancing time.

        .. note::
            This advances the chain for all pool connected to this chain.

        .. note::
            This function is a best effort attempt at being exact in advancing time, but the final result
            may be off by a second.

        Arguments
        ---------
        time_delta: int | timedelta
            The amount of time to advance. Can either be a `datetime.timedelta` object or an integer in seconds.
        create_checkpoints: bool, optional
            If set to true, will create intermediate checkpoints between advance times. Defaults to True.

        Returns
        -------
        dict[InteractiveHyperdrive, list[CreateCheckpoint]]
            Returns a dictionary keyed by the interactive hyperdrive object,
            with a value of a list of emitted `CreateCheckpoint` events called
            from advancing time.
        """
        # pylint: disable=too-many-locals
        if isinstance(time_delta, timedelta):
            time_delta = int(time_delta.total_seconds())
        else:
            time_delta = int(time_delta)  # convert int-like (e.g. np.int64) types to int

        out_dict: dict[LocalHyperdrive, list[CreateCheckpoint]] = {pool: [] for pool in self._deployed_hyperdrive_pools}

        # Don't checkpoint when advancing time if `create_checkpoints` is false
        # or there are no deployed pools
        if (not create_checkpoints) or (len(self._deployed_hyperdrive_pools) == 0):
            self._advance_chain_time(time_delta)
            for pool in self._deployed_hyperdrive_pools:
                pool._run_blocking_data_pipeline()  # pylint: disable=protected-access
        else:
            # For every pool, check the checkpoint duration and advance the chain for that amount of time,
            # followed by creating a checkpoint for that pool.
            # TODO support multiple pools with different checkpoint durations
            checkpoint_durations = [
                pool.interface.pool_config.checkpoint_duration for pool in self._deployed_hyperdrive_pools
            ]
            if not all(checkpoint_durations[0] == x for x in checkpoint_durations):
                raise NotImplementedError("All pools on this chain must have the same checkpoint duration")
            checkpoint_duration = checkpoint_durations[0]

            # Handle the first checkpoint, if it hasn't been created, make the checkpoint
            for pool in self._deployed_hyperdrive_pools:
                # Create checkpoint handles making a checkpoint at the right time
                checkpoint_event = pool._create_checkpoint(  # pylint: disable=protected-access
                    check_if_exists=True,
                    gas_limit=self.config.gas_limit,
                    retries=self.config.advance_time_create_checkpoint_retry_count,
                )
                if checkpoint_event is not None:
                    out_dict[pool].append(checkpoint_event)

            # Loop through each checkpoint duration epoch
            advance_iterations = int(time_delta / checkpoint_duration)
            last_advance_time = time_delta % checkpoint_duration
            offset = 0
            for _ in range(advance_iterations):
                # Advance the chain time by the checkpoint duration
                self._advance_chain_time(checkpoint_duration - offset)

                # Create checkpoints for each pool
                # Here, creating checkpoints mines the block, which itself may take time. Hence, we
                # calculate the offset and subtract it from the next advance time call.
                # However, if the amount of time advanced is an exact multiple of the checkpoint duration,
                # the last offset doesn't get applied, so this function can result in being off by however
                # long the checkpoint took to create (typically a second).
                time_before_checkpoints = self._web3.eth.get_block("latest").get("timestamp")
                assert time_before_checkpoints is not None
                for pool in self._deployed_hyperdrive_pools:
                    checkpoint_event = pool._create_checkpoint(
                        gas_limit=self.config.gas_limit,
                        retries=self.config.advance_time_create_checkpoint_retry_count,
                    )  # pylint: disable=protected-access
                    # These checkpoints should never fail
                    assert checkpoint_event is not None
                    # Add checkpoint event to the output
                    out_dict[pool].append(checkpoint_event)
                time_after_checkpoints = self._web3.eth.get_block("latest").get("timestamp")
                assert time_after_checkpoints is not None
                offset = time_after_checkpoints - time_before_checkpoints

            # Final advance time to advance the remainder
            # Best effort, if offset is larger than the remainder, don't advance time again.
            if last_advance_time - offset > 0:
                self._advance_chain_time(last_advance_time - offset)

            curr_block = self._web3.eth.get_block_number()
            for pool in self._deployed_hyperdrive_pools:
                pool._run_blocking_data_pipeline(curr_block)  # pylint: disable=protected-access

        return out_dict

    ##########
    # Saving and Loading
    ##########

    def save_state(self, save_dir: Path | None = None, save_prefix: str | None = None) -> Path:
        """Saves the interactive state using the `anvil_dumpState` RPC call.
        Saving/loading state can be done across chains.

        Arguments
        ---------
        save_dir: Path, optional
            The directory to save the state to. Defaults to `{Config.save_state_dir}/{save_prefix}_{current_time}/`,
            where `Config.save_state_dir` defaults to `./.interactive_state/`.
        save_prefix: str, optional
            If save_dir wasn't provided, prepends an optional prefix to the time suffix for this state.

        Returns
        -------
        str
            The path to the saved state.
        """
        if save_dir is None:
            curr_time = datetime.utcnow().replace(tzinfo=timezone.utc)
            fn_time_str = curr_time.strftime("%Y_%m_%d_%H_%M_%S_Z")
            if save_prefix is None:
                save_dir = Path(".interactive_state/") / fn_time_str
            else:
                save_dir = Path(".interactive_state/") / (save_prefix + "_" + fn_time_str)

        self._dump_db(save_dir)
        anvil_state_dump = get_anvil_state_dump(self._web3)
        assert anvil_state_dump is not None
        anvil_state_dump_file = save_dir / "anvil_state.dump"

        with open(anvil_state_dump_file, "w", encoding="utf-8") as f:
            f.write(anvil_state_dump)

        # TODO pickle all interactive objects and their underlying agents, see `load_state`

        return save_dir

    def load_state(self, load_dir: Path) -> None:
        """Loads the interactive state from the `save_state` function.
        Saving/loading state can be done across chains.

        .. note:: This feature is currently unavailable. There are issues around load_state, namely:

            - Anvil load state doesn't load the block number and timestamp.
            - Anvil load state only loads the current state, not all previous states.
            - There exists an issue with the underlying yield contract, as there is a `last_updated` var
              that gets saved, but anvil doesn't load the original timestamp, so the yield contract throws an error.
              (May be able to solve if we're able to solve issue 1 to correctly load the block number and
              previous states.)
            - To load the state in another chain, we need this function to load all original objects
              created from the saved chain, e.g., interactive_hyperdrive and all agents they contain, and return
              them from this function.

        Arguments
        ---------
        load_dir: Path
            The directory to load the state from.
        """
        raise NotImplementedError

    def save_snapshot(self) -> None:
        """Saves a snapshot using the `evm_snapshot` RPC call.
        The chain can store one snapshot at a time, saving another snapshot overwrites the previous snapshot.
        Saving/loading snapshot only persist on the same chain, not across chains.
        """
        self._anvil_save_snapshot()

        # Save the db state
        self._dump_db(self._snapshot_dir)

        # Save all states
        self._save_pool_bookkeeping(self._snapshot_dir)
        self._save_agent_bookkeeping(self._snapshot_dir)  # pylint: disable=protected-access
        self._save_policy_state(self._snapshot_dir)  # pylint: disable=protected-access

        self._has_saved_snapshot = True

    def load_snapshot(self) -> None:
        """Loads the previous snapshot using the `evm_revert` RPC call. Can load the snapshot multiple times.

        .. note::
            Saving/loading snapshot only persist on the same chain, not across chains.

        .. note::
            Loading a snapshot affects any agent's active pools and policies,
            and will revert both to the state of the saved snapshot.
        """
        # Loads the previous snapshot
        # When reverting snapshots, the chain deletes the previous snapshot, while we want it to persist.
        # Hence, in this function, we first revert the snapshot, then immediately create a new snapshot
        # to keep the original snapshot.

        if not self._has_saved_snapshot:
            raise ValueError("No saved snapshot to load")

        response = self._web3.provider.make_request(method=RPCEndpoint("evm_revert"), params=[self._saved_snapshot_id])
        if "result" not in response:
            raise KeyError("Response did not have a result.")

        # Load the bookkeeping of deployed pools
        # NOTE: existing pool objects initialized after snapshot will no longer be valid.
        self._load_pool_bookkeeping(self._snapshot_dir)
        # load snapshot database state
        self._load_db(self._snapshot_dir)
        # Update pool's agent bookkeeping
        # Note this will wipe the agent's active pool.
        self._load_agent_bookkeeping(self._snapshot_dir)

        # The hyperdrive interface in deployed pools need to wipe their cache
        for pool in self._deployed_hyperdrive_pools:
            pool._reinit_state_after_load_snapshot()  # pylint: disable=protected-access

        # This loads the agent's active policy
        # Note that this will set the active policy to the one before the snapshot.
        self._load_policy_state(self._snapshot_dir)

        # Save another anvil snapshot since reverting consumes the snapshot
        self._anvil_save_snapshot()

    # Save/Load helper functions
    def _anvil_save_snapshot(self) -> None:
        response = self._web3.provider.make_request(method=RPCEndpoint("evm_snapshot"), params=[])
        if "result" not in response:
            raise KeyError("Response did not have a result.")
        self._saved_snapshot_id = response["result"]

    def _add_deployed_pool_to_bookkeeping(self, pool: LocalHyperdrive):
        self._deployed_hyperdrive_pools.append(pool)

    def _dump_db(self, save_dir: Path):
        # TODO parameterize the save path
        os.makedirs(save_dir, exist_ok=True)
        export_db_to_file(save_dir, self.db_session)

    def _load_db(self, load_dir: Path):
        # TODO parameterize the load path
        import_to_db(self.db_session, load_dir, drop=True)

    def _save_pool_bookkeeping(self, save_dir: Path) -> None:
        # Save bookkeeping of deployed pools
        # We save the addresses of deployed pools for loading
        pool_filename = save_dir / "pools.pkl"
        pool_addr_list = [pool.hyperdrive_address for pool in self._deployed_hyperdrive_pools]
        with open(pool_filename, "wb") as file:
            dill.dump(pool_addr_list, file, dill.HIGHEST_PROTOCOL)

    def _load_pool_bookkeeping(self, load_dir: Path) -> None:
        pool_filename = load_dir / "pools.pkl"
        with open(pool_filename, "rb") as file:
            hyperdrive_pools: list[str] = dill.load(file)

        # Given the current list of deployed hyperdrive pools, we throw away any pools deployed
        # after the snapshot
        self._deployed_hyperdrive_pools = [
            p for p in self._deployed_hyperdrive_pools if p.hyperdrive_address in hyperdrive_pools
        ]

    def _save_agent_bookkeeping(self, save_dir: Path) -> None:
        policy_file = save_dir / "agents.pkl"

        agents = [agent.address for agent in self._chain_agents]
        with open(policy_file, "wb") as file:
            # We use dill, as pickle can't store local objects
            dill.dump(agents, file, protocol=dill.HIGHEST_PROTOCOL)
        for agent in self._chain_agents:
            active_pool_file = save_dir / (agent.address + "-active-pool.pkl")
            if agent._active_pool is not None:
                with open(active_pool_file, "wb") as file:
                    dill.dump(agent._active_pool.hyperdrive_address, file, protocol=dill.HIGHEST_PROTOCOL)

    def _load_agent_bookkeeping(self, load_dir: Path) -> None:
        policy_file = load_dir / "agents.pkl"
        with open(policy_file, "rb") as file:
            # We use dill, as pickle can't store local objects
            load_agents = dill.load(file)
        # Remove references of all agents added after snapshot
        # NOTE: existing agent objects initialized after snapshot will no longer be valid.
        self._chain_agents = [agent for agent in self._chain_agents if agent.address in load_agents]
        # Clear the _max_approval_pools to ensure we call approval
        # NOTE this might be a duplicate approval, which should be okay
        for agent in self._chain_agents:
            active_pool_file = load_dir / (agent.address + "-active-pool.pkl")
            # If the file doesn't exist, there was no active pool at time of snapshot
            if not os.path.isfile(active_pool_file):
                agent._active_pool = None
            else:
                with open(active_pool_file, "rb") as file:
                    # We use dill, as pickle can't store local objects
                    hyperdrive_address = dill.load(file)
                    # Find the pool in the list of deployed pools
                    target_pool = None
                    for pool in self._deployed_hyperdrive_pools:
                        if pool.hyperdrive_address == hyperdrive_address:
                            target_pool = pool
                            break
                    if target_pool is None:
                        raise ValueError("Saved active pool not found in list of deployed pools.")
                    agent._active_pool = target_pool

            agent._max_approval_pools = {}

    def _save_policy_state(self, save_dir: Path) -> None:
        for agent in self._chain_agents:
            policy_file = save_dir / (agent.address + ".pkl")
            with open(policy_file, "wb") as file:
                # We use dill, as pickle can't store local objects
                # This should also store None if there is no active policy
                dill.dump(agent._active_policy, file, protocol=dill.HIGHEST_PROTOCOL)

    def _load_policy_state(self, load_dir: Path) -> None:
        for agent in self._chain_agents:
            policy_file = load_dir / (agent.address + ".pkl")
            with open(policy_file, "rb") as file:
                # If we don't load rng, we get the current RNG state and set it after loading
                rng = None
                if not self.config.load_rng_on_snapshot and agent._active_policy is not None:
                    rng = agent._active_policy.rng
                # We use dill, as pickle can't store local objects
                agent._active_policy = dill.load(file)
                if not self.config.load_rng_on_snapshot and agent._active_policy is not None:
                    # For type checking
                    assert rng is not None
                    agent._active_policy.rng = rng

    ################
    # Agent functions
    ################

    def init_agent(
        self,
        private_key: str | None = None,
        public_address: str | None = None,
        pool: Hyperdrive | None = None,
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
        public_address: str | None, optional
            Must be None for local agents.
        pool: LocalHyperdrive, optional
            An optional pool to set as the active pool.
        policy: HyperdrivePolicy, optional
            An optional policy to set as the active policy.
        policy_config: HyperdrivePolicy, optional
            The configuration for the attached policy.
        name: str, optional
            The name of the agent. Defaults to the wallet address.
        base: FixedPoint | None, optional
            The amount of base to fund the agent with. Defaults to 0.
            If a private key is provided then the base amount is added to their previous balance.
        eth: FixedPoint | None, optional
            The amount of ETH to fund the agent with. Defaults to 0.
            If a private key is provided then the eth amount is added to their previous balance.

        Returns
        -------
        LocalHyperdriveAgent
            The agent object for a user to execute trades with.
        """
        # pylint: disable=too-many-arguments

        # Explicit type checking
        if pool is not None and not isinstance(pool, LocalHyperdrive):
            raise TypeError("Pool must be an instance of LocalHyperdrive for LocalChain")

        if public_address is not None:
            raise ValueError("Can't pass in public key for local agents.")

        if self._has_saved_snapshot:  # pylint: disable=protected-access
            logging.warning(
                "Adding new agent with existing snapshot. "
                "This object will no longer be valid if the snapshot is loaded."
            )
        if base is None:
            base = FixedPoint(0)
        if eth is None:
            eth = FixedPoint(0)

        policy_config = self._handle_policy_config(policy, policy_config)

        out_agent = LocalHyperdriveAgent(
            base=base,
            eth=eth,
            name=name,
            chain=self,
            pool=pool,
            policy=policy,
            policy_config=policy_config,
            private_key=private_key,
            public_address=None,
        )
        self._chain_agents.append(out_agent)
        return out_agent

    ##########
    # Analysis
    ##########

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
            A dashboard IFrame that can be shown in a Jupyter notebook with the `display` command.
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
        env = {key: str(val) for key, val in asdict(self.postgres_config).items()}
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

    def _get_dashboard_run_command(self, flags: list[str] | None = None) -> list[str]:
        """Returns the run command for launching a Streamlit dashboard.

        Arguments
        ---------
        flags: list[str] | None, optional
            List of streamlit flags to be added to the run command.
            Commands and arguments should be separate entries, for example: ["--server.headless", "true"]
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
        env = {key: str(val) for key, val in asdict(self.postgres_config).items()}

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
            self.dashboard_subprocess = None

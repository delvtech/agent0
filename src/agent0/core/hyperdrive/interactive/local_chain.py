"""The chain objects that encapsulates a chain."""

from __future__ import annotations

import contextlib
import os
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import dill
from eth_account.account import Account
from eth_account.signers.local import LocalAccount
from web3.types import RPCEndpoint

from agent0.chainsync.db.hyperdrive.import_export_data import export_db_to_file, import_to_db
from agent0.core.hyperdrive.crash_report import get_anvil_state_dump

from .chain import Chain
from .event_types import CreateCheckpoint

if TYPE_CHECKING:
    from .local_hyperdrive import LocalHyperdrive


# pylint: disable=too-many-instance-attributes
class LocalChain(Chain):
    """Launches a local anvil chain in a subprocess, along with a postgres container."""

    # Pylint is complaining that `load_state` is an abstract method, so we need to overwrite here.
    # However, `load_state` is just a function stub that needs to throw `NotImplementedError` if called.
    # pylint: disable=abstract-method

    @dataclass(kw_only=True)
    class Config(Chain.Config):
        """The configuration for the local chain object."""

        block_time: int | None = None
        """If None, mines per transaction. Otherwise mines every `block_time` seconds."""
        block_timestamp_interval: int | None = 12
        """Number of seconds to advance time for every mined block. Uses real time if None."""
        chain_port: int = 10_000
        """The port to bind for the anvil chain. Will fail if this port is being used."""
        transaction_block_keeper: int = 10_000
        """The number of blocks to keep transaction records for. Undocumented in Anvil, we're being optimistic here."""
        snapshot_dir: str = ".interactive_state/snapshot/"
        """The directory where the snapshot will be stored. Defaults to `.interactive_state/snapshot/`."""
        saved_state_dir: str = ".interactive_state/"
        """The directory where the saved state will be stored. Defaults to `.interactive_state/`."""

    def __init__(self, config: Config | None = None, fork_uri: str | None = None, fork_block_number: int | None = None):
        """Initialize the Chain class that connects to an existing chain.

        Also launch a postgres docker container for gathering data.

        Arguments
        ---------
        config: Config | None
            The local chain configuration.
        """
        if config is None:
            config = self.Config()

        anvil_launch_args = [
            "anvil",
            "--host",
            "127.0.0.1",
            "--port",
            str(config.chain_port),
            "--code-size-limit",
            "9999999999",
            "--transaction-block-keeper",
            str(config.transaction_block_keeper),
        ]
        if config.block_time is not None:
            anvil_launch_args.extend(("--block-time", str(config.block_time)))

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
        )

        # TODO HACK wait for anvil to start, ideally we would be looking for the output to stdout
        # Forking takes a bit longer to spin up, so we only sleep when forking
        if fork_uri is not None:
            time.sleep(2)

        super().__init__(f"http://127.0.0.1:{str(config.chain_port)}", config)

        # Snapshot bookkeeping
        # TODO snapshot dir will be clobbered if you run multiple chains simultaneously
        self._snapshot_dir = config.snapshot_dir
        self._saved_snapshot_id: str
        self._has_saved_snapshot = False
        self._deployed_hyperdrive_pools: list[LocalHyperdrive] = []

        # Ensure snapshot dir exists
        os.makedirs(self._snapshot_dir, exist_ok=True)

        if config.block_timestamp_interval is not None:
            self._set_block_timestamp_interval(config.block_timestamp_interval)

        # TODO hack, wait for chain to init
        time.sleep(1)

    def cleanup(self):
        """Kills the subprocess in this class' destructor."""
        # Runs cleanup on all deployed pools
        for pool in self._deployed_hyperdrive_pools:
            pool._cleanup()  # pylint: disable=protected-access
        self.anvil_process.kill()
        super().cleanup()

    def __del__(self):
        """Kill subprocess in this class' destructor."""
        with contextlib.suppress(Exception):
            self.cleanup()
        super().__del__()

    def get_deployer_account_private_key(self) -> str:
        """Get the private key of the deployer account.

        Returns
        -------
        str
            The private key for the deployer account.
        """
        # TODO this is the deployed account for anvil, get this programmatically
        return "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"

    def get_deployer_account_address(self) -> str:
        """Get the public key of the deployer account.

        Returns
        -------
        src
            The public key for the deployer account.
        """
        account: LocalAccount = Account().from_key(self.get_deployer_account_private_key())
        return account.address

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
                    checkpoint_event = pool._create_checkpoint()  # pylint: disable=protected-access
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

    def save_state(self, save_dir: str | None = None, save_prefix: str | None = None) -> str:
        """Saves the interactive state using the `anvil_dumpState` RPC call.
        Saving/loading state can be done across chains.

        Arguments
        ---------
        save_dir: str, optional
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
                save_dir = str(Path(".interactive_state/") / fn_time_str)
            else:
                save_dir = str(Path(".interactive_state/") / (save_prefix + "_" + fn_time_str))

        self._dump_db(save_dir)
        anvil_state_dump = get_anvil_state_dump(self._web3)
        assert anvil_state_dump is not None
        anvil_state_dump_file = Path(save_dir) / "anvil_state.dump"

        with open(anvil_state_dump_file, "w", encoding="utf-8") as f:
            f.write(anvil_state_dump)

        # TODO pickle all interactive objects and their underlying agents, see `load_state`

        return save_dir

    def load_state(self, load_dir: str) -> None:
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
        load_dir: str
            The directory to load the state from.
        """
        raise NotImplementedError

    def _anvil_save_snapshot(self) -> None:
        response = self._web3.provider.make_request(method=RPCEndpoint("evm_snapshot"), params=[])
        if "result" not in response:
            raise KeyError("Response did not have a result.")
        self._saved_snapshot_id = response["result"]

    def save_snapshot(self) -> None:
        """Saves a snapshot using the `evm_snapshot` RPC call.
        The chain can store one snapshot at a time, saving another snapshot overwrites the previous snapshot.
        Saving/loading snapshot only persist on the same chain, not across chains.
        """
        self._anvil_save_snapshot()

        # Save the db state
        self._dump_db(self._snapshot_dir)

        # Save bookkeeping of deployed pools
        # We save the addresses of deployed pools for loading
        pool_filename = self._snapshot_dir + "/" + self.chain_id + "-pools.pkl"
        pool_addr_list = [pool.get_hyperdrive_address() for pool in self._deployed_hyperdrive_pools]
        with open(pool_filename, "wb") as file:
            dill.dump(pool_addr_list, file, dill.HIGHEST_PROTOCOL)

        for pool in self._deployed_hyperdrive_pools:
            pool._save_agent_bookkeeping(self._snapshot_dir)  # pylint: disable=protected-access

        # Need to save all agent's policy states
        for pool in self._deployed_hyperdrive_pools:
            pool._save_policy_state(self._snapshot_dir)  # pylint: disable=protected-access

        self._has_saved_snapshot = True

    def load_snapshot(self) -> None:
        """Loads the previous snapshot using the `evm_revert` RPC call. Can load the snapshot multiple times.

        .. note::
            Saving/loading snapshot only persist on the same chain, not across chains.
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
        pool_filename = self._snapshot_dir + "/" + self.chain_id + "-pools.pkl"
        with open(pool_filename, "rb") as file:
            hyperdrive_pools: list[str] = dill.load(file)

        # Run cleanup on any invalid pools on load snapshot
        invalid_pools = [
            p for p in self._deployed_hyperdrive_pools if p.get_hyperdrive_address() not in hyperdrive_pools
        ]
        for pool in invalid_pools:
            pool._cleanup()  # pylint: disable=protected-access

        # Given the current list of deployed hyperdrive pools, we throw away any pools deployed
        # after the snapshot
        self._deployed_hyperdrive_pools = [
            p for p in self._deployed_hyperdrive_pools if p.get_hyperdrive_address() in hyperdrive_pools
        ]
        # NOTE: existing pool objects initialized after snapshot will no longer be valid.

        # load snapshot database state
        self._load_db(self._snapshot_dir)

        # Update pool's agent bookkeeping
        for pool in self._deployed_hyperdrive_pools:
            pool._load_agent_bookkeeping(self._snapshot_dir)  # pylint: disable=protected-access

        # The hyperdrive interface in deployed pools need to wipe it's cache
        for pool in self._deployed_hyperdrive_pools:
            pool._reinit_state_after_load_snapshot()  # pylint: disable=protected-access
            pool._load_policy_state(self._snapshot_dir)  # pylint: disable=protected-access

        # Save another anvil snapshot since reverting consumes the snapshot
        self._anvil_save_snapshot()

    def _add_deployed_pool_to_bookkeeping(self, pool: LocalHyperdrive):
        self._deployed_hyperdrive_pools.append(pool)

    def _dump_db(self, save_dir: str):
        # TODO parameterize the save path
        export_path = str(Path(save_dir))  # pylint: disable=protected-access
        os.makedirs(export_path, exist_ok=True)
        export_db_to_file(export_path, self.db_session)

    def _load_db(self, load_dir: str):
        # TODO parameterize the load path
        import_path = str(Path(load_dir))  # pylint: disable=protected-access
        import_to_db(self.db_session, import_path, drop=True)

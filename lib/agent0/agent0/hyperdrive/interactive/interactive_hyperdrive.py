"""Defines the interactive hyperdrive class that encapsulates a hyperdrive pool."""
from __future__ import annotations

import asyncio
import os
import time
from dataclasses import asdict, dataclass
from decimal import Decimal
from threading import Thread
from typing import Literal, Type, overload

import nest_asyncio
import pandas as pd
from chainsync import PostgresConfig
from chainsync.dashboard.usernames import build_user_mapping
from chainsync.db.base import add_addr_to_username, get_addr_to_username, get_username_to_user, initialize_session
from chainsync.db.hyperdrive import get_checkpoint_info
from chainsync.db.hyperdrive import get_current_wallet as chainsync_get_current_wallet
from chainsync.db.hyperdrive import (
    get_latest_block_number_from_analysis_table,
    get_pool_analysis,
    get_pool_config,
    get_pool_info,
    get_ticker,
    get_total_wallet_pnl_over_time,
    get_wallet_deltas,
    get_wallet_pnl,
)
from chainsync.exec import acquire_data, data_analysis
from eth_account.account import Account
from eth_typing import BlockNumber, ChecksumAddress
from eth_utils.address import to_checksum_address
from ethpy import EthConfig
from ethpy.base import set_anvil_account_balance, smart_contract_transact
from ethpy.hyperdrive import BASE_TOKEN_SYMBOL, DeployedHyperdrivePool, ReceiptBreakdown, deploy_hyperdrive_from_factory
from ethpy.hyperdrive.api import HyperdriveInterface
from fixedpointmath import FixedPoint
from hypertypes import Fees, PoolConfig
from web3._utils.threads import Timeout
from web3.constants import ADDRESS_ZERO
from web3.exceptions import TimeExhausted

from agent0.base.make_key import make_private_key
from agent0.hyperdrive.agents import HyperdriveAgent
from agent0.hyperdrive.crash_report import get_anvil_state_dump, log_hyperdrive_crash_report
from agent0.hyperdrive.exec import async_execute_agent_trades, build_wallet_positions_from_data, set_max_approval
from agent0.hyperdrive.policies import HyperdrivePolicy
from agent0.hyperdrive.state import HyperdriveActionType, TradeResult, TradeStatus
from agent0.test_utils import assert_never

from .chain import Chain
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
from .interactive_hyperdrive_agent import InteractiveHyperdriveAgent
from .interactive_hyperdrive_policy import InteractiveHyperdrivePolicy

# In order to support both scripts and jupyter notebooks with underlying async functions,
# we use the nest_asyncio package so that we can execute asyncio.run within a running event loop.
nest_asyncio.apply()


class InteractiveHyperdrive:
    """Hyperdrive class that supports an interactive interface for running tests and experiments."""

    # Lots of attributes in config
    # pylint: disable=too-many-instance-attributes
    @dataclass
    class Config:
        """The configuration for the initial pool configuration

        Attributes
        ----------
        initial_liquidity: FixedPoint
            The amount of money to be provided by the `deploy_account` for initial pool liquidity.
        initial_variable_rate: FixedPoint
            The starting variable rate for an underlying yield source.
        initial_fixed_rate: FixedPoint
            The fixed rate of the pool on initialization.
        initial_share_price: FixedPoint
            The initial share price
        minimum_share_reserves: FixedPoint
            The minimum share reserves
        minimum_transaction_amount: FixedPoint
            The minimum amount of tokens that a position can be opened or closed with.
        precision_threshold: int
            The amount of precision expected to lose due to exponentiation implementation.
        position_duration: int
            The duration of a position prior to maturity (in seconds)
        checkpoint_duration: int
            The duration of a checkpoint (in seconds)
        time_stretch: FixedPoint
            A parameter which decreases slippage around a target rate
        curve_fee: FixedPoint
            The LP fee applied to the curve portion of a trade.
        flat_fee: FixedPoint
            The LP fee applied to the flat portion of a trade.
        governance_fee: FixedPoint
            The portion of the LP fee that goes to governance.
        max_curve_fee: FixedPoint
            The upper bound on the curve fee that governance can set.
        max_flat_fee: FixedPoint
            The upper bound on the flat fee that governance can set.
        max_governance_fee: FixedPoint
            The upper bound on the governance fee that governance can set.
        preview_before_trade: bool, optional
            Whether to preview the position before executing a trade. Defaults to False.
        """

        # Environment variables
        data_pipeline_timeout: int = 60
        # Initial pool variables
        initial_liquidity: FixedPoint = FixedPoint(100_000_000)
        initial_variable_rate: FixedPoint = FixedPoint("0.05")
        initial_fixed_rate: FixedPoint = FixedPoint("0.05")
        # Initial Pool Config variables
        initial_share_price: FixedPoint = FixedPoint(1)
        minimum_share_reserves: FixedPoint = FixedPoint(10)
        minimum_transaction_amount: FixedPoint = FixedPoint("0.001")
        # TODO this likely should be FixedPoint
        precision_threshold: int = int(1e14)
        position_duration: int = 604800  # 1 week
        checkpoint_duration: int = 3600  # 1 hour
        time_stretch: FixedPoint | None = None
        curve_fee = FixedPoint("0.1")  # 10%
        flat_fee = FixedPoint("0.0005")  # 0.05%
        governance_fee = FixedPoint("0.15")  # 15%
        max_curve_fee = FixedPoint("0.3")  # 30%
        max_flat_fee = FixedPoint("0.0015")  # 0.15%
        max_governance_fee = FixedPoint("0.30")  # 30%
        preview_before_trade: bool = False

        def __post_init__(self):
            if self.time_stretch is None:
                self.time_stretch = FixedPoint(1) / (
                    FixedPoint("5.24592") / (FixedPoint("0.04665") * (self.initial_fixed_rate * FixedPoint(100)))
                )

    def __init__(self, chain: Chain, config: Config | None = None):
        """Constructor for the interactive hyperdrive agent.

        Arguments
        ---------
        chain: Chain
            The chain object to launch hyperdrive on
        config: Config | None
            The configuration for the initial pool configuration
        """
        if config is None:
            config = self.Config()

        # Define agent0 configs with this setup
        # TODO currently getting the path based on this file's path
        # This requires the entire monorepo to be check out, and will likely not work when
        # installing agent0 by itself.
        # This should get fixed when abis are exported in hypertypes.
        full_path = os.path.realpath(__file__)
        current_file_dir, _ = os.path.split(full_path)
        abi_dir = os.path.join(current_file_dir, "..", "..", "..", "..", "..", "packages", "hyperdrive", "src", "abis")

        self.eth_config = EthConfig(
            artifacts_uri="not_used",
            rpc_uri=chain.rpc_uri,
            abi_dir=abi_dir,
            preview_before_trade=config.preview_before_trade,
        )
        # Deploys a hyperdrive factory + pool on the chain
        self._deployed_hyperdrive = self._deploy_hyperdrive(config, chain, self.eth_config.abi_dir)
        self.hyperdrive_interface = HyperdriveInterface(
            self.eth_config,
            self._deployed_hyperdrive.hyperdrive_contract_addresses,
            web3=chain._web3,
        )
        # At this point, we've deployed hyperdrive, so we want to save the block where it was deployed
        # for the data pipeline
        self._deploy_block_number = self.hyperdrive_interface.get_block_number(
            self.hyperdrive_interface.get_current_block()
        )

        # Make a copy of the dataclass to avoid changing the base class
        self.postgres_config = PostgresConfig(**asdict(chain.postgres_config))
        # Update the database field to use a unique name for this pool using the hyperdrive contract address
        self.postgres_config.POSTGRES_DB = "interactive-hyperdrive-" + str(
            self.hyperdrive_interface.hyperdrive_contract.address
        )

        # Store the db_id here for later reference
        self._db_name = self.postgres_config.POSTGRES_DB

        self.db_session = initialize_session(self.postgres_config, ensure_database_created=True)

        # Keep track of how much base have been minted per agent
        self._initial_funds: dict[ChecksumAddress, FixedPoint] = {}

        # Add this pool to the chain bookkeeping for snapshots
        chain._add_deployed_pool_to_bookkeeping(self)
        self.chain = chain
        self._pool_agents: list[InteractiveHyperdriveAgent] = []

        # We use this variable to control underlying threads when to exit.
        # When this varible is set to true, the underlying threads will exit.
        self._stop_threads = False
        self._data_thread: Thread | None = None
        self._analysis_thread: Thread | None = None

        # Run the data pipeline in background threads

        self._launch_data_pipeline()
        self.data_pipeline_timeout = config.data_pipeline_timeout

        # Pool config should exist before returning
        for _ in range(10):
            try:
                self.get_pool_config()
                break
            except ValueError:
                time.sleep(1)

    def _launch_data_pipeline(self):
        # Run the data pipeline in background threads
        # Ensure the stop flag is set to false
        # This ensures no other threads are running when launching data pipeline
        if self._data_thread is not None or self._analysis_thread is not None:
            raise ValueError("Data pipeline already running")

        self._stop_threads = False
        # We need to create new threads every launch, since start can be called at most once per thread object
        self._data_thread = Thread(
            target=acquire_data,
            kwargs={
                "start_block": self._deploy_block_number,  # Start block is the block hyperdrive was deployed
                "eth_config": self.eth_config,
                "postgres_config": self.postgres_config,
                "contract_addresses": self.hyperdrive_interface.addresses,
                "exit_on_catch_up": False,
                "exit_callback_fn": lambda: self._stop_threads,
            },
        )
        self._analysis_thread = Thread(
            target=data_analysis,
            kwargs={
                "start_block": self._deploy_block_number,
                "eth_config": self.eth_config,
                "postgres_config": self.postgres_config,
                "contract_addresses": self.hyperdrive_interface.addresses,
                "exit_on_catch_up": False,
                "exit_callback_fn": lambda: self._stop_threads,
            },
        )
        self._data_thread.start()
        self._analysis_thread.start()

    def _stop_data_pipeline(self):
        if self._data_thread is None or self._analysis_thread is None:
            raise ValueError("Data pipeline not running")

        # This lets the underlying threads know to stop at the next opportunity
        self._stop_threads = True
        # These wait for the threads to finally stop
        self._data_thread.join()
        self._analysis_thread.join()
        # Dereference thread variables
        self._data_thread = None
        self._analysis_thread = None

    def cleanup(self):
        """Cleans up resources used by this object."""
        self._stop_data_pipeline()
        self.db_session.close_all()

    def __del__(self):
        # Attempt to close the session
        # These functions will raise errors if the session is already closed
        try:
            self.cleanup()
        # Never throw exception in destructor
        except Exception:  # pylint: disable=broad-except
            pass

    # We overwrite these dunder methods to allow this object to be used as a dictionary key
    def __hash__(self):
        """We use a combination of the chain's rpc uri and the hyperdrive contract address as the hash."""
        return hash((self.chain.rpc_uri, self._deployed_hyperdrive.hyperdrive_contract.address))

    def __eq__(self, other):
        return (self.chain.rpc_uri, self._deployed_hyperdrive.hyperdrive_contract.address) == (
            other.chain.rpc_uri,
            other._deployed_hyperdrive.hyperdrive_contract.address,
        )

    def _deploy_hyperdrive(self, config: Config, chain: Chain, abi_dir) -> DeployedHyperdrivePool:
        # sanity check (also for type checking), should get set in __post_init__
        assert config.time_stretch is not None

        initial_pool_config = PoolConfig(
            "",  # will be determined in the deploy function
            ADDRESS_ZERO,  # address(0), this address needs to be in a valid address format
            bytes(32),  # bytes32(0)
            config.initial_share_price.scaled_value,
            config.minimum_share_reserves.scaled_value,
            config.minimum_transaction_amount.scaled_value,
            config.precision_threshold,
            config.position_duration,
            config.checkpoint_duration,
            config.time_stretch.scaled_value,
            "",  # will be determined in the deploy function
            "",  # will be determined in the deploy function
            Fees(config.curve_fee.scaled_value, config.flat_fee.scaled_value, config.governance_fee.scaled_value),
        )

        max_fees = Fees(
            config.max_curve_fee.scaled_value, config.max_flat_fee.scaled_value, config.max_governance_fee.scaled_value
        )

        return deploy_hyperdrive_from_factory(
            chain.rpc_uri,
            abi_dir,
            chain.get_deployer_account_private_key(),
            config.initial_liquidity,
            config.initial_variable_rate,
            config.initial_fixed_rate,
            initial_pool_config,
            max_fees,
        )

    def set_variable_rate(self, variable_rate: FixedPoint) -> None:
        """Sets the underlying variable rate for this pool.

        Arguments
        ---------
        variable_rate: FixedPoint
            The new variable rate for the pool.
        """
        self.hyperdrive_interface.set_variable_rate(self._deployed_hyperdrive.deploy_account, variable_rate)

    def _create_checkpoint(
        self, checkpoint_time: int | None = None, check_if_exists: bool = True
    ) -> CreateCheckpoint | None:
        """Internal function without safeguard checks for creating a checkpoint.
        Creating checkpoints is called by the chain's `advance_time`.
        """

        if checkpoint_time is None:
            block_timestamp = self.hyperdrive_interface.get_block_timestamp(
                self.hyperdrive_interface.get_current_block()
            )
            checkpoint_time = self.hyperdrive_interface.calc_checkpoint_id(
                self.hyperdrive_interface.pool_config.checkpoint_duration, block_timestamp
            )

        if check_if_exists:
            checkpoint = self.hyperdrive_interface.hyperdrive_contract.functions.getCheckpoint(checkpoint_time).call()
            # If it exists, don't create a checkpoint and return None.
            if checkpoint.sharePrice > 0:
                return None

        try:
            tx_receipt = self.hyperdrive_interface.create_checkpoint(
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
            share_price=tx_receipt.share_price,
            matured_shorts=tx_receipt.matured_shorts,
            matured_longs=tx_receipt.matured_longs,
            lp_share_price=tx_receipt.lp_share_price,
        )

    def init_agent(
        self,
        base: FixedPoint | None = None,
        eth: FixedPoint | None = None,
        name: str | None = None,
        policy: Type[HyperdrivePolicy] | None = None,
        policy_config: HyperdrivePolicy.Config | None = None,
    ) -> InteractiveHyperdriveAgent:
        """Initializes an agent with initial funding and a logical name.

        Arguments
        ---------
        base: FixedPoint, optional
            The amount of base to fund the agent with. Defaults to 0.
        eth: FixedPoint, optional
            The amount of ETH to fund the agent with. Defaults to 10.
        name: str, optional
            The name of the agent. Defaults to the wallet address.
        policy: HyperdrivePolicy, optional
            An optional policy to attach to this agent.
        policy_config: HyperdrivePolicy, optional
            The configuration for the attached policy.

        Returns
        -------
        InteractiveHyperdriveAgent
            An object that contains the HyperdriveInterface, Agents,
            and provides access to the interactive Hyperdrive API.
        """
        # pylint: disable=too-many-arguments
        if self.chain._has_saved_snapshot:  # pylint: disable=protected-access
            raise ValueError("Cannot add a new agent after saving a snapshot")
        if base is None:
            base = FixedPoint(0)
        if eth is None:
            eth = FixedPoint(10)
        out_agent = InteractiveHyperdriveAgent(
            base=base, eth=eth, name=name, pool=self, policy=policy, policy_config=policy_config
        )
        self._pool_agents.append(out_agent)
        return out_agent

    ### Database methods
    # These methods expose the underlying chainsync getter methods with minimal processing
    # TODO expand in docstrings the columns of the output dataframe

    def get_pool_config(self, coerce_float: bool = True) -> pd.Series:
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
        pool_config = get_pool_config(self.db_session, coerce_float=coerce_float)
        if len(pool_config) == 0:
            raise ValueError("Pool config doesn't exist in the db.")
        return pool_config.iloc[0]

    def get_pool_state(self, coerce_float: bool = True) -> pd.DataFrame:
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
        # DB read calls ensures data pipeline is caught up before returning
        self._ensure_data_caught_up()

        pool_info = get_pool_info(self.db_session, coerce_float=coerce_float)
        pool_analysis = get_pool_analysis(self.db_session, coerce_float=coerce_float, return_timestamp=False)
        pool_info = pool_info.merge(pool_analysis, how="left", on="block_number")
        return pool_info

    def get_checkpoint_info(self, coerce_float: bool = True) -> pd.DataFrame:
        """Get the previous checkpoint infos per block and returns as a pandas dataframe.

        Arguments
        ---------
        coerce_float: bool
            If True, will coerce underlying Decimals to floats.

        Returns
        -------
        pd.Dataframe
            A pandas dataframe that consists of the checkpoint info per block.
        """
        # DB read calls ensures data pipeline is caught up before returning
        self._ensure_data_caught_up()
        out = get_checkpoint_info(self.db_session, coerce_float=coerce_float)
        return out

    def _add_username_to_dataframe(self, df: pd.DataFrame, addr_column: str):
        addr_to_username = get_addr_to_username(self.db_session)
        username_to_user = get_username_to_user(self.db_session)

        # Get corresponding usernames
        usernames = build_user_mapping(df[addr_column], addr_to_username, username_to_user)["username"]
        df.insert(df.columns.get_loc(addr_column), "username", usernames)
        return df

    def _adjust_base_positions(self, in_df: pd.DataFrame, value_column: str, coerce_float: bool):
        out_df = in_df.copy()
        for address, initial_balance in self._initial_funds.items():
            row_idxs = (out_df["wallet_address"] == address) & (out_df["base_token_type"] == BASE_TOKEN_SYMBOL)
            if coerce_float:
                out_df.loc[row_idxs, value_column] += float(initial_balance)
            else:
                out_df.loc[row_idxs, value_column] += Decimal(str(initial_balance))
        return out_df

    def get_current_wallet(self, coerce_float: bool = True) -> pd.DataFrame:
        """Gets the current wallet positions of all agents and their corresponding pnl
        and returns as a pandas dataframe.

        Arguments
        ---------
        coerce_float: bool
            If True, will coerce underlying Decimals to floats.

        Returns
        -------
        pd.Dataframe
            timestamp: pd.Timestamp
                The block timestamp of the entry.
            block_number: int
                The block number of the entry.
            username: str
                The username of the entry.
            wallet_address: str
                The wallet address of the entry.
            token_type: str
                A string specifying the token type. Longs and shorts are encoded as `LONG-{maturity_time}`.
            position: Decimal | float
                The current value of the token of the agent at the specified block number.
            pnl: Decimal | float
                The current pnl of the token of the agent at the specified block number.
            base_token_type: str
                A string specifying the type of the token.
            maturity_time: Decimal | float
                The maturity time of the token in epoch seconds. Can be NaN to denote not applicable.
            latest_block_update: int
                The last block number that the position was updated.
        """
        # DB read calls ensures data pipeline is caught up before returning
        self._ensure_data_caught_up()
        # TODO potential improvement is to pivot the table so that columns are the token type
        # Makes this data easier to work with
        # https://github.com/delvtech/agent0/issues/1106
        out = get_wallet_pnl(self.db_session, start_block=-1, coerce_float=coerce_float)
        # DB only stores final delta for base, we calculate actual base based on how much funds
        # were added in all
        out = self._adjust_base_positions(out, "value", coerce_float)
        # Rename column to match get_wallet_positions
        out = out.rename(columns={"value": "position"})
        # Add usernames
        out = self._add_username_to_dataframe(out, "wallet_address")
        # Filter and order columns
        out = out[
            [
                "timestamp",
                "block_number",
                "username",
                "wallet_address",
                "token_type",
                "position",
                "pnl",
                "base_token_type",
                "maturity_time",
                "latest_block_update",
            ]
        ]
        return out

    def get_ticker(self, coerce_float: bool = True) -> pd.DataFrame:
        """Gets the ticker history of all trades and the corresponding token deltas for each trade.

        Arguments
        ---------
        coerce_float: bool
            If True, will coerce underlying Decimals to floats.

        Returns
        -------
        pd.Dataframe
            timestamp: pd.Timestamp
                The block timestamp of the entry.
            block_number: int
                The block number of the entry.
            username: str
                The username of the entry.
            wallet_address: str
                The wallet address of the entry.
            trade_type: str
                The trade that the agent made.
            token_diffs: list[str]
                A list of token diffs for each trade. Each token diff is encoded as "<base_token_type>: <amount>"
        """
        # DB read calls ensures data pipeline is caught up before returning
        self._ensure_data_caught_up()
        out = get_ticker(self.db_session, coerce_float=coerce_float).drop("id", axis=1)
        out = self._add_username_to_dataframe(out, "wallet_address")
        out = out[
            [
                "timestamp",
                "block_number",
                "username",
                "wallet_address",
                "trade_type",
                "token_diffs",
            ]
        ]
        return out

    def get_wallet_positions(self, coerce_float: bool = True) -> pd.DataFrame:
        """Get a dataframe summarizing all wallet deltas and positions
        and returns as a pandas dataframe.

        Arguments
        ---------
        coerce_float: bool
            If True, will coerce underlying Decimals to floats.

        Returns
        -------
        pd.Dataframe
            timestamp: pd.Timestamp
                The block timestamp of the entry.
            block_number: int
                The block number of the entry.
            username: str
                The username of the entry.
            wallet_address: str
                The wallet address of the entry.
            token_type: str
                A string specifying the token type. Longs and shorts are encoded as `LONG-{maturity_time}`.
            position: Decimal | float
                The current value of the token of the agent at the specified block number.
            delta: Decimal | float
                The change in value of the token of the agent at the specified block number.
            base_token_type: str
                A string specifying the type of the token.
            maturity_time: Decimal | float
                The maturity time of the token in epoch seconds. Can be NaN to denote not applicable.
            transaction_hash: str
                The transaction hash that resulted in the deltas.
        """
        # DB read calls ensures data pipeline is caught up before returning
        self._ensure_data_caught_up()
        # We gather all deltas and calculate the current positions here
        # If computing this is too slow, we can get current positions from
        # the wallet_pnl table and left merge with the deltas
        out = get_wallet_deltas(self.db_session, coerce_float=coerce_float)
        out["position"] = out.groupby(["wallet_address", "token_type"])["delta"].transform(pd.Series.cumsum)

        # DB only stores final delta for base, we calculate actual base based on how much funds
        # were added in all
        out = self._adjust_base_positions(out, "position", coerce_float)
        # Add usernames
        out = self._add_username_to_dataframe(out, "wallet_address")
        # Filter and order columns
        out = out[
            [
                "timestamp",
                "block_number",
                "username",
                "wallet_address",
                "token_type",
                "position",
                "delta",
                "base_token_type",
                "maturity_time",
                "transaction_hash",
            ]
        ]
        return out

    def get_total_wallet_pnl_over_time(self, coerce_float: bool = True) -> pd.DataFrame:
        """Gets total pnl for each wallet for each block, aggregated across all open positions.

        Arguments
        ---------
        coerce_float: bool
            If True, will coerce underlying Decimals to floats.

        Returns
        -------
        pd.Dataframe
            timestamp: pd.Timestamp
                The block timestamp of the entry.
            block_number: int
                The block number of the entry.
            username: str
                The username of the entry.
            wallet_address: str
                The wallet address of the entry.
            pnl: Decimal | float
                The total pnl of the agent at the specified block number.
        """
        # DB read calls ensures data pipeline is caught up before returning
        self._ensure_data_caught_up()
        out = get_total_wallet_pnl_over_time(self.db_session, coerce_float=coerce_float)
        out = self._add_username_to_dataframe(out, "wallet_address")
        out = out[
            [
                "timestamp",
                "block_number",
                "username",
                "wallet_address",
                "pnl",
            ]
        ]
        return out

    ### Private agent methods ###

    def _init_agent(
        self,
        base: FixedPoint,
        eth: FixedPoint,
        name: str | None,
        policy: Type[HyperdrivePolicy] | None,
        policy_config: HyperdrivePolicy.Config | None,
    ) -> HyperdriveAgent:
        # pylint: disable=too-many-arguments
        agent_private_key = make_private_key()
        # Setting the budget to 0 here, `_add_funds` will take care of updating the wallet
        agent = HyperdriveAgent(
            Account().from_key(agent_private_key),
            initial_budget=FixedPoint(0),
            policy=InteractiveHyperdrivePolicy(
                InteractiveHyperdrivePolicy.Config(sub_policy=policy, sub_policy_config=policy_config)
            ),
        )

        # Fund agent
        if eth > 0 or base > 0:
            self._add_funds(agent, base, eth)

        # establish max approval for the hyperdrive contract
        asyncio.run(
            set_max_approval(
                [agent],
                self.hyperdrive_interface.web3,
                self.hyperdrive_interface.base_token_contract,
                str(self.hyperdrive_interface.hyperdrive_contract.address),
            )
        )

        # Register the username if it was provided
        if name is not None:
            add_addr_to_username(name, [agent.address], self.db_session)
        return agent

    def _add_funds(self, agent: HyperdriveAgent, base: FixedPoint, eth: FixedPoint) -> None:
        # TODO this can be fixed by getting actual base values from the chain.
        if self.chain._has_saved_snapshot:  # pylint: disable=protected-access
            raise ValueError("Cannot add funds to an agent after saving a snapshot")

        if eth > FixedPoint(0):
            # Eth is a set balance call
            eth_balance, _ = self.hyperdrive_interface.get_eth_base_balances(agent)
            new_eth_balance = eth_balance + eth
            _ = set_anvil_account_balance(self.hyperdrive_interface.web3, agent.address, new_eth_balance.scaled_value)

        if base > FixedPoint(0):
            # We mint base
            _ = smart_contract_transact(
                self.hyperdrive_interface.web3,
                self.hyperdrive_interface.base_token_contract,
                self._deployed_hyperdrive.deploy_account,
                "mint(address,uint256)",
                agent.checksum_address,
                base.scaled_value,
            )
            # Update the agent's wallet balance
            agent.wallet.balance.amount += base

            # Keep track of how much base has been minted for each agent
            if agent.address in self._initial_funds:
                self._initial_funds[agent.address] += base
            else:
                self._initial_funds[agent.address] = base

        # TODO do we want to report a status here?

    def _handle_trade_result(self, trade_results: list[TradeResult] | TradeResult) -> ReceiptBreakdown:
        # Sanity check, should only be one trade result
        if isinstance(trade_results, list):
            assert len(trade_results) == 1
            trade_result = trade_results[0]
        elif isinstance(trade_results, TradeResult):
            trade_result = trade_results
        else:
            assert False

        if trade_result.status == TradeStatus.FAIL:
            assert trade_result.exception is not None
            # TODO when we allow for async, we likely would want to ignore slippage checks here
            # We only get anvil state dump here, since it's an on chain call
            # and we don't want to do it when e.g., slippage happens
            trade_result.anvil_state = get_anvil_state_dump(self.hyperdrive_interface.web3)
            # Defaults to CRITICAL
            log_hyperdrive_crash_report(trade_result, crash_report_to_file=True)
            raise trade_result.exception

        assert trade_result.status == TradeStatus.SUCCESS
        tx_receipt = trade_result.tx_receipt
        assert tx_receipt is not None
        return tx_receipt

    def _ensure_data_caught_up(self, polling_interval: int = 1) -> None:
        latest_mined_block: BlockNumber | None = None
        analysis_latest_block_number: int | None = None

        try:
            with Timeout(self.data_pipeline_timeout) as _timeout:
                while True:
                    latest_mined_block = self.hyperdrive_interface.web3.eth.get_block_number()
                    analysis_latest_block_number = get_latest_block_number_from_analysis_table(self.db_session)
                    if latest_mined_block > analysis_latest_block_number:
                        _timeout.sleep(polling_interval)
                    else:
                        break
        except Timeout as exc:
            raise TimeExhausted(
                f"Data pipeline didn't catch up after {self.data_pipeline_timeout} seconds",
                f"{latest_mined_block=}, {analysis_latest_block_number=}",
            ) from exc

    def _open_long(self, agent: HyperdriveAgent, base: FixedPoint) -> OpenLong:
        # Set the next action to open a long
        assert isinstance(agent.policy, InteractiveHyperdrivePolicy)
        agent.policy.set_next_action(HyperdriveActionType.OPEN_LONG, base)
        # TODO expose async here to the caller eventually
        trade_results: list[TradeResult] = asyncio.run(
            async_execute_agent_trades(self.hyperdrive_interface, [agent], False)
        )
        tx_receipt = self._handle_trade_result(trade_results)
        return self._build_event_obj_from_tx_receipt(HyperdriveActionType.OPEN_LONG, tx_receipt)

    def _close_long(self, agent: HyperdriveAgent, maturity_time: int, bonds: FixedPoint) -> CloseLong:
        # Set the next action to open a long
        assert isinstance(agent.policy, InteractiveHyperdrivePolicy)
        agent.policy.set_next_action(HyperdriveActionType.CLOSE_LONG, bonds, maturity_time)
        # TODO expose async here to the caller eventually
        trade_results: list[TradeResult] = asyncio.run(
            async_execute_agent_trades(self.hyperdrive_interface, [agent], False)
        )
        tx_receipt = self._handle_trade_result(trade_results)
        return self._build_event_obj_from_tx_receipt(HyperdriveActionType.CLOSE_LONG, tx_receipt)

    def _open_short(self, agent: HyperdriveAgent, bonds: FixedPoint) -> OpenShort:
        # Set the next action to open a long
        assert isinstance(agent.policy, InteractiveHyperdrivePolicy)
        agent.policy.set_next_action(HyperdriveActionType.OPEN_SHORT, bonds)
        # TODO expose async here to the caller eventually
        trade_results: list[TradeResult] = asyncio.run(
            async_execute_agent_trades(self.hyperdrive_interface, [agent], False)
        )
        tx_receipt = self._handle_trade_result(trade_results)
        return self._build_event_obj_from_tx_receipt(HyperdriveActionType.OPEN_SHORT, tx_receipt)

    def _close_short(self, agent: HyperdriveAgent, maturity_time: int, bonds: FixedPoint) -> CloseShort:
        # Set the next action to open a long
        assert isinstance(agent.policy, InteractiveHyperdrivePolicy)
        agent.policy.set_next_action(HyperdriveActionType.CLOSE_SHORT, bonds, maturity_time=maturity_time)
        # TODO expose async here to the caller eventually
        trade_results: list[TradeResult] = asyncio.run(
            async_execute_agent_trades(self.hyperdrive_interface, [agent], False)
        )
        tx_receipt = self._handle_trade_result(trade_results)
        return self._build_event_obj_from_tx_receipt(HyperdriveActionType.CLOSE_SHORT, tx_receipt)

    def _add_liquidity(self, agent: HyperdriveAgent, base: FixedPoint) -> AddLiquidity:
        # Set the next action to open a long
        assert isinstance(agent.policy, InteractiveHyperdrivePolicy)
        agent.policy.set_next_action(HyperdriveActionType.ADD_LIQUIDITY, base)
        # TODO expose async here to the caller eventually
        trade_results: list[TradeResult] = asyncio.run(
            async_execute_agent_trades(self.hyperdrive_interface, [agent], False)
        )
        tx_receipt = self._handle_trade_result(trade_results)
        return self._build_event_obj_from_tx_receipt(HyperdriveActionType.ADD_LIQUIDITY, tx_receipt)

    def _remove_liquidity(self, agent: HyperdriveAgent, shares: FixedPoint) -> RemoveLiquidity:
        # Set the next action to open a long
        assert isinstance(agent.policy, InteractiveHyperdrivePolicy)
        agent.policy.set_next_action(HyperdriveActionType.REMOVE_LIQUIDITY, shares)
        # TODO expose async here to the caller eventually
        trade_results: list[TradeResult] = asyncio.run(
            async_execute_agent_trades(self.hyperdrive_interface, [agent], False)
        )
        tx_receipt = self._handle_trade_result(trade_results)
        return self._build_event_obj_from_tx_receipt(HyperdriveActionType.REMOVE_LIQUIDITY, tx_receipt)

    def _redeem_withdraw_share(self, agent: HyperdriveAgent, shares: FixedPoint) -> RedeemWithdrawalShares:
        # Set the next action to open a long
        assert isinstance(agent.policy, InteractiveHyperdrivePolicy)
        agent.policy.set_next_action(HyperdriveActionType.REDEEM_WITHDRAW_SHARE, shares)
        # TODO expose async here to the caller eventually
        trade_results: list[TradeResult] = asyncio.run(
            async_execute_agent_trades(self.hyperdrive_interface, [agent], False)
        )
        tx_receipt = self._handle_trade_result(trade_results)
        return self._build_event_obj_from_tx_receipt(HyperdriveActionType.REDEEM_WITHDRAW_SHARE, tx_receipt)

    def _execute_policy_action(
        self, agent: HyperdriveAgent
    ) -> list[OpenLong | OpenShort | CloseLong | CloseShort | AddLiquidity | RemoveLiquidity | RedeemWithdrawalShares]:
        assert isinstance(agent.policy, InteractiveHyperdrivePolicy)
        # Only allow executing agent policies if a policy was passed in the constructor
        if agent.policy.sub_policy is None:
            raise ValueError("Must pass in a policy in the constructor to execute policy action.")

        agent.policy.set_next_action_from_sub_policy()
        trade_results: list[TradeResult] = asyncio.run(
            async_execute_agent_trades(self.hyperdrive_interface, [agent], False)
        )
        out_events = []
        # The underlying policy can execute multiple actions in one step
        for trade_result in trade_results:
            tx_receipt = self._handle_trade_result(trade_results)
            assert trade_result.trade_object is not None
            action_type: HyperdriveActionType = trade_result.trade_object.market_action.action_type
            out_events.append(self._build_event_obj_from_tx_receipt(action_type, tx_receipt))
        # Build event from tx_receipt
        return out_events

    @overload
    def _build_event_obj_from_tx_receipt(
        self, trade_type: Literal[HyperdriveActionType.INITIALIZE_MARKET], tx_receipt: ReceiptBreakdown
    ) -> None:
        ...

    @overload
    def _build_event_obj_from_tx_receipt(
        self, trade_type: Literal[HyperdriveActionType.OPEN_LONG], tx_receipt: ReceiptBreakdown
    ) -> OpenLong:
        ...

    @overload
    def _build_event_obj_from_tx_receipt(
        self, trade_type: Literal[HyperdriveActionType.CLOSE_LONG], tx_receipt: ReceiptBreakdown
    ) -> CloseLong:
        ...

    @overload
    def _build_event_obj_from_tx_receipt(
        self, trade_type: Literal[HyperdriveActionType.OPEN_SHORT], tx_receipt: ReceiptBreakdown
    ) -> OpenShort:
        ...

    @overload
    def _build_event_obj_from_tx_receipt(
        self, trade_type: Literal[HyperdriveActionType.CLOSE_SHORT], tx_receipt: ReceiptBreakdown
    ) -> CloseShort:
        ...

    @overload
    def _build_event_obj_from_tx_receipt(
        self, trade_type: Literal[HyperdriveActionType.ADD_LIQUIDITY], tx_receipt: ReceiptBreakdown
    ) -> AddLiquidity:
        ...

    @overload
    def _build_event_obj_from_tx_receipt(
        self, trade_type: Literal[HyperdriveActionType.REMOVE_LIQUIDITY], tx_receipt: ReceiptBreakdown
    ) -> RemoveLiquidity:
        ...

    @overload
    def _build_event_obj_from_tx_receipt(
        self, trade_type: Literal[HyperdriveActionType.REDEEM_WITHDRAW_SHARE], tx_receipt: ReceiptBreakdown
    ) -> RedeemWithdrawalShares:
        ...

    @overload
    def _build_event_obj_from_tx_receipt(
        self, trade_type: HyperdriveActionType, tx_receipt: ReceiptBreakdown
    ) -> OpenLong | OpenShort | CloseLong | CloseShort | AddLiquidity | RemoveLiquidity | RedeemWithdrawalShares | None:
        ...

    def _build_event_obj_from_tx_receipt(
        self, trade_type: HyperdriveActionType, tx_receipt: ReceiptBreakdown
    ) -> OpenLong | OpenShort | CloseLong | CloseShort | AddLiquidity | RemoveLiquidity | RedeemWithdrawalShares | None:
        # pylint: disable=too-many-return-statements
        match trade_type:
            case HyperdriveActionType.INITIALIZE_MARKET:
                raise ValueError(f"{trade_type} not supported!")

            case HyperdriveActionType.OPEN_LONG:
                return OpenLong(
                    trader=to_checksum_address(tx_receipt.trader),
                    asset_id=tx_receipt.asset_id,
                    maturity_time=tx_receipt.maturity_time_seconds,
                    base_amount=tx_receipt.base_amount,
                    share_price=tx_receipt.share_price,
                    bond_amount=tx_receipt.bond_amount,
                )

            case HyperdriveActionType.CLOSE_LONG:
                return CloseLong(
                    trader=to_checksum_address(tx_receipt.trader),
                    asset_id=tx_receipt.asset_id,
                    maturity_time=tx_receipt.maturity_time_seconds,
                    base_amount=tx_receipt.base_amount,
                    share_price=tx_receipt.share_price,
                    bond_amount=tx_receipt.bond_amount,
                )

            case HyperdriveActionType.OPEN_SHORT:
                return OpenShort(
                    trader=to_checksum_address(tx_receipt.trader),
                    asset_id=tx_receipt.asset_id,
                    maturity_time=tx_receipt.maturity_time_seconds,
                    base_amount=tx_receipt.base_amount,
                    share_price=tx_receipt.share_price,
                    bond_amount=tx_receipt.bond_amount,
                )

            case HyperdriveActionType.CLOSE_SHORT:
                return CloseShort(
                    trader=to_checksum_address(tx_receipt.trader),
                    asset_id=tx_receipt.asset_id,
                    maturity_time=tx_receipt.maturity_time_seconds,
                    base_amount=tx_receipt.base_amount,
                    share_price=tx_receipt.share_price,
                    bond_amount=tx_receipt.bond_amount,
                )

            case HyperdriveActionType.ADD_LIQUIDITY:
                return AddLiquidity(
                    provider=to_checksum_address(tx_receipt.provider),
                    lp_amount=tx_receipt.lp_amount,
                    base_amount=tx_receipt.base_amount,
                    share_price=tx_receipt.share_price,
                    lp_share_price=tx_receipt.lp_share_price,
                )

            case HyperdriveActionType.REMOVE_LIQUIDITY:
                return RemoveLiquidity(
                    provider=to_checksum_address(tx_receipt.provider),
                    lp_amount=tx_receipt.lp_amount,
                    base_amount=tx_receipt.base_amount,
                    share_price=tx_receipt.share_price,
                    withdrawal_share_amount=tx_receipt.withdrawal_share_amount,
                    lp_share_price=tx_receipt.lp_share_price,
                )

            case HyperdriveActionType.REDEEM_WITHDRAW_SHARE:
                return RedeemWithdrawalShares(
                    provider=to_checksum_address(tx_receipt.provider),
                    withdrawal_share_amount=tx_receipt.withdrawal_share_amount,
                    base_amount=tx_receipt.base_amount,
                    share_price=tx_receipt.share_price,
                )

            case _:
                assert_never(trade_type)

    def _reinit_state_after_load_snapshot(self) -> None:
        """After loading a snapshot, we need to re-initialize the state the internal
        variables of the interactive hyperdrive.
        1. Wipe the cache from the hyperdrive interface.
        2. Load all agent's wallets from the db.
        """
        # Set internal state block number to 0 to enusre it updates
        self.hyperdrive_interface.last_state_block_number = BlockNumber(0)

        # Load and set all agent wallets from the db
        for agent in self._pool_agents:
            db_balances = chainsync_get_current_wallet(
                self.db_session, wallet_address=[agent.agent.checksum_address], coerce_float=False
            )
            agent.agent.wallet = build_wallet_positions_from_data(
                agent.agent.checksum_address, db_balances, self.hyperdrive_interface.base_token_contract
            )

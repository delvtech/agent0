"""Defines the interactive hyperdrive class that encapsulates a hyperdrive pool."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Type

import nest_asyncio
import numpy as np
import pandas as pd
from eth_typing import ChecksumAddress
from numpy.random._generator import Generator

from agent0.chainsync.dashboard.usernames import build_user_mapping
from agent0.chainsync.db.base import get_addr_to_username
from agent0.chainsync.db.hyperdrive import add_hyperdrive_addr_to_name, get_hyperdrive_addr_to_name
from agent0.core.hyperdrive.policies import HyperdriveBasePolicy
from agent0.ethpy.hyperdrive import (
    HyperdriveReadWriteInterface,
    generate_name_for_hyperdrive,
    get_hyperdrive_addresses_from_artifacts,
    get_hyperdrive_addresses_from_registry,
)

from .chain import Chain
from .hyperdrive_agent import HyperdriveAgent

# In order to support both scripts and jupyter notebooks with underlying async functions,
# we use the nest_asyncio package so that we can execute asyncio.run within a running event loop.
# TODO: nest_asyncio may cause compatibility issues with other libraries.
# Also, Jupyter and ASYNC compatibility might be improved, removing the need for this.
# See https://github.com/python/cpython/issues/66435.
nest_asyncio.apply()


class Hyperdrive:
    """Interactive Hyperdrive class that supports connecting to an existing hyperdrive deployment."""

    # Lots of config
    # pylint: disable=too-many-instance-attributes
    @dataclass(kw_only=True)
    class Config:
        """The configuration for the interactive hyperdrive class."""

        # Execution config
        exception_on_policy_error: bool = True
        """When executing agent policies, whether to raise an exception if an error is encountered. Defaults to True."""
        exception_on_policy_slippage: bool = False
        """
        When executing agent policies, whether to raise an exception if the slippage is too large. Defaults to False.
        """
        preview_before_trade: bool = False
        """Whether to preview the position before executing a trade. Defaults to False."""
        txn_receipt_timeout: float | None = None
        """The timeout for waiting for a transaction receipt in seconds. Defaults to 120."""

        # RNG config
        rng_seed: int | None = None
        """The seed for the random number generator. Defaults to None."""
        rng: Generator | None = None
        """
        The experiment's stateful random number generator. Defaults to creating a generator from
        the provided random seed if not set.
        """

        # Logging and crash reporting
        log_to_rollbar: bool = False
        """Whether to log crash reports to rollbar. Defaults to False."""
        rollbar_log_prefix: str | None = None
        """Additional prefix for this hyperdrive to log to rollbar."""
        crash_log_level: int = logging.CRITICAL
        """The log level to log crashes at. Defaults to critical."""
        crash_report_additional_info: dict[str, Any] | None = None
        """Additional information to include in the crash report."""
        always_execute_policy_post_action: bool = False
        """
        Whether to execute the policy `post_action` function after non-policy trades. 
        If True, the policy `post_action` function always be called after any agent trade.
        If False, the policy `post_action` function will only be called after `execute_policy_action`.
        Defaults to False.
        """

        # Data pipeline parameters
        calc_pnl: bool = True
        """Whether to calculate pnl. Defaults to True."""

        def __post_init__(self):
            """Create the random number generator if not set."""
            if self.rng is None:
                self.rng = np.random.default_rng(self.rng_seed)

    @classmethod
    def get_hyperdrive_addresses_from_artifacts(
        cls,
        artifacts_uri: str,
    ) -> dict[str, ChecksumAddress]:
        """Gather deployed Hyperdrive pool addresses.

        Arguments
        ---------
        artifacts_uri: str
            The uri of the artifacts json file. This is specific to the infra deployment.

        Returns
        -------
        dict[str, ChecksumAddress]
            A dictionary keyed by the pool's name, valued by the pool's address
        """
        # pylint: disable=protected-access
        return get_hyperdrive_addresses_from_artifacts(artifacts_uri)

    @classmethod
    def get_hyperdrive_addresses_from_registry(
        cls,
        chain: Chain,
        registry_contract_addr: str,
    ) -> dict[str, ChecksumAddress]:
        """Gather deployed Hyperdrive pool addresses.

        Arguments
        ---------
        chain: Chain
            The Chain object connected to a chain.
        registry_contract_addr: str
            The address of the Hyperdrive factory contract.

        Returns
        -------
        dict[str, ChecksumAddress]
            A dictionary keyed by the pool's name, valued by the pool's address
        """
        # pylint: disable=protected-access
        return get_hyperdrive_addresses_from_registry(registry_contract_addr, chain._web3)

    def _initialize(self, chain: Chain, hyperdrive_address: ChecksumAddress, name: str | None):
        self.interface = HyperdriveReadWriteInterface(
            hyperdrive_address,
            rpc_uri=chain.rpc_uri,
            web3=chain._web3,  # pylint: disable=protected-access
            txn_receipt_timeout=self.config.txn_receipt_timeout,
        )

        self.chain = chain
        # Register the username if it was provided
        if name is None:
            # Build the name in this case
            name = generate_name_for_hyperdrive(
                self.hyperdrive_address,
                self.chain._web3,  # pylint: disable=protected-access
            )

        add_hyperdrive_addr_to_name(name, self.hyperdrive_address, self.chain.db_session)

    def __init__(
        self,
        chain: Chain,
        hyperdrive_address: ChecksumAddress,
        config: Config | None = None,
        name: str | None = None,
    ):
        """Initialize the interactive hyperdrive class.

        Arguments
        ---------
        chain: Chain
            The chain to interact with
        hyperdrive_address: ChecksumAddress
            The address of the hyperdrive contract
        config: Config | None
            The configuration for the interactive hyperdrive class
        name: str | None, optional
            The logical name of the pool.
        """
        if config is None:
            self.config = self.Config()
        else:
            self.config = config

        # Since the hyperdrive objects manage data ingestion into the singular database
        # held by the chain object, we want to ensure that we dont mix and match
        # local vs non-local hyperdrive objects. Hence, we ensure that any hyperdrive
        # objects must come from a base Chain object and not a LocalChain.
        # We use `type` instead of `isinstance` to explicitly check for
        # the base Chain type instead of any subclass.
        # pylint: disable=unidiomatic-typecheck
        if type(chain) != Chain:
            raise TypeError("The chain parameter must be a Chain object, not a LocalChain.")

        self._initialize(chain, hyperdrive_address, name)

    def get_positions(self, show_closed_positions: bool = False, coerce_float: bool = False) -> pd.DataFrame:
        """Gets all current positions of this pool and their corresponding pnl
        and returns as a pandas dataframe.

        This function is not implemented for remote hyperdrive, as gathering this data
        is expensive. In the future, we can explicitly make this call gather data from
        the remote chain.

        Arguments
        ---------
        coerce_float: bool
            If True, will coerce underlying Decimals to floats.
        show_closed_positions: bool
            Whether to show positions closed positions (i.e., positions with zero balance). Defaults to False.
            When False, will only return currently open positions. Useful for gathering currently open positions.
            When True, will also return any closed positions. Useful for calculating overall pnl of all positions.

        Returns
        -------
        pd.Dataframe
            A dataframe consisting of currently open positions and their corresponding pnl.
        """
        raise NotImplementedError

    def get_trade_events(self, all_token_deltas: bool = False, coerce_float: bool = False) -> pd.DataFrame:
        """Gets the ticker history of all trades and the corresponding token deltas for each trade.

        This function is not implemented for remote hyperdrive, as gathering this data
        is expensive. In the future, we can explicitly make this call gather data from
        the remote chain.

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
        raise NotImplementedError

    def get_historical_positions(self, coerce_float: bool = False) -> pd.DataFrame:
        """Gets the history of all positions over time and their corresponding pnl
        and returns as a pandas dataframe.

        This function is not implemented for remote hyperdrive, as gathering this data
        is expensive. In the future, we can explicitly make this call gather data from
        the remote chain.

        Arguments
        ---------
        coerce_float: bool
            If True, will coerce underlying Decimals to floats.

        Returns
        -------
        pd.Dataframe
            A dataframe consisting of positions over time and their corresponding pnl.
        """
        raise NotImplementedError

    def get_historical_pnl(self, coerce_float: bool = False) -> pd.DataFrame:
        """Gets total pnl for each wallet for each block, aggregated across all open positions.

        This function is not implemented for remote hyperdrive, as gathering this data
        is expensive. In the future, we can explicitly make this call gather data from
        the remote chain.

        Arguments
        ---------
        coerce_float: bool
            If True, will coerce underlying Decimals to floats.

        Returns
        -------
        pd.Dataframe
            A dataframe of aggregated wallet pnl per block
        """
        raise NotImplementedError

    @property
    def hyperdrive_address(self) -> ChecksumAddress:
        """Returns the hyperdrive addresses for this pool.

        Returns
        -------
        ChecksumAddress
            The hyperdrive addresses for this pool
        """
        # pylint: disable=protected-access
        return self.interface.hyperdrive_address

    def init_agent(
        self,
        private_key: str,
        policy: Type[HyperdriveBasePolicy] | None = None,
        policy_config: HyperdriveBasePolicy.Config | None = None,
        name: str | None = None,
    ) -> HyperdriveAgent:
        """Initialize an agent object given a private key.

        .. note::
            Due to the underlying bookkeeping, each agent object needs a unique private key.

        Arguments
        ---------
        private_key: str
            The private key of the associated account.
        policy: HyperdrivePolicy, optional
            An optional policy to attach to this agent.
        policy_config: HyperdrivePolicy, optional
            The configuration for the attached policy.
        name: str, optional
            The name of the agent. Defaults to the wallet address.

        Returns
        -------
        HyperdriveAgent
            The agent object for a user to execute trades with.
        """
        # If the underlying policy's rng isn't set, we use the one from interactive hyperdrive
        if policy_config is not None and policy_config.rng is None and policy_config.rng_seed is None:
            policy_config.rng = self.config.rng
        out_agent = HyperdriveAgent(
            name=name,
            pool=self,
            policy=policy,
            policy_config=policy_config,
            private_key=private_key,
        )
        return out_agent

    def _add_username_to_dataframe(self, df: pd.DataFrame, addr_column: str):
        addr_to_username = get_addr_to_username(self.chain.db_session)

        # Get corresponding usernames
        usernames = build_user_mapping(df[addr_column], addr_to_username)["username"]
        out = df.copy()
        # Weird pandas type error
        out.insert(df.columns.get_loc(addr_column), "username", usernames)  # type: ignore
        return out

    def _add_hyperdrive_name_to_dataframe(self, df: pd.DataFrame, addr_column: str):
        hyperdrive_addr_to_name = get_hyperdrive_addr_to_name(self.chain.db_session)

        # Do lookup from address to name
        hyperdrive_name = (
            df[addr_column]
            .to_frame()
            .merge(hyperdrive_addr_to_name, how="left", left_on=addr_column, right_on="hyperdrive_address")
        )["name"]
        # Weird pandas type error
        out = df.copy()
        out.insert(df.columns.get_loc(addr_column), "hyperdrive_name", hyperdrive_name)  # type: ignore
        return out

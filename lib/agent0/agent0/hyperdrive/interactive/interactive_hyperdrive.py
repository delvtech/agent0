"""Defines the interactive hyperdrive class for a hyperdrive pool."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass

from eth_account.account import Account
from eth_utils.address import to_checksum_address
from ethpy import EthConfig
from ethpy.hyperdrive import DeployedHyperdrivePool, ReceiptBreakdown, deploy_hyperdrive_from_factory
from ethpy.hyperdrive.api import HyperdriveInterface
from fixedpointmath import FixedPoint
from hypertypes.IHyperdriveTypes import Fees, PoolConfig
from web3.constants import ADDRESS_ZERO

from agent0.base.make_key import make_private_key
from agent0.hyperdrive.agents import HyperdriveAgent
from agent0.hyperdrive.exec import async_execute_agent_trades
from agent0.hyperdrive.state import HyperdriveActionType, TradeResult, TradeStatus

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


class InteractiveHyperdrive:
    """Hyperdrive class that supports an interactive interface for running tests and experiments."""

    @dataclass
    class Config:
        """
        The configuration for the initial pool configuration

        Attributes
        ----------
        TODO
        """

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

        def __post_init__(self):
            if self.time_stretch is None:
                self.time_stretch = FixedPoint(1) / (
                    FixedPoint("5.24592") / (FixedPoint("0.04665") * (self.initial_fixed_rate * FixedPoint(100)))
                )

    def __init__(self, config: Config, chain: Chain):
        """Constructor for the interactive hyperdrive agent.

        Arguments
        ---------
        config: Config
            The configuration for the initial pool configuration
        chain: Chain
            The chain object to launch hyperdrive on
        """
        # Define agent0 configs with this setup
        # TODO this very likely needs to reference an absolute path
        # as if we're importing this package from another repo, this path won't work
        eth_config = EthConfig(artifacts_uri="not_used", rpc_uri=chain.rpc_uri, abi_dir="packages/hyperdrive/src/abis/")
        # Deploys a hyperdrive factory + pool on the chain
        self._deployed_hyperdrive = self._deploy_hyperdrive(config, chain, eth_config.abi_dir)
        self.hyperdrive_interface = HyperdriveInterface(
            eth_config,
            self._deployed_hyperdrive.hyperdrive_contract_addresses,
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

    def init_agent(
        self,
        eth: FixedPoint | None = None,
        base: FixedPoint | None = None,
        name: str | None = None,
    ) -> InteractiveHyperdriveAgent:
        """Initializes an agent with initial funding and a logical name.

        Arguments
        ---------
        eth: FixedPoint
            The amount of ETH to fund the agent with. Defaults to 10.
        base: FixedPoint
            The amount of base to fund the agent with. Defaults to 0.
        name: str
            The name of the agent. Defaults to the wallet address.
        """
        if eth is None:
            # We need eth to, at minimum, approve, hence, we start with a non-zero amount
            eth = FixedPoint(10)
        if base is None:
            base = FixedPoint(0)
        agent = InteractiveHyperdriveAgent(name=name, pool=self)
        if eth > 0 or base > 0:
            agent.add_funds(eth, base)
        return agent

    ### Agent methods
    def _init_agent(self, name: str | None) -> HyperdriveAgent:
        agent_private_key = make_private_key()
        return HyperdriveAgent(
            Account().from_key(agent_private_key), policy=InteractiveHyperdrivePolicy(budget=FixedPoint(0))
        )

    def _add_funds(self, agent: HyperdriveAgent, eth: FixedPoint, base: FixedPoint) -> None:
        pass

    def _handle_trade_result(self, trade_results: list[TradeResult]) -> ReceiptBreakdown:
        # Sanity check, should only be one trade result
        assert len(trade_results) == 1
        trade_result = trade_results[0]
        if trade_result.status == TradeStatus.FAIL:
            assert trade_result.exception is not None
            # TODO when we allow for async, we likely would want to ignore slippage checks here
            raise trade_result.exception
        assert trade_result.status == TradeStatus.SUCCESS
        assert len(trade_results) == 1
        tx_receipt = trade_results[0].tx_receipt
        assert tx_receipt is not None
        return tx_receipt

    def _open_long(self, agent: HyperdriveAgent, base: FixedPoint) -> OpenLong:
        # Set the next action to open a long
        assert isinstance(agent.policy, InteractiveHyperdrivePolicy)
        agent.policy.set_next_action(HyperdriveActionType.OPEN_LONG, base)
        # TODO expose async here to the caller eventually
        trade_results: list[TradeResult] = asyncio.run(
            async_execute_agent_trades(self.hyperdrive_interface, [agent], False)
        )
        tx_receipt = self._handle_trade_result(trade_results)
        # Build open long event from trade_result
        return OpenLong(
            trader=to_checksum_address(tx_receipt.trader),
            asset_id=tx_receipt.asset_id,
            maturity_time=tx_receipt.maturity_time_seconds,
            base_amount=tx_receipt.base_amount,
            share_price=tx_receipt.share_price,
            bond_amount=tx_receipt.bond_amount,
        )

"""Defines the interactive hyperdrive class for a hyperdrive pool."""
from __future__ import annotations

from dataclasses import dataclass

from ethpy.hyperdrive import DeployedHyperdrivePool, deploy_hyperdrive_from_factory
from fixedpointmath import FixedPoint
from hypertypes.IHyperdriveTypes import Fees, PoolConfig
from web3.constants import ADDRESS_ZERO

from .chain import Chain


class InteractiveHyperdrive:
    """Hyperdrive class that supports an interactive interface for running tests and experiments."""

    @dataclass
    class Config:
        """
        The configuration for the initial pool configuration

        Attributes
        ----------
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
        # Deploys a hyperdrive factory + pool on the chain
        self._deployed_hyperdrive = self._deploy_hyperdrive(config, chain)
        # Initializes the db session
        # The db container name is a combination of the rpc url and the address of the hyperdrive pool
        # This ensures the name to be unique
        # Initialize agent0 configurations

    def _deploy_hyperdrive(self, config: Config, chain: Chain) -> DeployedHyperdrivePool:
        # TODO this very likely needs to reference an absolute path
        # as if we're importing this package from another repo, this path won't work
        abi_folder = "packages/hyperdrive/src/abis/"

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
            chain.rpc_url,
            abi_folder,
            chain.get_deployer_account_private_key(),
            config.initial_liquidity,
            config.initial_variable_rate,
            config.initial_fixed_rate,
            initial_pool_config,
            max_fees,
        )

"""Tests for hyperdrive/api.py."""
from __future__ import annotations

from dataclasses import fields
from typing import cast

from eth_typing import URI
from fixedpointmath import FixedPoint
from hypertypes.fixedpoint_types import FeesFP
from hypertypes.types import Checkpoint, PoolConfig
from hypertypes.utilities.conversions import (
    checkpoint_to_fixedpoint,
    pool_config_to_fixedpoint,
    pool_info_to_fixedpoint,
)
from web3 import HTTPProvider

from ethpy import EthConfig
from ethpy.hyperdrive.addresses import HyperdriveAddresses
from ethpy.hyperdrive.deploy import DeployedHyperdrivePool

from .api import HyperdriveInterface


class TestHyperdriveInterface:
    """Tests for the HyperdriveInterface api class."""

    def setup_hyperdrive_interface(self, _local_hyperdrive_pool: DeployedHyperdrivePool) -> HyperdriveInterface:
        """Set up the hyperdrive interface to access a deployed hyperdrive pool.

        All arguments are fixtures.

        Returns
        -------
            HyperdriveInterface
                The interface to access the deployed hyperdrive pool.
        """
        rpc_uri = cast(HTTPProvider, _local_hyperdrive_pool.web3.provider).endpoint_uri or URI("http://localhost:8545")
        hyperdrive_contract_addresses: HyperdriveAddresses = _local_hyperdrive_pool.hyperdrive_contract_addresses
        eth_config = EthConfig(artifacts_uri="not used", rpc_uri=rpc_uri, abi_dir="./packages/hyperdrive/src/abis")
        return HyperdriveInterface(eth_config, addresses=hyperdrive_contract_addresses)
        # TODO: need an agent address to mock up trades

    def test_pool_config(self, local_hyperdrive_pool: DeployedHyperdrivePool):
        """Checks that the Hyperdrive pool_config matches what is returned from the smart contract.

        All arguments are fixtures.
        """
        interface = self.setup_hyperdrive_interface(local_hyperdrive_pool)
        pool_config = cast(PoolConfig, interface.hyperdrive_contract.functions.getPoolConfig().call())
        assert pool_config_to_fixedpoint(pool_config) == interface.current_pool_state.pool_config

    def test_pool_info(self, local_hyperdrive_pool: DeployedHyperdrivePool):
        """Checks that the Hyperdrive pool_info matches what is returned from the smart contract.

        All arguments are fixtures.
        """
        interface = self.setup_hyperdrive_interface(local_hyperdrive_pool)
        pool_info = interface.hyperdrive_contract.functions.getPoolInfo().call()
        assert pool_info_to_fixedpoint(pool_info) == interface.current_pool_state.pool_info

    def test_checkpoint(self, local_hyperdrive_pool: DeployedHyperdrivePool):
        """Checks that the Hyperdrive checkpoint matches what is returned from the smart contract.

        All arguments are fixtures.
        """
        interface = self.setup_hyperdrive_interface(local_hyperdrive_pool)
        checkpoint_id = interface.calc_checkpoint_id(block_timestamp=interface.current_pool_state.block_time)
        checkpoint = cast(Checkpoint, interface.hyperdrive_contract.functions.getCheckpoint(checkpoint_id).call())
        assert checkpoint_to_fixedpoint(checkpoint) == interface.current_pool_state.checkpoint

    def test_spot_price_and_fixed_rate(self, local_hyperdrive_pool: DeployedHyperdrivePool):
        """Checks that the Hyperdrive spot price and fixed rate match computing it by hand."""
        interface = self.setup_hyperdrive_interface(local_hyperdrive_pool)
        # get pool config variables
        pool_config = interface.current_pool_state.pool_config
        init_share_price: FixedPoint = pool_config.initial_share_price
        time_stretch: FixedPoint = pool_config.time_stretch
        # get pool info variables
        pool_info = interface.current_pool_state.pool_info
        share_reserves: FixedPoint = pool_info.share_reserves
        bond_reserves: FixedPoint = pool_info.bond_reserves
        # test spot price
        spot_price = ((init_share_price * share_reserves) / bond_reserves) ** time_stretch
        assert abs(spot_price - interface.calc_spot_price()) <= FixedPoint(scaled_value=1)
        # test fixed rate (rounding issues can cause it to be off by 1e-18)
        # TODO: This should be exact up to 1e-18, but is not
        fixed_rate = (FixedPoint(1) - spot_price) / (spot_price * interface.calc_position_duration_in_years())
        assert abs(fixed_rate - interface.calc_fixed_rate()) <= FixedPoint(scaled_value=100)

    def test_misc(self, local_hyperdrive_pool: DeployedHyperdrivePool):
        """Miscellaneous tests only verify that the attributes exist and functions can be called."""
        interface = self.setup_hyperdrive_interface(local_hyperdrive_pool)
        _ = interface.current_pool_state
        _ = interface.current_pool_state.variable_rate
        _ = interface.current_pool_state.vault_shares
        _ = interface.calc_open_long(FixedPoint(100))
        _ = interface.calc_open_short(FixedPoint(100))
        _ = interface.calc_bonds_given_shares_and_rate(FixedPoint(0.05))
        _ = interface.calc_max_long(FixedPoint(1000))
        _ = interface.calc_max_short(FixedPoint(1000))

    def test_bonds_given_shares_and_rate(self, local_hyperdrive_pool: DeployedHyperdrivePool):
        """Check that the bonds calculated actually hit the target rate."""
        # pylint: disable=too-many-locals
        interface = self.setup_hyperdrive_interface(local_hyperdrive_pool)
        # get pool config variables
        pool_config = interface.pool_config
        init_share_price: FixedPoint = pool_config.initial_share_price
        time_stretch: FixedPoint = pool_config.time_stretch
        position_duration_years = pool_config.position_duration / FixedPoint(60 * 60 * 24 * 365)
        # get pool info variables
        pool_info = interface.current_pool_state.pool_info
        share_reserves: FixedPoint = pool_info.share_reserves
        share_adjustment: FixedPoint = pool_info.share_adjustment
        effective_share_reserves = share_reserves - share_adjustment
        bond_reserves: FixedPoint = pool_info.bond_reserves
        # check current rate
        spot_price = ((init_share_price * effective_share_reserves) / bond_reserves) ** time_stretch
        fixed_rate = (FixedPoint(1) - spot_price) / (spot_price * position_duration_years)
        assert abs(fixed_rate - FixedPoint(0.05)) < FixedPoint(scaled_value=100)
        # test hitting target of 10%
        target_apr = FixedPoint("0.10")
        bonds_needed = interface.calc_bonds_given_shares_and_rate(target_rate=target_apr)
        spot_price = ((init_share_price * effective_share_reserves) / bonds_needed) ** time_stretch
        fixed_rate = (FixedPoint(1) - spot_price) / (spot_price * position_duration_years)
        assert abs(fixed_rate - target_apr) <= FixedPoint(1e-16)
        # test hitting target of 1%
        target_apr = FixedPoint("0.01")
        bonds_needed = interface.calc_bonds_given_shares_and_rate(target_rate=target_apr)
        spot_price = ((init_share_price * effective_share_reserves) / bonds_needed) ** time_stretch
        fixed_rate = (FixedPoint(1) - spot_price) / (spot_price * position_duration_years)
        assert abs(fixed_rate - target_apr) <= FixedPoint(1e-16)

    def test_deployed_values(self, local_hyperdrive_pool: DeployedHyperdrivePool):
        """Test the hyperdrive interface versus expected values."""
        # pylint: disable=too-many-locals
        interface = self.setup_hyperdrive_interface(local_hyperdrive_pool)

        initial_fixed_rate = FixedPoint("0.05")
        expected_timestretch_fp = FixedPoint(1) / (
            FixedPoint("5.24592") / (FixedPoint("0.04665") * (initial_fixed_rate * FixedPoint(100)))
        )

        deploy_account = local_hyperdrive_pool.deploy_account
        hyperdrive_contract_addresses = local_hyperdrive_pool.hyperdrive_contract_addresses

        expected_pool_config = {
            "base_token": hyperdrive_contract_addresses.base_token,
            "initial_share_price": FixedPoint("1"),
            "minimum_share_reserves": FixedPoint("10"),
            "minimum_transaction_amount": FixedPoint("0.001"),
            "precision_threshold": int(1e14),
            "position_duration": 604800,  # 1 week
            "checkpoint_duration": 3600,  # 1 hour
            "time_stretch": expected_timestretch_fp,
            "governance": deploy_account.address,
            "fee_collector": deploy_account.address,
        }
        expected_pool_config["fees"] = FeesFP(
            curve=FixedPoint("0.1"),  # 10,
            flat=FixedPoint("0.0005"),  # 0.0%
            governance=FixedPoint("0.15"),  # 1%
        )

        api_pool_config = interface.current_pool_state.pool_config

        # Existence test
        assert len(fields(api_pool_config)) > 0, "API pool config must have length greater than 0"

        # Ensure keys and fields match (ignoring linker_factory and linker_code_hash)
        api_keys = [n.name for n in fields(api_pool_config) if n.name not in ["linker_factory", "linker_code_hash"]]
        expected_keys = set(expected_pool_config.keys())
        for key in expected_keys:
            assert key in api_keys, f"Key {key} in expected but not in API."
        for key in api_keys:
            assert key in expected_keys, f"Key {key} in API not in expected."

        # Ensure values match
        for key, expected_value in expected_pool_config.items():
            actual_value = getattr(api_pool_config, key)
            assert actual_value == expected_value, f"Values do not match for {key} ({actual_value} != {expected_value})"

        # Pool info comparison
        expected_pool_info_keys = {
            "share_reserves",
            "bond_reserves",
            "lp_total_supply",
            "share_price",
            "share_adjustment",
            "lp_share_price",
            "long_exposure",
            "longs_outstanding",
            "long_average_maturity_time",
            "shorts_outstanding",
            "short_average_maturity_time",
            "withdrawal_shares_ready_to_withdraw",
            "withdrawal_shares_proceeds",
        }

        api_pool_info = interface.current_pool_state.pool_info

        # Ensure keys and fields match (ignoring linker_factory and linker_code_hash)
        api_keys = [n.name for n in fields(api_pool_info)]
        for key in expected_pool_info_keys:
            assert key in api_keys, f"Key {key} in expected but not in API."
        for key in api_keys:
            assert key in expected_pool_info_keys, f"Key {key} in API not in expected."

        # Check spot price and fixed rate
        api_spot_price = interface.calc_spot_price()
        effective_share_reserves = api_pool_info.share_reserves - api_pool_info.share_adjustment
        expected_spot_price = (
            (api_pool_config.initial_share_price * effective_share_reserves) / api_pool_info.bond_reserves
        ) ** api_pool_config.time_stretch

        api_fixed_rate = interface.calc_fixed_rate()
        expected_fixed_rate = (1 - expected_spot_price) / (
            expected_spot_price * (api_pool_config.position_duration / FixedPoint(365 * 24 * 60 * 60))
        )

        # TODO there's rounding errors between api spot price and fixed rates
        assert abs(api_spot_price - expected_spot_price) <= FixedPoint(1e-16)
        assert abs(api_fixed_rate - expected_fixed_rate) <= FixedPoint(1e-16)

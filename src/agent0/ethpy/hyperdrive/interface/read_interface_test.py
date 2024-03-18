"""Tests for hyperdrive_read_interface.py."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import fields
from typing import TYPE_CHECKING, cast

from fixedpointmath import FixedPoint

from agent0.hypertypes import PoolConfig
from agent0.hypertypes.fixedpoint_types import FeesFP
from agent0.hypertypes.utilities.conversions import pool_config_to_fixedpoint, pool_info_to_fixedpoint

if TYPE_CHECKING:
    from .read_interface import HyperdriveReadInterface

# we need to use the outer name for fixtures
# pylint: disable=redefined-outer-name


class TestHyperdriveReadInterface:
    """Tests for the HyperdriveReadInterface api class."""

    def test_pool_config(self, hyperdrive_read_interface: HyperdriveReadInterface):
        """Checks that the Hyperdrive pool_config matches what is returned from the smart contract."""
        pool_config = cast(PoolConfig, hyperdrive_read_interface.hyperdrive_contract.functions.getPoolConfig().call())
        assert pool_config_to_fixedpoint(pool_config) == hyperdrive_read_interface.current_pool_state.pool_config

    def test_pool_config_deployed(self, hyperdrive_read_interface: HyperdriveReadInterface):
        """Checks that the Hyperdrive pool_config matches what is returned from the smart contract."""
        pool_config = cast(PoolConfig, hyperdrive_read_interface.hyperdrive_contract.functions.getPoolConfig().call())
        assert pool_config_to_fixedpoint(pool_config) == hyperdrive_read_interface.current_pool_state.pool_config

    def test_pool_info(self, hyperdrive_read_interface: HyperdriveReadInterface):
        """Checks that the Hyperdrive pool_info matches what is returned from the smart contract."""
        pool_info = hyperdrive_read_interface.hyperdrive_contract.functions.getPoolInfo().call()
        assert pool_info_to_fixedpoint(pool_info) == hyperdrive_read_interface.current_pool_state.pool_info

    def test_checkpoint(self, hyperdrive_read_interface: HyperdriveReadInterface):
        """Checks that the Hyperdrive checkpoint matches what is returned from the smart contract."""
        checkpoint_id = hyperdrive_read_interface.calc_checkpoint_id(
            block_timestamp=hyperdrive_read_interface.current_pool_state.block_time
        )
        checkpoint = hyperdrive_read_interface.get_checkpoint(checkpoint_id)
        assert checkpoint == hyperdrive_read_interface.current_pool_state.checkpoint

    def test_spot_price_and_fixed_rate(self, hyperdrive_read_interface: HyperdriveReadInterface):
        """Checks that the Hyperdrive spot price and fixed rate match computing it by hand."""
        # get pool config variables
        pool_config = hyperdrive_read_interface.current_pool_state.pool_config
        init_vault_share_price: FixedPoint = pool_config.initial_vault_share_price
        time_stretch: FixedPoint = pool_config.time_stretch
        # get pool info variables
        pool_info = hyperdrive_read_interface.current_pool_state.pool_info
        share_reserves: FixedPoint = pool_info.share_reserves
        bond_reserves: FixedPoint = pool_info.bond_reserves
        # test spot price
        spot_price = ((init_vault_share_price * share_reserves) / bond_reserves) ** time_stretch
        assert abs(spot_price - hyperdrive_read_interface.calc_spot_price()) <= FixedPoint(1e-18)
        # test fixed rate (rounding issues can cause it to be off by 1e-18)
        # TODO: This should be exact up to 1e-18, but is not
        fixed_rate = (FixedPoint(1) - spot_price) / (
            spot_price * hyperdrive_read_interface.calc_position_duration_in_years()
        )
        assert abs(fixed_rate - hyperdrive_read_interface.calc_fixed_rate()) <= FixedPoint(1e-16)

    def test_misc(self, hyperdrive_read_interface: HyperdriveReadInterface):
        """Miscellaneous tests only verify that the attributes exist and functions can be called."""
        _ = hyperdrive_read_interface.current_pool_state
        _ = hyperdrive_read_interface.current_pool_state.variable_rate
        _ = hyperdrive_read_interface.current_pool_state.vault_shares
        _ = hyperdrive_read_interface.calc_open_long(FixedPoint(100))
        _ = hyperdrive_read_interface.calc_close_long(FixedPoint(100), FixedPoint(1.0))
        _ = hyperdrive_read_interface.calc_open_short(FixedPoint(100))
        _ = hyperdrive_read_interface.calc_close_short(
            FixedPoint(100), FixedPoint(scaled_value=int(9e17)), FixedPoint(scaled_value=int(9.9e17)), FixedPoint(0.9)
        )
        _ = hyperdrive_read_interface.calc_bonds_given_shares_and_rate(FixedPoint(0.05))
        _ = hyperdrive_read_interface.calc_max_long(FixedPoint(1000))
        _ = hyperdrive_read_interface.calc_max_short(FixedPoint(1000))
        _ = hyperdrive_read_interface.calc_present_value()

    def test_deployed_fixed_rate(self, hyperdrive_read_interface: HyperdriveReadInterface):
        """Check that the bonds calculated actually hit the target rate."""
        assert abs(hyperdrive_read_interface.calc_fixed_rate() - FixedPoint(0.05)) < FixedPoint(1e-16)

    def test_bonds_given_shares_and_rate(self, hyperdrive_read_interface: HyperdriveReadInterface):
        """Check that the bonds calculated actually hit the target rate."""
        # get pool state so we can modify them to run what-if scenarios
        pool_state = deepcopy(hyperdrive_read_interface.current_pool_state)
        pool_info = pool_state.pool_info

        # test hitting target of 10%
        target_apr = FixedPoint("0.10")
        pool_info.bond_reserves = hyperdrive_read_interface.calc_bonds_given_shares_and_rate(target_rate=target_apr)
        fixed_rate = hyperdrive_read_interface.calc_fixed_rate(pool_state=pool_state)
        assert abs(fixed_rate - target_apr) <= FixedPoint(1e-16)

        # test hitting target of 1%
        target_apr = FixedPoint("0.01")
        pool_info.bond_reserves = hyperdrive_read_interface.calc_bonds_given_shares_and_rate(target_rate=target_apr)
        fixed_rate = hyperdrive_read_interface.calc_fixed_rate(pool_state=pool_state)
        assert abs(fixed_rate - target_apr) <= FixedPoint(1e-16)

    def test_deployed_values(self, hyperdrive_read_interface: HyperdriveReadInterface):
        """Test the hyperdrive interface versus expected values."""
        # pylint: disable=too-many-locals
        local_hyperdrive_pool = hyperdrive_read_interface.deployed_hyperdrive_pool
        initial_fixed_rate = FixedPoint("0.05")
        # This expected time stretch is only true for 1 year position duration
        expected_timestretch_fp = FixedPoint(1) / (
            FixedPoint("5.24592") / (FixedPoint("0.04665") * (initial_fixed_rate * FixedPoint(100)))
        )
        deploy_account = local_hyperdrive_pool.deploy_account
        hyperdrive_contract_addresses = local_hyperdrive_pool.hyperdrive_contract_addresses
        expected_pool_config = {
            "base_token": hyperdrive_contract_addresses.base_token,
            "initial_vault_share_price": FixedPoint("1"),
            "minimum_share_reserves": FixedPoint("10"),
            "minimum_transaction_amount": FixedPoint("0.001"),
            "position_duration": 60 * 60 * 24 * 365,  # 1 year
            "checkpoint_duration": 3600,  # 1 hour
            "time_stretch": expected_timestretch_fp,
            "governance": deploy_account.address,
            "fee_collector": deploy_account.address,
            "sweep_collector": deploy_account.address,
        }
        expected_pool_config["fees"] = FeesFP(
            curve=FixedPoint("0.01"),  # 1%,
            flat=FixedPoint("0.0005"),  # 0.05%
            governance_lp=FixedPoint("0.15"),  # 15%
            governance_zombie=FixedPoint("0.03"),  # 3%
        )

        api_pool_config = hyperdrive_read_interface.current_pool_state.pool_config

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
            "zombie_base_proceeds",
            "zombie_share_reserves",
            "lp_total_supply",
            "vault_share_price",
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

        api_pool_info = hyperdrive_read_interface.current_pool_state.pool_info

        # Ensure keys and fields match (ignoring linker_factory and linker_code_hash)
        api_keys = [n.name for n in fields(api_pool_info)]
        for key in expected_pool_info_keys:
            assert key in api_keys, f"Key {key} in expected but not in API."
        for key in api_keys:
            assert key in expected_pool_info_keys, f"Key {key} in API not in expected."

        # Check spot price and fixed rate
        api_spot_price = hyperdrive_read_interface.calc_spot_price()
        effective_share_reserves = api_pool_info.share_reserves - api_pool_info.share_adjustment
        expected_spot_price = (
            (api_pool_config.initial_vault_share_price * effective_share_reserves) / api_pool_info.bond_reserves
        ) ** api_pool_config.time_stretch

        api_fixed_rate = hyperdrive_read_interface.calc_fixed_rate()
        expected_fixed_rate = (1 - expected_spot_price) / (
            expected_spot_price * (api_pool_config.position_duration / FixedPoint(365 * 24 * 60 * 60))
        )

        # TODO there are rounding errors between api spot price and fixed rates
        assert abs(api_spot_price - expected_spot_price) <= FixedPoint(1e-16)
        assert abs(api_fixed_rate - expected_fixed_rate) <= FixedPoint(1e-16)

"""System test for end to end usage of agent0 libraries."""

from __future__ import annotations

import logging
import os
from decimal import Decimal
from typing import Type, cast

import numpy as np
import pandas as pd
import pytest
from eth_account.signers.local import LocalAccount
from eth_typing import URI
from fixedpointmath import FixedPoint, isclose
from sqlalchemy.orm import Session
from web3 import HTTPProvider
from web3.constants import ADDRESS_ZERO

from agent0.chainsync.db.hyperdrive.interface import (
    get_current_wallet,
    get_pool_analysis,
    get_pool_config,
    get_pool_info,
    get_transactions,
    get_wallet_deltas,
)
from agent0.chainsync.exec import acquire_data, data_analysis
from agent0.core import build_account_key_config_from_agent_config
from agent0.core.base.config import AgentConfig, EnvironmentConfig
from agent0.core.hyperdrive.exec import setup_and_run_agent_loop
from agent0.core.test_utils import CycleTradesPolicy
from agent0.ethpy import EthConfig
from agent0.ethpy.hyperdrive import BASE_TOKEN_SYMBOL, HyperdriveReadInterface
from agent0.ethpy.hyperdrive.addresses import HyperdriveAddresses
from agent0.ethpy.test_fixtures import DeployedHyperdrivePool


def _to_unscaled_decimal(fp_val: FixedPoint) -> Decimal:
    return Decimal(str(fp_val))


class TestBotToDb:
    """Test pipeline from bots making trades to viewing the trades in the db."""

    # TODO split this up into different functions that work with tests
    # pylint: disable=too-many-locals, too-many-statements
    # ruff: noqa: PLR0915 (Too many statements)
    @pytest.mark.anvil
    def test_bot_to_db(
        self,
        local_hyperdrive_pool: DeployedHyperdrivePool,
        cycle_trade_policy: Type[CycleTradesPolicy],
        db_session: Session,
        db_api: str,
    ):
        """Run the entire pipeline and checks the database at the end. All arguments are fixtures."""
        # Run this test with develop mode on
        os.environ["DEVELOP"] = "true"
        # Get hyperdrive chain info
        uri: URI | None = cast(HTTPProvider, local_hyperdrive_pool.web3.provider).endpoint_uri
        rpc_uri = uri if uri else URI("http://localhost:8545")
        deploy_account: LocalAccount = local_hyperdrive_pool.deploy_account
        hyperdrive_contract_addresses: HyperdriveAddresses = local_hyperdrive_pool.hyperdrive_contract_addresses

        # Build environment config
        env_config = EnvironmentConfig(
            delete_previous_logs=False,
            halt_on_errors=True,
            log_filename="system_test",
            log_level=logging.INFO,
            log_stdout=True,
            global_random_seed=1234,
            username="test",
        )

        # Build agent config
        agent_config: list[AgentConfig] = [
            AgentConfig(
                policy=cycle_trade_policy,
                number_of_agents=1,
                base_budget_wei=FixedPoint("1_000_000").scaled_value,  # 1 million base
                eth_budget_wei=FixedPoint("100").scaled_value,  # 100 base
                policy_config=cycle_trade_policy.Config(
                    slippage_tolerance=FixedPoint("0.0001"),
                ),
            ),
        ]

        # No need for random seed, this bot is deterministic
        account_key_config = build_account_key_config_from_agent_config(agent_config)

        # Build custom eth config pointing to local test chain
        eth_config = EthConfig(
            # Artifacts_uri isn't used here, as we explicitly set addresses and passed to run_bots
            artifacts_uri="not_used",
            database_api_uri=db_api,
            rpc_uri=rpc_uri,
            # Using default abi dir
        )

        # Run bots
        setup_and_run_agent_loop(
            env_config,
            agent_config,
            account_key_config,
            eth_config=eth_config,
            contract_addresses=hyperdrive_contract_addresses,
        )

        # Run acquire data to get data from chain to db
        acquire_data(
            start_block=local_hyperdrive_pool.deploy_block_number,  # We only want to get data past the deploy block
            eth_config=eth_config,
            db_session=db_session,
            contract_addresses=hyperdrive_contract_addresses,
            # Exit the script after catching up to the chain
            exit_on_catch_up=True,
        )

        # Run data analysis to calculate various analysis values
        data_analysis(
            start_block=local_hyperdrive_pool.deploy_block_number,  # We only want to get data past the deploy block
            eth_config=eth_config,
            db_session=db_session,
            contract_addresses=hyperdrive_contract_addresses,
            # Exit the script after catching up to the chain
            exit_on_catch_up=True,
        )

        # Run bots again, but this time only for 4 trades

        # Build agent config
        agent_config: list[AgentConfig] = [
            AgentConfig(
                policy=cycle_trade_policy,
                number_of_agents=1,
                base_budget_wei=FixedPoint("1_000_000").scaled_value,  # 1 million base
                eth_budget_wei=FixedPoint("100").scaled_value,  # 100 base
                policy_config=cycle_trade_policy.Config(
                    slippage_tolerance=FixedPoint("0.0001"),
                    max_trades=3,
                ),
            ),
        ]

        setup_and_run_agent_loop(
            env_config,
            agent_config,
            account_key_config,
            eth_config=eth_config,
            contract_addresses=hyperdrive_contract_addresses,
        )

        # Run acquire data to get data from chain to db
        acquire_data(
            start_block=local_hyperdrive_pool.deploy_block_number,  # We only want to get data past the deploy block
            eth_config=eth_config,
            db_session=db_session,
            contract_addresses=hyperdrive_contract_addresses,
            # Exit the script after catching up to the chain
            exit_on_catch_up=True,
        )

        # Run data analysis to calculate various analysis values
        data_analysis(
            start_block=local_hyperdrive_pool.deploy_block_number,
            eth_config=eth_config,
            db_session=db_session,
            contract_addresses=hyperdrive_contract_addresses,
            # Exit the script after catching up to the chain
            exit_on_catch_up=True,
        )

        # This bot does the following known trades in sequence:
        # 1. addLiquidity of 111_111 base
        # 2. openLong of 22_222 base
        # 3. openShort of 333 bonds
        # 4. removeLiquidity of all LP tokens
        # 5. closeLong on long from trade 2
        # 6. closeShort on short from trade 3
        # 7. redeemWithdrawalShares of all withdrawal tokens from trade 4
        # The bot then runs again, this time for 3 trades:
        # 8. addLiquidity of 111_111 base
        # 9. openLong of 22_222 base
        # 10. openShort of 333 bonds

        # Test db entries are what we expect
        # We don't coerce to float because we want exact values in decimal
        db_pool_config_df: pd.DataFrame = get_pool_config(db_session, coerce_float=False)

        # TODO these expected values are defined in src/agent0/ethpy/test_fixtures/deploy_hyperdrive.py
        # Eventually, we want to parameterize these values to pass into deploying hyperdrive
        initial_fixed_rate = FixedPoint("0.05")
        # This expected time stretch is only true for 1 year position duration
        expected_timestretch_fp = FixedPoint(1) / (
            FixedPoint("5.24592") / (FixedPoint("0.04665") * (initial_fixed_rate * FixedPoint(100)))
        )
        expected_timestretch = _to_unscaled_decimal(expected_timestretch_fp)
        expected_inv_timestretch = _to_unscaled_decimal((1 / expected_timestretch_fp))
        # Ignore linker factory since we don't know the target address
        db_pool_config_df = db_pool_config_df.drop(columns=["linker_factory"])
        expected_pool_config = {
            "contract_address": hyperdrive_contract_addresses.erc4626_hyperdrive,
            "base_token": hyperdrive_contract_addresses.base_token,
            "initial_vault_share_price": _to_unscaled_decimal(FixedPoint("1")),
            "minimum_share_reserves": _to_unscaled_decimal(FixedPoint("10")),
            "minimum_transaction_amount": _to_unscaled_decimal(FixedPoint("0.001")),
            "position_duration": 60 * 60 * 24 * 365,  # 1 year
            "checkpoint_duration": 3600,  # 1 hour
            "time_stretch": expected_timestretch,
            "governance": deploy_account.address,
            "fee_collector": deploy_account.address,
            # TODO current bug in solidity that returns zero address for sweep_collector
            # Fix to look for deploy_account.address once this is fixed
            # "sweep_collector": deploy_account.address,
            "sweep_collector": ADDRESS_ZERO,
            "curve_fee": _to_unscaled_decimal(FixedPoint("0.01")),  # 1%
            "flat_fee": _to_unscaled_decimal(FixedPoint("0.0005")),  # 0.05% APR
            "governance_lp_fee": _to_unscaled_decimal(FixedPoint("0.15")),  # 15%
            "governance_zombie_fee": _to_unscaled_decimal(FixedPoint("0.03")),  # 3%
            "inv_time_stretch": expected_inv_timestretch,
        }

        # Existence test
        assert len(db_pool_config_df) == 1, "DB must have one entry for pool config"
        db_pool_config: pd.Series = db_pool_config_df.iloc[0]

        # Ensure keys match
        # Converting to sets and compare
        db_keys = set(db_pool_config.index)
        expected_keys = set(expected_pool_config.keys())
        assert db_keys == expected_keys, "Keys in db do not match expected"

        # Value comparison
        for key, expected_value in expected_pool_config.items():
            assert_val = db_pool_config[key] == expected_value
            assert assert_val, f"Values do not match for {key} ({db_pool_config[key]} != {expected_value})"

        # Pool info comparison
        db_pool_info: pd.DataFrame = get_pool_info(db_session, coerce_float=False)
        expected_pool_info_keys = [
            # Keys from contract call
            "block_number",
            "timestamp",
            "share_reserves",
            "share_adjustment",
            "zombie_base_proceeds",
            "zombie_share_reserves",
            "bond_reserves",
            "lp_total_supply",
            "vault_share_price",
            "longs_outstanding",
            "long_average_maturity_time",
            "shorts_outstanding",
            "short_average_maturity_time",
            "withdrawal_shares_ready_to_withdraw",
            "withdrawal_shares_proceeds",
            "lp_share_price",
            "long_exposure",
            # Added keys
            "epoch_timestamp",
            "total_supply_withdrawal_shares",
            "gov_fees_accrued",
            "hyperdrive_base_balance",
            "hyperdrive_eth_balance",
            "variable_rate",
            "vault_shares",
        ]
        # Convert to sets and compare
        assert set(db_pool_info.columns) == set(expected_pool_info_keys)

        db_transaction_info: pd.DataFrame = get_transactions(db_session, coerce_float=False)
        # TODO check transaction keys
        # This likely involves cleaning up what columns we grab from transactions

        db_wallet_delta: pd.DataFrame = get_wallet_deltas(db_session, coerce_float=False)

        # Ensure trades exist in database
        # Should be 10 total transactions
        expected_number_of_transactions = 10
        assert len(db_transaction_info) == expected_number_of_transactions
        np.testing.assert_array_equal(
            db_transaction_info["input_method"],
            [
                "addLiquidity",
                "openLong",
                "openShort",
                "removeLiquidity",
                "closeLong",
                "closeShort",
                "redeemWithdrawalShares",
                "addLiquidity",
                "openLong",
                "openShort",
            ],
        )

        # 10 total trades in wallet deltas
        assert db_wallet_delta["block_number"].nunique() == expected_number_of_transactions
        # 21 different wallet deltas (2 token deltas per trade except for withdraw shares, which is 3)
        assert len(db_wallet_delta) == 2 * expected_number_of_transactions + 1

        actual_num_longs = Decimal("nan")
        actual_num_shorts = Decimal("nan")
        actual_num_lp = Decimal("nan")
        actual_num_withdrawal = Decimal("nan")
        # Go through each trade and ensure wallet deltas are correct
        # The asserts here are equality because they are either int -> Decimal, which is lossless,
        # or they're comparing values after the lossy conversion
        expected_number_of_deltas = 2
        for _, txn in db_transaction_info.iterrows():
            # TODO differentiate between the first and second addLiquidity
            block_number = txn["block_number"]
            if txn["input_method"] == "addLiquidity":
                assert txn["input_params_contribution"] == Decimal(111_111)
                # Filter for all deltas of this trade
                block_wallet_deltas = db_wallet_delta[db_wallet_delta["block_number"] == block_number]
                # Ensure number of token deltas
                assert len(block_wallet_deltas) == expected_number_of_deltas
                lp_delta_df = block_wallet_deltas[block_wallet_deltas["base_token_type"] == "LP"]
                base_delta_df = block_wallet_deltas[block_wallet_deltas["base_token_type"] == BASE_TOKEN_SYMBOL]
                assert len(lp_delta_df) == 1
                assert len(base_delta_df) == 1
                lp_delta = lp_delta_df.iloc[0]
                base_delta = base_delta_df.iloc[0]
                # 111_111 base for...
                assert base_delta["delta"] == -Decimal(111_111)

                # TODO check LP delta
                # TODO check wallet info matches the deltas
                # TODO check pool info after this tx

                actual_num_lp = lp_delta["delta"]

            # TODO differentiate between the first and second openLong
            if txn["input_method"] == "openLong":
                assert txn["input_params_amount"] == Decimal(22_222)
                # Filter for all deltas of this trade
                block_wallet_deltas = db_wallet_delta[db_wallet_delta["block_number"] == block_number]
                # Ensure number of token deltas
                assert len(block_wallet_deltas) == expected_number_of_deltas
                long_delta_df = block_wallet_deltas[block_wallet_deltas["base_token_type"] == "LONG"]
                base_delta_df = block_wallet_deltas[block_wallet_deltas["base_token_type"] == BASE_TOKEN_SYMBOL]
                assert len(long_delta_df) == 1
                assert len(base_delta_df) == 1
                long_delta = long_delta_df.iloc[0]
                base_delta = base_delta_df.iloc[0]
                # 22_222 base for...
                assert base_delta["delta"] == -Decimal(22_222)
                # TODO check long delta
                # TODO check maturity time and token_type
                # TODO check current wallet matches the deltas
                # TODO check pool info after this tx

                actual_num_longs = long_delta["delta"]

            # TODO differentiate between the first and second openShort
            if txn["input_method"] == "openShort":
                assert txn["input_params_bond_amount"] == Decimal(333)
                block_wallet_deltas = db_wallet_delta[db_wallet_delta["block_number"] == block_number]
                assert len(block_wallet_deltas) == expected_number_of_deltas
                short_delta_df = block_wallet_deltas[block_wallet_deltas["base_token_type"] == "SHORT"]
                base_delta_df = block_wallet_deltas[block_wallet_deltas["base_token_type"] == BASE_TOKEN_SYMBOL]
                assert len(short_delta_df) == 1
                assert len(base_delta_df) == 1
                short_delta = short_delta_df.iloc[0]
                base_delta = base_delta_df.iloc[0]
                # 333 bonds for...
                assert short_delta["delta"] == Decimal(333)
                # TODO check base delta
                # TODO check maturity time and token_type
                # TODO check pool info after this tx

                actual_num_shorts = short_delta["delta"]

            if txn["input_method"] == "removeLiquidity":
                # TODO change this to expected num lp
                assert txn["input_params_lp_shares"] == actual_num_lp
                block_wallet_deltas = db_wallet_delta[db_wallet_delta["block_number"] == block_number]
                assert len(block_wallet_deltas) == expected_number_of_deltas + 1  # 3 deltas for withdraw shares
                lp_delta_df = block_wallet_deltas[block_wallet_deltas["base_token_type"] == "LP"]
                withdrawal_delta_df = block_wallet_deltas[block_wallet_deltas["base_token_type"] == "WITHDRAWAL_SHARE"]
                base_delta_df = block_wallet_deltas[block_wallet_deltas["base_token_type"] == BASE_TOKEN_SYMBOL]
                assert len(lp_delta_df) == 1
                assert len(withdrawal_delta_df) == 1
                assert len(base_delta_df) == 1
                lp_delta = lp_delta_df.iloc[0]
                withdrawal_delta = withdrawal_delta_df.iloc[0]
                base_delta = base_delta_df.iloc[0]
                # TODO check against expected lp
                assert lp_delta["delta"] == -actual_num_lp
                # TODO check base delta
                # TODO check withdrawal delta
                # TODO check wallet info matches the deltas
                # TODO check pool info after this tx

                actual_num_withdrawal = withdrawal_delta["delta"]

            if txn["input_method"] == "closeLong":
                # TODO change this to expected long amount
                assert txn["input_params_bond_amount"] == actual_num_longs
                block_wallet_deltas = db_wallet_delta[db_wallet_delta["block_number"] == block_number]
                assert len(block_wallet_deltas) == expected_number_of_deltas
                long_delta_df = block_wallet_deltas[block_wallet_deltas["base_token_type"] == "LONG"]
                base_delta_df = block_wallet_deltas[block_wallet_deltas["base_token_type"] == BASE_TOKEN_SYMBOL]
                assert len(long_delta_df) == 1
                assert len(base_delta_df) == 1
                long_delta = long_delta_df.iloc[0]
                base_delta = base_delta_df.iloc[0]
                # TODO check against expected longs
                assert long_delta["delta"] == -actual_num_longs
                # TODO check base delta
                # TODO check maturity time and token_type
                # TODO check wallet info matches the deltas
                # TODO check pool info after this tx

            if txn["input_method"] == "closeShort":
                assert txn["input_params_bond_amount"] == Decimal(333)
                block_wallet_deltas = db_wallet_delta[db_wallet_delta["block_number"] == block_number]
                assert len(block_wallet_deltas) == expected_number_of_deltas
                short_delta_df = block_wallet_deltas[block_wallet_deltas["base_token_type"] == "SHORT"]
                base_delta_df = block_wallet_deltas[block_wallet_deltas["base_token_type"] == BASE_TOKEN_SYMBOL]
                assert len(short_delta_df) == 1
                assert len(base_delta_df) == 1
                short_delta = short_delta_df.iloc[0]
                base_delta = base_delta_df.iloc[0]
                # TODO check against expected shorts
                assert short_delta["delta"] == -actual_num_shorts
                # TODO check base delta
                # TODO check maturity time and token_type
                # TODO check wallet info matches the deltas
                # TODO check pool info after this tx

            if txn["input_method"] == "redeemWithdrawalShares":
                # TODO change this to expected withdrawal shares
                assert txn["input_params_withdrawal_shares"] == actual_num_withdrawal
                block_wallet_deltas = db_wallet_delta[db_wallet_delta["block_number"] == block_number]
                assert len(block_wallet_deltas) == expected_number_of_deltas
                withdrawal_delta_df = block_wallet_deltas[block_wallet_deltas["base_token_type"] == "WITHDRAWAL_SHARE"]
                base_delta_df = block_wallet_deltas[block_wallet_deltas["base_token_type"] == BASE_TOKEN_SYMBOL]
                assert len(withdrawal_delta_df) == 1
                assert len(base_delta_df) == 1
                withdrawal_delta = withdrawal_delta_df.iloc[0]
                base_delta = base_delta_df.iloc[0]
                # TODO check against expected withdrawal shares
                assert withdrawal_delta["delta"] == -actual_num_withdrawal
                # TODO check base delta
                # TODO check wallet info matches the deltas
                # TODO check pool info after this tx

        # Check final wallet positions
        db_current_wallet: pd.DataFrame = get_current_wallet(db_session, coerce_float=False)
        # TODO currently only shorts are not dependent on poolinfo, so we only check shorts here
        # Eventually we want to double check all token types
        short_pos = db_current_wallet[db_current_wallet["base_token_type"] == "SHORT"]
        assert short_pos.iloc[0]["value"] == Decimal(333)

        # Check spot price and fixed rate
        db_pool_analysis: pd.DataFrame = get_pool_analysis(db_session, coerce_float=False)
        # Compare last value to what hyperdrive interface is reporting
        hyperdrive = HyperdriveReadInterface(
            eth_config=eth_config,
            addresses=hyperdrive_contract_addresses,
        )
        latest_pool_analysis = db_pool_analysis.iloc[-1]

        latest_spot_price = FixedPoint(str(latest_pool_analysis["spot_price"]))
        expected_spot_price = hyperdrive.calc_spot_price()

        latest_fixed_rate = FixedPoint(str(latest_pool_analysis["fixed_rate"]))
        expected_fixed_rate = hyperdrive.calc_fixed_rate()

        assert latest_pool_analysis["block_number"] == hyperdrive.current_pool_state.block_number
        # Spot price and fixed rate is off by one wei
        assert isclose(latest_spot_price, expected_spot_price, abs_tol=FixedPoint("1e-18"))
        assert isclose(latest_fixed_rate, expected_fixed_rate, abs_tol=FixedPoint("1e-18"))

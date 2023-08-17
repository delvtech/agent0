"""System test for end to end testing of elf-simulations"""
import logging
from decimal import Decimal
from typing import Type

import numpy as np
import pandas as pd
from agent0 import build_account_key_config_from_agent_config
from agent0.base.config import AgentConfig, EnvironmentConfig
from agent0.base.policies import BasePolicy
from agent0.hyperdrive.exec import run_agents
from chainsync.db.hyperdrive.interface import get_pool_config, get_pool_info, get_transactions, get_wallet_deltas
from chainsync.exec import acquire_data
from eth_account.signers.local import LocalAccount
from ethpy import EthConfig
from ethpy.hyperdrive import HyperdriveAddresses
from ethpy.test_fixtures.deploy_hyperdrive import _calculateTimeStretch
from fixedpointmath import FixedPoint
from sqlalchemy.orm import Session
from web3 import Web3

# This pass is to prevent auto reordering imports from reordering the imports below
pass  # pylint: disable=unnecessary-pass

# Test fixture imports
# Ignoring unused import warning, fixtures are used through variable name
from agent0.test_fixtures import (  # pylint: disable=unused-import, ungrouped-imports
    AgentDoneException,
    cycle_trade_policy,
)
from chainsync.test_fixtures import db_session  # pylint: disable=unused-import
from ethpy.test_fixtures import local_chain, local_hyperdrive_chain  # pylint: disable=unused-import, ungrouped-imports

# fixture arguments in test function have to be the same as the fixture name
# pylint: disable=redefined-outer-name


class TestLocalChain:
    """Tests bringing up local chain"""

    # This is using 2 fixtures. Since hyperdrive_contract_address depends on local_chain, we need both here
    # This is due to adding test fixtures through imports
    def test_hyperdrive_init_and_deploy(self, local_chain: str, local_hyperdrive_chain: dict):
        """Create and entry"""
        print(local_chain)
        print(local_hyperdrive_chain)


def _to_unscaled_decimal(scaled_value: int) -> Decimal:
    return Decimal(str(FixedPoint(scaled_value=scaled_value)))


def _decimal_almost_equal(a: Decimal, b: Decimal) -> bool:
    return abs(a - b) < 1e-12


class TestBotToDb:
    """Tests pipeline from bots making trades to viewing the trades in the db"""

    # TODO split this up into different functions that work with tests
    def test_bot_to_db(
        self,
        local_chain: str,
        local_hyperdrive_chain: dict,
        cycle_trade_policy: Type[BasePolicy],
        db_session: Session,
    ):
        # Get hyperdrive chain info
        web3: Web3 = local_hyperdrive_chain["web3"]
        deploy_account: LocalAccount = local_hyperdrive_chain["deploy_account"]
        hyperdrive_contract_addresses: HyperdriveAddresses = local_hyperdrive_chain["hyperdrive_contract_addresses"]

        # Build environment config
        env_config = EnvironmentConfig(
            delete_previous_logs=False,
            halt_on_errors=True,
            log_filename="system_test",
            log_level=logging.INFO,
            log_stdout=True,
            random_seed=1234,
            username="test",
        )

        # Build agent config
        agent_config: list[AgentConfig] = [
            AgentConfig(
                policy=cycle_trade_policy,
                number_of_agents=1,
                slippage_tolerance=FixedPoint(0.0001),
                base_budget_wei=int(1_000_000e18),  # 1 million base
                eth_budget_wei=int(100e18),  # 100 base
                init_kwargs={},
            ),
        ]

        # No need for random seed, this bot is deterministic
        account_key_config = build_account_key_config_from_agent_config(agent_config)

        # Build custom eth config pointing to local test chain
        eth_config = EthConfig(
            # Artifacts_url isn't used here, as we explicitly set addresses and passed to run_bots
            ARTIFACTS_URL="not_used",
            RPC_URL=local_chain,
            # Using default abi dir
        )

        # Run bots
        try:
            run_agents(
                env_config,
                agent_config,
                account_key_config,
                develop=True,
                eth_config=eth_config,
                contract_addresses=hyperdrive_contract_addresses,
            )
        except AgentDoneException:
            # Using this exception to stop the agents,
            # so this exception is expected on test pass
            pass

        # Run acquire data to get data from chain to db in subprocess
        acquire_data(
            start_block=8,  # First 7 blocks are deploying hyperdrive, ignore
            eth_config=eth_config,
            db_session=db_session,
            contract_addresses=hyperdrive_contract_addresses,
            # Exit the script after catching up to the chain
            exit_on_catch_up=True,
        )

        # Test db entries are what we expect
        # We don't coerce to float because we want exact values in decimal
        db_pool_config_df: pd.DataFrame = get_pool_config(db_session, coerce_float=False)

        # TODO these expected values are defined in lib/ethpy/ethpy/test_fixtures/deploy_hyperdrive.py
        # Eventually, we want to parameterize these values to pass into deploying hyperdrive
        expected_timestretch_fp = FixedPoint(scaled_value=_calculateTimeStretch(int(0.05e18)))
        # TODO this is actually inv of solidity time stretch, fix
        expected_timestretch = _to_unscaled_decimal((1 / expected_timestretch_fp).scaled_value)
        expected_inv_timestretch = _to_unscaled_decimal(expected_timestretch_fp.scaled_value)

        expected_pool_config = {
            "contractAddress": hyperdrive_contract_addresses.mock_hyperdrive,
            "baseToken": hyperdrive_contract_addresses.base_token,
            "initialSharePrice": _to_unscaled_decimal(int(1e18)),
            "minimumShareReserves": _to_unscaled_decimal(int(10e18)),
            "positionDuration": 604800,  # 1 week
            "checkpointDuration": 3600,  # 1 hour
            # TODO this is actually inv of solidity time stretch, fix
            "timeStretch": expected_timestretch,
            "governance": deploy_account.address,
            "feeCollector": deploy_account.address,
            "curveFee": _to_unscaled_decimal(int(0.1e18)),  # 10%
            "flatFee": _to_unscaled_decimal(int(0.0005e18)),  # 0.05%
            "governanceFee": _to_unscaled_decimal(int(0.15e18)),  # 15%
            "oracleSize": _to_unscaled_decimal(10),
            "updateGap": 3600,  # TODO don't know where this is getting set
            "invTimeStretch": expected_inv_timestretch,
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
            # TODO In testing, we use sqlite, which does not implement the fixed point Numeric type
            # Internally, they store Numeric types as floats, hence we see rounding errors in testing
            # This does not happen in postgres, where these values match exactly.
            # https://github.com/delvtech/elf-simulations/issues/836

            if isinstance(expected_value, Decimal):
                assert_val = _decimal_almost_equal(db_pool_config[key], expected_value)
            else:
                assert_val = db_pool_config[key] == expected_value

            assert assert_val, f"Values do not match for {key} ({db_pool_config[key]} != {expected_value})"

        # Pool info comparison
        db_pool_info: pd.DataFrame = get_pool_info(db_session, coerce_float=False)
        expected_pool_info_keys = [
            # Keys from contract call
            "shareReserves",
            "bondReserves",
            "lpTotalSupply",
            "sharePrice",
            "longsOutstanding",
            "longAverageMaturityTime",
            "shortsOutstanding",
            "shortAverageMaturityTime",
            "shortBaseVolume",
            "withdrawalSharesReadyToWithdraw",
            "withdrawalSharesProceeds",
            "lpSharePrice",
            # Added keys
            "timestamp",
            # blockNumber is the index of the dataframe
            # Calculated keys
            "totalSupplyWithdrawalShares",
        ]
        # Convert to sets and compare
        assert set(db_pool_info.columns) == set(expected_pool_info_keys)

        db_transaction_info: pd.DataFrame = get_transactions(db_session, coerce_float=False)
        # TODO check transaction keys
        # This likely involves cleaning up what columns we grab from transactions

        db_wallet_delta: pd.DataFrame = get_wallet_deltas(db_session, coerce_float=False)

        # Ensure trades exist in database
        # Should be 7 total transactions
        assert len(db_transaction_info) == 7
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
            ],
        )

        # 7 total trades in wallet deltas
        assert db_wallet_delta["blockNumber"].nunique() == 7
        # 15 different wallet deltas (2 token deltas per trade except for withdraw shares, which is 3)
        assert len(db_wallet_delta) == 15

        actual_num_longs = Decimal("nan")
        actual_num_shorts = Decimal("nan")
        actual_num_lp = Decimal("nan")
        actual_num_withdrawal = Decimal("nan")
        # Go through each trade and ensure wallet deltas are correct
        # The asserts here are equality because they are either int -> Decimal, which is lossless,
        # or they're comparing values after the lossy conversion
        for block_number, txn in db_transaction_info.iterrows():
            if txn["input_method"] == "addLiquidity":
                assert txn["input_params_contribution"] == Decimal(11111)
                block_wallet_deltas = db_wallet_delta[db_wallet_delta["blockNumber"] == block_number]
                assert len(block_wallet_deltas) == 2
                lp_delta_df = block_wallet_deltas[block_wallet_deltas["baseTokenType"] == "LP"]
                base_delta_df = block_wallet_deltas[block_wallet_deltas["baseTokenType"] == "BASE"]
                assert len(lp_delta_df) == 1
                assert len(base_delta_df) == 1
                lp_delta = lp_delta_df.iloc[0]
                base_delta = base_delta_df.iloc[0]
                # 11111 base for...
                assert base_delta["delta"] == -Decimal(11111)
                # TODO check LP delta
                # TODO check wallet info matches the deltas
                # TODO check pool info after this tx

                actual_num_lp = lp_delta["delta"]

            if txn["input_method"] == "openLong":
                assert txn["input_params_baseAmount"] == Decimal(22222)
                block_wallet_deltas = db_wallet_delta[db_wallet_delta["blockNumber"] == block_number]
                assert len(block_wallet_deltas) == 2
                long_delta_df = block_wallet_deltas[block_wallet_deltas["baseTokenType"] == "LONG"]
                base_delta_df = block_wallet_deltas[block_wallet_deltas["baseTokenType"] == "BASE"]
                assert len(long_delta_df) == 1
                assert len(base_delta_df) == 1
                long_delta = long_delta_df.iloc[0]
                base_delta = base_delta_df.iloc[0]
                # 22222 base for...
                assert base_delta["delta"] == -Decimal(22222)
                # TODO check long delta
                # TODO check maturity time and tokenType
                # TODO check wallet info matches the deltas
                # TODO check pool info after this tx

                actual_num_longs = long_delta["delta"]

            if txn["input_method"] == "openShort":
                assert txn["input_params_bondAmount"] == Decimal(33333)
                block_wallet_deltas = db_wallet_delta[db_wallet_delta["blockNumber"] == block_number]
                assert len(block_wallet_deltas) == 2
                short_delta_df = block_wallet_deltas[block_wallet_deltas["baseTokenType"] == "SHORT"]
                base_delta_df = block_wallet_deltas[block_wallet_deltas["baseTokenType"] == "BASE"]
                assert len(short_delta_df) == 1
                assert len(base_delta_df) == 1
                short_delta = short_delta_df.iloc[0]
                base_delta = base_delta_df.iloc[0]
                # 33333 bonds for...
                assert short_delta["delta"] == Decimal(33333)
                # TODO check base delta
                # TODO check maturity time and tokenType
                # TODO check wallet info matches the deltas
                # TODO check pool info after this tx

                actual_num_shorts = short_delta["delta"]

            if txn["input_method"] == "removeLiquidity":
                # TODO change this to expected num lp
                assert txn["input_params_shares"] == actual_num_lp
                block_wallet_deltas = db_wallet_delta[db_wallet_delta["blockNumber"] == block_number]
                assert len(block_wallet_deltas) == 3
                lp_delta_df = block_wallet_deltas[block_wallet_deltas["baseTokenType"] == "LP"]
                withdrawal_delta_df = block_wallet_deltas[block_wallet_deltas["baseTokenType"] == "WITHDRAWAL_SHARE"]
                base_delta_df = block_wallet_deltas[block_wallet_deltas["baseTokenType"] == "BASE"]
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
                assert txn["input_params_bondAmount"] == actual_num_longs
                block_wallet_deltas = db_wallet_delta[db_wallet_delta["blockNumber"] == block_number]
                assert len(block_wallet_deltas) == 2
                long_delta_df = block_wallet_deltas[block_wallet_deltas["baseTokenType"] == "LONG"]
                base_delta_df = block_wallet_deltas[block_wallet_deltas["baseTokenType"] == "BASE"]
                assert len(long_delta_df) == 1
                assert len(base_delta_df) == 1
                long_delta = long_delta_df.iloc[0]
                base_delta = base_delta_df.iloc[0]
                # TODO check against expected longs
                assert long_delta["delta"] == -actual_num_longs
                # TODO check base delta
                # TODO check maturity time and tokenType
                # TODO check wallet info matches the deltas
                # TODO check pool info after this tx

            if txn["input_method"] == "closeShort":
                assert txn["input_params_bondAmount"] == Decimal(33333)
                block_wallet_deltas = db_wallet_delta[db_wallet_delta["blockNumber"] == block_number]
                assert len(block_wallet_deltas) == 2
                short_delta_df = block_wallet_deltas[block_wallet_deltas["baseTokenType"] == "SHORT"]
                base_delta_df = block_wallet_deltas[block_wallet_deltas["baseTokenType"] == "BASE"]
                assert len(short_delta_df) == 1
                assert len(base_delta_df) == 1
                short_delta = short_delta_df.iloc[0]
                base_delta = base_delta_df.iloc[0]
                # TODO check against expected shorts
                assert short_delta["delta"] == -actual_num_shorts
                # TODO check base delta
                # TODO check maturity time and tokenType
                # TODO check wallet info matches the deltas
                # TODO check pool info after this tx

            if txn["input_method"] == "redeemWithdrawalShares":
                # TODO change this to expected withdrawal shares
                assert txn["input_params_shares"] == actual_num_withdrawal
                block_wallet_deltas = db_wallet_delta[db_wallet_delta["blockNumber"] == block_number]
                assert len(block_wallet_deltas) == 2
                withdrawal_delta_df = block_wallet_deltas[block_wallet_deltas["baseTokenType"] == "WITHDRAWAL_SHARE"]
                base_delta_df = block_wallet_deltas[block_wallet_deltas["baseTokenType"] == "BASE"]
                assert len(withdrawal_delta_df) == 1
                assert len(base_delta_df) == 1
                withdrawal_delta = withdrawal_delta_df.iloc[0]
                base_delta = base_delta_df.iloc[0]
                # TODO check against expected withdrawal shares
                assert withdrawal_delta["delta"] == -actual_num_withdrawal
                # TODO check base delta
                # TODO check wallet info matches the deltas
                # TODO check pool info after this tx

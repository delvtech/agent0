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
from agent0.test_fixtures import AgentDoneException
from chainsync.db.hyperdrive.interface import get_pool_config, get_pool_info, get_transactions, get_wallet_deltas
from chainsync.exec import acquire_data, data_analysis
from eth_account.signers.local import LocalAccount
from ethpy import EthConfig
from ethpy.hyperdrive import HyperdriveAddresses
from ethpy.test_fixtures.deploy_hyperdrive import _calculateTimeStretch
from fixedpointmath import FixedPoint
from sqlalchemy.orm import Session


def _to_unscaled_decimal(fp_val: FixedPoint) -> Decimal:
    return Decimal(str(fp_val))


class TestBotToDb:
    """Tests pipeline from bots making trades to viewing the trades in the db"""

    # TODO split this up into different functions that work with tests
    # pylint: disable=too-many-locals, too-many-statements
    def test_bot_to_db(
        self,
        local_hyperdrive_chain: dict,
        cycle_trade_policy: Type[BasePolicy],
        db_session: Session,
    ):
        """Runs the entire pipeline and checks the database at the end.
        All arguments are fixtures.
        """
        # Get hyperdrive chain info
        rpc_url: str = local_hyperdrive_chain["rpc_url"]
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
                slippage_tolerance=FixedPoint("0.0001"),
                base_budget_wei=FixedPoint("1_000_000").scaled_value,  # 1 million base
                eth_budget_wei=FixedPoint("100").scaled_value,  # 100 base
                init_kwargs={},
            ),
        ]

        # No need for random seed, this bot is deterministic
        account_key_config = build_account_key_config_from_agent_config(agent_config)

        # Build custom eth config pointing to local test chain
        eth_config = EthConfig(
            # Artifacts_url isn't used here, as we explicitly set addresses and passed to run_bots
            ARTIFACTS_URL="not_used",
            RPC_URL=rpc_url,
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

        # Run acquire data to get data from chain to db
        acquire_data(
            start_block=8,  # First 7 blocks are deploying hyperdrive, ignore
            eth_config=eth_config,
            db_session=db_session,
            contract_addresses=hyperdrive_contract_addresses,
            # Exit the script after catching up to the chain
            exit_on_catch_up=True,
        )

        # Run data analysis to calculate various analysis values
        data_analysis(
            start_block=8,  # First 7 blocks are deploying hyperdrive, ignore
            db_session=db_session,
            # Exit the script after catching up to the chain
            exit_on_catch_up=True,
        )

        # Run bots again, but this time only for 4 trades

        # Build agent config
        agent_config: list[AgentConfig] = [
            AgentConfig(
                policy=cycle_trade_policy,
                number_of_agents=1,
                slippage_tolerance=FixedPoint("0.0001"),
                base_budget_wei=FixedPoint("1_000_000").scaled_value,  # 1 million base
                eth_budget_wei=FixedPoint("100").scaled_value,  # 100 base
                init_kwargs={"max_trades": 4},
            ),
        ]

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

        # Run acquire data to get data from chain to db
        acquire_data(
            start_block=8,  # First 7 blocks are deploying hyperdrive, ignore
            eth_config=eth_config,
            db_session=db_session,
            contract_addresses=hyperdrive_contract_addresses,
            # Exit the script after catching up to the chain
            exit_on_catch_up=True,
        )

        # Run data analysis to calculate various analysis values
        data_analysis(
            start_block=8,  # First 7 blocks are deploying hyperdrive, ignore
            db_session=db_session,
            # Exit the script after catching up to the chain
            exit_on_catch_up=True,
        )

        # This bot does the following known trades in sequence:
        # 1. addLiquidity of 11111 base
        # 2. openLong of 22222 base
        # 3. openShort of 33333 bonds
        # 4. removeLiquidity of all LP tokens
        # 5. closeLong on long from trade 2
        # 6. closeShort on short from trade 3
        # 7. redeemWithdrawalShares of all withdrawal tokens from trade 4
        # 8. openLong for 1 base
        # The bot then runs again, this time for 4 trades:
        # 9. addLiquidity of 11111 base
        # 10. openLong of 22222 base
        # 11. openShort of 33333 bonds
        # 12. removeLiquidity of all LP tokens
        # The last trade here won't show up in the database, due to data lag of one block

        # Test db entries are what we expect
        # We don't coerce to float because we want exact values in decimal
        db_pool_config_df: pd.DataFrame = get_pool_config(db_session, coerce_float=False)

        # TODO these expected values are defined in lib/ethpy/ethpy/test_fixtures/deploy_hyperdrive.py
        # Eventually, we want to parameterize these values to pass into deploying hyperdrive
        expected_timestretch_fp = FixedPoint(scaled_value=_calculateTimeStretch(FixedPoint("0.05").scaled_value))
        # TODO this is actually inv of solidity time stretch, fix
        expected_timestretch = _to_unscaled_decimal((1 / expected_timestretch_fp))
        expected_inv_timestretch = _to_unscaled_decimal(expected_timestretch_fp)

        expected_pool_config = {
            "contractAddress": hyperdrive_contract_addresses.mock_hyperdrive,
            "baseToken": hyperdrive_contract_addresses.base_token,
            "initialSharePrice": _to_unscaled_decimal(FixedPoint("1")),
            "minimumShareReserves": _to_unscaled_decimal(FixedPoint("10")),
            "positionDuration": 604800,  # 1 week
            "checkpointDuration": 3600,  # 1 hour
            # TODO this is actually inv of solidity time stretch, fix
            "timeStretch": expected_timestretch,
            "governance": deploy_account.address,
            "feeCollector": deploy_account.address,
            "curveFee": _to_unscaled_decimal(FixedPoint("0.1")),  # 10%
            "flatFee": _to_unscaled_decimal(FixedPoint("0.0005")),  # 0.05%
            "governanceFee": _to_unscaled_decimal(FixedPoint("0.15")),  # 15%
            "oracleSize": 10,
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
        # Should be 11 total transactions
        assert len(db_transaction_info) == 11
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
                "openLong",
                "addLiquidity",
                "openLong",
                "openShort",
            ],
        )

        # 11 total trades in wallet deltas
        assert db_wallet_delta["blockNumber"].nunique() == 11
        # 23 different wallet deltas (2 token deltas per trade except for withdraw shares, which is 3)
        assert len(db_wallet_delta) == 23

        actual_num_longs = Decimal("nan")
        actual_num_shorts = Decimal("nan")
        actual_num_lp = Decimal("nan")
        actual_num_withdrawal = Decimal("nan")
        # Go through each trade and ensure wallet deltas are correct
        # The asserts here are equality because they are either int -> Decimal, which is lossless,
        # or they're comparing values after the lossy conversion
        for block_number, txn in db_transaction_info.iterrows():
            # TODO differentiate between the first and second addLiquidity
            if txn["input_method"] == "addLiquidity":
                assert txn["input_params_contribution"] == Decimal(11111)
                # Filter for all deltas of this trade
                block_wallet_deltas = db_wallet_delta[db_wallet_delta["blockNumber"] == block_number]
                # Ensure number of token deltas
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

            # TODO differentiate between the first, second, and third openLong
            if txn["input_method"] == "openLong":
                # First and third openLong, TODO differentiate between the two
                if txn["input_params_baseAmount"] == Decimal(22222):
                    expected_base = Decimal(22222)
                # Second openLong
                elif txn["input_params_baseAmount"] == Decimal(1):
                    expected_base = Decimal(1)
                else:
                    assert False

                # Filter for all deltas of this trade
                block_wallet_deltas = db_wallet_delta[db_wallet_delta["blockNumber"] == block_number]
                # Ensure number of token deltas
                assert len(block_wallet_deltas) == 2
                long_delta_df = block_wallet_deltas[block_wallet_deltas["baseTokenType"] == "LONG"]
                base_delta_df = block_wallet_deltas[block_wallet_deltas["baseTokenType"] == "BASE"]
                assert len(long_delta_df) == 1
                assert len(base_delta_df) == 1
                long_delta = long_delta_df.iloc[0]
                base_delta = base_delta_df.iloc[0]
                # 22222 base for...
                assert base_delta["delta"] == -expected_base
                # TODO check long delta
                # TODO check maturity time and tokenType
                # TODO check current wallet matches the deltas
                # TODO check pool info after this tx

                actual_num_longs = long_delta["delta"]

            # TODO differentiate between the first and second openShort
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

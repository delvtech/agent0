"""System test for end to end testing of elf-simulations"""
import logging
from decimal import Decimal
from typing import Type

import pandas as pd
from agent0 import build_account_key_config_from_agent_config
from agent0.base.config import AgentConfig, EnvironmentConfig
from agent0.base.policies import BasePolicy
from agent0.hyperdrive.exec import run_agents
from chainsync.db.hyperdrive.interface import get_pool_config
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
                base_budget_wei=int(10_000e18),  # 10k base
                eth_budget_wei=int(10e18),  # 10 base
                init_kwargs={"static_trade_amount_wei": int(100e18)},  # 100 base static trades
            ),
        ]

        # No need for random seed, this bot is deterministic
        account_key_config = build_account_key_config_from_agent_config(agent_config)

        # Build custom eth config pointing to local chain
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

        expected_values = {
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
        expected_keys = set(expected_values.keys())
        assert db_keys == expected_keys, "Keys in db do not match expected"

        # Value comparison
        for key, expected_value in expected_values.items():
            # TODO In testing, we use sqlite, which does not implement the fixed point Numeric type
            # Internally, they store Numeric types as floats, hence we see rounding errors in testing
            # This does not happen in postgres, where these values match exactly.
            # https://github.com/delvtech/elf-simulations/issues/836

            if isinstance(expected_value, Decimal):
                assert_val = abs(db_pool_config[key] - expected_value) < 1e-12
            else:
                assert_val = db_pool_config[key] == expected_value

            assert assert_val, f"Values do not match for {key} ({db_pool_config[key]} != {expected_value})"

        # Ensure all trades are in the db

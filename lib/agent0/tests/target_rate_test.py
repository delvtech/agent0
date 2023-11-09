"""Test the ability of bots to hit a target rate."""
from __future__ import annotations

import logging
import os
import warnings
from decimal import Decimal
from typing import cast

import pandas as pd
import pytest
from agent0 import build_account_key_config_from_agent_config
from agent0.base.config import AgentConfig, EnvironmentConfig
from agent0.hyperdrive.exec import run_agents
from agent0.hyperdrive.policies.zoo import Zoo
from chainsync.db.hyperdrive.interface import get_pool_analysis, get_pool_info
from chainsync.exec import acquire_data, data_analysis
from eth_typing import URI
from ethpy import EthConfig
from ethpy.hyperdrive.addresses import HyperdriveAddresses
from ethpy.test_fixtures.local_chain import DeployedHyperdrivePool
from fixedpointmath import FixedPoint
from sqlalchemy.orm import Session
from web3 import HTTPProvider

# To suppress only the MismatchedABI warnings
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("web3").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)
logging.getLogger("PIL").setLevel(logging.WARNING)
logging.getLogger("matplotlib").setLevel(logging.WARNING)
logging.getLogger().setLevel(logging.DEBUG)


@pytest.mark.parametrize("delta", [-1e5, 1e5])
def test_hit_target_rate(local_hyperdrive_pool: DeployedHyperdrivePool, db_session: Session, db_api: str, delta: float):
    """Ensure bot can hit target rate."""
    warnings.filterwarnings("ignore", category=UserWarning, module="web3.contract.base_contract")
    # Run this test with develop mode on
    os.environ["DEVELOP"] = "true"
    # Get hyperdrive chain info
    uri: URI | None = cast(HTTPProvider, local_hyperdrive_pool.web3.provider).endpoint_uri
    rpc_uri = uri if uri else URI("http://localhost:8545")
    hyperdrive_contract_addresses: HyperdriveAddresses = local_hyperdrive_pool.hyperdrive_contract_addresses

    # Build environment config
    env_config = EnvironmentConfig(
        delete_previous_logs=False,
        halt_on_errors=True,
        log_filename="target_rate_test",
        log_level=logging.DEBUG,
        log_stdout=True,
        random_seed=1234,
        username="test",
    )

    # Build custom eth config pointing to local test chain
    eth_config = EthConfig(
        # Artifacts_uri isn't used here, as we explicitly set addresses and passed to run_bots
        artifacts_uri="not_used",
        database_api_uri=db_api,
        rpc_uri=rpc_uri,
        # Using default abi dir
    )

    if delta > 0:
        trade_tuple = ("open_short", int(delta))
    else:
        trade_tuple = ("open_long", int(-delta))
    # One deterministic bot to increase the fixed rate
    agent_config: list[AgentConfig] = [
        AgentConfig(
            policy=Zoo.deterministic,
            number_of_agents=1,
            base_budget_wei=FixedPoint("1_000_000").scaled_value,  # 1 million base
            eth_budget_wei=FixedPoint("100").scaled_value,  # 100 base
            policy_config=Zoo.deterministic.Config(trade_list=[trade_tuple]),
        ),
    ]
    run_agents(
        env_config,
        agent_config,
        account_key_config=build_account_key_config_from_agent_config(agent_config, random_seed=1),
        eth_config=eth_config,
        contract_addresses=hyperdrive_contract_addresses,
    )

    # One deterministic bot to hit the variable rate
    agent_config: list[AgentConfig] = [
        AgentConfig(
            policy=Zoo.lp_and_arb,
            number_of_agents=1,
            base_budget_wei=FixedPoint("10_000_000").scaled_value,  # 10 million base
            eth_budget_wei=FixedPoint("100").scaled_value,  # 100 base
            policy_config=Zoo.lp_and_arb.Config(
                lp_portion=FixedPoint("0"),  # don't LP, just arb
                done_on_empty=True,  # exit the bot if there are no trades
                high_fixed_rate_thresh=FixedPoint(1e-6),
                low_fixed_rate_thresh=FixedPoint(1e-6),
            ),
        ),
    ]
    run_agents(
        env_config,
        agent_config,
        account_key_config=build_account_key_config_from_agent_config(agent_config, random_seed=2),
        eth_config=eth_config,
        contract_addresses=hyperdrive_contract_addresses,
    )

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
        eth_config=eth_config,
        db_session=db_session,
        contract_addresses=hyperdrive_contract_addresses,
        # Exit the script after catching up to the chain
        exit_on_catch_up=True,
    )

    # Get pool config and pool info from the db, in exact decimal values.
    db_pool_info: pd.DataFrame = get_pool_info(db_session, coerce_float=False)
    db_analysis: pd.DataFrame = get_pool_analysis(db_session, coerce_float=False)
    logging.log(10, "fixed rate is %s", db_analysis["fixed_rate"].iloc[-1])
    logging.log(10, "variable rate is %s", db_pool_info["variable_rate"].iloc[-1])
    abs_diff = abs(db_analysis["fixed_rate"].iloc[-1] - db_pool_info["variable_rate"].iloc[-1])
    logging.log(10, "difference is %s", abs_diff)
    assert abs_diff < Decimal(1e-6)

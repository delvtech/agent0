"""Test the hyperdrive interface."""
from typing import cast

from chainsync.analysis import calc_fixed_rate, calc_spot_price
from eth_typing import URI
from ethpy import EthConfig
from ethpy.hyperdrive.api import HyperdriveInterface
from ethpy.test_fixtures.local_chain import DeployedHyperdrivePool
from fixedpointmath import FixedPoint
from web3 import HTTPProvider

# need lots of lcoals
# pylint: disable=too-many-locals


def test_pool_info(local_hyperdrive_pool: DeployedHyperdrivePool):
    """Test the hyperdrive interface versus expected values."""
    uri = cast(HTTPProvider, local_hyperdrive_pool.web3.provider).endpoint_uri
    rpc_uri = uri or URI("http://localhost:8545")
    deploy_account = local_hyperdrive_pool.deploy_account
    hyperdrive_contract_addresses = local_hyperdrive_pool.hyperdrive_contract_addresses
    interface = HyperdriveInterface(
        eth_config=EthConfig(artifacts_uri="not used", rpc_uri=rpc_uri), addresses=hyperdrive_contract_addresses
    )

    initial_fixed_rate = FixedPoint("0.05")
    expected_timestretch_fp = FixedPoint(1) / (
        FixedPoint("5.24592") / (FixedPoint("0.04665") * (initial_fixed_rate * FixedPoint(100)))
    )

    expected_pool_config = {
        "contractAddress": hyperdrive_contract_addresses.mock_hyperdrive,
        "baseToken": hyperdrive_contract_addresses.base_token,
        "initialSharePrice": FixedPoint("1"),
        "minimumShareReserves": FixedPoint("10"),
        "minimumTransactionAmount": FixedPoint("0.001"),
        "positionDuration": 604800,  # 1 week
        "checkpointDuration": 3600,  # 1 hour
        "timeStretch": expected_timestretch_fp,
        "governance": deploy_account.address,
        "feeCollector": deploy_account.address,
        "curveFee": FixedPoint("0.1"),  # 10,
        "flatFee": FixedPoint("0.0005"),  # 0.0%
        "governanceFee": FixedPoint("0.15"),  # 1%
        "oracleSize": 10,
        "updateGap": 3600,  # TODO don't know where this is getting set
        "invTimeStretch": (1 / expected_timestretch_fp),
    }
    expected_pool_config["fees"] = [
        expected_pool_config["curveFee"],
        expected_pool_config["flatFee"],
        expected_pool_config["governanceFee"],
    ]

    api_pool_config = interface.pool_config

    # Existence test
    assert len(api_pool_config) > 0, "API pool config must have length greater than 0"

    # Ensure keys match
    # Converting to sets and compare
    api_keys = set(api_pool_config.keys())
    expected_keys = set(expected_pool_config.keys())
    assert api_keys == expected_keys, "Keys in API do not match expected"

    # Value comparison
    for key, expected_value in expected_pool_config.items():
        print(f"{expected_value=}")
        print(f"{api_pool_config[key]=}")
        assert_val = api_pool_config[key] == expected_value
        assert assert_val, f"Values do not match for {key} ({api_pool_config[key]} != {expected_value})"

    # Pool info comparison
    api_pool_info = interface.pool_info
    expected_pool_info_keys = [
        # Keys from contract call
        "blockNumber",
        "shareReserves",
        "bondReserves",
        "lpTotalSupply",
        "sharePrice",
        "shareAdjustment",
        "lpSharePrice",
        "longExposure",
        "longsOutstanding",
        "longAverageMaturityTime",
        "shortsOutstanding",
        "shortAverageMaturityTime",
        "withdrawalSharesReadyToWithdraw",
        "withdrawalSharesProceeds",
        # Added keys
        "timestamp",
        # Calculated keys
        "totalSupplyWithdrawalShares",
    ]
    # Convert to sets and compare
    assert set(api_pool_info.keys()) == set(expected_pool_info_keys)

    # Check spot price and fixed rate
    api_spot_price = interface.spot_price
    expected_spot_price = calc_spot_price(
        share_reserves=api_pool_info["shareReserves"],
        share_adjustment=api_pool_info["shareAdjustment"],
        bond_reserves=api_pool_info["bondReserves"],
        initial_share_price=api_pool_config["initialSharePrice"],
        time_stretch=api_pool_config["timeStretch"],
    )

    api_fixed_rate = interface.fixed_rate
    expected_fixed_rate = calc_fixed_rate(expected_spot_price,api_pool_config["positionDuration"])

    # TODO there's rounding errors between api spot price and fixed rates
    print(f"{abs(api_spot_price - expected_spot_price)=}")
    print(f"{abs(api_fixed_rate - expected_fixed_rate)=}")
    assert abs(api_spot_price - expected_spot_price) <= FixedPoint(1e-16)
    assert abs(api_fixed_rate - expected_fixed_rate) <= FixedPoint(1e-16)

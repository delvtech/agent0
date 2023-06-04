"""
This function is a demo for executing an arbitrary number of trades from a pair of
smart bots that track the fixed/variable rates using longs & shorts. It is meant to be
a temporary demonstration, and will be gradually replaced with utilities in elfpy src.
As such, we are relaxing some of the lint rules.
"""
from __future__ import annotations

# external lib
import ape
from ape.contracts import ContractInstance
from eth_typing import HexAddress

# elfpy core repo
import elfpy.markets.hyperdrive.hyperdrive_assets as hyperdrive_assets
import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market
from elfpy.math.fixed_point import FixedPoint
from tests.cross_platform.fixtures.hyperdrive_config import HyperdriveConfig


def to_fixed_point(float_var: float, decimal_places=18):
    """Convert floating point argument to fixed point with desired number of decimals"""
    return int(float_var * 10**decimal_places)


def to_floating_point(int_var: int, decimal_places=18):
    """Convert fixed point argument to floating point with specified number of decimals"""
    return float(int_var / 10**decimal_places)


def get_simulation_market_state_from_contract(
    hyperdrive_data_contract: ContractInstance,
    agent_address: HexAddress,
    position_duration_seconds: FixedPoint,
    checkpoint_duration_days: FixedPoint,
    variable_apr: FixedPoint,
    config: HyperdriveConfig,
) -> hyperdrive_market.HyperdriveMarketState:
    """
    hyperdrive_contract: ape.contracts.base.ContractInstance
        Ape project `ContractInstance
        <https://docs.apeworx.io/ape/stable/methoddocs/contracts.html#ape.contracts.base.ContractInstance>`_
        wrapped around the initialized MockHyperdriveTestnet smart contract.
    agent_address: ape.api.accounts.AccountAPI
        Ape address container, or `AccountAPI
        <https://docs.apeworx.io/ape/stable/methoddocs/api.html#ape.api.accounts.AccountAPI>`_
        representing the agent which is executing the action.
    """
    # pylint: disable=too-many-arguments
    pool_config = hyperdrive_data_contract.getPoolConfig()
    print(f"{pool_config=}")
    pool_info = hyperdrive_data_contract.getPoolInfo()
    print(f"{pool_info=}")
    pool_state = pool_info
    with ape.accounts.use_sender(agent_address):  # sender for contract calls
        asset_id = hyperdrive_assets.encode_asset_id(
            hyperdrive_assets.AssetIdPrefix.WITHDRAWAL_SHARE,
            int(position_duration_seconds),
        )
        total_supply_withdraw_shares = hyperdrive_data_contract.balanceOf(asset_id, agent_address)

    return hyperdrive_market.HyperdriveMarketState(
        lp_total_supply=FixedPoint(scaled_value=pool_state["lpTotalSupply"]),
        share_reserves=FixedPoint(scaled_value=pool_state["shareReserves"]),
        bond_reserves=FixedPoint(scaled_value=pool_state["bondReserves"]),
        base_buffer=FixedPoint(scaled_value=pool_state["longsOutstanding"]),  # so do we not need any buffers now?
        # TODO: bond_buffer=0,
        variable_apr=variable_apr,
        share_price=FixedPoint(scaled_value=pool_state["sharePrice"]),
        init_share_price=config.share_price,
        curve_fee_multiple=config.curve_fee,
        flat_fee_multiple=config.flat_fee,
        longs_outstanding=FixedPoint(scaled_value=pool_state["longsOutstanding"]),
        shorts_outstanding=FixedPoint(scaled_value=pool_state["shortsOutstanding"]),
        long_average_maturity_time=FixedPoint(scaled_value=pool_state["longAverageMaturityTime"]),
        short_average_maturity_time=FixedPoint(scaled_value=pool_state["shortAverageMaturityTime"]),
        long_base_volume=FixedPoint(0),  # FixedPoint(scaled_value=pool_state["longBaseVolume"]),
        short_base_volume=FixedPoint(scaled_value=pool_state["shortBaseVolume"]),
        # TODO: checkpoints=defaultdict
        checkpoint_duration=checkpoint_duration_days,
        total_supply_longs={FixedPoint(0): FixedPoint(scaled_value=pool_state["longsOutstanding"])},
        total_supply_shorts={FixedPoint(0): FixedPoint(scaled_value=pool_state["shortsOutstanding"])},
        total_supply_withdraw_shares=FixedPoint(scaled_value=total_supply_withdraw_shares),
        withdraw_shares_ready_to_withdraw=FixedPoint(scaled_value=pool_state["withdrawalSharesReadyToWithdraw"]),
        withdraw_capital=FixedPoint(scaled_value=pool_state["withdrawalSharesProceeds"]),
        withdraw_interest=FixedPoint(0),  # FixedPoint(scaled_value=pool_state["interest"]),
    )

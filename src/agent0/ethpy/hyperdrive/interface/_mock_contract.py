"""Mock function calls using hyperdrivepy."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import hyperdrivepy
from fixedpointmath import FixedPoint
from web3.types import Timestamp

from agent0.hypertypes.utilities.conversions import fixedpoint_to_pool_config, fixedpoint_to_pool_info

if TYPE_CHECKING:
    from agent0.ethpy.hyperdrive.state import PoolState

# We only worry about protected access for users outside of this folder
# pylint: disable=protected-access


def _calc_checkpoint_id(checkpoint_duration: int, block_timestamp: Timestamp) -> Timestamp:
    """See API for documentation."""
    latest_checkpoint_timestamp = block_timestamp - (block_timestamp % checkpoint_duration)
    return cast(Timestamp, latest_checkpoint_timestamp)


def _calc_position_duration_in_years(pool_state: PoolState) -> FixedPoint:
    """See API for documentation."""
    return FixedPoint(pool_state.pool_config.position_duration) / FixedPoint(60 * 60 * 24 * 365)


def _calc_fixed_rate(pool_state: PoolState) -> FixedPoint:
    """See API for documentation."""
    spot_rate = hyperdrivepy.get_spot_rate(
        fixedpoint_to_pool_config(pool_state.pool_config),
        fixedpoint_to_pool_info(pool_state.pool_info),
    )
    return FixedPoint(scaled_value=int(spot_rate))


def _calc_effective_share_reserves(pool_state: PoolState) -> FixedPoint:
    """See API for documentation."""
    effective_share_reserves = hyperdrivepy.get_effective_share_reserves(
        str(pool_state.pool_info.share_reserves.scaled_value),
        str(pool_state.pool_info.share_adjustment.scaled_value),
    )
    return FixedPoint(scaled_value=int(effective_share_reserves))


def _calc_spot_price(pool_state: PoolState):
    """See API for documentation."""
    spot_price = hyperdrivepy.get_spot_price(
        fixedpoint_to_pool_config(pool_state.pool_config),
        fixedpoint_to_pool_info(pool_state.pool_info),
    )
    return FixedPoint(scaled_value=int(spot_price))


def _calc_open_long(pool_state: PoolState, base_amount: FixedPoint) -> FixedPoint:
    """See API for documentation."""
    long_amount = hyperdrivepy.calculate_open_long(
        fixedpoint_to_pool_config(pool_state.pool_config),
        fixedpoint_to_pool_info(pool_state.pool_info),
        str(base_amount.scaled_value),
    )
    return FixedPoint(scaled_value=int(long_amount))


def _calc_close_long(
    pool_state: PoolState, bond_amount: FixedPoint, normalized_time_remaining: FixedPoint
) -> FixedPoint:
    """See API for documentation."""
    long_returns = hyperdrivepy.calculate_close_long(
        fixedpoint_to_pool_config(pool_state.pool_config),
        fixedpoint_to_pool_info(pool_state.pool_info),
        str(bond_amount.scaled_value),
        str(normalized_time_remaining.scaled_value),
    )
    return FixedPoint(scaled_value=int(long_returns))


def _calc_open_short(
    pool_state: PoolState,
    short_amount: FixedPoint,
    spot_price: FixedPoint,
    open_vault_share_price: FixedPoint | None = None,
) -> FixedPoint:
    """See API for documentation."""
    open_vault_share_price_str: str | None
    if open_vault_share_price is None:  # keep it None
        open_vault_share_price_str = None
    else:  # convert FixedPoint to string
        open_vault_share_price_str = str(open_vault_share_price.scaled_value)
    short_deposit = hyperdrivepy.calculate_open_short(
        fixedpoint_to_pool_config(pool_state.pool_config),
        fixedpoint_to_pool_info(pool_state.pool_info),
        str(short_amount.scaled_value),
        str(spot_price.scaled_value),
        open_vault_share_price_str,  # str | None
    )
    return FixedPoint(scaled_value=int(short_deposit))


def _calc_close_short(
    pool_state: PoolState,
    bond_amount: FixedPoint,
    open_vault_share_price: FixedPoint,
    close_vault_share_price: FixedPoint,
    normalized_time_remaining: FixedPoint,
) -> FixedPoint:
    """See API for documentation."""
    short_returns = hyperdrivepy.calculate_close_short(
        fixedpoint_to_pool_config(pool_state.pool_config),
        fixedpoint_to_pool_info(pool_state.pool_info),
        str(bond_amount.scaled_value),
        str(open_vault_share_price.scaled_value),
        str(close_vault_share_price.scaled_value),
        str(normalized_time_remaining.scaled_value),
    )
    return FixedPoint(scaled_value=int(short_returns))


def _calc_bonds_out_given_shares_in_down(
    pool_state: PoolState,
    amount_in: FixedPoint,
) -> FixedPoint:
    """See API for documentation."""
    amount_out = hyperdrivepy.calculate_bonds_out_given_shares_in_down(
        fixedpoint_to_pool_config(pool_state.pool_config),
        fixedpoint_to_pool_info(pool_state.pool_info),
        str(amount_in.scaled_value),
    )
    return FixedPoint(scaled_value=int(amount_out))


def _calc_shares_in_given_bonds_out_up(
    pool_state: PoolState,
    amount_in: FixedPoint,
) -> FixedPoint:
    """See API for documentation."""
    amount_out = hyperdrivepy.calculate_shares_in_given_bonds_out_up(
        fixedpoint_to_pool_config(pool_state.pool_config),
        fixedpoint_to_pool_info(pool_state.pool_info),
        str(amount_in.scaled_value),
    )

    return FixedPoint(scaled_value=int(amount_out))


def _calc_shares_in_given_bonds_out_down(
    pool_state: PoolState,
    amount_in: FixedPoint,
) -> FixedPoint:
    """See API for documentation."""
    amount_out = hyperdrivepy.calculate_shares_in_given_bonds_out_down(
        fixedpoint_to_pool_config(pool_state.pool_config),
        fixedpoint_to_pool_info(pool_state.pool_info),
        str(amount_in.scaled_value),
    )
    return FixedPoint(scaled_value=int(amount_out))


def _calc_shares_out_given_bonds_in_down(
    pool_state: PoolState,
    amount_in: FixedPoint,
) -> FixedPoint:
    """See API for documentation."""
    amount_out = hyperdrivepy.calculate_shares_out_given_bonds_in_down(
        fixedpoint_to_pool_config(pool_state.pool_config),
        fixedpoint_to_pool_info(pool_state.pool_info),
        str(amount_in.scaled_value),
    )
    return FixedPoint(scaled_value=int(amount_out))


def _calc_fees_out_given_bonds_in(
    pool_state: PoolState, bonds_in: FixedPoint, maturity_time: int | None = None
) -> tuple[FixedPoint, FixedPoint, FixedPoint]:
    """See API for documentation.

    ..todo::
        This should be done in the hyperdrive sdk.
    """
    if maturity_time is None:
        maturity_time = pool_state.block_time + int(pool_state.pool_config.position_duration)
    time_remaining_in_seconds = FixedPoint(maturity_time - pool_state.block_time)
    normalized_time_remaining = time_remaining_in_seconds / pool_state.pool_config.position_duration
    curve_fee = (
        (FixedPoint(1) - _calc_spot_price(pool_state))
        * pool_state.pool_config.fees.curve
        * bonds_in
        * normalized_time_remaining
    ) / pool_state.pool_config.initial_vault_share_price
    flat_fee = (
        bonds_in * (FixedPoint(1) - normalized_time_remaining) * pool_state.pool_config.fees.flat
    ) / pool_state.pool_config.initial_vault_share_price
    gov_fee = (
        curve_fee * pool_state.pool_config.fees.governance_lp + flat_fee * pool_state.pool_config.fees.governance_lp
    )
    return curve_fee, flat_fee, gov_fee


def _calc_fees_out_given_shares_in(
    pool_state: PoolState, shares_in: FixedPoint, maturity_time: int | None = None
) -> tuple[FixedPoint, FixedPoint, FixedPoint]:
    """See API for documentation.

    ..todo::
        This should be done in the hyperdrive sdk.
    """
    if maturity_time is None:
        maturity_time = pool_state.block_time + int(pool_state.pool_config.position_duration)
    time_remaining_in_seconds = FixedPoint(maturity_time - pool_state.block_time)
    normalized_time_remaining = time_remaining_in_seconds / pool_state.pool_config.position_duration
    curve_fee = (
        ((FixedPoint(1) / _calc_spot_price(pool_state)) - FixedPoint(1))
        * pool_state.pool_config.fees.curve
        * pool_state.pool_config.initial_vault_share_price
        * shares_in
    )
    flat_fee = (
        shares_in * (FixedPoint(1) - normalized_time_remaining) * pool_state.pool_config.fees.flat
    ) / pool_state.pool_config.initial_vault_share_price
    gov_fee = (
        curve_fee * pool_state.pool_config.fees.governance_lp + flat_fee * pool_state.pool_config.fees.governance_lp
    )
    return curve_fee, flat_fee, gov_fee


def _calc_bonds_given_shares_and_rate(
    pool_state: PoolState,
    target_rate: FixedPoint,
    target_shares: FixedPoint | None = None,
) -> FixedPoint:
    """See API for documentation."""
    if target_shares is None:
        target_shares = _calc_effective_share_reserves(pool_state)
    return FixedPoint(
        scaled_value=int(
            hyperdrivepy.calculate_initial_bond_reserves(
                str(target_shares.scaled_value),
                str(pool_state.pool_config.initial_vault_share_price.scaled_value),
                str(target_rate.scaled_value),
                str(pool_state.pool_config.position_duration),
                str(pool_state.pool_config.time_stretch.scaled_value),
            )
        )
    )


def _calc_max_long(pool_state: PoolState, budget: FixedPoint) -> FixedPoint:
    """See API for documentation."""
    return FixedPoint(
        scaled_value=int(
            hyperdrivepy.get_max_long(
                fixedpoint_to_pool_config(pool_state.pool_config),
                fixedpoint_to_pool_info(pool_state.pool_info),
                str(budget.scaled_value),
                checkpoint_exposure=str(pool_state.exposure.scaled_value),
                maybe_max_iterations=None,
            )
        )
    )


def _calc_max_short(pool_state: PoolState, budget: FixedPoint) -> FixedPoint:
    """See API for documentation."""
    return FixedPoint(
        scaled_value=int(
            hyperdrivepy.get_max_short(
                pool_config=fixedpoint_to_pool_config(pool_state.pool_config),
                pool_info=fixedpoint_to_pool_info(pool_state.pool_info),
                budget=str(budget.scaled_value),
                open_vault_share_price=str(pool_state.pool_info.vault_share_price.scaled_value),
                checkpoint_exposure=str(pool_state.exposure.scaled_value),
                maybe_conservative_price=None,
                maybe_max_iterations=None,
            )
        )
    )


def _calc_present_value(pool_state: PoolState, current_block_timestamp: int) -> FixedPoint:
    """See API for documentation."""
    return FixedPoint(
        scaled_value=int(
            hyperdrivepy.calculate_present_value(
                pool_config=fixedpoint_to_pool_config(pool_state.pool_config),
                pool_info=fixedpoint_to_pool_info(pool_state.pool_info),
                current_block_timestamp=str(current_block_timestamp),
            )
        )
    )


def _calc_time_stretch(target_rate: FixedPoint, target_position_duration: FixedPoint) -> FixedPoint:
    """See API for documentation."""
    return FixedPoint(
        scaled_value=int(
            hyperdrivepy.get_time_stretch(str(target_rate.scaled_value), str(int(target_position_duration)))
        )
    )

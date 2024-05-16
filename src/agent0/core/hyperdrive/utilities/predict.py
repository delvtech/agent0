"""Predict the outcome of trades.

A trade results in changes to 4 entities, measured in 3 units.
    accounts: pool, user, fee, governance
    units: base, bonds, shares (base and shares refer to the same account)
Applications where this is useful:
    LP and Arb bot uses this logic to hit a target rate.
    Trade by specifying the output units (base for open long, bonds otherwise).

For example:
    +------------+--------------+---------------+--------------+
    | Entity     |         Base |         Bonds |       Shares |
    +============+==============+===============+==============+
    | user       | 100          |  104.95       | 100          |
    +------------+--------------+---------------+--------------+
    | pool       |  99.9952     | -104.955      |  99.9952     |
    +------------+--------------+---------------+--------------+
    | fee        |   0.0428367  |    0.0449786  |   0.0428367  |
    +------------+--------------+---------------+--------------+
    | governance |   0.00475964 |    0.00499762 |   0.00475964 |
    +------------+--------------+---------------+--------------+
"""

from __future__ import annotations

from copy import deepcopy
from typing import NamedTuple

from fixedpointmath import FixedPoint

from agent0.ethpy.hyperdrive.interface.read_interface import HyperdriveReadInterface
from agent0.ethpy.hyperdrive.state import PoolState

# need to cover a wide variety of cases
# pylint: disable=too-many-arguments
# being very explicit
# pylint: disable=too-many-locals

YEAR_IN_SECONDS = 31_536_000
YEAR_IN_BLOCKS = YEAR_IN_SECONDS / 12

Deltas = NamedTuple(
    "Deltas",
    [
        ("base", FixedPoint),
        ("bonds", FixedPoint),
        ("shares", FixedPoint),
    ],
)
TradeDeltas = NamedTuple(
    "TradeDeltas",
    [
        ("user", Deltas),
        ("pool", Deltas),
        ("fee", Deltas),
        ("governance", Deltas),
    ],
)


def _get_vars(hyperdrive_interface, pool_state):
    if pool_state is None:
        pool_state = deepcopy(hyperdrive_interface.current_pool_state)
    spot_price = hyperdrive_interface.calc_spot_price(pool_state)
    price_discount = FixedPoint(1) - spot_price
    curve_fee = pool_state.pool_config.fees.curve
    governance_fee = pool_state.pool_config.fees.governance_lp
    share_price = hyperdrive_interface.current_pool_state.pool_info.vault_share_price
    return pool_state, spot_price, price_discount, curve_fee, governance_fee, share_price


def predict_long(
    hyperdrive_interface: HyperdriveReadInterface,
    pool_state: PoolState | None = None,
    base: FixedPoint | None = None,
    bonds: FixedPoint | None = None,
    for_pool: bool = False,
) -> TradeDeltas:
    """Predict the outcome of a long trade.

    Arguments
    ---------
    hyperdrive_interface: HyperdriveReadInterface
        Hyperdrive interface.
    pool_state: PoolState, optional
        The state of the pool, which includes block details, pool config, and pool info.
        If not given, use the current pool state.
    base: FixedPoint, optional
        The size of the long to open, in base. If not given, converted from bonds.
    bonds: FixedPoint, optional
        The size of the long to open, in bonds.
    for_pool: bool
        Whether the base or bonds specified is for the pool.

    Returns
    -------
    TradeDeltas
        The predicted deltas of base, bonds, and shares.

    """
    pool_state, spot_price, price_discount, curve_fee, governance_fee, share_price = _get_vars(
        hyperdrive_interface, pool_state
    )
    if base is not None and bonds is None:
        if for_pool is False:
            base_needed = base
        else:
            # scale up input to account for fees
            base_needed = base / (FixedPoint(1) - price_discount * governance_fee)
    elif bonds is not None and base is None:
        # we need to calculate base_needed
        bonds_needed = bonds
        shares_needed = hyperdrive_interface.calc_shares_in_given_bonds_out_up(bonds_needed)
        # scale down output to account for fees
        if for_pool is False:
            shares_needed /= FixedPoint(1) - price_discount * curve_fee
        else:
            shares_needed /= FixedPoint(1) - price_discount * curve_fee * governance_fee
        share_price_on_next_block = share_price * (
            FixedPoint(1) + hyperdrive_interface.get_variable_rate(pool_state.block_number) / FixedPoint(YEAR_IN_BLOCKS)
        )
        base_needed = shares_needed * share_price_on_next_block
    else:
        raise ValueError("Need to specify either bonds or base, but not both.")
    # continue with common logic, now that we have base_needed
    assert base_needed is not None
    bonds_after_fees = hyperdrive_interface.calc_open_long(base_needed)
    bond_fees = bonds_after_fees * price_discount * curve_fee
    bond_fees_to_pool = bond_fees * (FixedPoint(1) - governance_fee)
    bond_fees_to_gov = bond_fees * governance_fee
    predicted_delta_bonds = -bonds_after_fees - bond_fees_to_gov
    # gov_scaling factor is the ratio by which we lower the change in base and increase the change in shares
    # this is done to take into account the effect of the governance fee on pool reserves
    gov_scaling_factor = FixedPoint(1) - price_discount * curve_fee * governance_fee
    predicted_delta_base = base_needed * gov_scaling_factor
    predicted_delta_shares = base_needed / share_price * gov_scaling_factor
    return TradeDeltas(
        user=Deltas(bonds=bonds_after_fees, base=base_needed, shares=base_needed / share_price),
        pool=Deltas(
            base=predicted_delta_base,
            shares=predicted_delta_shares,
            bonds=predicted_delta_bonds,
        ),
        fee=Deltas(
            bonds=bond_fees_to_pool,
            base=bond_fees_to_pool * spot_price,
            shares=bond_fees_to_pool * spot_price * share_price,
        ),
        governance=Deltas(
            bonds=bond_fees_to_gov,
            base=bond_fees_to_gov * spot_price,
            shares=bond_fees_to_gov * spot_price * share_price,
        ),
    )


def predict_short(
    hyperdrive_interface: HyperdriveReadInterface,
    pool_state: PoolState | None = None,
    base: FixedPoint | None = None,
    bonds: FixedPoint | None = None,
    for_pool: bool = False,
) -> TradeDeltas:
    """Predict the outcome of a short trade.

    Arguments
    ---------
    hyperdrive_interface: HyperdriveReadInterface
        Hyperdrive interface.
    pool_state: PoolState, optional
        The state of the pool, which includes block details, pool config, and pool info.
        If not given, use the current pool state.
    base: FixedPoint, optional
        The size of the short to open, in base.
    bonds: FixedPoint, optional
        The size of the short to open, in bonds. If not given, bonds is calculated from base.
    for_pool: bool
        Whether the base or bonds specified is for the pool.

    Returns
    -------
    TradeDeltas
        The predicted deltas of base, bonds, and shares.
    """
    pool_state, spot_price, price_discount, curve_fee, governance_fee, share_price = _get_vars(
        hyperdrive_interface, pool_state
    )
    if bonds is not None and base is None:
        if for_pool is False:
            bonds_needed = bonds
        else:
            # scale up input to account for fees
            bonds_needed = bonds * (FixedPoint(1) - price_discount * curve_fee * governance_fee)
    elif base is not None and bonds is None:
        # we need to calculate bonds_needed
        base_needed = base
        # this is the wrong direction for the swap, but we don't have the function in the other direction
        # tracked in issue https://github.com/delvtech/agent0/issues/1010
        bonds_needed = hyperdrive_interface.calc_bonds_out_given_shares_in_down(base_needed / share_price)
        # scale down output to account for fees
        if for_pool is False:
            bonds_needed /= FixedPoint(1) - price_discount * curve_fee * (FixedPoint(1) - governance_fee)
        else:
            bonds_needed /= FixedPoint(1) - price_discount * curve_fee
    else:
        raise ValueError("Need to specify either bonds or base, but not both.")
    shares_before_fees = hyperdrive_interface.calc_shares_out_given_bonds_in_down(bonds_needed)
    base_fees = bonds_needed * price_discount * curve_fee
    base_fees_to_pool = base_fees * (FixedPoint(1) - governance_fee)
    base_fees_to_gov = base_fees * governance_fee
    shares_after_fees = shares_before_fees + base_fees_to_pool + base_fees_to_gov
    base_after_fees = shares_after_fees * share_price
    predicted_delta_bonds = bonds_needed
    predicted_delta_shares = -shares_before_fees + base_fees_to_pool
    predicted_delta_base = predicted_delta_shares * share_price
    return TradeDeltas(
        user=Deltas(bonds=bonds_needed, base=base_after_fees, shares=shares_after_fees),
        pool=Deltas(
            base=predicted_delta_base,
            shares=predicted_delta_shares,
            bonds=predicted_delta_bonds,
        ),
        fee=Deltas(
            bonds=base_fees_to_pool / spot_price,
            base=base_fees_to_pool,
            shares=base_fees_to_pool / share_price,
        ),
        governance=Deltas(
            bonds=base_fees_to_gov / spot_price,
            base=base_fees_to_gov,
            shares=base_fees_to_gov / share_price,
        ),
    )

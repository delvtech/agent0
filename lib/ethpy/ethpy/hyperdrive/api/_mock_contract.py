"""Mock function calls using Pyperdrive."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pyperdrive
from fixedpointmath import FixedPoint
from hypertypes.IHyperdriveTypes import Fees, PoolConfig, PoolInfo

if TYPE_CHECKING:
    from .api import HyperdriveInterface

# We only worry about protected access for users outside of this folder
# pylint: disable=protected-access


def _construct_pool_config(contract_pool_config: dict[str, Any]) -> PoolConfig:
    """Convert the contract call return value into a proper PoolConfig object.

    .. note::
        This function will be deprecated as soon as we finish integrating pypechain.
    """
    return PoolConfig(
        baseToken=contract_pool_config["baseToken"],
        initialSharePrice=contract_pool_config["initialSharePrice"],
        minimumShareReserves=contract_pool_config["minimumShareReserves"],
        minimumTransactionAmount=contract_pool_config["minimumTransactionAmount"],
        positionDuration=contract_pool_config["positionDuration"],
        checkpointDuration=contract_pool_config["checkpointDuration"],
        timeStretch=contract_pool_config["timeStretch"],
        governance=contract_pool_config["governance"],
        feeCollector=contract_pool_config["feeCollector"],
        fees=Fees(
            curve=contract_pool_config["fees"][0],
            flat=contract_pool_config["fees"][1],
            governance=contract_pool_config["fees"][2],
        ),
        oracleSize=contract_pool_config["oracleSize"],
        updateGap=contract_pool_config["updateGap"],
    )


def _construct_pool_info(contract_pool_info: dict[str, Any]) -> PoolInfo:
    """Convert the contract call return value into a proper PoolInfo object.

    .. note::
        This function will be deprecated as soon as we finish integrating pypechain.
    """
    return PoolInfo(**contract_pool_info)


def _calc_position_duration_in_years(cls: HyperdriveInterface) -> FixedPoint:
    """See API for documentation.

    ..todo::
        This should be done in the hyperdrive sdk.
    """
    return FixedPoint(cls.pool_config["positionDuration"]) / FixedPoint(60 * 60 * 24 * 365)


def _calc_fixed_rate(cls: HyperdriveInterface) -> FixedPoint:
    """See API for documentation."""
    spot_rate = pyperdrive.get_spot_rate(
        _construct_pool_config(cls._contract_pool_config), _construct_pool_info(cls._contract_pool_info)
    )
    return FixedPoint(scaled_value=int(spot_rate))


def _calc_effective_share_reserves(cls: HyperdriveInterface) -> FixedPoint:
    """See API for documentation."""
    effective_share_reserves = pyperdrive.get_effective_share_reserves(
        str(cls.pool_info["shareReserves"].scaled_value),
        str(cls.pool_info["shareAdjustment"].scaled_value),
    )
    return FixedPoint(scaled_value=int(effective_share_reserves))


def _calc_spot_price(cls: HyperdriveInterface):
    """See API for documentation."""
    spot_price = pyperdrive.get_spot_price(
        _construct_pool_config(cls._contract_pool_config), _construct_pool_info(cls._contract_pool_info)
    )
    return FixedPoint(scaled_value=int(spot_price))


def _calc_long_amount(cls: HyperdriveInterface, base_amount: FixedPoint) -> FixedPoint:
    """See API for documentation."""
    long_amount = pyperdrive.get_long_amount(
        _construct_pool_config(cls._contract_pool_config),
        _construct_pool_info(cls._contract_pool_info),
        str(base_amount.scaled_value),
    )
    return FixedPoint(scaled_value=int(long_amount))


def _calc_short_deposit(
    cls: HyperdriveInterface,
    short_amount: FixedPoint,
    spot_price: FixedPoint,
    open_share_price: FixedPoint | None = None,
) -> FixedPoint:
    """See API for documentation."""
    if open_share_price is not None:  # convert FixedPoint to string
        open_share_price = str(open_share_price.scaled_value)
    short_deposit = pyperdrive.get_short_deposit(
        _construct_pool_config(cls._contract_pool_config),
        _construct_pool_info(cls._contract_pool_info),
        str(short_amount.scaled_value),
        str(spot_price.scaled_value),
        open_share_price,  # str | None
    )
    return FixedPoint(scaled_value=int(short_deposit))


def _calc_out_for_in(
    cls: HyperdriveInterface,
    amount_in: FixedPoint,
    shares_in: bool,
) -> FixedPoint:
    """See API for documentation."""
    out_for_in = pyperdrive.get_out_for_in(
        _construct_pool_config(cls._contract_pool_config),
        _construct_pool_info(cls._contract_pool_info),
        str(amount_in.scaled_value),
        shares_in,
    )
    return FixedPoint(scaled_value=int(out_for_in))


def _calc_in_for_out(
    cls: HyperdriveInterface,
    amount_out: FixedPoint,
    shares_out: bool,
) -> FixedPoint:
    """See API for documentation."""
    in_for_out = pyperdrive.get_in_for_out(
        _construct_pool_config(cls._contract_pool_config),
        _construct_pool_info(cls._contract_pool_info),
        str(amount_out.scaled_value),
        shares_out,
    )
    return FixedPoint(scaled_value=int(in_for_out))


def _calc_fees_out_given_bonds_in(
    cls: HyperdriveInterface, bonds_in: FixedPoint, maturity_time: int | None = None
) -> tuple[FixedPoint, FixedPoint, FixedPoint]:
    """See API for documentation.

    ..todo::
        This should be done in the hyperdrive sdk.
    """
    if maturity_time is None:
        maturity_time = cls.current_block_time + int(cls.pool_config["positionDuration"])
    time_remaining_in_seconds = FixedPoint(maturity_time - cls.current_block_time)
    normalized_time_remaining = time_remaining_in_seconds / cls.pool_config["positionDuration"]
    curve_fee = (
        (FixedPoint(1) - cls.spot_price) * cls.pool_config["curveFee"] * bonds_in * normalized_time_remaining
    ) / cls.pool_config["initialSharePrice"]
    flat_fee = (bonds_in * (FixedPoint(1) - normalized_time_remaining) * cls.pool_config["flatFee"]) / cls.pool_config[
        "initialSharePrice"
    ]
    gov_fee = curve_fee * cls.pool_config["governanceFee"] + flat_fee * cls.pool_config["governanceFee"]
    return curve_fee, flat_fee, gov_fee


def _calc_fees_out_given_shares_in(
    cls: HyperdriveInterface, shares_in: FixedPoint, maturity_time: int | None = None
) -> tuple[FixedPoint, FixedPoint, FixedPoint]:
    """See API for documentation.

    ..todo::
        This should be done in the hyperdrive sdk.
    """
    if maturity_time is None:
        maturity_time = cls.current_block_time + int(cls.pool_config["positionDuration"])
    time_remaining_in_seconds = FixedPoint(maturity_time - cls.current_block_time)
    normalized_time_remaining = time_remaining_in_seconds / cls.pool_config["positionDuration"]
    curve_fee = (
        ((FixedPoint(1) / cls.spot_price) - FixedPoint(1))
        * cls.pool_config["curveFee"]
        * cls.pool_config["initialSharePrice"]
        * shares_in
    )
    flat_fee = (shares_in * (FixedPoint(1) - normalized_time_remaining) * cls.pool_config["flatFee"]) / cls.pool_config[
        "initialSharePrice"
    ]
    gov_fee = curve_fee * cls.pool_config["governanceFee"] + flat_fee * cls.pool_config["governanceFee"]
    return curve_fee, flat_fee, gov_fee


def _calc_bonds_given_shares_and_rate(
    cls: HyperdriveInterface, target_rate: FixedPoint, target_shares: FixedPoint | None = None
) -> FixedPoint:
    """See API for documentation."""
    if target_shares is None:
        target_shares = cls.effective_share_reserves
    return FixedPoint(
        scaled_value=int(
            pyperdrive.calculate_bonds_given_shares_and_rate(
                str(target_shares.scaled_value),
                str(cls.pool_config["initialSharePrice"].scaled_value),
                str(target_rate.scaled_value),
                str(cls.pool_config["positionDuration"]),
                str(cls.pool_config["timeStretch"].scaled_value),
            )
        )
    )


def _calc_max_long(cls: HyperdriveInterface, budget: FixedPoint) -> FixedPoint:
    """See API for documentation."""
    cls._ensure_current_state()
    return FixedPoint(
        scaled_value=int(
            pyperdrive.get_max_long(
                _construct_pool_config(cls._contract_pool_config),
                _construct_pool_info(cls._contract_pool_info),
                str(budget.scaled_value),
                checkpoint_exposure=str(cls.latest_checkpoint["longExposure"].scaled_value),
                maybe_max_iterations=None,
            )
        )
    )


def _calc_max_short(cls: HyperdriveInterface, budget: FixedPoint) -> FixedPoint:
    """See API for documentation."""
    cls._ensure_current_state()
    return FixedPoint(
        scaled_value=int(
            pyperdrive.get_max_short(
                pool_config=_construct_pool_config(cls._contract_pool_config),
                pool_info=_construct_pool_info(cls._contract_pool_info),
                budget=str(budget.scaled_value),
                open_share_price=str(cls.pool_info["sharePrice"].scaled_value),
                checkpoint_exposure=str(cls.latest_checkpoint["longExposure"].scaled_value),
                maybe_conservative_price=None,
                maybe_max_iterations=None,
            )
        )
    )

"""A container for hyperdrive contract return values."""

from __future__ import annotations

from dataclasses import dataclass

from fixedpointmath import FixedPoint


# Lots of attributes for dataclass
# pylint: disable=too-many-instance-attributes
@dataclass
class ReceiptBreakdown:
    r"""A granular breakdown of important values in a trade receipt."""

    trader: str = ""
    destination: str = ""
    provider: str = ""
    asset_id: int = 0
    maturity_time_seconds: int = 0
    amount: FixedPoint = FixedPoint(0)
    bond_amount: FixedPoint = FixedPoint(0)
    lp_amount: FixedPoint = FixedPoint(0)
    withdrawal_share_amount: FixedPoint = FixedPoint(0)
    vault_share_price: FixedPoint = FixedPoint(0)
    checkpoint_vault_share_price: FixedPoint = FixedPoint(0)
    base_proceeds: FixedPoint = FixedPoint(0)
    base_payment: FixedPoint = FixedPoint(0)
    as_base: bool = False
    lp_share_price: FixedPoint = FixedPoint(0)
    # checkpoint event params
    checkpoint_time: int = 0
    matured_shorts: FixedPoint = FixedPoint(0)
    matured_longs: FixedPoint = FixedPoint(0)

    def __post_init__(self):
        # lots of attributes to check
        # pylint: disable=too-many-boolean-expressions
        if (
            self.amount < 0
            or self.bond_amount < 0
            or self.maturity_time_seconds < 0
            or self.lp_amount < 0
            or self.withdrawal_share_amount < 0
            or self.vault_share_price < 0
            or self.checkpoint_vault_share_price < 0
            or self.base_proceeds < 0
            or self.lp_share_price < 0
            or self.checkpoint_time < 0
            or self.matured_shorts < 0
            or self.matured_longs < 0
        ):
            raise ValueError(
                "All ReceiptBreakdown arguments must be positive,"
                " since they are expected to be unsigned integer values from smart contracts."
            )

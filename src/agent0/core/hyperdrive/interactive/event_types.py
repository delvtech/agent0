"""Defines the output hyperdrive events as dataclasses"""

from dataclasses import dataclass

from eth_typing import ChecksumAddress
from fixedpointmath import FixedPoint

# Lots of attributes for dataclass
# pylint: disable=too-many-instance-attributes


@dataclass
class OpenLong:
    """Dataclass mirroring OpenLong event in Hyperdrive."""

    trader: ChecksumAddress
    """The address of the trader."""
    asset_id: int
    """The encoded asset id for this long."""
    maturity_time: int
    """The maturity time for the opened long."""
    amount: FixedPoint
    """The amount of longs opened, units dependent on `as_base` flag."""
    vault_share_price: FixedPoint
    """The share price at the time of this trade."""
    as_base: bool
    """If the input amount for the trade was in base or shares."""
    bond_amount: FixedPoint
    """The amount of longs opened in units of bonds."""

    # Expose the name of the object
    __name__: str = "OpenLong"


@dataclass
class CloseLong:
    """Dataclass mirroring CloseLong event in Hyperdrive."""

    trader: ChecksumAddress
    """The address of the trader."""
    destination: ChecksumAddress
    """The address that receives the proceeds of the trade."""
    asset_id: int
    """The encoded asset id for this long."""
    maturity_time: int
    """The maturity time for the closed long."""
    amount: FixedPoint
    """The amount of longs closed, units dependent on `as_base` flag."""
    vault_share_price: FixedPoint
    """The share price at the time of this trade."""
    as_base: bool
    """If the input amount for the trade was in base or shares."""
    bond_amount: FixedPoint
    """The amount of longs closed in units of bonds."""

    # Expose the name of the object
    __name__: str = "CloseLong"


@dataclass
class OpenShort:
    # pylint: disable=too-many-instance-attributes
    """Dataclass mirroring OpenShort event in Hyperdrive."""
    trader: ChecksumAddress
    """The address of the trader."""
    asset_id: int
    """The encoded asset id for this short."""
    maturity_time: int
    """The maturity time for the opened short."""
    amount: FixedPoint
    """The amount spent from opening the short, units dependent on `as_base` flag."""
    vault_share_price: FixedPoint
    """The share price at the time of this trade."""
    as_base: bool
    """If the input amount for the trade was in base or shares."""
    base_proceeds: FixedPoint
    """The amount of base in the underlying short when shorting bonds."""
    bond_amount: FixedPoint
    """The amount of shorts opened in units of bonds."""

    # Expose the name of the object
    __name__: str = "OpenShort"


@dataclass
class CloseShort:
    """Dataclass mirroring CloseShort event in Hyperdrive."""

    trader: ChecksumAddress
    """The address of the trader."""
    destination: ChecksumAddress
    """The address that receives the proceeds of the trade."""
    asset_id: int
    """The encoded asset id for this short."""
    maturity_time: int
    """The maturity time for the closed short."""
    amount: FixedPoint
    """The amount spent from closing the short, units dependent on `as_base` flag."""
    vault_share_price: FixedPoint
    """The share price at the time of this trade."""
    as_base: bool
    """If the input amount for the trade was in base or shares."""
    base_payment: FixedPoint
    """The amount of base in the underlying short when shorting bonds."""
    bond_amount: FixedPoint
    """The amount of shorts closed in units of bonds."""

    # Expose the name of the object
    __name__: str = "CloseShort"


@dataclass
class AddLiquidity:
    """Dataclass mirroring AddLiquidity event in Hyperdrive."""

    provider: ChecksumAddress
    """The address of the lp provider."""
    lp_amount: FixedPoint
    """The amount of liquidity added in units of lp."""
    amount: FixedPoint
    """The amount of liquidity added, units dependent on `as_base` flag."""
    vault_share_price: FixedPoint
    """The share price at the time of this trade."""
    as_base: bool
    """If the input amount for the trade was in base or shares."""
    lp_share_price: FixedPoint
    """The lp share price for this trade."""

    # Expose the name of the object
    __name__: str = "AddLiquidity"


@dataclass
class RemoveLiquidity:
    """Dataclass mirroring RemoveLiquidity event in Hyperdrive."""

    provider: ChecksumAddress
    """The address of the lp provider."""
    destination: ChecksumAddress
    """The address that receives the proceeds of the trade."""
    lp_amount: FixedPoint
    """The amount of liquidity removed in units of lp."""
    amount: FixedPoint
    """The amount of liquidity removed, units dependent on `as_base` flag."""
    vault_share_price: FixedPoint
    """The share price at the time of this trade."""
    as_base: bool
    """If the input amount for the trade was in base or shares."""
    withdrawal_share_amount: FixedPoint
    """The amount of withdrawal shares received from removing liquidity."""
    lp_share_price: FixedPoint
    """The lp share price for this trade."""

    # Expose the name of the object
    __name__: str = "RemoveLiquidity"


@dataclass
class RedeemWithdrawalShares:
    """Dataclass mirroring RedeemWithdrawalShares event in Hyperdrive."""

    provider: ChecksumAddress
    """The address of the lp provider."""
    destination: ChecksumAddress
    """The address that receives the proceeds of the trade."""
    withdrawal_share_amount: FixedPoint
    """The amount of withdrawal shares redeemed, in units of withdrawal shares."""
    amount: FixedPoint
    """The amount of withdrawal shares redeemed, units dependent on `as_base` flag."""
    vault_share_price: FixedPoint
    """The share price at the time of this trade."""
    as_base: bool
    """If the input amount for the trade was in base or shares."""

    # Expose the name of the object
    __name__: str = "RedeemWithdrawalShares"


@dataclass
class CreateCheckpoint:
    """Dataclass mirroring CreateCheckpoint event in Hyperdrive."""

    checkpoint_time: int
    """The seconds epoch time index for this checkpoint."""
    vault_share_price: FixedPoint
    """The current vault share price."""
    checkpoint_vault_share_price: FixedPoint
    """The share price that was checkpointed in this checkpoint."""
    matured_shorts: FixedPoint
    """The amount of shorts that matured within this checkpoint."""
    matured_longs: FixedPoint
    """The amount of longs that matured within this checkpoint."""
    lp_share_price: FixedPoint
    """The lp share price at the checkpoint."""

    # Expose the name of the object
    __name__: str = "CreateCheckpoint"

"""Defines the output hyperdrive events as dataclasses"""

from dataclasses import dataclass

from eth_typing import ChecksumAddress
from fixedpointmath import FixedPoint


@dataclass
class OpenLong:
    """Dataclass mirroring OpenLong event in Hyperdrive.

    Attributes
    ----------
    trader: ChecksumAddress
        The address of the trader.
    asset_id: int
        The encoded asset id for this long.
    maturity_time: int
        The maturity time for the opened long
    base_amount: FixedPoint
        The amount of longs opened in units of base.
    vault_share_amount: FixedPoint
        The amount of longs opened in units of shares.
    as_base: bool
        If the input amount for the trade was in base or shares.
    bond_amount: FixedPoint
        The amount of longs opened in units of bonds.
    """

    trader: ChecksumAddress
    asset_id: int
    maturity_time: int
    base_amount: FixedPoint
    vault_share_amount: FixedPoint
    as_base: bool
    bond_amount: FixedPoint


@dataclass
class CloseLong:
    """Dataclass mirroring CloseLong event in Hyperdrive.

    Attributes
    ----------
    trader: ChecksumAddress
        The address of the trader.
    asset_id: int
        The encoded asset id for this long.
    maturity_time: int
        The maturity time for the closed long
    base_amount: FixedPoint
        The amount longs closed in units of base.
    vault_share_amount: FixedPoint
        The amount of longs closed in units of shares.
    as_base: bool
        If the input amount for the trade was in base or shares.
    bond_amount: FixedPoint
        The amount of longs closed in units of bonds.
    """

    trader: ChecksumAddress
    asset_id: int
    maturity_time: int
    base_amount: FixedPoint
    vault_share_amount: FixedPoint
    as_base: bool
    bond_amount: FixedPoint


@dataclass
class OpenShort:
    """Dataclass mirroring OpenShort event in Hyperdrive.

    Attributes
    ----------
    trader: ChecksumAddress
        The address of the trader.
    asset_id: int
        The encoded asset id for this short.
    maturity_time: int
        The maturity time for the opened short
    base_amount: FixedPoint
        The amount spent from opening the short, in units of base.
    vault_share_amount: FixedPoint
        The amount spent from opening the short, in units of shares.
    as_base: bool
        If the input amount for the trade was in base or shares.
    base_proceeds: FixedPoint
        The amount of base in the underlying short when shorting bonds.
    bond_amount: FixedPoint
        The amount of shorts opened in units of bonds.
    """

    # pylint: disable=too-many-instance-attributes

    trader: ChecksumAddress
    asset_id: int
    maturity_time: int
    base_amount: FixedPoint
    vault_share_amount: FixedPoint
    as_base: bool
    base_proceeds: FixedPoint
    bond_amount: FixedPoint


@dataclass
class CloseShort:
    """Dataclass mirroring CloseShort event in Hyperdrive

    Attributes
    ----------
    trader: ChecksumAddress
        The address of the trader.
    asset_id: int
        The encoded asset id for this short.
    maturity_time: int
        The maturity time for the closed short
    base_amount: FixedPoint
        The amount retrieved from closing the short, in units of base.
    vault_share_amount: FixedPoint
        The amount retrieved from closing the short, in units of shares.
    as_base: bool
        If the input amount for the trade was in base or shares.
    bond_amount: FixedPoint
        The amount of shorts closed in units of bonds.
    """

    trader: ChecksumAddress
    asset_id: int
    maturity_time: int
    base_amount: FixedPoint
    vault_share_amount: FixedPoint
    as_base: bool
    bond_amount: FixedPoint


@dataclass
class AddLiquidity:
    """Dataclass mirroring AddLiquidity event in Hyperdrive

    Attributes
    ----------
    provider: ChecksumAddress
        The address of the lp provider.
    lp_amount: FixedPoint
        The amount of liquidity added in units of lp.
    base_amount: FixedPoint
        The amount liquidity added, in units of base.
    vault_share_amount: FixedPoint
        The amount liquidity added, in units of shares.
    as_base: bool
        If the input amount for the trade was in base or shares.
    lp_share_price: FixedPoint
        The lp share price for this trade.
    """

    provider: ChecksumAddress
    lp_amount: FixedPoint
    base_amount: FixedPoint
    vault_share_amount: FixedPoint
    as_base: bool
    lp_share_price: FixedPoint


@dataclass
class RemoveLiquidity:
    """Dataclass mirroring RemoveLiquidity event in Hyperdrive

    Attributes
    ----------
    provider: ChecksumAddress
        The address of the lp provider.
    lp_amount: FixedPoint
        The amount of liquidity removed in units of lp.
    base_amount: FixedPoint
        The amount of liquidity removed, in units of base.
    vault_share_amount: FixedPoint
        The amount of liquidiyt removed, in units of shares.
    as_base: bool
        If the input amount for the trade was in base or shares.
    withdrawal_share_amount: FixedPoint
        The amount of withdrawal shares received from removing liquidity.
    lp_share_price: FixedPoint
        The lp share price for this trade.
    """

    provider: ChecksumAddress
    lp_amount: FixedPoint
    base_amount: FixedPoint
    vault_share_amount: FixedPoint
    as_base: bool
    withdrawal_share_amount: FixedPoint
    lp_share_price: FixedPoint


@dataclass
class RedeemWithdrawalShares:
    """Dataclass mirroring RedeemWithdrawalShares event in Hyperdrive

    Attributes
    ----------
    provider: ChecksumAddress
        The address of the lp provider.
    withdrawal_share_amount: FixedPoint
        The amount of withdrawal shares redeemed, in units of withdrawal shares.
    base_amount: FixedPoint
        The amount of withdrawal shares redeemed, in units of base.
    vault_share_amount: FixedPoint
        The amount of withdrawal shares redeemed, in units of shares.
    as_base: bool
        If the input amount for the trade was in base or shares.
    """

    provider: ChecksumAddress
    withdrawal_share_amount: FixedPoint
    base_amount: FixedPoint
    vault_share_amount: FixedPoint
    as_base: bool


@dataclass
class CreateCheckpoint:
    """Dataclass mirroring CreateCheckpoint event in Hyperdrive

    Attributes
    ----------
    checkpoint_time: int
        The seconds epoch time for this checkpoint.
    vault_share_price: FixedPoint
        The share price at the checkpoint.
    matured_shorts: FixedPoint
        The amount of shorts that matured within this checkpoint
    matured_longs: FixedPoint
        The amount of longs that matured within this checkpoint
    lp_share_price: FixedPoint
        The lp share price at the checkpoint
    """

    checkpoint_time: int
    vault_share_price: FixedPoint
    matured_shorts: FixedPoint
    matured_longs: FixedPoint
    lp_share_price: FixedPoint

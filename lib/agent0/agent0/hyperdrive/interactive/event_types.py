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
    share_price: FixedPoint
        The value of shares during the time of the trade.
    bond_amount: FixedPoint
        The amount of longs opened in units of bonds.
    """

    trader: ChecksumAddress
    asset_id: int
    maturity_time: int
    base_amount: FixedPoint
    share_price: FixedPoint
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
        The amount of longs closed in units of base.
    share_price: FixedPoint
        The share price for the long.
    bond_amount: FixedPoint
        The amount of longs closed in units of bonds.
    """

    trader: ChecksumAddress
    asset_id: int
    maturity_time: int
    base_amount: FixedPoint
    share_price: FixedPoint
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
        The amount of shorts opened in units of base.
    share_price: FixedPoint
        The share price for the short.
    bond_amount: FixedPoint
        The amount of shorts opened in units of bonds.
    """

    trader: ChecksumAddress
    asset_id: int
    maturity_time: int
    base_amount: FixedPoint
    share_price: FixedPoint
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
        The amount of shorts closed in units of base.
    share_price: FixedPoint
        The share price for the short.
    bond_amount: FixedPoint
        The amount of shorts closed in units of bonds.
    """

    trader: ChecksumAddress
    asset_id: int
    maturity_time: int
    base_amount: FixedPoint
    share_price: FixedPoint
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
        The amount of liquidity added in units of base.
    share_price: FixedPoint
        The share price for this trade.
    lp_share_price: FixedPoint
        The lp share price for this trade.
    """

    provider: ChecksumAddress
    lp_amount: FixedPoint
    base_amount: FixedPoint
    share_price: FixedPoint
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
        The amount of liquidity removed in units of base.
    share_price: FixedPoint
        The share price for this trade.
    withdrawal_share_amount: FixedPoint
        The amount of withdrawal shares received from removing liquidity.
    lp_share_price: FixedPoint
        The lp share price for this trade.
    """

    provider: ChecksumAddress
    lp_amount: FixedPoint
    base_amount: FixedPoint
    share_price: FixedPoint
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
        The amount of withdrawal shares redeemed in units of shares.
    base_amount: FixedPoint
        The amount of withdrawal shares redeemed in units of base.
    share_price: FixedPoint
        The share price for this trade.
    """

    provider: ChecksumAddress
    withdrawal_share_amount: FixedPoint
    base_amount: FixedPoint
    share_price: FixedPoint


@dataclass
class CreateCheckpoint:
    """Dataclass mirroring CreateCheckpoint event in Hyperdrive

    Attributes
    ----------
    checkpoint_time: int
        The seconds epoch time for this checkpoint.
    share_price: FixedPoint
        The share price at the checkpoint.
    matured_shorts: FixedPoint
        The amount of shorts that matured within this checkpoint
    matured_longs: FixedPoint
        The amount of longs that matured within this checkpoint
    lp_share_price: FixedPoint
        The lp share price at the checkpoint
    """

    checkpoint_time: int
    share_price: FixedPoint
    matured_shorts: FixedPoint
    matured_longs: FixedPoint
    lp_share_price: FixedPoint

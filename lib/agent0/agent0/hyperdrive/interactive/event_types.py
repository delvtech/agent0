"""Defines the output hyperdrive events as dataclasses"""
from dataclasses import dataclass

from eth_typing import ChecksumAddress
from fixedpointmath import FixedPoint


@dataclass
class OpenLong:
    """Dataclass mirroring OpenLong event in Hyperdrive"""

    trader: ChecksumAddress
    asset_id: int
    maturity_time: int
    base_amount: FixedPoint
    share_price: FixedPoint
    bond_amount: FixedPoint


@dataclass
class CloseLong:
    """Dataclass mirroring CloseLong event in Hyperdrive"""

    trader: ChecksumAddress
    asset_id: int
    maturity_time: int
    base_amount: FixedPoint
    share_price: FixedPoint
    bond_amount: FixedPoint


@dataclass
class OpenShort:
    """Dataclass mirroring OpenShort event in Hyperdrive"""

    trader: ChecksumAddress
    asset_id: int
    maturity_time: int
    base_amount: FixedPoint
    share_price: FixedPoint
    bond_amount: FixedPoint


@dataclass
class CloseShort:
    """Dataclass mirroring CloseShort event in Hyperdrive"""

    trader: ChecksumAddress
    asset_id: int
    maturity_time: int
    base_amount: FixedPoint
    share_price: FixedPoint
    bond_amount: FixedPoint


@dataclass
class AddLiquidity:
    """Dataclass mirroring AddLiquidity event in Hyperdrive"""

    provider: ChecksumAddress
    lp_amount: FixedPoint
    base_amount: FixedPoint
    share_price: FixedPoint
    lp_share_price: FixedPoint


@dataclass
class RemoveLiquidity:
    """Dataclass mirroring RemoveLiquidity event in Hyperdrive"""

    provider: ChecksumAddress
    lp_amount: FixedPoint
    base_amount: FixedPoint
    share_price: FixedPoint
    withdrawal_share_amount: FixedPoint
    lp_share_price: FixedPoint


@dataclass
class RedeemWithdrawalShares:
    """Dataclass mirroring RedeemWithdrawalShares event in Hyperdrive"""

    provider: ChecksumAddress
    withdrawal_share_amount: FixedPoint
    base_amount: FixedPoint
    share_price: FixedPoint


@dataclass
class CreateCheckpoint:
    """Dataclass mirroring CreateCheckpoint event in Hyperdrive"""

    checkpoint_time: int
    share_price: FixedPoint
    matured_shorts: FixedPoint
    matured_longs: FixedPoint
    lp_share_price: FixedPoint

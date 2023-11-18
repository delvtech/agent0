from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from eth_typing import ChecksumAddress
    from fixedpointmath import FixedPoint

    from .event_types import (
        AddLiquidity,
        CloseLong,
        CloseShort,
        CreateCheckpoint,
        OpenLong,
        OpenShort,
        RedeemWithdrawalShares,
        RemoveLiquidity,
    )
    from .interactive_hyperdrive import InteractiveHyperdrive


# We keep this class bare bones, while we want the logic functions in InteractiveHyperdrive to be private
# Hence, we call protected class methods in this class.
# pylint: disable=protected-access


class InteractiveHyperdriveAgent:
    """Interactive Hyperdrive Agent.
    This class is barebones with documentation, will just call the corresponding function
    in the interactive hyperdrive class to keep all logic in the same place. Adding these
    wrappers here for ease of use.
    """

    def __init__(self, base: FixedPoint, eth: FixedPoint, name: str | None, pool: InteractiveHyperdrive):
        self._pool = pool
        self.name = name
        # TODO
        self.agent = self._pool._init_agent(base, eth, name)

    def add_funds(self, base: FixedPoint | None = None, eth: FixedPoint | None = None) -> None:
        """Adds additional funds to the agent."""
        if base is None:
            base = FixedPoint(0)
        if eth is None:
            eth = FixedPoint(0)
        return self._pool._add_funds(self.agent, base, eth)

    def create_checkpoint(self, base: FixedPoint) -> CreateCheckpoint:
        return self._pool._create_checkpoint(self.agent, base)

    def open_long(self, base: FixedPoint) -> OpenLong:
        return self._pool._open_long(self.agent, base)

    def close_long(self, maturity_time: int, bonds: FixedPoint) -> CloseLong:
        return self._pool._close_long(self.agent, maturity_time, bonds)

    def open_short(self, bonds: FixedPoint) -> OpenShort:
        return self._pool._open_short(self.agent, bonds)

    def close_short(self, maturity_time: int, bonds: FixedPoint) -> CloseShort:
        return self._pool._close_short(self.agent, maturity_time, bonds)

    def add_liquidity(self, base: FixedPoint) -> AddLiquidity:
        return self._pool._add_liquidity(self.agent, base)

    def remove_liquidity(self, bonds: FixedPoint) -> RemoveLiquidity:
        return self._pool._remove_liquidity(self.agent, bonds)

    def redeem_withdraw_shares(self, shares: FixedPoint) -> RedeemWithdrawalShares:
        return self._pool._redeem_withdraw_shares(self.agent, shares)

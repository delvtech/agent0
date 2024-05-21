"""Empty accounts for engaging with smart contracts"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, TypeVar

from fixedpointmath import FixedPoint

from agent0.core.base import MarketType, PolicyAgent
from agent0.core.base.policies import BasePolicy
from agent0.ethpy.hyperdrive.interface import HyperdriveReadInterface

from .hyperdrive_actions import (
    HyperdriveMarketAction,
    close_long_trade,
    close_short_trade,
    redeem_withdraw_shares_trade,
    remove_liquidity_trade,
)
from .hyperdrive_wallet import HyperdriveWallet

if TYPE_CHECKING:
    from eth_account.signers.local import LocalAccount

    from agent0.core.base import Trade


Policy = TypeVar("Policy", bound=BasePolicy)


class HyperdrivePolicyAgent(PolicyAgent[Policy, HyperdriveReadInterface, HyperdriveMarketAction]):
    r"""Enact policies on smart contracts and tracks wallet state

    .. todo::
        should be able to get the HyperdriveMarketAction type from the HyperdriveInterface
    """

    def __init__(self, account: LocalAccount, initial_budget: FixedPoint | None = None, policy: Policy | None = None):
        """Initialize an agent and wallet account

        Arguments
        ---------
        account: LocalAccount
            A Web3 local account for storing addresses & signing transactions.
        initial_budget: FixedPoint | None, optional
            The initial budget for the wallet bookkeeping.
        policy: Policy | None, optional
            Policy for producing agent actions.
            If None, then a policy that executes no actions is used.

        """
        super().__init__(account, initial_budget, policy)
        # Reinitialize the wallet to the subclass
        self.wallet = HyperdriveWallet(address=self.wallet.address, balance=self.wallet.balance)

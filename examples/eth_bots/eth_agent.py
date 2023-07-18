"""Agent with an ethereum account."""
from __future__ import annotations

from elfpy.agents.agent import Agent
from elfpy.agents.policies import BasePolicy
from elfpy.eth.accounts import EthAccount


class EthAgent(Agent):
    """An agent with an EthAccount."""

    def __init__(self, wallet_address: int, eth_account: EthAccount = EthAccount(), policy: BasePolicy | None = None):
        r"""Store agent wallet & policy"""
        super().__init__(wallet_address=wallet_address, policy=policy)
        self.eth_account = eth_account

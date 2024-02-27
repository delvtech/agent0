"""The hyperdrive agent object that encapsulates an agent."""

from __future__ import annotations

from typing import Type

from agent0.hyperdrive.interactive.hyperdrive import Hyperdrive
from agent0.hyperdrive.policies import HyperdriveBasePolicy


class HyperdriveAgent:
    def __init__(
        self,
        pool: Hyperdrive,
        policy: Type[HyperdriveBasePolicy] | None,
        policy_config: HyperdriveBasePolicy.Config | None,
        private_key: str | None = None,
    ) -> None:
        """Constructor for the interactive hyperdrive agent.
        NOTE: this constructor shouldn't be called directly, but rather from Hyperdrive's
        `init_agent` method.

        Arguments
        ---------
        base: FixedPoint
            The amount of base to fund the agent with.
        eth: FixedPoint
            The amount of ETH to fund the agent with.
        name: str | None
            The name of the agent. Defaults to the wallet address.
        pool: InteractiveHyperdrive
            The pool object that this agent belongs to.
        policy: HyperdrivePolicy | None
            An optional policy to attach to this agent.
        private_key: str | None, optional
            The private key of the associated account. Default is auto-generated.
        """
        # pylint: disable=too-many-arguments
        self._pool = pool
        self.agent = self._pool._init_agent(policy, policy_config, private_key)

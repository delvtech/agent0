"""The hyperdrive agent object that encapsulates an agent."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fixedpointmath import FixedPoint

from .i_hyperdrive_agent import IHyperdriveAgent

if TYPE_CHECKING:
    from typing import Type

    from agent0.hyperdrive.policies import HyperdriveBasePolicy

    from .i_local_hyperdrive import ILocalHyperdrive


# We keep this class bare bones, while we want the logic functions in InteractiveHyperdrive to be private
# Hence, we call protected class methods in this class.
# pylint: disable=protected-access


class ILocalHyperdriveAgent(IHyperdriveAgent):
    """Local Hyperdrive Agent.
    This class is barebones with documentation, will just call the corresponding function
    in the interactive hyperdrive class to keep all logic in the same place. Adding these
    wrappers here for ease of use.
    """

    def __init__(
        self,
        base: FixedPoint,
        eth: FixedPoint,
        name: str | None,
        pool: ILocalHyperdrive,
        policy: Type[HyperdriveBasePolicy] | None,
        policy_config: HyperdriveBasePolicy.Config | None,
        private_key: str | None = None,
    ) -> None:
        """Constructor for the interactive hyperdrive agent.
        NOTE: this constructor shouldn't be called directly, but rather from LocalHyperdrive's
        `init_agent` method.

        Arguments
        ---------
        base: FixedPoint
            The amount of base to fund the agent with.
        eth: FixedPoint
            The amount of ETH to fund the agent with.
        name: str | None
            The name of the agent. Defaults to the wallet address.
        pool: LocalHyperdrive
            The pool object that this agent belongs to.
        policy: HyperdrivePolicy | None
            An optional policy to attach to this agent.
        policy_config: HyperdrivePolicy.Config | None,
            The configuration for the attached policy.
        private_key: str | None, optional
            The private key of the associated account. Default is auto-generated.
        """
        # pylint: disable=too-many-arguments
        self._pool = pool
        self.name = name
        self.agent = self._pool._init_agent(base, eth, name, policy, policy_config, private_key)

    def add_funds(self, base: FixedPoint | None = None, eth: FixedPoint | None = None) -> None:
        """Adds additional funds to the agent.

        Arguments
        ---------
        base: FixedPoint
            The amount of base to fund the agent with. Defaults to 0.
        eth: FixedPoint
            The amount of ETH to fund the agent with. Defaults to 0.
        """
        if base is None:
            base = FixedPoint(0)
        if eth is None:
            eth = FixedPoint(0)
        self._pool._add_funds(self.agent, base, eth)

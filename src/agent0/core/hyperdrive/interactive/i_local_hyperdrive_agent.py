"""The hyperdrive agent object that encapsulates an agent."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fixedpointmath import FixedPoint

from .i_hyperdrive_agent import IHyperdriveAgent

if TYPE_CHECKING:
    from typing import Type

    from agent0.core.hyperdrive.policies import HyperdriveBasePolicy

    from .i_local_hyperdrive import ILocalHyperdrive


class ILocalHyperdriveAgent(IHyperdriveAgent):
    """Interactive Local Hyperdrive Agent.

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
        # We overwrite the base init agents with different parameters
        # pylint: disable=super-init-not-called
        # pylint: disable=too-many-arguments
        self._pool = pool
        self.name = name
        self.agent = self._pool._init_local_agent(base, eth, name, policy, policy_config, private_key)

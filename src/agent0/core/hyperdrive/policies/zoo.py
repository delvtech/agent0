"""Policies for expert system trading bots."""

from __future__ import annotations

from typing import NamedTuple

from .deterministic import Deterministic
from .lpandarb import LPandArb
from .random import Random
from .random_hold import RandomHold
from .simple_lp import SimpleLP
from .smart_long import SmartLong


# Container for all the policies
class PolicyZoo(NamedTuple):
    """All policies in agent0."""

    random = Random
    random_hold = RandomHold
    smart_long = SmartLong
    simple_lp = SimpleLP
    lp_and_arb = LPandArb
    deterministic = Deterministic

    def describe(self, policies: list | str | None = None) -> str:
        """Describe policies, either specific ones provided, or all of them.

        Arguments
        ---------
        policies: list | str | None, optional
            A policy name string or list of policy names to describe.
            If not provided, then all available policies are described.

        Returns
        -------
        str
            A string containing the policy descriptions joined by new-lines.
        """
        # programmatically create a list with all the policies
        existing_policies = [
            attr for attr in dir(self) if not attr.startswith("_") and attr not in ["describe", "count", "index"]
        ]
        if policies is None:  # we are not provided specific policies to describe
            policies = existing_policies
        elif not isinstance(policies, list):  # not a list
            policies = [policies]  # we make it a list

        for policy in policies:
            if policy not in existing_policies:
                raise ValueError(f"Unknown policy: {policy}")

        return "\n".join([f"=== {policy} ===\n{getattr(self, policy).description()}" for policy in policies])

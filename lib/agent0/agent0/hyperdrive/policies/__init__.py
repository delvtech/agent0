"""Policies for expert system trading bots"""
from __future__ import annotations

from typing import NamedTuple

# Base policy to subclass from
from .hyperdrive_policy import HyperdrivePolicy
from .random_agent import RandomAgent


class Policies(NamedTuple):
    """All policies in elfpy."""

    random_agent = RandomAgent

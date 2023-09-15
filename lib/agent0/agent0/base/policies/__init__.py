"""Policies for expert system trading agents"""
from __future__ import annotations

from typing import NamedTuple

from .base import BasePolicy
from .no_action import NoActionPolicy


class BasePolicies(NamedTuple):
    """All base policies in agent0."""

    no_action = NoActionPolicy

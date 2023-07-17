"""Unit tests for the loading agent policies"""
from __future__ import annotations

import os
import sys
import unittest

from elfpy.agents import load_agent_policies


class TestLoadAgentPolicies(unittest.TestCase):
    def setUp(self):
        this_file_directory = os.path.dirname(os.path.abspath(sys.argv[0]))
        self.root_path = os.path.dirname(this_file_directory)  # /path/to/elf-simulations

    def test_get_invoked_path(self):
        invoked_path = load_agent_policies.get_invoked_path()
        assert invoked_path == os.path.join(self.root_path, "tests")

    def test_load_builtin_policies(self):
        builtin_policies = load_agent_policies.load_builtin_policies()


if __name__ == "__main__":
    builtin_policie = load_agent_policies.load_builtin_policies()
    print(f"{builtin_policie=}")

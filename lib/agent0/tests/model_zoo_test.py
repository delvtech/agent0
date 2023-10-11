"""System test for end to end testing of elf-simulations."""
from __future__ import annotations

import logging

import agent0


class TestModelZoo:
    """Test model zoo."""

    def test_describe_all(self):
        """Test model zoo."""
        str_output = "Testing model zoo\n"
        zoo = agent0.Zoo()  # pylint: disable=no-member
        zoo_description = zoo.describe()
        str_output += zoo_description
        logging.info(str_output)

    def test_describe_single(self):
        """Test single agent."""
        str_output = "Testing single policy description\n"
        zoo = agent0.Zoo()  # pylint: disable=no-member
        zoo_description = zoo.describe("random_agent")
        str_output += zoo_description
        logging.info(str_output)

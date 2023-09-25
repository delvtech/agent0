"""Testing for generating code from pypechain"""
from __future__ import annotations

import os
import shutil
import unittest

from pypechain import run_pypechain


def count_files(directory) -> int:
    """Return the number of files in the given directory."""
    return sum(1 for entry in os.listdir(directory) if os.path.isfile(os.path.join(directory, entry)))


class CodegenTest(unittest.TestCase):
    """Test class."""

    def test_codegen(self):
        """Test the pypechain codegen produces the same files"""
        # <package_dir>/lib/hyperdrive_types/hyperdrive_types
        test_location = os.path.dirname(os.path.abspath(__file__))
        # <package_dir>/packages/hyperdrive/src/abis
        abis_location = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(test_location))),
            "packages",
            "hyperdrive",
            "src",
            "abis",
        )
        test_temp_location = os.path.join(test_location, "test_temp")
        if os.path.exists(test_temp_location):
            shutil.rmtree(test_temp_location)  # Forcefully remove the directory and its contents
        os.makedirs(test_temp_location)
        for root, _, files in os.walk(abis_location):
            for file in files:
                if file.endswith(".json"):
                    json_file_path = os.path.join(root, file)
                    try:
                        run_pypechain.main(json_file_path, test_temp_location)
                    except Exception as exc:  # pylint: disable=broad-exception-caught
                        print(f"{exc=}; skipping file")
                        continue
        # ensure that the number of files is the same
        assert count_files(test_location) - 1 == count_files(test_temp_location)
        # ensure that the file names are the same
        for file in os.listdir(test_temp_location):
            assert file in os.listdir(test_location)
        # ensure that the file contents are the same
        for file in os.listdir(test_location):
            if os.path.isfile(file) and file != "test_codegen.py":
                with open(os.path.join(test_temp_location, file), mode="r", encoding="utf-8") as temp_file:
                    with open(os.path.join(test_location, file), mode="r", encoding="utf-8") as original_file:
                        temp_contents = temp_file.read()
                        original_contents = original_file.read()
                        assert temp_contents == original_contents, (
                            f"\n{temp_file.name=}\n\n{temp_contents=}\n\n"
                            f"!=\n\n{original_file.name=}\n\n{original_contents=}"
                        )

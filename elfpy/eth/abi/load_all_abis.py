"""Load all abis"""
from __future__ import annotations

import json
import logging
import os


def load_all_abis(abi_folder: str) -> dict:
    """Load all ABI jsons given an abi_folder

    Arguments
    ---------
    abi_folder: str
        The local directory that contains all abi json
    """
    abis = {}
    abi_files = _collect_files(abi_folder)
    loaded = []
    for abi_file in abi_files:
        file_name = os.path.splitext(os.path.basename(abi_file))[0]
        with open(abi_file, mode="r", encoding="UTF-8") as file:
            data = json.load(file)
        if "abi" in data:
            abis[file_name] = data["abi"]
            loaded.append(abi_file)
        else:
            logging.warning("JSON file %s did not contain an ABI", abi_file)
    logging.info("Loaded ABI files %s", str(loaded))
    return abis


def _collect_files(folder_path: str, extension: str = ".json") -> list[str]:
    """Load all files with the given extension into a list"""
    collected_files = []
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(extension):
                file_path = os.path.join(root, file)
                collected_files.append(file_path)
    return collected_files

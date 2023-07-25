"""Load ABIs"""
from __future__ import annotations

import json
import logging
import os


def load_all_abis(abi_folder: str) -> dict:
    """Load all ABI JSONs given an abi_folder.

    Arguments
    ---------
    abi_folder : str
        The local directory that contains all abi json

    Returns
    -------
    dict
        A dictionary with keys for each abi filename and value is the "abi" field of the JSON decoded file
    """
    abis = {}
    abi_files = _collect_files(abi_folder)
    loaded = []
    for abi_file in abi_files:
        file_name = os.path.splitext(os.path.basename(abi_file))[0]
        try:
            abi_data = load_abi_from_file(abi_file)
        except AssertionError as err:
            logging.debug("JSON file %s did not contain an ABI.\nError: %s", abi_file, err)
        abis[file_name] = abi_data
        loaded.append(abi_file)
    logging.debug("Loaded ABI files %s", str(loaded))
    return abis


def load_abi_from_file(file_name: str) -> dict:
    """Load an ABI JSON given an ABI file.

    Arguments
    ---------
    abi_folder: str
        The local directory that contains all abi json

    Returns
    -------
    dict
        A dictionary containing "abi" field of the JSON decoded file
    """
    with open(file_name, mode="r", encoding="UTF-8") as file:
        data = json.load(file)
    if "abi" in data:
        return data["abi"]
    raise AssertionError(f"ABI for {file_name=} must contain an 'abi' field")


def _collect_files(folder_path: str, extension: str = ".json") -> list[str]:
    """Load all files with the given extension into a list"""
    collected_files = []
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(extension):
                file_path = os.path.join(root, file)
                collected_files.append(file_path)
    return collected_files

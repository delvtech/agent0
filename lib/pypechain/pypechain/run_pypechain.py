"""Script to generate typed web3.py classes for solidity contracts."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, Template
from pypechain.utilities import avoid_python_keywords, is_abi_function, solidity_to_python_type
from web3 import Web3
from web3.types import ABIElement, ABIFunction


def load_abi_from_file(file_path: Path):
    """Loads a contract ABI from a file.

    Arguments
    ---------
    file_path : Path
        The path to the ABI file.

    Returns
    -------
    Any
        An object containing the contract's abi.
    """

    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)["abi"]


def main(abi_file_path: str, output_file_path: str) -> None:
    """Generates class files for a given abi.

    Arguments
    ---------
    abi_file_path : str
        Path to the abi json file.

    output_file_path : str
        Path to the file to output the generated code.
    """

    file_path = Path(abi_file_path)
    template = setup_template()

    abi_functions_and_events = get_abi_items(file_path)

    # Extract function names and their input parameters from the ABI
    function_datas = []
    for abi_function in abi_functions_and_events:
        if is_abi_function(abi_function):
            # TODO: investigate better typing here?  templete.render expects an object so we'll have to convert.
            function_data = {
                # TODO: pass a typeguarded ABIFunction that has only required fields?
                # name is required in the typeguard.  Should be safe to default to empty string.
                "name": abi_function.get("name", "").capitalize(),
                "input_names_and_types": get_input_names_and_values(abi_function),
                "input_names": get_input_names(abi_function),
            }
            function_datas.append(function_data)

    # Render the template
    filename = file_path.name
    contract_name = os.path.splitext(filename)[0]
    # TODO: Add more features:
    # TODO:  return types to function calls
    # TODO:  events
    # TODO:  structs
    rendered_code = template.render(contract_name=contract_name, functions=function_datas)

    # Save the rendered code to a file
    with open(output_file_path, "w", encoding="utf-8") as output_file:
        output_file.write(rendered_code)


def setup_template() -> Template:
    """Grabs the necessary template files.

    Returns
    -------
    Template
        A jinja template for a python file containing a custom web3.py contract and its functions.
    """
    ### Set up the Jinja2 environment
    # Determine the absolute path to the directory containing your script.
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Construct the path to your templates directory.
    templates_dir = os.path.join(script_dir, "templates")
    env = Environment(loader=FileSystemLoader(templates_dir))
    template = env.get_template("contract.jinja2")
    return template


def get_abi_items(file_path: Path) -> list[ABIElement]:
    """Gets all the

    Parameters
    ----------
    file_path : Path
        the file path to the ABI.

    Returns
    -------
    List[Union[ABIFunction, ABIEvent]]
        _description_
    """

    web3 = Web3()
    abi = load_abi_from_file(file_path)
    contract = web3.eth.contract(abi=abi)

    # leverage the private list of ABIFunction's
    # pylint: disable=protected-access
    abi_functions_and_events = contract.functions._functions
    return abi_functions_and_events


def get_input_names_and_values(function: ABIFunction) -> list[str]:
    """Returns function input name/type strings for jinja templating.

    i.e. for the solidity function signature: function doThing(address who, uint256 amount, bool
    flag, bytes extraData)

    the following list would be returned: ['who: str', 'amount: int', 'flag: bool', 'extraData:
    bytes']

    Arguments
    ---------
    function : ABIFunction
        A web3 dict of an ABI function description.

    Returns
    -------
    list[str]
        A list of function names and corresponding python values, i.e. ['arg1: str', 'arg2: bool']
    """

    stringified_function_parameters: list[str] = []
    for _input in function.get("inputs", []):
        name = _input.get("name")
        if name is None:
            raise ValueError("Solidity function parameter name cannot be None")
        python_type = solidity_to_python_type(_input.get("type", "unknown"))
        stringified_function_parameters.append(f"{avoid_python_keywords(name)}: {python_type}")

    return stringified_function_parameters


def get_input_names(function: ABIFunction) -> list[str]:
    """Returns function input name/type strings for jinja templating.

    i.e. for the solidity function signature:
    function doThing(address who, uint256 amount, bool flag, bytes extraData)

    the following list would be returned:
    ['who', 'amount', 'flag', 'extraData']

    ---------
    Arguments
    function : ABIFunction
        A web3 dict of an ABI function description.

    Returns
    -------
    list[str]
        A list of function names i.e. ['arg1', 'arg2']

    """

    stringified_function_parameters: list[str] = []
    for _input in function.get("inputs", []):
        name = _input.get("name")
        if name is None:
            raise ValueError("name cannot be None")
        stringified_function_parameters.append(avoid_python_keywords(name))

    return stringified_function_parameters


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python script_name.py <path_to_abi_file> <contract_address> <output_file>")
    else:
        # TODO: pass output path, not file, i.e. './build'
        # TODO: pass input path, not file, i.e. './abis'
        # TODO: add a bash script to make this easier, i.e. ./pypechain './abis', './build'
        # TODO: make this installable so that other packages can use the command line tool
        main(sys.argv[1], sys.argv[2])

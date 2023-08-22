"""Script to generate typed web3.py classes for solidity contracts."""
from __future__ import annotations

import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import NamedTuple

from jinja2 import Environment, FileSystemLoader, Template
from pypechain.utilities.abi import get_param_name, get_structs_for_abi, is_abi_function, load_abi_from_file
from pypechain.utilities.format import avoid_python_keywords
from pypechain.utilities.types import solidity_to_python_type
from web3 import Web3
from web3.types import ABIElement, ABIFunction


def main(abi_file_path: str, output_dir: str) -> None:
    """Generates class files for a given abi.

    Arguments
    ---------
    abi_file_path : str
        Path to the abi json file.

    output_dr: str
        Path to the directory to output the generated files.
    """

    file_path = Path(abi_file_path)
    contract_template, types_template = setup_templates()

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
                "outputs": get_outputs(abi_function),
            }
            function_datas.append(function_data)

    # Render the template
    filename = file_path.name
    contract_name = os.path.splitext(filename)[0]
    # TODO: Add more features:
    # TODO:  return types to function calls
    # TODO:  events
    # TODO:  structs
    rendered_contract_code = contract_template.render(contract_name=contract_name, functions=function_datas)
    abi = load_abi_from_file(file_path)
    structs = get_structs_for_abi(abi)
    struct_infos = list(structs.values())
    struct_infos = [asdict(info) for info in struct_infos]
    rendered_types_code = types_template.render(contract_name=contract_name, structs=struct_infos)

    contract_output_file_path = Path(output_dir).joinpath(contract_name + "Contract.py")
    types_output_file_path = Path(output_dir).joinpath(contract_name + "Types.py")
    # Save the rendered code to a file
    with open(contract_output_file_path, "w", encoding="utf-8") as output_file:
        output_file.write(rendered_contract_code)
    # TODO: makes this better, don't use splitting/joining.  have user pass in dir, not file name
    with open(types_output_file_path, "w", encoding="utf-8") as output_file:
        output_file.write(rendered_types_code)


class Templates(NamedTuple):
    """Templates for codegen.  Each template represent a different file."""

    contract_template: Template
    types_template: Template


def setup_templates() -> Templates:
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
    contract_template = env.get_template("contract.jinja2")
    types_template = env.get_template("types.jinja2")
    return Templates(contract_template, types_template)


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


def get_outputs(function: ABIFunction) -> list[str]:
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
        A list of function names i.e. [{name: 'arg1', type: 'int'}, { name: 'TransferInfo', components: [{
            name: 'from', type: 'str'}, name: '
        }]]
    """

    stringified_function_outputs: list[str] = []
    for _input in function.get("inputs", []):
        name = get_param_name(_input)
        if not name:
            # TODO: handle empty strings.  Should replace them with 'arg1', 'arg2', and so one.
            # TODO: recursively handle this too for evil nested tuples with no names.
            raise ValueError("name cannot be empty")
        stringified_function_outputs.append(avoid_python_keywords(name))

    return stringified_function_outputs


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python script_name.py <path_to_abi_file> <contract_address> <output_file>")
    else:
        # TODO: add a bash script to make this easier, i.e. ./pypechain './abis', './build'
        # TODO: make this installable so that other packages can use the command line tool
        main(sys.argv[1], sys.argv[2])

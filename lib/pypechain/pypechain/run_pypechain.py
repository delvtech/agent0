"""Script to generate typed web3.py classes for solidity contracts."""
from __future__ import annotations

import os
import sys
from dataclasses import asdict
from pathlib import Path

from jinja2 import Template
from pypechain.utilities.abi import (
    get_abi_items,
    get_param_name,
    get_structs_for_abi,
    is_abi_function,
    load_abi_from_file,
)
from pypechain.utilities.format import avoid_python_keywords, capitalize_first_letter_only
from pypechain.utilities.templates import setup_templates
from pypechain.utilities.types import solidity_to_python_type
from web3.types import ABIFunction


def main(abi_file_path: str, output_dir: str) -> None:
    """Generates class files for a given abi.

    Arguments
    ---------
    abi_file_path : str
        Path to the abi json file.

    output_dr: str
        Path to the directory to output the generated files.
    """

    # get names
    file_path = Path(abi_file_path)
    filename = file_path.name
    contract_name = os.path.splitext(filename)[0]

    # grab the templates
    contract_template, types_template = setup_templates()

    # render the code
    rendered_contract_code = render_contract_file(contract_name, contract_template, file_path)
    rendered_types_code = render_types_file(contract_name, types_template, file_path)

    # TODO: Add more features:
    # TODO:  events

    # Write the renders to a file
    types_output_file_path = Path(output_dir).joinpath(contract_name + "Types.py")
    contract_output_file_path = Path(output_dir).joinpath(contract_name + "Contract.py")
    with open(contract_output_file_path, "w", encoding="utf-8") as output_file:
        output_file.write(rendered_contract_code)
    with open(types_output_file_path, "w", encoding="utf-8") as output_file:
        output_file.write(rendered_types_code)


def render_contract_file(contract_name: str, contract_template: Template, abi_file_path: Path) -> str:
    """Returns a string of the contract file to be generated.

    Parameters
    ----------
    contract_template : Template
        A jinja template containging types for all structs within an abi.
    abi_file_path : Path
        The path to the abi file to parse.

    Returns
    -------
    str
        A serialized python file.
    """

    # TODO:  return types to function calls
    # Extract function names and their input parameters from the ABI
    abi_functions_and_events = get_abi_items(abi_file_path)

    function_datas = []
    for abi_function in abi_functions_and_events:
        if is_abi_function(abi_function):
            # TODO: investigate better typing here?  templete.render expects an object so we'll have to convert.
            name = abi_function.get("name", "")
            function_data = {
                # TODO: pass a typeguarded ABIFunction that has only required fields?
                # name is required in the typeguard.  Should be safe to default to empty string.
                "name": name,
                "capitalized_name": capitalize_first_letter_only(name),
                "input_names_and_types": get_input_names_and_values(abi_function),
                "input_names": get_input_names(abi_function),
                "outputs": get_outputs(abi_function),
            }
            function_datas.append(function_data)
    # Render the template
    return contract_template.render(contract_name=contract_name, functions=function_datas)


def render_types_file(contract_name: str, types_template: Template, abi_file_path: Path) -> str:
    """Returns a string of the types file to be generated.

    Arguments
    ---------
    types_template : Template
        A jinja template containging types for all structs within an abi.
    abi_file_path : Path
        The path to the abi file to parse.

    Returns
    -------
    str
        A serialized python file.
    """

    abi = load_abi_from_file(abi_file_path)

    structs_by_name = get_structs_for_abi(abi)
    structs_list = list(structs_by_name.values())
    structs = [asdict(struct) for struct in structs_list]
    return types_template.render(contract_name=contract_name, structs=structs)


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


def stringify_parameters(parameters) -> list[str]:
    """Stringifies parameters."""
    stringified_function_parameters: list[str] = []
    for _input in parameters:
        if name := _input.get("name"):
            stringified_function_parameters.append(avoid_python_keywords(name))
        else:
            raise ValueError("input name cannot be None")
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
    return stringify_parameters(function.get("inputs", []))


def get_outputs(function: ABIFunction) -> list[str]:
    """Returns function output name/type strings for jinja templating.

    i.e. for the solidity function signature:
    function doThing() returns (address who, uint256 amount, bool flag, bytes extraData)

    the following list would be returned:
    ['who', 'amount', 'flag', 'extraData']

    Arguments
    ---------
    function : ABIFunction
        A web3 dict of an ABI function description.

    Returns
    -------
    list[str]
        A list of function names i.e. [{name: 'arg1', type: 'int'}, { name: 'TransferInfo', components: [{
            name: 'from', type: 'str'}, name: '
        }]]
    """
    return stringify_parameters(function.get("outputs", []))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python script_name.py <path_to_abi_file> <contract_address> <output_file>")
    else:
        # TODO: add a bash script to make this easier, i.e. ./pypechain './abis', './build'
        # TODO: make this installable so that other packages can use the command line tool
        main(sys.argv[1], sys.argv[2])

"""Script to generate typed web3.py classes for solidity contracts."""
from __future__ import annotations

import os
import re
import sys
from dataclasses import asdict
from pathlib import Path

import black
from jinja2 import Template
from pypechain.utilities.abi import (
    get_abi_items,
    get_events_for_abi,
    get_param_name,
    get_structs_for_abi,
    is_abi_function,
    load_abi_from_file,
)
from pypechain.utilities.format import avoid_python_keywords, capitalize_first_letter_only
from pypechain.utilities.templates import setup_templates
from pypechain.utilities.types import solidity_to_python_type
from web3.types import ABIFunction


def get_intersection_and_unique(lists: list[list[str]]) -> tuple[set[str], set[str]]:
    """Process a list of lists of strings to get the intersection and unique values.

    The intersection is a set of strings that occur in all sub-lists.
    The unique values are strings that only occur in one sub-list.

    Arguments
    ---------
    lists : list[list[str]]
        A list of lists of strings, where each sub-list is an entity to compute sets over.

    Returns
    -------
    tuple[set[str], set[str]]
        The (intersection, unique_values) sets
    """
    intersection = set(lists[0])
    for lst in lists[1:]:
        intersection &= set(lst)
    string_counts = {}
    for lst in lists:
        for item in set(lst):
            string_counts[item] = string_counts.get(item, 0) + 1
    unique_values = {item for item, count in string_counts.items() if count == 1}
    return (intersection, unique_values)


def format_code(code: str, line_length: int) -> str:
    """Format code with Black on default settings.

    Arguments
    ---------
    code : str
        A string containing Python code
    line_length : int
        Output file's maximum line length.

    Returns
    -------
    str
        A string containing the Black-formatted code
    """
    while "\n\n" in code:  # remove extra newlines and let Black sort it out
        code = re.sub(r"^[\s\t]*\n", "", code, flags=re.MULTILINE)
    code = code.replace(", )", ")")  # remove trailing comma
    try:
        return black.format_file_contents(code, fast=False, mode=black.Mode(line_length=line_length))
    except ValueError as exc:
        raise ValueError(f"cannot format with Black\n code:\n{code}") from exc


def write_code(path: str | os.PathLike, code: str) -> None:
    """Save to specified path the provided code.

    Arguments
    ---------
    path : str | os.PathLike
        The location of the output file.
    code : str
        The code to be written, as a single string.
    """
    with open(path, "w", encoding="utf-8") as output_file:
        output_file.write(code)


def main(abi_file_path: str, output_dir: str, line_length: int = 80) -> None:
    """Generates class files for a given abi.

    Arguments
    ---------
    abi_file_path : str
        Path to the abi JSON file.
    output_dr: str
        Path to the directory where files will be generated.
    line_length : int
        Optional argument for the output file's maximum line length. Defaults to 80.
    """

    # get names
    file_path = Path(abi_file_path)
    filename = file_path.name
    contract_name = os.path.splitext(filename)[0]
    contract_path = Path(output_dir).joinpath(f"{contract_name}")

    # grab the templates
    contract_template, types_template = setup_templates()

    # render the code
    rendered_contract_code = render_contract_file(contract_name, contract_template, file_path)
    rendered_types_code = render_types_file(contract_name, types_template, file_path)

    # TODO: Add more features:
    # TODO:  events

    # Format the generated code using Black
    formatted_contract_code = format_code(rendered_contract_code, line_length)
    formatted_types_code = format_code(rendered_types_code, line_length)

    # Write the code to file
    write_code(f"{contract_path}Contract.py", formatted_contract_code)
    write_code(f"{contract_path}Types.py", formatted_types_code)


def render_contract_file(contract_name: str, contract_template: Template, abi_file_path: Path) -> str:
    """Returns a string of the contract file to be generated.

    Arguments
    ---------
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
    function_datas = {}
    for abi_function in get_abi_items(abi_file_path):
        if is_abi_function(abi_function):
            # TODO: investigate better typing here?  templete.render expects an object so we'll have to convert.
            name = abi_function.get("name", "")
            if name not in function_datas:
                function_data = {
                    # TODO: pass a typeguarded ABIFunction that has only required fields?
                    # name is required in the typeguard.  Should be safe to default to empty string.
                    "name": name,
                    "capitalized_name": capitalize_first_letter_only(name),
                    "input_names_and_types": [get_input_names_and_values(abi_function)],
                    "input_names": [get_input_names(abi_function)],
                    "outputs": [get_outputs(abi_function)],
                }
                function_datas[name] = function_data
            else:  # this function already exists, presumably with a different signature
                function_datas[name]["input_names_and_types"].append(get_input_names_and_values(abi_function))
                function_datas[name]["input_names"].append(get_input_names(abi_function))
                function_datas[name]["outputs"].append(get_outputs(abi_function))
                # input_names_and_types will need optional args at the end
                shared_input_names_and_types, unique_input_names_and_types = get_intersection_and_unique(
                    function_datas[name]["input_names_and_types"]
                )
                function_datas[name]["required_input_names_and_types"] = shared_input_names_and_types
                function_datas[name]["optional_input_names_and_types"] = []
                for name_and_type in unique_input_names_and_types:  # optional args
                    name_and_type += " | None = None"
                    function_datas[name]["optional_input_names_and_types"].append(name_and_type)
                # we will also need the names to be separated
                shared_input_names, unique_input_names = get_intersection_and_unique(
                    function_datas[name]["input_names"]
                )
                function_datas[name]["required_input_names"] = shared_input_names
                function_datas[name]["optional_input_names"] = unique_input_names
    # Render the template
    return contract_template.render(contract_name=contract_name, functions=list(function_datas.values()))


def render_types_file(contract_name: str, types_template: Template, abi_file_path: Path) -> str:
    """Returns a string of the types file to be generated.

    Arguments
    ---------
    contract_name : str
        The name of the contract to be parsed.
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
    events = [asdict(event) for event in get_events_for_abi(abi)]

    return types_template.render(contract_name=contract_name, structs=structs, events=events)


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
        if name := get_param_name(_input):
            python_type = solidity_to_python_type(_input.get("type", "unknown"))
        else:
            raise ValueError("Solidity function parameter name cannot be None")
        stringified_function_parameters.append(f"{avoid_python_keywords(name)}: {python_type}")
    return stringified_function_parameters


def stringify_parameters(parameters) -> list[str]:
    """Stringifies parameters.

    .. todo::
        handle empty strings.  Should replace them with 'arg1', 'arg2', and so one.
        recursively handle this too for evil nested tuples with no names.
    """
    stringified_function_parameters: list[str] = []
    arg_counter: int = 1
    for _input in parameters:
        if name := get_param_name(_input):
            stringified_function_parameters.append(avoid_python_keywords(name))
        else:
            name = f"arg{arg_counter}"
            arg_counter += 1
    return stringified_function_parameters


def get_input_names(function: ABIFunction) -> list[str]:
    """Returns function input name/type strings for jinja templating.

    i.e. for the solidity function signature:
    function doThing(address who, uint256 amount, bool flag, bytes extraData)

    the following list would be returned:
    ['who', 'amount', 'flag', 'extraData']

    Arguments
    ---------
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
        print("Usage: python script_name.py <path_to_abi_file> <contract_address> <output_dir>")
    else:
        # TODO: add a bash script to make this easier, i.e. ./pypechain './abis', './build'
        # TODO: make this installable so that other packages can use the command line tool
        main(sys.argv[1], sys.argv[2])

"""Programatically load agent policies"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import inspect
import os
import sys


def get_invoked_path():
    """
    Retrieves the file location of the script invoking this function.

    Returns
    -------
        str :
            The path of the script invoking this function.
    """
    frame = inspect.stack()[1]  # frame of the caller
    caller_module = inspect.getmodule(frame[0])
    return caller_module.__file__


def load_builtin_policies() -> dict[str, type]:
    """Grab the policy classes in the `elfpy/agents/policies` folder

    This function gets the directory of this file, appends the `policies` folder, and parses it for the script objects.

    Returns
    -------
    dict
        The dict is indexed by the name of the class, and the value is an policy object that can be invoked.
    """
    # get the frame of the current function
    frame = inspect.currentframe()
    # get the module of the current function
    module = inspect.getmodule(frame)
    # return the file location of the module
    this_file_directory = os.path.abspath(module.__file__)
    # get the parent directory
    agents_path = os.path.dirname(this_file_directory)
    policies_path = os.path.join(agents_path, "policies")
    # call the parse_folder_for_classes function with the folder path
    return parse_folder_for_classes(policies_path)


# def parse_folder_for_classes(folder_path: str) -> dict[str, type]:
#    """
#    Recursively parses a folder for Python files, imports each of them, and retrieves all the top-level classes.
#
#    Arguments
#    ---------
#        folder_path : str
#            The path to the folder to be parsed.
#
#    Returns:
#        dict
#            A dictionary where the keys are class names and the values are class objects.
#    """
#    class_dict = {}
#    for root, _, files in os.walk(folder_path):
#        for file_name in files:
#            if file_name.endswith(".py"):
#                file_path = os.path.join(root, file_name)
#                module_name = os.path.splitext(file_name)[0]
#                # create a spec from the file location
#                spec = importlib.util.spec_from_file_location(module_name, file_path)
#                # create a module from the spec
#                module = importlib.util.module_from_spec(spec)
#                # execute the module to populate its namespace
#                spec.loader.exec_module(module)
#                for _, obj in module.__dict__.items():
#                    # check that the object is a class (or dataclass) and top-level
#                    if isinstance(obj, type) and obj.__module__ == module_name:
#                        # add the class object to the dictionary with the class name as the key
#                        class_dict[obj.__name__] = obj
#    return class_dict


def parse_folder_for_classes(folder_path: str) -> dict[str, type]:
    """
    Recursively parses a folder for Python files, imports each of them, and retrieves all the top-level classes.

    Arguments
    ---------
        folder_path : str
            The path to the folder to be parsed.

    Returns:
        dict
            A dictionary where the keys are class names and the values are class objects.
    """
    class_dict = {}
    for root, _, files in os.walk(folder_path):
        for file_name in files:
            if file_name.endswith(".py"):
                file_path = os.path.join(root, file_name)
                module_name = os.path.splitext(file_name)[0]
                # create the module loader
                loader = importlib.machinery.SourceFileLoader(module_name, file_path)
                spec = importlib.util.spec_from_loader(loader.name, loader)
                # check if the module is already loaded
                if module_name in sys.modules:
                    module = sys.modules[module_name]
                else:
                    # import the module and add it to sys.modules
                    module = importlib.util.module_from_spec(spec)
                    print(f"{spec=}")
                    sys.modules[module_name] = module
                    loader.exec_module(module)
                for _, obj in module.__dict__.items():
                    # check that the object is a class (or dataclass) and top-level
                    if isinstance(obj, type) and obj.__module__ == module_name:
                        # add the class object to the dictionary with the class name as the key
                        class_dict[obj.__name__] = obj
    return class_dict

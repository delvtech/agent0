"""Formatting utilities."""
import keyword

from git import UpdateProgress


def avoid_python_keywords(name: str) -> str:
    """Make sure the variable name is not a reserved Python word.  If it is, prepend with an underscore.

    Arguments
    ---------
    name : str
       unsafe variable name.

    Returns
    -------
    str
        A string prepended with an underscore if it was a python reserved word.
    """
    if keyword.iskeyword(name) or keyword.issoftkeyword(name) or isbuiltin(name):
        return "_" + name

    return name


builtin_function_names = [
    "abs",
    "aiter",
    "all",
    "any",
    "ascii",
    "bin",
    "bool",
    "breakpoint",
    "bytearray",
    "bytes",
    "callable",
    "chr",
    "classmethod",
    "compile",
    "complex",
    "delattr",
    "dict",
    "dir",
    "divmod",
    "enumerate",
    "eval",
    "exec",
    "filter",
    "float",
    "format",
    "frozenset",
    "getattr",
    "globals",
    "hasattr",
    "hash",
    "help",
    "hex",
    "id",
    "input",
    "int",
    "isinstance",
    "issubclass",
    "iter",
    "len",
    "list",
    "locals",
    "map",
    "max",
    "min",
    "next",
    "object",
    "oct",
    "open",
    "ord",
    "pow",
    "print",
    "property",
    "repr",
    "reversed",
    "round",
    "set",
    "setattr",
    "slice",
    "sorted",
    "staticmethod",
    "str",
    "sum",
    "super",
    "tuple",
    "type",
    "vars",
    "zip",
    "import",
]

isbuiltin = frozenset(builtin_function_names).__contains__


def capitalize_first_letter_only(string: str) -> str:
    """Capitalizes the first letter of a string without affecting the rest of the string.
    capitalize() will lowercase the rest of the letters."""

    if len(string) < 2:
        return string
    return string[0].upper() + string[1:]

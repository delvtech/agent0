"""Formatting utilities."""
import keyword


def avoid_python_keywords(name: str) -> str:
    """Make sure the variable name is not a reserved Python word.  If it is, prepend with an underscore."""
    if keyword.iskeyword(name):
        return "_" + name

    return name

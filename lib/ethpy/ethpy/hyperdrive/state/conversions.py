"""Functions for converting Hyperdrive state values."""
from __future__ import annotations

import re


def camel_to_snake(snake_string: str) -> str:
    """Convert camel case string to snake case string."""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", snake_string).lower()


def snake_to_camel(snake_string: str) -> str:
    """Convert snake case string to camel case string."""
    # First capitalize the letters following the underscores and remove underscores
    camel_string = re.sub(r"_([a-z])", lambda x: x.group(1).upper(), snake_string)
    # Ensure the first character is lowercase to achieve lowerCamelCase
    return camel_string[0].lower() + camel_string[1:] if camel_string else camel_string

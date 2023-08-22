"""Utilities for templating."""
import os
from typing import NamedTuple

from jinja2 import Environment, FileSystemLoader, Template


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
    templates_dir = os.path.join(script_dir, "../templates")
    print(f"{templates_dir=}")
    env = Environment(loader=FileSystemLoader(templates_dir))
    contract_template = env.get_template("contract.jinja2")
    types_template = env.get_template("types.jinja2")
    return Templates(contract_template, types_template)

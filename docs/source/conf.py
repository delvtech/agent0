"""
Configuration file for the Sphinx documentation builder.

For the full list of built-in configuration values, see the documentation:
https://www.sphinx-doc.org/en/master/usage/configuration.html
"""

import sys
import os
import datetime
import tomli

# indicate where the elfpy Python package lives
elfpy_root = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))
sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.join(elfpy_root, "src"))


# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
def _get_project_meta():
    with open(os.path.join(elfpy_root, "pyproject.toml"), mode="rb") as pyproject:
        return tomli.load(pyproject)["project"]


# General information about the project.
pkg_meta = _get_project_meta()
project = str(pkg_meta["name"])
author = ", ".join([person["name"] for person in pkg_meta["authors"]])
organization = "Element Finance"
copyright = f" {datetime.date.today().year}, {organization}"

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
# The short X.Y version.
version = str(pkg_meta["version"])
# The full version, including alpha/beta/rc tags.
release = version

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.duration",  # gives reading length summaries at build time
    "sphinx.ext.todo",  # support for todo items
    "sphinx.ext.doctest",  # allows one to test code snippets against the python code to ensure synchrony
    "sphinx.ext.autodoc",  # allows rendering of docs automatically from the python code
    "sphinx.ext.autosummary",  # generates documents that contain all the necessary autodoc directives
    "sphinx_autodoc_typehints",  # insert typehints into the final docs
    "myst_parser",  # include .md files
    "sphinx.ext.napoleon",  # enables Sphinx to understand docstrings in Google format
    "numpydoc",  # enables NumPy docstring format
    "sphinx.ext.coverage",  # collect documentation coverage stats
    "autodocsumm",  # display a list of all class methods in table format
    "nbsphinx",  # to showcase Jupyter notebooks
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
autodoc_default_options = {"autosummary": True}
autosummary_generate = True

github_url = "https://github.com"
github_repo_org = "element-fi"
github_repo_name = "elf-simulations"
github_repo_slug = f"{github_repo_org}/{github_repo_name}"
github_repo_url = f"{github_url}/{github_repo_slug}"
extlinks = {
    "issue": (f"{github_repo_url}/issues/%s", "#%s"),
    "pr": (f"{github_repo_url}/pull/%s", "PR #%s"),
    "commit": (f"{github_repo_url}/commit/%s", "%s"),
}

# The master toctree document.
master_doc = "index"

# -- Options for autodocs -------------------------------------------------
autoclass_content = "class"
autodoc_member_order = "bysource"
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    # "exclude-members": "__dict__,__weakref__",
    "show-inheritance": True,
}
set_type_checking_flag = True
always_document_param_types = True
typehints_fully_qualified = True


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output
def setup(app):
    app.add_css_file("custom.css")


html_theme = "alabaster"
html_static_path = ["_static"]

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = {
    "sidebar_collapse": True,
    "show_powered_by": False,
    "relbarbgcolor": "black",
}

# Custom sidebar templates, must be a dictionary that maps document names
# to template names.
#
# This is required for the alabaster theme
# refs: http://alabaster.readthedocs.io/en/latest/installation.html#sidebars
# html_sidebars = {
#    '**': [
#        'about.html',
#        'badges.html',
#        'navigation.html',
#        'moreinfo.html',
#        'github.html',
#        'searchbox.html',
#    ],
# }

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = "en"

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
# today = ''
# Else, today_fmt is used as the format for a strftime call.
today_fmt = "%B %d, %Y"

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
html_title = f"{project} Documentation"

# A shorter title for the navigation bar.  Default is the same as html_title.
html_short_title = "Documentation"

# -- Options for todo extension ----------------------------------------------

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = False

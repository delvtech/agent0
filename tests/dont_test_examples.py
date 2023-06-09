"""Testing for example notebooks"""
import matplotlib

matplotlib.use("Agg")  # headless backend so that plots won't render

# pylint: disable=wrong-import-order
# pylint: disable=wrong-import-position
import unittest
import builtins
import logging
import os
import pathlib
import ast
import tempfile
from contextlib import redirect_stdout, redirect_stderr

import astunparse
from IPython.core.inputtransformer2 import TransformerManager
import jupytext

import elfpy.utils.outputs as output_utils


class TestExamples(unittest.TestCase):
    """Test functions for Jupyter notebooks"""

    def test_example_execution(self):
        """Tests example py files in the `examples/` folder to ensure that they run without error"""
        # pylint: disable=too-many-locals
        # pylint: disable=too-many-branches
        # pylint: disable=too-many-statements
        output_utils.setup_logging("test_examples")
        isp = TransformerManager()  # module for converting jupyter cell into source code
        example_location = os.path.join(os.path.dirname(pathlib.Path(__file__).parent.resolve()), "examples")
        for file in os.listdir(example_location):
            logging.info("file=%s", file)
            if not file.endswith("notebook.py"):
                continue
            # Convert the python text to normal (json) jupyter notebook format
            notebook = jupytext.read(os.path.join(example_location, file), fmt="py:percent")
            # Read the notebook cell by cell, grab the code & add it to a string
            first_code_cell = next(
                (cell for cell in notebook["cells"] if cell["cell_type"] == "code"),
                None,  # No code cells
            )
            if first_code_cell is None or "# test: skip-notebook" in first_code_cell["source"]:
                continue  # skip the whole file
            # Then start over checking it more carefully
            file_source = ""
            for cell in notebook["cells"]:
                if cell["cell_type"] != "code":  # only parse code blocks
                    continue
                cell_source_lines = cell["source"]
                if "# test: skip-cell" in cell_source_lines:  # optional ability to skip cells
                    continue
                code_lines = []
                for line in cell_source_lines.split("\n"):  # parse line-by-line for checks
                    if line.startswith("%"):  # skip jupyter magic commands
                        continue
                    if line.startswith("display("):  # skip display commands, as they're notebook-specific
                        continue
                    code_lines.append(line)
                cell_source = isp.transform_cell("\n".join(code_lines))  # recombine lines
                file_source += cell_source + "\n"
            logging.info("file_source=\n%s\n------------\n", file_source)
            # Convert the source code into a syntax tree to modify some config values
            tree = ast.parse(file_source)
            for node_idx, node in enumerate(tree.body):
                # type conditionals are used to narrow down the node type to assignment to a named object attribute
                if not isinstance(node, ast.Assign):
                    continue
                target = node.targets[0]
                if not isinstance(target, ast.Attribute):
                    continue
                if not isinstance(target.value, ast.Name):
                    continue
                obj = target.value.id  # object being modified
                attrib = target.attr  # attribute of object
                if obj == "config" and attrib in ["num_trading_days", "num_blocks_per_day"]:
                    test_value = 4  # reduces the total number of trades to keep things fast
                    tree.body[node_idx] = ast.Assign(
                        targets=[target],
                        value=ast.Constant(value=test_value, kind=None),
                        type_comment=node.type_comment,
                    )
            tree = ast.fix_missing_locations(tree)  # adds newlines to modified nodes
            # decompile ast into source, write to a fake file, execute the file
            # writing to a fake file (as opposed to just directly executing the source)
            # allows us to hold an environment state (e.g. import aliases) throughout execution
            try:
                with tempfile.NamedTemporaryFile(mode="w", suffix=".py") as ntf:
                    ntf.write(astunparse.unparse(tree))
                    ntf.seek(0)
                    cleaned_source = compile(tree, filename=ntf.name, mode="exec")
                    with open(os.devnull, "w", encoding="UTF-8") as tmp_file, redirect_stdout(
                        tmp_file
                    ), redirect_stderr(tmp_file):
                        global_env = {}
                        exec(cleaned_source, global_env)  # pylint: disable=exec-used
            except builtins.BaseException as exc:
                raise AssertionError(f"notebook {file} failed") from exc
        output_utils.close_logging()

"""Testing to ensure that notebooks run"""
import unittest
import os
import pathlib
import ast
import tempfile

import matplotlib

matplotlib.use("Agg")

from contextlib import redirect_stdout, redirect_stderr
import astunparse

from IPython.core.inputtransformer2 import TransformerManager
import nbformat


class TestNotebook(unittest.TestCase):
    def test_notebook_execution(self):
        isp = TransformerManager()
        notebook_location = os.path.join(
            os.path.dirname(pathlib.Path(__file__).parent.resolve()),
            os.path.join("examples", "notebooks"),
        )
        for file in os.listdir(notebook_location):
            if not file.endswith(".ipynb"):
                continue
            try:
                nb = nbformat.read(os.path.join(notebook_location, file), as_version=4)
                file_source = ""
                for cell in nb["cells"]:
                    if cell["cell_type"] != "code":
                        continue
                    cell_source_lines = cell["source"]
                    source_is_str = False
                    if isinstance(cell_source_lines, str):
                        cell_source_lines = cell_source_lines.split("\n")
                        source_is_str = True
                    if "# test: skip-cell" in cell_source_lines:
                        continue
                    code_lines = []
                    for line in cell_source_lines:
                        if line.startswith("%"):
                            continue
                        code_lines.append(line)
                        if source_is_str:
                            code_lines.append("\n")
                    cell_source = isp.transform_cell("".join(code_lines))
                    file_source += cell_source + "\n"
                tree = ast.parse(file_source)
                exec(compile(tree, filename="<ast>", mode="exec"))
                for node_idx, node in enumerate(tree.body):
                    if not isinstance(node, ast.Assign):
                        continue
                    target = node.targets[0]
                    if not isinstance(target, ast.Attribute):
                        continue
                    if not isinstance(target.value, ast.Name):
                        continue
                    obj = target.value.id
                    attrib = target.attr
                    if obj == "config" and attrib in ["num_trading_days", "num_blocks_per_day"]:
                        tree.body[node_idx] = ast.Assign(
                            targets=[target],
                            value=ast.Constant(value=2, kind=None),
                            type_comment=node.type_comment,
                        )
                        print(ast.dump(tree.body[node_idx]))

                # exec(compile(ast.fix_missing_locations(tree), filename="<ast>", mode="exec"))
                with tempfile.NamedTemporaryFile(mode="w", suffix=".py") as ntf:
                    ntf.write(astunparse.unparse(tree))
                    ntf.seek(0)
                    cleaned_source = compile(tree, filename=ntf.name, mode="exec")
                    with open(os.devnull, "w") as f, redirect_stdout(f), redirect_stderr(f):
                        global_env = {}
                        exec(cleaned_source, global_env)

            except Exception as exc:
                raise AssertionError(f"notebook {file} failed") from exc


if __name__ == "__main__":
    test = TestNotebook()
    test.test_notebook_execution()

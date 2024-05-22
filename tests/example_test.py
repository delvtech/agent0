"""System test for verifying that the agent0 repo examples work."""

from __future__ import annotations

import ast
import os
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from io import TextIOWrapper

import astunparse
import pytest


@pytest.fixture
def file_location(file_name: str) -> str:
    """Return the location of the file."""
    package_root = os.path.abspath(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
    return os.path.join(package_root, "examples/" + file_name)


@pytest.fixture
def file_contents(file_name: str) -> TextIOWrapper:
    """Return the file contents of the file."""
    package_root = os.path.abspath(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
    file_handle = open(os.path.join(package_root, "examples/" + file_name))
    return file_handle.readlines()


class Base:
    def prepare_tree_for_testing(self, tree):
        """Parse the tree & make required modifications."""
        return ast.fix_missing_locations(tree)

    def exec_tree(self, tree) -> None:
        """Execute the ast."""
        # decompile ast into source, write to a fake file, execute the file
        # writing to a fake file (as opposed to just directly executing the source)
        # allows us to hold an environment state (e.g. import aliases) throughout execution
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py") as ntf:
            ntf.write(astunparse.unparse(tree))
            ntf.seek(0)
            cleaned_source = compile(tree, filename=ntf.name, mode="exec")
            with (
                open(os.devnull, "w", encoding="UTF-8") as tmp_file,
                redirect_stdout(tmp_file),
                redirect_stderr(tmp_file),
            ):
                global_env = {}
                exec(cleaned_source, global_env)  # pylint: disable=exec-used


@pytest.mark.skip(reason="Temporarily skipping.")
class TestInteractiveHyperdriveForkingExamples(Base):
    """Test the example file."""

    FILE = "interactive_hyperdrive_forking_example.py"

    def prepare_tree_for_testing(self, tree):
        """Parse the tree & make required modifications."""
        for node_idx, node in enumerate(tree.body):
            # type conditionals are used to narrow down the node type to assignment to a named object attribute
            if isinstance(node, ast.Assign):
                target = node.targets[0]
                obj_name = target.id  # object being modified
                if obj_name == "NUM_TEST_TRADES":
                    test_value = 1  # reduces the total number of trades to keep things fast
                    tree.body[node_idx] = ast.Assign(
                        targets=[target],
                        value=ast.Constant(value=test_value, kind=None),
                        type_comment=node.type_comment,
                    )
        return ast.fix_missing_locations(tree)  # adds newlines to modified nodes

    @pytest.mark.parametrize("file_name", [FILE])
    def test_file_exists(self, file_location):
        """Make sure the file exists."""
        assert os.path.exists(file_location)
        assert os.path.isfile(file_location)

    @pytest.mark.parametrize("file_name", [FILE])
    @pytest.mark.docker
    def test_file_runs(self, file_contents):
        """Test that the example runs."""
        # Convert the source code into a syntax tree to modify some config values
        tree = self.prepare_tree_for_testing(ast.parse("\n".join(file_contents)))
        try:
            self.exec_tree(tree)
        except Exception as exc:
            raise AssertionError(f"notebook {self.FILE} failed") from exc


class TestInteractiveLocalHyperdriveAdvancedExamples(Base):
    """Test the example file."""

    FILE = "interactive_local_hyperdrive_advanced_example.py"

    def prepare_tree_for_testing(self, tree):
        """Parse the tree & make required modifications."""
        for node_idx, node in enumerate(tree.body):
            # type conditionals are used to narrow down the node type to assignment to a named object attribute
            if isinstance(node, ast.Expr):
                node_str = astunparse.unparse(node)
                if "run_dashboard" in node_str or "time.sleep" in node_str:
                    node_str = node_str.strip("\n")
                    tree.body[node_idx] = ast.Expr(
                        value=ast.Call(
                            func=ast.Name(id="print", ctx=ast.Load()),
                            args=[ast.Constant(s="skipping `" + node_str + "`")],
                            keywords=[],
                        ),
                    )
        return ast.fix_missing_locations(tree)  # adds newlines to modified nodes

    @pytest.mark.parametrize("file_name", [FILE])
    def test_file_exists(self, file_location):
        """Make sure the file exists."""
        assert os.path.exists(file_location)
        assert os.path.isfile(file_location)

    @pytest.mark.parametrize("file_name", [FILE])
    @pytest.mark.docker
    def test_file_runs(self, file_contents):
        """Test that the example runs."""
        # Convert the source code into a syntax tree to modify some config values
        tree = self.prepare_tree_for_testing(ast.parse("\n".join(file_contents)))
        try:
            self.exec_tree(tree)
        except Exception as exc:
            raise AssertionError(f"notebook {self.FILE} failed") from exc


class TestInteractiveLocalHyperdriveExamples(Base):
    """Test the example file."""

    FILE = "interactive_local_hyperdrive_example.py"

    @pytest.mark.parametrize("file_name", [FILE])
    def test_file_exists(self, file_location):
        """Make sure the file exists."""
        assert os.path.exists(file_location)
        assert os.path.isfile(file_location)

    @pytest.mark.parametrize("file_name", [FILE])
    @pytest.mark.docker
    def test_file_runs(self, file_contents):
        """Test that the example runs."""
        # Convert the source code into a syntax tree to modify some config values
        tree = self.prepare_tree_for_testing(ast.parse("\n".join(file_contents)))
        try:
            self.exec_tree(tree)
        except Exception as exc:
            raise AssertionError(f"notebook {self.FILE} failed") from exc


class TestInteractiveRemoteHyperdriveExamples(Base):
    """Test the example file."""

    FILE = "interactive_remote_hyperdrive_example.py"

    @pytest.mark.parametrize("file_name", [FILE])
    def test_file_exists(self, file_location):
        """Make sure the file exists."""
        assert os.path.exists(file_location)
        assert os.path.isfile(file_location)

    @pytest.mark.parametrize("file_name", [FILE])
    @pytest.mark.docker
    def test_file_runs(self, file_contents):
        """Test that the example runs."""
        # Convert the source code into a syntax tree to modify some config values
        tree = self.prepare_tree_for_testing(ast.parse("\n".join(file_contents)))
        try:
            self.exec_tree(tree)
        except Exception as exc:
            raise AssertionError(f"notebook {self.FILE} failed") from exc


class TestStreamlitExamples(Base):
    """Test the example file."""

    FILE = "streamlit_example.py"

    def prepare_tree_for_testing(self, tree):
        """Parse the tree & make required modifications."""
        for node_idx, node in enumerate(tree.body):
            # type conditionals are used to narrow down the node type to assignment to a named object attribute
            if isinstance(node, ast.Assign):
                target = node.targets[0]
                obj_name = target.id  # object being modified
                if obj_name == "DEMO_NUM_ITERATIONS":
                    test_value = 1  # reduces the total number of trades to keep things fast
                    tree.body[node_idx] = ast.Assign(
                        targets=[target],
                        value=ast.Constant(value=test_value, kind=None),
                        type_comment=node.type_comment,
                    )
            if isinstance(node, ast.Expr):
                node_str = astunparse.unparse(node)
                if "run_dashboard" in node_str or "time.sleep" in node_str:
                    node_str = node_str.strip("\n")
                    tree.body[node_idx] = ast.Expr(
                        value=ast.Call(
                            func=ast.Name(id="print", ctx=ast.Load()),
                            args=[ast.Constant(s="skipping `" + node_str + "`")],
                            keywords=[],
                        ),
                    )
        return ast.fix_missing_locations(tree)  # adds newlines to modified nodes

    @pytest.mark.parametrize("file_name", [FILE])
    def test_file_exists(self, file_location):
        """Make sure the file exists."""
        assert os.path.exists(file_location)
        assert os.path.isfile(file_location)

    @pytest.mark.parametrize("file_name", [FILE])
    @pytest.mark.docker
    def test_file_runs(self, file_contents):
        """Test that the example runs."""
        # Convert the source code into a syntax tree to modify some config values
        tree = self.prepare_tree_for_testing(ast.parse("\n".join(file_contents)))
        try:
            self.exec_tree(tree)
        except Exception as exc:
            raise AssertionError(f"notebook {self.FILE} failed") from exc

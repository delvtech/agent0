"""Project fixture"""
from pathlib import Path

import ape
from ape.managers.project import ProjectManager
import pytest

# TODO: convert to not use ape
pytestmark = pytest.mark.skip("disabled until converted to not use ape")

@pytest.fixture(scope="function")
def project() -> ProjectManager:
    "Returns the ape project."
    project_root = Path.cwd()
    return ape.Project(path=project_root)

"""Project fixture"""
from pathlib import Path

import ape
from ape.managers.project import ProjectManager
import pytest


@pytest.fixture(scope="function")
def project() -> ProjectManager:
    "Returns the ape project."
    project_root = Path.cwd()
    return ape.Project(path=project_root)

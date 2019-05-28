import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Union

import pytest

from .common import TestParam, scan_tree


@dataclass
class CreateTestCase(TestParam):
    """Simple test parameters for tests.

    This makes reading much, much easier and makes developers happier.

    Attributes:
        site_packages: flag that controls site package copy
        overwrite: flag that controls rewrite entire virtual env folder
        symlinks: flag that controls symlinks instead of copy
        upgrade: flag that controls whether to upgrade python to latest
        include_pip: flag that controls if pip is included
        prompt: control how prompt is displayed while in virtual env
        python: control which python to use in virtual env
        verbose: setting for output... generally only used for debugging
        interactive: setting for controlling steps... typically for debug
        dry_run: setting to identify what might happen... typically for debug

    """

    site_packages: bool = False
    overwrite: bool = False
    symlinks: bool = False
    upgrade: bool = False
    include_pip: bool = False
    prompt: str = ""
    python: str = ""
    verbose: Union[int, bool] = False
    interactive: bool = False
    dry_run: bool = False

    @property
    def kwds(self):
        return asdict(self)


@pytest.mark.parametrize(
    "test_case",
    [
        CreateTestCase(site_packages=True),
        CreateTestCase(overwrite=True),
        CreateTestCase(symlinks=True),
        CreateTestCase(upgrade=True),
        CreateTestCase(include_pip=True),
        CreateTestCase(prompt="temp"),
        # use current python3 with a <major>.<minor> version
        CreateTestCase(python=".".join(map(str, sys.version_info[0:2]))),
        # simple python3
        CreateTestCase(python="3"),
        CreateTestCase(verbose=1),
        CreateTestCase(interactive=True),
        CreateTestCase(dry_run=True),
    ],
)
def test_create(venv_path, test_case):
    from vsh import api

    # TODO: mock dry-runs and interactive behaviors
    test_case.interactive = False
    test_case.dry_run = False

    pre_create_folder_structure = list(scan_tree(venv_path))  # noqa

    expected_venv_path = venv_path
    assert not expected_venv_path.exists()
    created_path = api.create(path=expected_venv_path, **test_case.kwds)
    assert isinstance(created_path, Path)
    assert created_path.exists()
    assert expected_venv_path.exists()
    assert created_path == expected_venv_path

    post_create_folder_structure = list(scan_tree(expected_venv_path))  # noqa
    # Validate structure
    expected_valid = True if not any([test_case.dry_run, test_case.upgrade]) else False
    assert api.validate_environment(expected_venv_path) is expected_valid

    expected_structure = {Path("bin/python")}

    new_files = set(post_create_folder_structure) - set(pre_create_folder_structure)
    for path in expected_structure:
        assert path in new_files
    for path in post_create_folder_structure:
        actual_path = venv_path / path
        if actual_path.exists():
            actual_path.unlink()

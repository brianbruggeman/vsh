import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Union

import pytest

from .common import scan_tree, TestParam


@dataclass
class CreateTestParams(TestParam):
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
    prompt: str = ''
    python: str = ''
    verbose: Union[int, bool] = False
    interactive: bool = False
    dry_run: bool = False


@pytest.mark.unit
@pytest.mark.parametrize("params", [
    CreateTestParams(),
    CreateTestParams(site_packages=True),
    CreateTestParams(overwrite=True),
    CreateTestParams(symlinks=True),
    CreateTestParams(upgrade=True),
    CreateTestParams(include_pip=True),
    CreateTestParams(prompt='temp'),
    # use current python3 with a <major>.<minor> version
    CreateTestParams(python='.'.join(map(str, sys.version_info[0:2]))),
    # simple python3
    CreateTestParams(python='3'),
    CreateTestParams(verbose=True),
    CreateTestParams(interactive=True),
    CreateTestParams(dry_run=True),
    ])
def test_create(tmpdir, params):
    from vsh import api
    # TODO: mock dry-runs and interactive behaviors
    params.interactive = False
    params.dry_run = False

    name = 'test-create'
    path = Path(str(tmpdir.join(name)))
    assert not path.exists()
    created_path = api.create(path=path, **params)
    assert created_path == path
    assert created_path.exists()

    created_paths = []
    for root, directories, files in os.walk(str(created_path)):
        relroot = Path(root).relative_to(created_path)

        for directory in directories:
            dirpath = relroot / directory
            created_paths.append(dirpath)

        for filename in files:
            filepath = relroot / filename
            created_paths.append(filepath)

    files_in_structure = list(scan_tree(path))  # noqa
    # Validate structure
    expected_valid = True if not any([params.dry_run, params.upgrade]) else False
    assert api.validate_environment(path) is expected_valid


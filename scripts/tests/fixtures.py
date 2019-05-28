import os
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture(scope="function")
def workon_home(tmpdir) -> Generator[Path, None, None]:
    old_workon_home = os.environ.get("WORKON_HOME", "")
    # tmpdir is actually a LocalPath vs a PosixPath and for some reason
    # the api is not the same.
    new_workon_home = Path(str(tmpdir))
    os.environ["WORKON_HOME"] = str(new_workon_home)
    yield new_workon_home
    if old_workon_home:
        os.environ["WORKON_HOME"] = old_workon_home


@pytest.fixture(scope="function")
def venv_path(workon_home) -> Path:
    venv_name = "mocked-venv"
    venv_path = workon_home / venv_name
    return venv_path


@pytest.fixture(scope="function")
def package_path() -> Path:
    import vsh

    return Path(vsh.__file__).parent


@pytest.fixture(scope="function")
def repo_path(package_path) -> Path:
    return package_path.parent

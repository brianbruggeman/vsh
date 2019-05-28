import os
from pathlib import Path

import pytest


def touch(path, mode=0o666, dir_fd=None, **kwargs):
    if not path.parent.absolute().exists():
        path.parent.absolute().mkdir(parents=True, exist_ok=True)
    flags = os.O_CREAT | os.O_APPEND
    with os.fdopen(os.open(path, flags=flags, mode=mode, dir_fd=dir_fd)) as f:
        os.utime(
            f.fileno() if os.utime in os.supports_fd else str(path), dir_fd=None if os.supports_fd else dir_fd, **kwargs
        )


def scan_tree(path):
    """Finds files in tree

    * Order is random
    * Folders which start with . and _ are excluded unless excluded is used (e.g. [])
    * This list is memoized

    Args:
        top_path (str): top of folder to search

    Yields:
        str: paths as found
    """
    for root, folders, files in os.walk(path):
        relative_root = Path(root).relative_to(path)
        # Control traversal
        folders[:] = [f for f in folders if f not in ['.git']]
        # Yield files
        for filename in files:
            relative_path = relative_root / filename
            yield relative_path


@pytest.mark.parametrize(
    'name, error_name, check',
    [
        # Just remove without pre-creating; an error should be raised with check=True
        (None, 'InvalidEnvironmentError', True),
        # Just remove without pre-creating; an error should not be raised with check=False
        (None, None, False),
        # Remove after creating
        ('test-create', None, None),
    ],
)
def test_remove(workon_home, venv_path, name, error_name, check):
    from vsh.api import create, remove
    from vsh import errors

    if name:
        assert not venv_path.exists()
        path = create(path=venv_path)
    else:
        name = 'this-should-not-exist'
        path = workon_home / name
        assert not path.exists()

    ExpectedException = getattr(errors, error_name) if error_name is not None else None
    if check is True:
        with pytest.raises(ExpectedException):
            remove(path, check=check)
    else:
        remove(path, check=check)

    assert not os.path.exists(path)


def test_show_venvs(venv_path, capfd):
    from vsh.api import create, remove, show_venvs

    create(path=venv_path)
    # must be a path that contains virtual environments
    show_venvs(path=venv_path.parent)
    capture = capfd.readouterr()
    remove(path=venv_path)
    assert venv_path.name in capture.out


def test_show_version(capfd):
    from vsh.api import show_version
    from vsh.__metadata__ import package_metadata

    version = package_metadata['version']
    show_version()

    out, err = capfd.readouterr()
    assert version in out


@pytest.mark.parametrize(
    'structure, check, expected',
    [
        # Nothing
        ([], False, False),
        # Valid
        (
            [
                'pyvenv.cfg',
                'bin/activate',
                'bin/activate.csh',
                'bin/activate.fish',
                'bin/python',
                'bin/python3',
                'bin/python3.6',
                'include/foo',
                'lib/python3.6/site-packages/bar',
            ],
            True,
            True,
        ),
    ],
)
def test_validate_environment(venv_path, structure, check, expected):
    from vsh import api

    for path in structure:
        touch(venv_path / path)
    assert expected == api.validate_environment(venv_path, check=check)

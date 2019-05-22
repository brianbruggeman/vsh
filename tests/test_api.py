import os
from pathlib import Path

import pytest


def touch(path, mode=0o666, dir_fd=None, **kwargs):
    if not path.parent.absolute().exists():
        path.parent.absolute().mkdir(parents=True, exist_ok=True)
    flags = os.O_CREAT | os.O_APPEND
    with os.fdopen(os.open(path, flags=flags, mode=mode, dir_fd=dir_fd)) as f:
        os.utime(
            f.fileno() if os.utime in os.supports_fd else str(path),
            dir_fd=None if os.supports_fd else dir_fd, **kwargs
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


@pytest.mark.unit
@pytest.mark.parametrize("command, expected_output", [
    # Simple echo command
    ('echo "Hello, World!"', "Hello, World!"),
    ('env', "VSH=test-create"),
    ])
def test_enter(tmpdir, capsys, command, expected_output):
    from vsh.api import create, enter

    name = 'test-create'
    path = Path(str(tmpdir.join(name)))
    assert not path.exists()

    # Make sure there's a venv availabl
    created_path = create(path=path, overwrite=True)

    # Then run the command
    enter(created_path, command)

    # TODO: Make this actually work
    # Validate that the command performed correctly
    # captured = capsys.readouterr()
    # assert expected_output in captured.out


@pytest.mark.unit
@pytest.mark.parametrize("name, error_name, check", [
    # Just remove without pre-creating; an error should be raised with check=True
    (None, 'InvalidEnvironmentError', True),
    # Just remove without pre-creating; an error should not be raised with check=False
    (None, None, False),
    # Remove after creating
    ('test-create', None, None),
    ])
def test_remove(tmpdir, name, error_name, check):
    from vsh.api import create, remove
    from vsh import errors

    if name:
        path = Path(str(tmpdir.join(name)))
        assert not path.exists()
        path = create(path)
    else:
        name = 'this-should-not-exist'
        path = Path(str(tmpdir.join(name)))
        assert not path.exists()

    ExpectedException = getattr(errors, error_name) if error_name is not None else None
    if check is True:
        with pytest.raises(ExpectedException):
            remove(path, check=check)
    else:
        remove(path, check=check)

    assert not os.path.exists(path)


@pytest.mark.unit
def test_show_envs(tmpdir, capsys):
    from vsh.api import create, remove, show_envs

    name = 'test-show-envs'
    path = Path(str(tmpdir.join(name)))
    create(path)
    show_envs(str(tmpdir))
    remove(path)

    out, err = capsys.readouterr()
    assert name in out


@pytest.mark.unit
def test_show_version(tmpdir, capsys):
    from vsh.api import show_version
    from vsh.__metadata__ import package_metadata

    version = package_metadata['version']
    show_version()

    out, err = capsys.readouterr()
    assert version in out


@pytest.mark.unit
@pytest.mark.parametrize("structure, check, expected", [
    # Nothing
    ([], False, False),
    # Valid
    ([
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
        True),
    ])
def test_validate_environment(tmpdir, structure, check, expected):
    from vsh import api

    tmp_venv = Path(str(tmpdir.join('test-validate-environment')))
    for path in structure:
        touch(tmp_venv.joinpath(path))
    assert expected == api.validate_environment(tmp_venv, check=check)

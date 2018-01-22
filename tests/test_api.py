import os
import sys
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
        rel = Path(root.replace(path, '').lstrip('/'))
        # Control traversal
        folders[:] = [f for f in folders if f not in ['.git']]
        # Yield files
        for filename in files:
            relpath = rel.joinpath(filename)
            yield relpath


@pytest.mark.unit
@pytest.mark.parametrize("site_packages, overwrite, symlinks, upgrade, include_pip, prompt, python, verbose, interactive, dry_run", [
    # Defaults
    (None, None, None, None, None, None, None, None, None, None),
    # include_pip is False
    (None, None, None, None, False, None, None, None, None, None),
    # use python
    (None, None, None, None, None, None, '.'.join(map(str, sys.version_info[0:2])), None, None, None),
    #
    ])
def test_create(tmpdir, site_packages, overwrite, symlinks, upgrade, include_pip, prompt, python, verbose, interactive, dry_run):
    from vsh import api

    name = 'test-create'
    path = str(tmpdir.join(name))
    assert not os.path.exists(path)

    created_path = api.create(path=path, site_packages=site_packages, overwrite=overwrite, symlinks=symlinks, upgrade=upgrade,
                              include_pip=include_pip, python=python, prompt=prompt, verbose=verbose, interactive=interactive, dry_run=dry_run)
    assert created_path == path
    assert os.path.exists(created_path)

    created_paths = []
    for root, directories, files in os.walk(created_path):
        relroot = os.path.join(root.replace(created_path, '').lstrip('/'))

        for directory in directories:
            dirpath = os.path.join(relroot, directory)
            created_paths.append(dirpath)

        for filename in files:
            filepath = os.path.join(relroot, filename)
            created_paths.append(filepath)

    files_in_structure = list(scan_tree(path))  # noqa
    # Validate structure
    assert api.validate_environment(path) is True


@pytest.mark.unit
@pytest.mark.parametrize("command, expected_output", [
    # Simple echo command
    ('echo "Hello, World!"', "Hello, World!"),
    ('env', "VSH=test-create"),
    ])
def test_enter(tmpdir, capsys, command, expected_output):
    from vsh.api import create, enter

    name = 'test-create'
    path = str(tmpdir.join(name))
    assert not os.path.exists(path)

    # Make sure there's a venv available
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
        path = str(tmpdir.join(name))
        assert not os.path.exists(path)
        path = create(path)
    else:
        name = 'this-should-not-exist'
        path = str(tmpdir.join(name))
        assert not os.path.exists(path)

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
    path = str(tmpdir.join(name))
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

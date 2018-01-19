import os
import sys

import pytest


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
    from vesty.api import create

    name = 'test-create'
    path = str(tmpdir.join(name))
    assert not os.path.exists(path)

    created_path = create(path=path, site_packages=site_packages, overwrite=overwrite, symlinks=symlinks, upgrade=upgrade, include_pip=include_pip, python=python, prompt=prompt, verbose=verbose, interactive=interactive, dry_run=dry_run)
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

    # Validate structure
    unexpected_paths = []
    expected_paths = [
        'pyvenv.cfg',
        'bin',
        'bin/activate',
        'bin/python',
        'include',
        'lib',
        ]
    if include_pip is not False:
        expected_paths.append('bin/pip')
    else:
        unexpected_paths.append('bin/pip')

    assert all([expected_path in created_paths for expected_path in expected_paths])
    assert all([unexpected_path not in created_paths for unexpected_path in unexpected_paths])


@pytest.mark.unit
@pytest.mark.parametrize("command, expected_output", [
    # Simple echo command
    ('echo "Hello, World!"', "Hello, World!"),
    ('env', "VES=test-create"),
    ])
def test_enter(tmpdir, capsys, command, expected_output):
    from vesty.api import create, enter

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
    from vesty.api import create, remove
    from vesty import errors

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
    from vesty.api import create, remove, show_envs

    name = 'test-show-envs'
    path = str(tmpdir.join(name))
    create(path)
    show_envs(str(tmpdir))
    remove(path)

    out, err = capsys.readouterr()
    assert name in out


@pytest.mark.unit
def test_show_version(tmpdir, capsys):
    from vesty.api import show_version
    from vesty.__metadata__ import package_metadata

    version = package_metadata['version']
    show_version()

    out, err = capsys.readouterr()
    assert version in out

import os
import shlex
from unittest.mock import MagicMock

import pytest


@pytest.mark.unit
@pytest.mark.parametrize('command, expected, exit_code', [
    ('vsh --help', {}, 0),
    ('vsh test-vsh-cli echo "hi"', {'create': 1, 'enter': 1}, 0),
    ('vsh -r test-vsh-cli', {'remove': 1}, 0),
    ('vsh -e --path ~/tmp/test-vsh-cli env', {'create': 1, 'enter': 1, 'remove': 1}, 0),
    ('vsh --version', {'show_version': 1}, 0),
    ('vsh --no-pip test-vsh-cli env', {'create': 1, 'enter': 1}, 0),
    ('vsh --ls', {'show_envs': 1}, 0),
    ('vsh', {}, 1),
    ])
def test_vsh_cli(tmpdir, mocked_api, command, expected, click_runner, exit_code):
    """Tests `vsh` command-line interface"""
    from vsh.cli.vsh import vsh

    os.environ['WORKON_HOME'] = str(tmpdir)

    command = shlex.split(command)[1:]

    result = click_runner.invoke(vsh, command)
    assert result.exit_code == exit_code

    called = {k: v.call_count for k, v in mocked_api.items() if v.call_count != 0}
    assert called == expected


@pytest.mark.unit
def test_vsh_cli_multi_command(tmpdir, click_runner, mocked_api, venv_path):
    """Tests `vsh` command-line interface with multiple lines"""
    from vsh import api
    from vsh.cli.vsh import vsh

    os.environ['WORKON_HOME'] = str(tmpdir)

    commands = [
        ('vsh test-vsh-cli echo "hi"', False),
        ('vsh -e test-vsh-cli echo "hi"', True),
        ]

    for command, exists in commands:
        command = shlex.split(command)[1:]

        api.validate_environment = MagicMock(return_value=exists)

        result = click_runner.invoke(vsh, command)
        assert result.exit_code == 0

    expected = {'create': 1, 'enter': 2}

    called = {k: v.call_count for k, v in mocked_api.items() if v.call_count != 0}
    assert called == expected

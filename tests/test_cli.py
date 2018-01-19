import os
import shlex
from unittest.mock import MagicMock

import pytest


@pytest.mark.unit
@pytest.mark.parametrize('command, expected, exit_code', [
    ('ves --help', {}, 0),
    ('ves test-ves-cli echo "hi"', {'create': 1, 'enter': 1}, 0),
    ('ves -r test-ves-cli', {'remove': 1}, 0),
    ('ves -e --path ~/tmp/test-ves-cli env', {'create': 1, 'enter': 1, 'remove': 1}, 0),
    ('ves --version', {'show_version': 1}, 0),
    ('ves --no-pip test-ves-cli env', {'create': 1, 'enter': 1}, 0),
    ('ves --ls', {'show_envs': 1}, 0),
    ('ves', {}, 1),
    ])
def test_ves_cli(tmpdir, mocked_api, command, expected, click_runner, exit_code):
    """Tests `ves` command-line interface"""
    from vesty.cli.ves import ves

    os.environ['WORKON_HOME'] = str(tmpdir)

    command = shlex.split(command)[1:]

    result = click_runner.invoke(ves, command)
    assert result.exit_code == exit_code

    called = {k: v.call_count for k, v in mocked_api.items() if v.call_count != 0}
    assert called == expected


@pytest.mark.unit
def test_ves_cli_multi_command(tmpdir, click_runner, mocked_api, venv_path):
    """Tests `ves` command-line interface with multiple lines"""
    from vesty import api
    from vesty.cli.ves import ves

    os.environ['WORKON_HOME'] = str(tmpdir)

    commands = [
        ('ves test-ves-cli echo "hi"', False),
        ('ves -e test-ves-cli echo "hi"', True),
        ]

    for command, exists in commands:
        command = shlex.split(command)[1:]

        api.validate_environment = MagicMock(return_value=exists)

        result = click_runner.invoke(ves, command)
        assert result.exit_code == 0

    expected = {'create': 1, 'enter': 2}

    called = {k: v.call_count for k, v in mocked_api.items() if v.call_count != 0}
    assert called == expected

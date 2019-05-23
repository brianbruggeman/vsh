import os
import shlex
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List

import pytest


@dataclass
class Counts:
    """Stores call counts of various api methods and contains methods
    to help capture and validate call counts

    Attributes:
        create: expected call count for vsh.api.create
        enter: expected call count for vsh.api.enter
        remove: expected call count for vsh.api.remove
        show_envs: expected call count for vsh.api.show_envs
        show_version: expected call count for vsh.api.show_version

    """
    create: int = 0
    enter: int = 0
    remove: int = 0
    show_envs: int = 0
    show_version: int = 0

    def check(self) -> Dict[str, bool]:
        """Returns a dictionary of boolean which represents whether or
        not the actual call counts matched the expected call counts.
        """
        import vsh.api

        counts = {
            method_name: getattr(vsh.api, method_name).call_count == expected_call_count
            for method_name, expected_call_count in asdict(self).items()
            }
        return counts

    def mock_all(self, mocker, venv_path: Path, exit_code: int = 0):
        """Mocks all tracked api methods

        Args:
            mocker: pytest-mock's mocker fixture
            venv_path: path to virtual environment under test
            exit_code: the expected exit code of the vsh.api.enter call
        """
        self.mock_create(mocker=mocker, venv_path=venv_path)
        self.mock_enter(mocker=mocker, exit_code=exit_code)
        self.mock_remove(mocker=mocker, venv_path=venv_path)
        self.mock_show_envs(mocker=mocker)
        self.mock_show_version(mocker=mocker)

    def mock_create(self, mocker, venv_path: Path):
        mocker.patch('vsh.api.create', return_value=venv_path)

    def mock_enter(self, mocker, exit_code: int = 0):
        mocker.patch('vsh.api.enter', return_value=exit_code)

    def mock_remove(self, mocker, venv_path: Path):
        mocker.patch('vsh.api.remove', return_value=venv_path)

    def mock_show_envs(self, mocker):
        mocker.patch('vsh.api.show_envs')

    def mock_show_version(self, mocker):
        mocker.patch('vsh.api.show_version')


@dataclass
class VshCliTestCase:
    """Test case class for vsh cli

    Attributes:
        command: the command to run using vsh cli
        exit_code: the expected exit code
        counts: the call counts for each of the mocked api methods

    """
    command: str = ''
    exit_code: int = 0
    counts: Counts = field(default_factory=Counts)


@dataclass
class VshMultiCliTestCase:
    """Test case class for vsh cli

    Attributes:
        command: the command to run using vsh cli
        exit_code: the expected exit code
        counts: the call counts for each of the mocked api methods

    """
    commands: List[str] = field(default_factory=list)
    exit_code: int = 0
    counts: Counts = field(default_factory=Counts)


@pytest.mark.unit
@pytest.mark.parametrize('test_case', [
    VshCliTestCase(command='vsh', exit_code=1),
    VshCliTestCase(command='vsh --help'),
    VshCliTestCase(command='vsh -l', counts=Counts(show_envs=1)),
    VshCliTestCase(command='vsh --list', counts=Counts(show_envs=1)),
    VshCliTestCase(command='vsh -C test-vsh-cli', counts=Counts(create=1)),
    VshCliTestCase(command='vsh test-vsh-cli echo "hi"', counts=Counts(create=1, enter=1)),
    VshCliTestCase(command='vsh -r test-vsh-cli', counts=Counts(remove=1)),
    VshCliTestCase(command='vsh -e --path ~/tmp/test-vsh-cli env', counts=Counts(create=1, enter=1, remove=1)),
    VshCliTestCase(command='vsh --version', counts=Counts(show_version=1)),
    VshCliTestCase(command='vsh --no-pip test-vsh-cli env', counts=Counts(create=1, enter=1)),
    VshCliTestCase(command='vsh -C tmp-venv', counts=Counts(create=1)),
    ])
def test_vsh_cli(workon_home, test_case, click_runner, mocker, venv_path):
    """Tests `vsh` command-line interface"""
    import vsh

    test_case.counts.mock_all(mocker, venv_path=venv_path, exit_code=test_case.exit_code)

    pre_exists = set()
    for root, folders, files in os.walk(workon_home):
        rel_root = Path(root).relative_to(workon_home)
        for folder_name in folders:
            folder_path = rel_root / folder_name
            pre_exists.add(folder_path)
        for file_name in files:
            file_path = rel_root / file_name
            pre_exists.add(file_path)

    command = shlex.split(test_case.command)[1:]

    result = click_runner.invoke(vsh.cli.vsh, command)
    assert result.exit_code == test_case.exit_code

    actual = test_case.counts.check()
    assert all(actual.values())


@pytest.mark.parametrize('test_case', [
    VshMultiCliTestCase(commands=[
        'vsh test-vsh-cli echo "hi"',
        'vsh -e test-vsh-cli echo "hi"',
        ],
        counts=Counts(create=2, enter=2, remove=1)),
    ])
def test_vsh_cli_multi_command(test_case, click_runner, mocker, venv_path):
    """Tests `vsh` command-line interface with multiple lines"""
    import vsh

    test_case.counts.mock_all(mocker, venv_path=venv_path, exit_code=test_case.exit_code)

    for command in test_case.commands:
        command = shlex.split(command)[1:]

        result = click_runner.invoke(vsh.cli.vsh, command)
        assert result.exit_code == 0, result.stdout

    actual = test_case.counts.check()
    assert all(actual.values())

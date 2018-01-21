from collections import Counter
from unittest.mock import MagicMock

import pytest

counts = Counter()


@pytest.fixture(scope='function')
def click_runner():
    from vsh.cli.click.testing import CliRunner

    runner = CliRunner()
    yield runner


@pytest.fixture(scope='function')
def package_name():
    from vsh.__metadata__ import package_metadata

    return package_metadata['name']


@pytest.fixture(scope='function')
def package_version():
    from vsh.__metadata__ import package_metadata

    return package_metadata['version']


@pytest.fixture(scope='function')
def venv_path(tmpdir):
    venv_name = 'mocked-venv'
    venv_path = str(tmpdir.join(venv_name))
    return venv_path


@pytest.fixture(scope='function')
def mock_api_create(venv_path):
    from vsh import api

    api.create = MagicMock(return_value=venv_path)
    return api.create


@pytest.fixture(scope='function')
def mock_api_enter():
    from vsh import api

    process_exit_code = 0
    api.enter = MagicMock(return_value=process_exit_code)
    return api.enter


@pytest.fixture(scope='function')
def mock_api_remove(venv_path):
    from vsh import api

    api.remove = MagicMock(return_value=venv_path)
    return api.remove


@pytest.fixture(scope='function')
def mock_api_show_envs():
    from vsh import api

    api.show_envs = MagicMock(return_value=None)
    return api.show_envs


@pytest.fixture(scope='function')
def mock_show_version():
    from vsh import api

    api.show_version = MagicMock(return_value=None)
    return api.show_version


@pytest.fixture(scope='function')
def mocked_api(mock_api_create, mock_api_enter, mock_api_remove, mock_api_show_envs, mock_show_version):
    """Mocks vsh api"""

    return {'create': mock_api_create,
            'enter': mock_api_enter,
            'remove': mock_api_remove,
            'show_envs': mock_api_show_envs,
            'show_version': mock_show_version,
            }

# Use a decorator, @pytest.mark.<marker_id>, for tests that meet
# the qualifications for the cli_options.  If --{marker_id} is not
# present on the command-line, then the test will be skipped.
import pytest


cli_options = {
    'stress': 'run stress tests',
    'slow': 'run slow-running tests',
    }


def pytest_addoption(parser):
    for marker_id, help_string in cli_options.items():
        cli_option = f'--{marker_id}'
        parser.addoption(cli_option, action='store_true', help=help_string)


def pytest_collection_modifyitems(config, items):
    # Skip slow if option not present
    for marker_id in cli_options.keys():
        add_marker(marker_id, config, items)


def add_marker(marker_id, config, items, reason=None):
    cli_option = f'--{marker_id}'
    reason = reason or f'need {cli_option} option to run'
    if not config.getoption(cli_option):
        skip_slow = pytest.mark.skip(reason=reason)
        for item in items:
            if marker_id in item.keywords:
                item.add_marker(skip_slow)

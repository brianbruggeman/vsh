import platform

import pytest

platform_python = 'python' if platform.python_implementation() == 'CPython' else platform.python_implementation().lower()
platform_version = platform.python_version()


# @pytest.mark.parametrize('data', [
#     {'name': '.', 'expected': (platform_python, platform_version)},
#     {'name': '37', 'expected': ('python', '3.7')},
#     {'name': 'pypy35', 'expected': ('pypy', '3.5')},
#     {'name': 'pypy6', 'expected': ('pypy', '6')},
#     {'name': 'p37', 'expected': ('python', '3.7')},
#     {'name': 'py37', 'expected': ('python', '3.7')},
#     {'name': '375', 'expected': ('python', '3.7.5')},
#
#     ])
# def test_expand_interpreter_name(data):
#     from vsh.api import _expand_interpreter_name
#
#     name = data['name']
#     expected = data['expected']
#
#     assert _expand_interpreter_name(name) == expected

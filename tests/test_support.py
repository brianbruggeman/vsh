from textwrap import dedent
from unittest import mock

import pytest


@pytest.mark.unit
@pytest.mark.parametrize('text, verbose, expected', [
    # Simple
    ('Hello, World!', None, 'Hello, World!\n'),
    # Multi-line
    (dedent("""
    Another
    World!
    """), None, '\nAnother\nWorld!\n\n'),
    # Check verbose = False
    ('Stranger Things', False, '')
    ])
def test_echo(capsys, text, verbose, expected):
    from vesty.cli.support import echo

    echo(text, verbose=verbose)
    out, err = capsys.readouterr()
    assert out == expected


@pytest.mark.unit
@pytest.mark.parametrize('keystroke, valid_responses, default, expected, raised', [
    ('\r', None, None, 'n', None),
    ('n', None, None, 'n', None),
    ('y', None, None, 'y', None),
    ('y', ['A', 'b', 'c'], None, 'y', SystemExit),
    ('\r', ['A', 'b', 'c'], None, 'A', None),
    ('\r', ['A', 'b', 'c'], 'c', 'c', None),
    ('\r', ['A', 'b', 'c'], 'd', 'd', None),
    ('a', ['A', 'b', 'c'], 'd', 'd', SystemExit),
    ('A', ['A', 'b', 'c'], 'd', 'A', None),
    ('c', ['A', 'b', 'c'], 'd', 'c', None),
    ])
def test_prompt(capsys, keystroke, valid_responses, default, expected, raised):
    from vesty.cli.support import prompt

    result = None
    with mock.patch('vesty.cli.click.api.getchar', create=True) as mocker:
        mocker.return_value = keystroke
        if raised:
            with pytest.raises(raised):
                result = prompt(prompt, valid_responses=valid_responses, default=default)
        else:
            result = prompt(prompt, valid_responses=valid_responses, default=default)
            assert result == expected

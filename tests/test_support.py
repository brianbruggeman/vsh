from textwrap import dedent

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
    from vsh.terminal import echo

    echo(text, verbose=verbose)
    out, err = capsys.readouterr()
    assert out == expected

from textwrap import dedent

import pytest


@pytest.mark.unit
@pytest.mark.parametrize('text, verbose, indent, expected', [
    # Simple
    ('Hello, World!', None, None, 'Hello, World!\n'),
    # Multi-line
    (dedent("""
    Another
    World!
    """), None, 4, """\n    Another\n    World!\n"""),
    # Multi-line
    (dedent("""
    Another
    World!
    """), None, None, '\nAnother\nWorld!\n'),
    # Check verbose = False
    ('Stranger Things', False, None, ''),
    # Check for multiple messages
    (('Hello,', 'World'), None, None, 'Hello, World\n'),
    (('Hello,', 'World'), None, None, 'Hello, World\n'),
    ])
def test_echo(capsys, text, verbose, indent, expected):
    from vsh.cli.support import echo

    if isinstance(text, str):
        echo(text, indent=indent, verbose=verbose)
    elif isinstance(text, (tuple, list)):
        echo(*text, indent=indent, verbose=verbose)
    out, err = capsys.readouterr()
    assert out == expected

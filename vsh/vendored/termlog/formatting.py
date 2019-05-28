import textwrap
from pathlib import Path
from typing import Any, Optional, Union

from .. import pygments
from ..pygments.formatters import get_formatter_by_name
from ..pygments.lexer import Lexer
from ..pygments.lexers import get_lexer_by_name, guess_lexer

from .message import Message

__all__ = ('beautify', 'format')


def beautify(
        message: Any,
        indent: int = 0,
        lexer: Optional[Union[pygments.lexer.Lexer, str]] = None
        ) -> str:
    """Beautify *message*.

    Args:
        message: message to beautify
        indent: number of spaces to indent
        lexer: message lexical analyzer

    Returns:
        str: beautified message

    """
    formatter = get_formatter_by_name('16m')

    indent = max(int(indent or 0), 0)
    if isinstance(message, Path):
        message = str(message)
    elif isinstance(message, bytes):
        message = message.decode('utf-8')

    single = False
    if isinstance(message, str):
        single = len(message) - len(message.rstrip('\n')) == 0

    if isinstance(message, Exception):
        lexer = lexer or 'py3tb'

    if isinstance(lexer, str):
        lexer = get_lexer_by_name(lexer)

    if not lexer and isinstance(message, str):
        lexer = guess_lexer(message, stripall=True) if lexer is None else lexer

    if lexer and isinstance(message, str):
        messages = message.split('\n')
        for index, message in enumerate(messages):
            message = pygments.highlight(message, lexer, formatter)
            messages[index] = message.strip()
        message = '\n'.join(messages)
    if indent > 0:
        message = textwrap.indent(message, ' ' * indent)
    return message.rstrip('\n') if single and isinstance(message, str) else message


def format(*messages: Any,
           lexer: Optional[Union[Lexer, str]] = None,
           color: bool = None,
           json: bool = None,
           time_format: Optional[str] = None,
           add_timestamp: Optional[bool] = None,
           ) -> str:
    """Echo *message*.

    lexers can be passed in, and if they are, the resulting output
    will attempt to be setup

    Args:
        messages: messages to echo
        color: colorize output
        lexer: message lexical analyzer
        json: Dump out a structured text
        time_format: control time format
        add_timestamp: add a timestamp to the output

    Returns:
        Tuple[str]: beautified messages

    """
    # Allows echo to be used in settings and prevents circular dependencies
    string = ''
    for index, message in enumerate(messages):
        include_timestamp = False
        if add_timestamp is True:
            include_timestamp = True
        if add_timestamp is None:
            if index == 0:
                include_timestamp = True
            elif json is True:
                include_timestamp = True
        msg = Message(
            data=message,
            lexer=str(lexer) if lexer else '',
            json=bool(json),
            color=bool(color),
            time_format=time_format,
            include_timestamp=include_timestamp,
            )
        separator = ('\n' if json else ' ') if string else ''
        string = f'{string}{separator}{msg}'
    return string

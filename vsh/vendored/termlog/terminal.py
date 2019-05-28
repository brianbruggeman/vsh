import sys
from dataclasses import dataclass
from typing import IO, Any, Optional, Union

from ..pygments.lexer import Lexer

from .formatting import format

__all__ = ('echo', 'set_config')


@dataclass
class TerminalConfig:
    """Data class to hold some simple configuration data

    Attributes:
        color: when True, display output with color
        json: when True, display output as json
        timestamp: when True, include timestamp in output
        time_format: control how the timestamp appears in the output

    """
    color: bool = True
    json: bool = False
    timestamp: Optional[bool] = None
    time_format: str = '%Y%m%d%H%M%S'


_terminal_config = TerminalConfig()


def set_config(
        color: Optional[bool] = None,
        json: Optional[bool] = None,
        time_format: Optional[str] = None,
        timestamp: Optional[bool] = None,
        ) -> TerminalConfig:
    global _terminal_config
    _terminal_config.color = color if color is not None else _terminal_config.color
    _terminal_config.json = json if json is not None else _terminal_config.json
    _terminal_config.timestamp = timestamp if timestamp is not None else _terminal_config.timestamp
    _terminal_config.time_format = time_format if time_format is not None else _terminal_config.time_format
    return _terminal_config


def echo(*messages: Any,
         verbose: Optional[Union[bool, int]] = None,
         end: str = '\n',
         flush: bool = True,
         lexer: Optional[Union[Lexer, str]] = None,
         file: IO = sys.stdout,
         color: Optional[bool] = None,
         json: Optional[bool] = None,
         time_format: Optional[str] = None,
         add_timestamp: Optional[bool] = None,
         ) -> Optional[str]:
    """Echo *message*.

    lexers can be passed in, and if they are, the resulting output
    will attempt to be setup

    Args:
        messages: messages to echo
        verbose: verbosity level
        end: text to print at end of message, defaults to newline
        flush: flush output after write
        lexer: message lexical analyzer
        file: file to echo message to
        json: Dump out a structured text
        time_format: string to control time formatting
        string_format: string to control string formatting
        add_timestamp: Controls whether the timestamp is dumped out
        color: control color output

    Returns:
        Tuple[str]: beautified messages

    """
    # verbose should be minimally capped to 0
    verbose = 1 if verbose is None else max(int(verbose or 0), 0)
    if not verbose:
        return None

    time_format = time_format if time_format is not None else _terminal_config.time_format
    add_timestamp = add_timestamp if add_timestamp is not None else _terminal_config.timestamp
    json = json if json is not None else _terminal_config.json
    color = color if color is not None else _terminal_config.color

    string = format(*messages, lexer=lexer, color=color, json=json, time_format=time_format, add_timestamp=add_timestamp)
    print(string, file=file, end=end, flush=flush)
    return string

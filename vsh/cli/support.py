import sys
import textwrap


def echo(*messages, verbose=None, indent=True, end=None, flush=None, file=None):
    """Echo *message*.

    indentation can be finely controlled, but by default, indentation
    is related to the verbose setting set by the command-line interface
    and the verbose setting passed in as a parameter.  The difference
    of the two identifies how much indentation is created.

    Args:
        messages (Tuple[Any]): messages to echo
        verbose (bool|int, optional): verbosity level
        indent (int): number of spaces to indent
        end (str): text to print at end of message, defaults to newline
        flush (bool): flush output after write
        file (typing.IO): file to echo message to

    Returns:
        Tuple[str]: beautified messages

    """
    verbose = True if verbose is None else max(int(verbose or 0), 0)
    indent = 0 if indent in [None, False, True] else max(int(indent or 0), 0)
    file = file or sys.stdout
    messages = list(messages)
    if verbose:
        for index, message in enumerate(messages):
            message_end = end if index == len(messages) - 1 else ' '
            message = '' if message is None else message
            end = '\n' if end is None else end
            if end == '\n' and indent:
                message = textwrap.indent(message, ' ' * indent)
            message = message.rstrip('\n') if end == '\n' else message
            print(message, flush=flush, end=message_end, file=file)
    return tuple(messages)

from .vendored.colorama import Fore, Style
from typing import Any, Optional, Union


def blue(msg: Any):
    msg = Fore.BLUE + str(msg) + Style.RESET_ALL
    return msg


def green(msg: Any):
    msg = Fore.GREEN + str(msg) + Style.RESET_ALL
    return msg


def magenta(msg: Any):
    msg = Fore.MAGENTA + str(msg) + Style.RESET_ALL
    return msg


def red(msg: Any):
    msg = Fore.RED + str(msg) + Style.RESET_ALL
    return msg


def yellow(msg: Any):
    msg = Fore.YELLOW + str(msg) + Style.RESET_ALL
    return msg


def echo(message, verbose: Optional[Union[bool, int]] = None, flush: bool = True, end: str = '\n'):
    if verbose or (verbose is None):
        print(message, flush=flush, end=end)

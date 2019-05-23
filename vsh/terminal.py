from typing import Any, Optional, Union

from .vendored.colorama import Fore, Style


def blue(msg: Any) -> str:
    msg = Fore.BLUE + str(msg) + Style.RESET_ALL
    return msg


def green(msg: Any) -> str:
    msg = Fore.GREEN + str(msg) + Style.RESET_ALL
    return msg


def magenta(msg: Any) -> str:
    msg = Fore.MAGENTA + str(msg) + Style.RESET_ALL
    return msg


def red(msg: Any) -> str:
    msg = Fore.RED + str(msg) + Style.RESET_ALL
    return msg


def yellow(msg: Any) -> str:
    msg = Fore.YELLOW + str(msg) + Style.RESET_ALL
    return msg


def echo(message, verbose: Optional[Union[bool, int]] = None, flush: bool = True, end: str = '\n'):
    if verbose or (verbose is None):
        print(message, flush=flush, end=end)

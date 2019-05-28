"""Color module

Contains resources to build 256 (standard) and 16m (true-color) text
output.

"""
import ctypes
import os
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional, Tuple

from .decorations import factory

__all__ = (
    'black', 'blue', 'cyan', 'green', 'grey', 'magenta', 'rgb', 'red',
    'yellow', 'white', 'Color'
    )


_colors: Dict[Tuple[int, int, int], 'Color'] = {}


# This will get updated below, see: _true_color_supported
def true_color_supported() -> bool:
    """Check if truecolor is supported by the current tty.

    Note: this currently only checks to see if COLORTERM contains
          one of the following enumerated case-sensitive values:
             - truecolor
             - 24bit

    """
    color_term = os.getenv('COLORTERM', '')
    return True if any(check in color_term for check in ['truecolor', '24bit']) else False


if os.name == 'nt':
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

TRUE_COLOR_SUPPORTED = true_color_supported()
ESCAPE: str = '\x1b'

# style codes
#  Not all of these are supported within all terminals
BRIGHT: str = f'{ESCAPE}[1m'
DIM: str = f'{ESCAPE}[2m'
ITALIC: str = f'{ESCAPE}[3m'
UNDERLINED: str = f'{ESCAPE}[4m'
BLINK: str = f'{ESCAPE}[5m'
STROBE: str = f'{ESCAPE}[6m'
INVERTED: str = f'{ESCAPE}[7m'
HIDDEN: str = f'{ESCAPE}[8m'


@factory(names=['red', 'green', 'blue'], repository=_colors)
@dataclass
class Color:
    """A data structure for packaging up Color display information

    Example:
        >>> from termlog import Color, echo
        >>> solarized_red = Color(red=220, green=50, blue=47)
        >>> solarized_magenta = Color(red=221, green=54, blue=130)
        >>> msg = ...
        >>> echo(f'{solarized_red("ERROR")}: {solarized_magenta(msg)}')

    Attributes:
        red: the value for the red aspect of the color [0-255]
        green: the value for the green aspect of the color [0-255]
        blue: the value for the blue aspect of the color [0-255]
        color_prefix: the string prefix when true-color is not enabled
        true_color_prefix: the string prefix for when true-color is enabled
        suffix: the reset suffix
        truecolor: enables true color when True
        bright: a bold/bright version of the color
        dim: a dim version of the color
        italic: an italic version of the color
        underlined: an underlined version of the message

    """
    red: int = 0
    green: int = 0
    blue: int = 0
    color_prefix: str = ''
    true_color_prefix: str = f'{ESCAPE}[38;2;{{red}};{{green}};{{blue}}m'
    suffix: str = f'{ESCAPE}[0m'
    truecolor: bool = TRUE_COLOR_SUPPORTED

    # style attributes
    dim: bool = False
    bright: bool = False
    italic: bool = False
    underline: bool = False
    blink: bool = False
    inverted: bool = False
    hidden: bool = False
    strobe: bool = False

    def __post_init__(self):
        # cap red, green and blue
        prefix_mapping = {
            (0, 0, 0): 30,  # black
            (255, 0, 0): 31,  # red
            (0, 255, 0): 32,  # green
            (255, 255, 0): 33,  # yellow
            (0, 0, 255): 34,  # blue
            (255, 0, 255): 35,  # magenta
            (0, 255, 255): 36,  # cyan
            (255, 255, 255): 37,  # white
            (127, 127, 127): 37,  # grey
            }
        if self.color_prefix == '':
            key = self.red, self.green, self.blue
            mapped = prefix_mapping.get(key)
            self.color_prefix = f'{ESCAPE}[{mapped}m' or ''
            if key == (127, 127, 127) and self.color_prefix:
                self.color_prefix += DIM
        if not self.color_prefix:
            self.color_prefix = self.true_color_prefix
        self.red = max(min(int(self.red or 0), 255), 0)
        self.green = max(min(int(self.green or 0), 255), 0)
        self.blue = max(min(int(self.blue or 0), 255), 0)

    def __call__(self, message: Any, color: bool = True, truecolor: Optional[bool] = None) -> str:
        truecolor = self.truecolor if truecolor is None else truecolor
        if color:
            if truecolor:
                prefix = self.true_color_prefix.format(**asdict(self))
            else:
                prefix = self.color_prefix
            if self.hidden:
                prefix += HIDDEN
            else:
                if self.dim:
                    prefix += DIM
                elif self.bright:
                    prefix += BRIGHT
                if self.italic:
                    prefix += ITALIC
                if self.underline:
                    prefix += UNDERLINED
                if self.blink:
                    prefix += BLINK
                if self.strobe:
                    prefix += STROBE
            return f'{prefix}{message}{self.suffix}'
        else:
            return f'{message}'

    def __eq__(self, other):
        return id(self) == id(other)

    def __getitem__(self, item):
        if item in ('red', 'green', 'blue'):
            return getattr(self, item)
        else:
            raise KeyError(f'Could not find {item} in {self}')

    @staticmethod
    def keys():
        return ('red', 'green', 'blue')

    @staticmethod
    def __len__():
        return 3

    def __iter__(self):
        for name in ('red', 'green', 'blue'):
            yield getattr(self, name)


# Set simple terminal colors
BLACK = Color(0, 0, 0, color_prefix=f'{ESCAPE}[30m')
RED = Color(255, 0, 0, color_prefix=f'{ESCAPE}[31m')
GREEN = Color(0, 255, 0, color_prefix=f'{ESCAPE}[32m')
YELLOW = Color(255, 255, 0, color_prefix=f'{ESCAPE}[33m')
BLUE = Color(0, 0, 255, color_prefix=f'{ESCAPE}[34m')
MAGENTA = Color(255, 0, 255, color_prefix=f'{ESCAPE}[35m')
CYAN = Color(0, 255, 255, color_prefix=f'{ESCAPE}[36m')
WHITE = Color(255, 255, 255, color_prefix=f'{ESCAPE}[37m')
GREY = Color(127, 127, 127, color_prefix=f'{ESCAPE}[37m{ESCAPE}[2m')


def black(message: Any, color: bool = True, truecolor: Optional[bool] = None) -> str:
    """Add black color to *message*.

    Example:
        >>> from termlog import black, echo
        >>> f'{black("black")}'
        '{ESCAPE}[38;2;0;0;0mblack{ESCAPE}[0m'

    Args:
        message: text to color
        color: enable color on output

    Returns:
        Colored text if color is enabled

    """
    return rgb(message=message, color=color, truecolor=truecolor)


def blue(message: Any, color: bool = True, truecolor: Optional[bool] = None) -> str:
    """Add blue color to *message*.

    Example:
        >>> from termlog import black, echo
        >>> echo(f'A {blue("blue")} message')
        '20190606105532 a {ESCAPE}[38;2;0;0;255mblue{ESCAPE}[0m message'

    Args:
        message: text to color
        color: enable color on output

    Returns:
        Colored text if color is enabled

    """
    return rgb(message=message, color=color, blue=255, truecolor=truecolor)


def cyan(message: Any, color: bool = True, truecolor: Optional[bool] = None) -> str:
    """Add cyan color to *message*.

    Example:
        >>> from termlog import black, echo, set_config
        >>> set_config(timestamp=False)
        >>> echo(f'A {cyan("cyan")} message')
        'a {ESCAPE}[38;2;0;255;255mcyan{ESCAPE}[0m message'

    Args:
        message: text to color
        color: enable color on output

    Returns:
        Colored text if color is enabled

    """
    return rgb(message=message, color=color, green=255, blue=255, truecolor=truecolor)


def green(message: Any, color: bool = True, truecolor: Optional[bool] = None) -> str:
    """Add green color to *message*.

    Example:
        >>> from termlog import echo, green
        >>> msg = green("green")
        >>> print(msg)
        '{ESCAPE}[38;2;0;255;0mgreen{ESCAPE}[0m'
        >>> echo(f'A {msg} message', color=False)
        '20190606143659 a green message'

    Args:
        message: text to color
        color: enable color on output

    Returns:
        Colored text if color is enabled

    """
    return rgb(message=message, color=color, green=255, truecolor=truecolor)


def grey(message: Any, color: bool = True, truecolor: Optional[bool] = None) -> str:
    """Add grey color to *message*.

    Example:
        >>> from termlog import echo, grey
        >>> echo(f'A {grey("grey")} message', json=True)
        '{"data": "a \u001b[38;2;127;127;127mgrey\u001b[0m message", "timestamp": "20190606144743"}'

    Args:
        message: text to color
        color: enable color on output

    Returns:
        Colored text if color is enabled

    """
    return rgb(message=message, color=color, red=127, green=127, blue=127, truecolor=truecolor)


def magenta(message: Any, color: bool = True, truecolor: Optional[bool] = None) -> str:
    """Add orange color to *message*.

    Example:
        >>> from termlog import echo, magenta
        >>> msg = magenta('magenta')
        >>> echo(f'A {msg} message', json=True)
        '20190606143659 a {ESCAPE}[38;2;255;0;255mmagenta{ESCAPE}[0m message'

    Args:
        message: text to color
        color: enable color on output

    Returns:
        Colored text if color is enabled

    """
    return rgb(message=message, color=color, red=255, blue=255, truecolor=truecolor)


def rgb(message: Any, red: int = 0, green: int = 0, blue: int = 0, color: bool = True, truecolor: Optional[bool] = None) -> str:
    """Add any true color to *message*.

    Example:
        >>> from termlog import echo, rgb, Color
        >>> c = Color(red=223, green=81, blue=127)
        >>> print(f'{c!r}')
        Color(red=223, green=81, blue=127, color_prefix='', true_color_prefix='{ESCAPE}[38;2;{red};{green};{blue}m', suffix='{ESCAPE}[0m', truecolor=False)
        >>> f'A {rgb("colored", **c)} message'
        'A {ESCAPE}[38;2;223;81;127mcolored{ESCAPE}[0m message'

    Note: this only works if the terminal supports true color and there
          is no way to definitively determine if truecolor is supported
          by the terminal.

    Args:
        message: text to color
        red: red portion of color [0 to 255]
        green: green portion of color [0 to 255]
        blue: blue portion of color [0 to 255]
        color: enable color on output

    Returns:
        Colored text if color is enabled

    """
    truecolor = TRUE_COLOR_SUPPORTED if truecolor is None else truecolor
    _color = Color(red=red, green=green, blue=blue, truecolor=truecolor)
    return _color(message, color)


def red(message: Any, color: bool = True, truecolor: Optional[bool] = None) -> str:
    """Add red color to *message*.

    Example:
        >>> from termlog import echo, red
        >>> f'A {red("red")} message'
        'A {ESCAPE}[38;2;225;0;0mred{ESCAPE}[0m message'

    Args:
        message: text to color
        color: enable color on output

    Returns:
        Colored text if color is enabled

    """
    return rgb(message=message, color=color, red=255, truecolor=truecolor)


def yellow(message: Any, color: bool = True, truecolor: Optional[bool] = None) -> str:
    """Add yellow color to *message*.

    Example:
        >>> from termlog import echo, yellow
        >>> f'A {yellow("yellow")} message'
        'A {ESCAPE}[38;2;225;255;0myellow{ESCAPE}[0m message'

    Args:
        message: text to color
        color: enable color on output

    Returns:
        Colored text if color is enabled

    """
    return rgb(message=message, color=color, red=255, green=255, truecolor=truecolor)


def white(message: Any, color: bool = True, truecolor: Optional[bool] = None) -> str:
    """Add white color to *message*.

    Example:
        >>> from termlog import echo, white
        >>> f'A {white("white")} message'
        'A {ESCAPE}[38;2;225;255;255mwhite{ESCAPE}[0m message'

    Args:
        message: text to color
        color: enable color on output

    Returns:
        Colored text if color is enabled

    """
    return rgb(message=message, color=color, red=255, green=255, blue=255, truecolor=truecolor)

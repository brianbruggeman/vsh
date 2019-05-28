import os
from dataclasses import dataclass
from pathlib import Path
from typing import Union


@dataclass
class Environment:
    HOME: Union[str, Path] = os.getenv('HOME') or ''
    WORKON_HOME: Union[str, Path] = os.getenv('WORKON_HOME') or ''
    SHELL: Union[str, Path] = os.getenv('SHELL') or ''
    PATH: str = os.getenv('PATH') or ''
    PS1: str = os.getenv('PS1') or ''
    PROMPT: str = os.getenv('PROMPT') or ''

    def __post_init__(self):
        if self.HOME and isinstance(self.HOME, str):
            self.HOME = Path(self.HOME)
        if not self.HOME or not self.HOME.exists():
            self.HOME = Path.home()

        if os.name == 'nt':
            self.SHELL = 'powershell.exe'
        else:
            if self.SHELL and isinstance(self.SHELL, str):
                self.SHELL = Path(self.SHELL)
            if not self.SHELL or not self.SHELL.exists():
                self.SHELL = Path(f'/bin/sh')

        if self.WORKON_HOME and isinstance(self.WORKON_HOME, str):
            self.WORKON_HOME = Path(self.WORKON_HOME)
        if not self.WORKON_HOME or not self.WORKON_HOME.exists():
            self.WORKON_HOME = self.HOME / '.virtualenvs'


env = Environment()

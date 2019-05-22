import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, Iterable, Optional, Union

import pytest


@dataclass
class EnterVenvTestCase:
    """Basic api spec for build_vsh_rc_file

    Attributes:
        path: path to virtual environment
        command: command to execute (default is current shell)
        verbose: verbosity level
        working: path to working dir
        expected: return code of command run
    """
    path: Union[Path, str] = field(default_factory=Path)
    command: Optional[Iterable] = None
    verbose: int = 0
    working: Optional[Union[Path, str]] = None
    expected_return_code: int = 0
    expected_stdout: str = ''
    expected_stderr: str = ''

    @property
    def kwds(self) -> Dict:
        kwds = asdict(self)
        keys_to_remove = []
        for key in kwds:
            if key.startswith('expected'):
                keys_to_remove.append(key)
        for key in keys_to_remove:
            kwds.pop(key)
        return kwds

    def __post_init__(self):
        self.path = Path(self.path)


@pytest.mark.parametrize('test_case', [
    EnterVenvTestCase(command=['env']),
    EnterVenvTestCase(command=['echo', '"hello, world"']),
    ])
def test_api_enter(test_case):
    """Tests build_vsh_rc_file properly creates a .vshrc
    """
    from vsh.api import enter

    exit_code = enter(**test_case.kwds)
    assert exit_code == test_case.expected_return_code

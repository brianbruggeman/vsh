from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional, Union

import pytest


@dataclass
class BuildVshConfigTestCase:
    """Basic api spec for build_vsh_rc_file

    Attributes:
        venv_path: path to virtual environment
        working: path to start virtual environment in
        expected: path to config file
    """

    venv_path: Union[Path, str] = field(default_factory=Path)
    working: Union[Optional[Path]] = None
    expected: Union[Path, str] = field(default_factory=Path)

    def __post_init__(self):
        self.venv_path = Path(self.venv_path)
        if self.working is not None:
            self.working = Path(self.expected)
        self.expected = Path(self.expected)


@pytest.mark.parametrize("test_case", [BuildVshConfigTestCase(expected=".vshrc")])
def test_api_build_vsh_config_file(test_case):
    """Tests build_vsh_rc_file properly creates a .vshrc
    """
    from vsh.api import build_vsh_rc_file

    kwds = asdict(test_case)
    expected_config_filepath = kwds.pop("expected")
    actual_config_filepath = build_vsh_rc_file(**kwds)
    assert isinstance(actual_config_filepath, Path)
    assert actual_config_filepath == expected_config_filepath

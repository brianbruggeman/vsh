import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from .__metadata__ import package_metadata
from .env import env
from .vendored import toml

PathString = Union[str, Path]


def converter(result: List[Tuple]) -> dict:
    """Converts dictionary data"""
    data = {}
    for key, value in result:
        if isinstance(value, Path):
            data[key] = f'"{value}"'
        else:
            data[key] = value
    return data


@dataclass
class VshConfig:
    """Vsh configuration data

    Attributes:
        venv_name: name of the virtual environment
        venv_path: path to the virtual environment
        vsh_config_path: path to the file containing this configuration
        working_path: startup path
        interpreter: path to the python executable
        shell: path to the os shell to run commands
        vsh_version: version of vsh

    """

    venv_name: Optional[str] = None
    venv_path: Optional[PathString] = None
    vsh_config_path: Optional[PathString] = None
    working_path: Optional[PathString] = None
    interpreter_path: Optional[PathString] = None
    shell_path: Optional[PathString] = None
    vsh_version: str = package_metadata.version

    @property
    def json(self):
        json = asdict(self, dict_factory=converter)
        return json

    def __post_init__(self):
        if self.shell_path is None or (self.shell_path and not isinstance(self.shell_path, Path)):
            self.shell_path = env.SHELL

        if self.working_path and not isinstance(self.working_path, Path):
            self.working_path = Path(self.working_path)

        if self.venv_path and not isinstance(self.venv_path, Path):
            self.venv_path = Path(self.venv_path)

        if self.vsh_config_path:
            vsh_path = self.vsh_config_path.expanduser().resolve().absolute()
            self.load(vsh_path)

        if self.venv_path and not self.venv_name:
            self.venv_name = self.venv_path.name
        elif self.venv_path is None and self.venv_name:
            self.venv_path = env.WORKON_HOME / self.venv_name

        if not self.vsh_config_path and self.venv_name:
            self.vsh_config_path = Path.home() / ".vsh" / f"{self.venv_name}.cfg"

        if self.interpreter_path is None:
            self.interpreter_path = Path(sys.executable)
        else:
            self.interpreter_path = self._find_interpreter_path(self.interpreter_path)

    def dump(self, config_path: Path):
        with config_path.open("w") as stream:
            toml.dump(self.json, stream)

    def load(self, config_path: Optional[Path] = None):
        if not config_path and self.vsh_config_path:
            config_path = Path(self.vsh_config_path)
        if config_path and config_path.exists():
            text = config_path.read_text(encoding="utf-8")
            data = self.parse(text)
            for field_name, value in asdict(self).items():
                if field_name in data:
                    value = data.get(field_name)
                    if field_name.endswith("_path"):
                        value = self._load_path(value)
                    if value is None and field_name == "shell_path" and env.SHELL and os.name == "nt":
                        value = Path(r"powershell.exe")
                    setattr(self, field_name, value)
        return self

    @staticmethod
    def _find_interpreter_path(interpreter: Optional[PathString] = None) -> Path:
        default_interpreter = Path(sys.executable)
        interpreter = Path(interpreter or default_interpreter)
        return interpreter

    @staticmethod
    def _load_path(path: str, default: Optional[Path] = None):
        new_path = Path(path.strip('"'))
        if new_path.expanduser().resolve().absolute().exists():
            return new_path
        else:
            return default

    @staticmethod
    def parse(raw_data: str) -> Dict:
        data = toml.loads(raw_data)
        return data

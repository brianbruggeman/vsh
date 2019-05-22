import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Type

import pytest


class NonValue:
    pass


NonValue = NonValue()


@dataclass
class VenvConfigAttrTestCase:
    name: str = ''
    value: Any = NonValue
    expected_type: Type = NonValue
    expected_value: Any = NonValue

    @property
    def kwds(self) -> Dict[str, Any]:
        if self.value != NonValue:
            return {self.name: self.value}
        return {}


@pytest.mark.parametrize('test_case', [
    VenvConfigAttrTestCase(name='venv_name', value='bar', expected_value='bar'),
    VenvConfigAttrTestCase(name='venv_path'),
    VenvConfigAttrTestCase(name='venv_path', expected_type=Path),
    VenvConfigAttrTestCase(name='venv_path', value=Path.home() / '.virtualenvs', expected_type=Path),
    VenvConfigAttrTestCase(name='venv_path', value=str(Path.home() / '.virtualenvs'), expected_type=Path),
    VenvConfigAttrTestCase(name='working_path'),
    VenvConfigAttrTestCase(name='working_path', value=str(Path.home()), expected_value=Path.home()),
    VenvConfigAttrTestCase(name='interpreter_path'),
    VenvConfigAttrTestCase(name='interpreter_path', value=sys.executable, expected_value=Path(sys.executable)),
    VenvConfigAttrTestCase(name='shell_path', expected_value=Path(os.getenv('SHELL'))),
    VenvConfigAttrTestCase(name='shell_path', value=os.getenv('SHELL'), expected_value=Path(os.getenv('SHELL'))),
    VenvConfigAttrTestCase(name='vsh_version'),
    VenvConfigAttrTestCase(name='vsh_version', value='1.2.3', expected_value='1.2.3'),
    ])
def test_vsh_config_attributes(test_case):
    """Validates that the venv config accepts a variety of parameters
    for each attribute and will create the proper typed values for
    those attributes
    """
    from ..vsh_config import VshConfig

    kwds = test_case.kwds
    # this will guarantee we always have a venv name to avoid the
    #  invalid config exception
    venv_name = test_case.value if test_case.name == 'venv_name' and test_case.value != NonValue else 'foo'
    if test_case.name == 'venv_path' and test_case.value != NonValue:
        venv_name = Path(test_case.value).name
    kwds.update({'venv_name': venv_name})

    config = VshConfig(**kwds)
    assert hasattr(config, test_case.name)
    config_value = getattr(config, test_case.name)
    if test_case.expected_type != NonValue:
        assert isinstance(config_value, test_case.expected_type)
    if test_case.expected_value != NonValue:
        assert config_value == test_case.expected_value

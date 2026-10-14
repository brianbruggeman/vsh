import pytest
import vsh


def test_config_constructor_validates_and_exposes_fields(tmp_path):
    path = tmp_path / "demo"
    config = vsh.Config("demo", venv_path=path)
    assert config.venv_name == "demo"
    assert config.venv_path == path


def test_config_rejects_blank_name():
    with pytest.raises(vsh.VshConfigError):
        vsh.Config("  ")


def test_config_environment_is_resolved_and_validated(monkeypatch):
    monkeypatch.setenv("VSH_VENV_NAME", "from-env")
    assert vsh.Config.from_environment().venv_name == "from-env"
    monkeypatch.setenv("VSH_VENV_NAME", "  ")
    with pytest.raises(vsh.VshConfigError):
        vsh.Config.from_environment()


def test_config_store_and_load_validate(tmp_path):
    path = tmp_path / "config.toml"
    config = vsh.Config("demo", vsh_config_path=path)
    config.store()
    assert vsh.Config.load(path).venv_name == "demo"
    path.write_text('venv_name = " "\n')
    with pytest.raises(vsh.VshConfigError):
        vsh.Config.load(path)


def test_create_options_defaults_and_environment(monkeypatch):
    defaults = vsh.CreateOptions()
    assert defaults.include_pip is True
    assert defaults.symlinks is True
    monkeypatch.setenv("VSH_CREATE_INCLUDE_PIP", "false")
    assert vsh.CreateOptions.from_environment().include_pip is False
    monkeypatch.setenv("VSH_CREATE_INCLUDE_PIP", "invalid")
    with pytest.raises(vsh.VshConfigError):
        vsh.CreateOptions.from_environment()


def test_config_errors_have_a_shared_base():
    assert issubclass(vsh.VshConfigError, vsh.VshError)

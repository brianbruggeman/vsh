import sys
from pathlib import Path

import pytest
import vsh


def test_venv_create_enter_and_remove_use_rust_pipes(tmp_path):
    path = tmp_path / "new-parent" / "demo"
    if sys.platform == "win32":
        pytest.skip("native Windows shell argument behavior is covered by C21")
    config = vsh.Config(
        venv_name="demo",
        venv_path=path,
        vsh_config_path=tmp_path / "demo.vsh.cfg",
        working_path=tmp_path,
        interpreter_path=Path(sys.executable),
        shell_path=Path("/bin/sh"),
    )
    venv = vsh.Venv.from_config(config)
    venv.create(vsh.CreateOptions(include_pip=False))

    assert venv.name == "demo"
    assert venv.path == path
    assert venv.is_valid()

    code = "import os, sys; print(sys.prefix); print(os.getcwd()); print(123, file=sys.stderr)"
    stdout, stderr, status = venv.enter(["-c", f"python -c '{code}'"])
    assert status == 0, stderr.decode()
    lines = stdout.decode().splitlines()
    assert Path(lines[0]).resolve() == path.resolve()
    assert Path(lines[1]).resolve() == tmp_path.resolve()
    assert stderr.decode().strip() == "123"
    scripts = "Scripts" if sys.platform == "win32" else "bin"
    assert not list((path / scripts).glob("pip*"))

    venv.remove()
    assert not venv.is_valid()


def test_venv_failed_create_cleans_reserved_target(tmp_path):
    path = tmp_path / "partial"
    venv = vsh.Venv(
        path,
        interpreter_path=tmp_path / "missing-python",
        shell_path=Path(__import__("os").environ.get("COMSPEC", "cmd.exe") if sys.platform == "win32" else "/bin/sh"),
    )
    with pytest.raises(vsh.VshError):
        venv.create()
    assert not path.exists()


def test_venv_remove_rejects_an_invalid_directory(tmp_path):
    path = tmp_path / "not-a-venv"
    path.mkdir()
    shell = __import__("os").environ.get("COMSPEC", "cmd.exe") if sys.platform == "win32" else "/bin/sh"
    with pytest.raises(vsh.VshError):
        vsh.Venv(path, shell_path=Path(shell)).remove()
    assert path.is_dir()

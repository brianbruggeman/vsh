"""Checks that must run against the isolated, installed maturin wheel."""

import os
import json
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlparse

import pytest


def test_installed_console_entry_reports_distribution_version():
    executable = Path(os.environ["VSH_TEST_EXECUTABLE"])
    python = Path(os.environ["VSH_TEST_PYTHON"])
    scripts = subprocess.run(
        [str(python), "-I", "-c", "import sysconfig; print(sysconfig.get_path('scripts'))"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert scripts.returncode == 0, scripts.stderr
    assert executable.resolve().parent == Path(scripts.stdout.strip()).resolve()
    metadata = subprocess.run(
        [
            str(python),
            "-I",
            "-c",
            "from importlib.metadata import version; print(version('vsh'))",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert metadata.returncode == 0, metadata.stderr
    version = metadata.stdout.strip()
    assert version
    print(f"installed metadata version: {version}")
    result = subprocess.run(
        [str(executable), "--version"], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == version


@pytest.mark.parametrize(
    ("stdout_bytes", "stderr_bytes"),
    [
        (b"stdout without newline", b"stderr without newline"),
        (b"stdout with newline\n", b"stderr with newline\n"),
    ],
)
def test_installed_console_flushes_child_output_exactly(
    tmp_path, stdout_bytes, stderr_bytes
):
    executable = Path(os.environ["VSH_TEST_EXECUTABLE"])
    python = Path(os.environ["VSH_TEST_PYTHON"])
    code = (
        "import sys; "
        f"sys.stdout.buffer.write({stdout_bytes!r}); "
        f"sys.stderr.buffer.write({stderr_bytes!r}); "
        "sys.exit(23)"
    )
    result = subprocess.run(
        [
            str(executable),
            "enter",
            "--name",
            "demo",
            "--venv-path",
            str(tmp_path / "demo"),
            "--working-path",
            str(tmp_path),
            "--shell",
            str(python),
            "--",
            "-c",
            code,
        ],
        capture_output=True,
        check=False,
    )
    assert result.returncode == 23
    assert (result.stdout, result.stderr) == (stdout_bytes, stderr_bytes)


def test_installed_python_package_exposes_rust_api():
    python = Path(os.environ["VSH_TEST_PYTHON"])
    site = subprocess.run(
        [
            str(python),
            "-I",
            "-c",
            "import sysconfig; print(sysconfig.get_paths()['purelib'])",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert site.returncode == 0, site.stderr
    site_packages = Path(site.stdout.strip()).resolve()
    print(f"isolated site-packages: {site_packages}")
    result = subprocess.run(
        [
            str(python),
            "-I",
            "-c",
            "import vsh; from vsh import _vsh; "
            "assert vsh.Config and vsh.Venv and callable(_vsh.cli); "
            "print(vsh.__file__); print(_vsh.__file__)",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    paths = [Path(line).resolve() for line in result.stdout.splitlines()]
    assert len(paths) == 2, result.stdout
    assert all(path.is_relative_to(site_packages) for path in paths), paths
    print(f"installed imports: {paths[0]} ; {paths[1]}")
    if wheel_path := os.environ.get("VSH_TEST_WHEEL"):
        from importlib.metadata import distribution

        direct_url = distribution("vsh").read_text("direct_url.json")
        assert direct_url is not None
        source = unquote(urlparse(json.loads(direct_url)["url"]).path)
        if os.name == "nt" and len(source) > 2 and source[0] == "/" and source[2] == ":":
            source = source[1:]
        source_path = Path(source).resolve()
        assert source_path == Path(wheel_path).resolve(), source_path
        print(f"installed wheel source: {source_path}")

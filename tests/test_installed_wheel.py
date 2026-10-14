"""Checks that must run against the isolated, installed maturin wheel."""

import os
import subprocess
from pathlib import Path


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

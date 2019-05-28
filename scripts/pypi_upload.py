#!/usr/bin/env python
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Tuple

from vsh import api
from vsh.vendored import termlog
from vsh.vendored.click import command, echo, option, style


@command()
@option("-v", "verbose", count=True, help="More spam")
@option("-i", "--interactive", is_flag=True, help="Run interactively")
@option("-p", "--prod", is_flag=True, help="Install to https://upload.pypi.org/legacy/")
def main(interactive: bool, prod: bool, verbose: int):
    """Installs to https://test.pypi.org/legacy/ unless --prod is
    specified
    """
    verbose = max(int(verbose or 0), 0)
    repo_path = Path(__file__).absolute().parent.parent
    venv_path = Path.home() / ".virtualenvs" / f"{repo_path.name}-pypi-upload"

    # determine git branch
    cmd = ["git", "rev-parse", "--abbrev-ref", "HEAD"]
    branch = subprocess.check_output(cmd, cwd=str(repo_path)).strip().decode("utf-8")
    if prod and branch != "master":
        echo(style(f"ERROR: Production can only be pushed from the master branch", fg="red"), file=sys.stderr)
        sys.tracebacklimit = 0
        exit(1)

    setup_venv(venv_path, repo_path, verbose=verbose)
    create_distribution(venv_path, verbose=verbose)
    run_tests(venv_path, verbose=verbose)
    upload_distribution(venv_path, repo_path, prod, verbose=verbose)
    cleanup(venv_path, repo_path, verbose=verbose)


def cleanup(venv_path: Path, repo_path: Path, verbose: int = 0):
    """Removes venv and build artifacts within repository

    Args:
        venv_path: path to virtual environment
        repo_path: path to top of repository
    """
    verbose = max(int(verbose or 0), 0)
    api.remove(venv_path, verbose=verbose)

    artifacts = ["build", "dist"]
    for artifact in artifacts:
        path = repo_path / artifact
        if path.exists():
            shutil.rmtree(str(path))


def create_distribution(venv_path: Path, verbose: int = 0):
    """Installs package into virtual environment and installs necessary
    packages for upload to public pypi

    Args:
        venv_path: path to virtual environment
        verbose: verbosity level
    """
    verbose = max(int(verbose or 0), 0)
    command = "python setup.py sdist"
    if api.enter(Path(venv_path), command, verbose=verbose) != 0:
        termlog.echo(f"Failed to run {command} in {venv_path}")
        exit(1)


def find_matched_gpg(repo_path: Path) -> Tuple[Path, Path]:
    repo_path = Path(repo_path)
    # find distribution path
    dist_path = repo_path / "dist"
    # find matched gpg
    for root, folders, files in os.walk(str(dist_path)):
        for filename in files:
            # Wheels don't support MANIFEST.in.
            if filename.endswith(".tar.gz"):
                dist_file_path = Path(root) / filename.replace(".tar.gz", "")
                matched_gpg = Path(str(dist_file_path) + ".asc")
                return dist_file_path, matched_gpg


def setup_venv(venv_path: Path, repo_path: Path, verbose: int = 0):
    """Installs package into virtual environment and installs necessary
    packages for upload to public pypi

    Args:
        venv_path (str): path to virtual environment
        repo_path (str): path to top of repository
    """
    verbose = max(int(verbose or 0), 0)
    repo_path = Path(repo_path)
    artifacts = ["build", "dist", "vsh.egg-info"]
    for artifact in artifacts:
        path = repo_path / artifact
        if path.exists():
            shutil.rmtree(str(path))

    api.create(path=venv_path, verbose=verbose)
    commands = [f"pip install {repo_path}[pypi]", f"pip install {repo_path}"]
    for cmd in commands:
        if api.enter(Path(venv_path), cmd, verbose=verbose):
            termlog.echo(f'Failed to run: "{cmd}" in "{venv_path}"')
            exit()


def run_tests(venv_path: Path, verbose: int = 0):
    """Runs tests"""
    verbose = max(int(verbose or 0), 0)
    exit_code = api.enter(Path(venv_path), "pytest --cache-clear", verbose=verbose)
    if exit_code != 0:
        echo(style(f"ERROR: Tests failed.", fg="red"), file=sys.stderr)
        sys.tracebacklimit = 0
        exit(1)


def upload_distribution(venv_path: Path, repo_path: Path, prod: bool = False, verbose: int = 0):
    """Uploads distribution to pypi server

    Args:
        venv_path (str): path to virtual environment
        repo_path (str): path to top of repository
    """
    verbose = max(int(verbose or 0), 0)
    found = find_matched_gpg(repo_path)
    if found:
        dist_file_path, matched_gpg = found
        if matched_gpg.exists():
            matched_gpg.unlink()
        upload_args = "-r pypi" if prod else "-r pypi-test"
        command = f"twine upload {upload_args} -s {dist_file_path}.tar.gz"
        exit_code = api.enter(Path(venv_path), command, verbose=verbose)
        if exit_code != 0:
            echo(style(f"ERROR: Could not upload", fg="red"), file=sys.stderr)
            sys.tracebacklimit = 0
            exit(1)


if __name__ == "__main__":
    main()

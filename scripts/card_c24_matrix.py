#!/usr/bin/env python3
"""Build and exercise the native-platform C24 wheel in an isolated venv."""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path

from card_gate import run_card


ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], *, cwd: Path = ROOT) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def main() -> int:
    output = ROOT / "target" / "c24-wheels"
    output.mkdir(parents=True, exist_ok=True)
    maturin = "maturin.exe" if os.name == "nt" else "maturin"
    run(
        [
            maturin,
            "build",
            "--manifest-path",
            "crates/vsh-py/Cargo.toml",
            "--out",
            str(output),
            "--interpreter",
            sys.executable,
        ]
    )
    wheels = list(output.glob("vsh-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(f"expected exactly one wheel, found {wheels}")
    wheel = wheels[0]
    tag = wheel.name.removesuffix(".whl").rsplit("-", 1)[-1]
    os_family = platform.system()
    expected = {"Windows": "win_", "Darwin": "macosx_", "Linux": ("linux_", "manylinux")}[os_family]
    expected_prefixes = (expected,) if isinstance(expected, str) else expected
    if not tag.startswith(expected_prefixes):
        raise RuntimeError(f"native wheel tag {tag!r} does not match {os_family}")

    environment = ROOT / "target" / "c24-venv"
    uv = "uv.exe" if os.name == "nt" else "uv"
    run([uv, "venv", "--python", sys.executable, str(environment)])
    scripts = environment / ("Scripts" if os.name == "nt" else "bin")
    python = scripts / ("python.exe" if os.name == "nt" else "python")
    executable = scripts / ("vsh.exe" if os.name == "nt" else "vsh")
    run([uv, "pip", "install", "--python", str(python), "pytest", str(wheel)])
    os.environ.update(
        {
            "VSH_TEST_PYTHON": str(python),
            "VSH_TEST_EXECUTABLE": str(executable),
        }
    )
    log = ROOT / "target" / "card-logs" / f"C24-{os_family.lower()}.log"
    command = [
        str(python),
        "-m",
        "pytest",
        "-q",
        "-s",
        "-c",
        os.devnull,
        "-p",
        "no:cacheprovider",
        "-rA",
        str(ROOT / "tests" / "test_installed_wheel.py"),
    ]
    print(f"C24 platform={os_family} wheel={wheel.name} tag={tag}", flush=True)
    return run_card(f"C24-{os_family.lower()}", command, log)


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build and exercise the native-platform C24 wheel in an isolated venv."""

from __future__ import annotations

import os
import platform
import subprocess
import sys
import uuid
from pathlib import Path

from packaging.tags import sys_tags
from packaging.utils import parse_wheel_filename

from card_gate import run_card


ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], *, cwd: Path = ROOT) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def main() -> int:
    run_id = uuid.uuid4().hex
    output = ROOT / "target" / f"c24-wheels-{run_id}"
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
    _, _, _, wheel_tags = parse_wheel_filename(wheel.name)
    compatible_tags = wheel_tags.intersection(sys_tags())
    if not compatible_tags:
        raise RuntimeError(f"wheel tags {wheel_tags} are unsupported by this runner")
    if all(tag.platform == "any" for tag in wheel_tags):
        raise RuntimeError(f"expected a native extension wheel, got tags {wheel_tags}")
    os_family = platform.system()

    environment = ROOT / "target" / f"c24-venv-{run_id}"
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
            "VSH_TEST_WHEEL": str(wheel),
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
    print(f"C24 platform={platform.system()} wheel={wheel.name} compatible_tags={len(compatible_tags)}", flush=True)
    return run_card(f"C24-{platform.system().lower()}", command, log)


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Install a vsh wheel and execute the native-platform guide examples."""

from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

FENCE = re.compile(r"```(?P<language>[a-zA-Z0-9_-]+)\n(?P<body>.*?)\n```", re.DOTALL)


def run(command: list[str], *, env: dict[str, str], cwd: Path) -> str:
    result = subprocess.run(
        command, cwd=cwd, env=env, text=True, capture_output=True, check=False
    )
    if result.returncode:
        raise RuntimeError(
            f"command failed ({result.returncode}): {command!r}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result.stdout + result.stderr


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python scripts/card_c25_examples.py <built-vsh-wheel>", file=sys.stderr)
        return 2
    wheel_input = Path(sys.argv[1]).resolve(strict=True)
    if wheel_input.is_dir():
        wheels = sorted(wheel_input.glob("vsh-*.whl"))
        if len(wheels) != 1:
            raise RuntimeError(f"expected one vsh wheel in {wheel_input}, found {len(wheels)}")
        wheel = wheels[0]
    else:
        wheel = wheel_input
    if wheel.suffix != ".whl":
        raise ValueError(f"expected a wheel file or directory, got {wheel}")
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("uv is required to create the isolated example environment")

    guide = Path(__file__).resolve().parents[1] / "docs" / "using-vsh.md"
    guide_text = guide.read_text(encoding="utf-8")
    required = ("--config", "VSH_VENV_NAME", "--ephemeral", "--dry-run", "enter", "list", "remove")
    missing = [item for item in required if item not in guide_text]
    if missing:
        raise RuntimeError(f"guide is missing required executable-example topics: {missing}")
    sections = list(FENCE.finditer(guide_text))
    toml_examples = [match.group("body") for match in sections if match.group("language") == "toml"]
    if len(toml_examples) != 1:
        raise RuntimeError(f"expected one TOML example in {guide}, got {len(toml_examples)}")

    shell_language = "powershell" if os.name == "nt" else "sh"
    shell_examples = [
        match.group("body") for match in sections if match.group("language") == shell_language
    ]
    shell_examples = [
        body for body in shell_examples if "pip install vsh==0.8.0" not in body
    ]
    dry_run_check = (
        "if (-not (Test-Path $venvPath)) { throw 'dry-run deleted the environment' }"
        if os.name == "nt"
        else 'test -d "$venv_path" || { echo "dry-run deleted the environment" >&2; exit 1; }'
    )
    for index, body in enumerate(shell_examples):
        lines = body.splitlines()
        for line_number, line in enumerate(lines):
            if "--dry-run" in line:
                lines.insert(line_number + 1, dry_run_check)
                break
        shell_examples[index] = "\n".join(lines)
    python_examples = [
        match.group("body") for match in sections if match.group("language") == "python"
    ]
    native_source = "\n".join(shell_examples)
    required_native = (
        "vsh create", "vsh list", "vsh enter", "vsh remove", "--ephemeral",
        "--dry-run", "--config", "VSH_VENV_NAME",
    )
    missing_native = [item for item in required_native if item not in native_source]
    expected_shell_blocks = 8 if os.name == "nt" else 9
    if len(shell_examples) != expected_shell_blocks or missing_native or len(python_examples) != 1:
        raise RuntimeError(
            f"guide must retain all {expected_shell_blocks} native shell blocks "
            "and one Python API block; "
            f"missing commands/topics={missing_native}, shell blocks={len(shell_examples)}, "
            f"Python blocks={len(python_examples)}"
        )

    with tempfile.TemporaryDirectory(prefix="vsh-c25-") as directory:
        root = Path(directory)
        home = root / "home"
        home.mkdir()
        env = os.environ.copy()
        for key in list(env):
            if key.upper().startswith(("VSH_", "VSH_CREATE_")):
                env.pop(key, None)
        env.update(
            HOME=str(home),
            USERPROFILE=str(home),
            APPDATA=str(home / "AppData" / "Roaming"),
            LOCALAPPDATA=str(home / "AppData" / "Local"),
            XDG_CONFIG_HOME=str(home / ".config"),
        )
        tool_env = root / "tool-env"
        run([uv, "venv", "--python", sys.executable, str(tool_env)], env=env, cwd=root)
        scripts = tool_env / ("Scripts" if os.name == "nt" else "bin")
        python = scripts / ("python.exe" if os.name == "nt" else "python")
        run([uv, "pip", "install", "--python", str(python), str(wheel)], env=env, cwd=root)
        env["PATH"] = str(scripts) + os.pathsep + env.get("PATH", "")
        env["Path"] = env["PATH"]
        executable = scripts / ("vsh.exe" if os.name == "nt" else "vsh")
        version = run([str(executable), "--version"], env=env, cwd=root)
        if version.strip() != "0.8.0":
            raise RuntimeError(f"installed wheel reports unexpected version {version!r}")
        (root / "demo.toml").write_text(toml_examples[0] + "\n", encoding="utf-8")

        if os.name == "nt":
            powershell = shutil.which("pwsh") or shutil.which("powershell")
            if powershell is None:
                raise RuntimeError("PowerShell is required to execute the Windows guide examples")
            powershell_source = ["$ErrorActionPreference = 'Stop'"]
            for example in shell_examples:
                command_pending = False
                for line in example.splitlines():
                    powershell_source.append(line)
                    if line.strip().startswith("vsh "):
                        command_pending = True
                    if command_pending and not line.rstrip().endswith("`"):
                        powershell_source.append(
                            "if ($LASTEXITCODE -ne 0) { throw 'vsh command failed' }"
                        )
                        command_pending = False
            output = run(
                [powershell, "-NoProfile", "-NonInteractive", "-Command", "\n".join(powershell_source)],
                env=env,
                cwd=root,
            )
            demo = home / ".virtualenvs" / "demo"
            once = home / ".virtualenvs" / "demo-once"
        else:
            bash = shutil.which("bash")
            if bash is None:
                raise RuntimeError("bash is required to execute POSIX guide examples")
            output = run(
                [bash, "-euo", "pipefail", "-c", "\n".join(shell_examples)],
                env=env,
                cwd=root,
            )
            demo = home / ".virtualenvs" / "demo"
            once = home / ".virtualenvs" / "demo-once"
        if str(demo) not in output or "Python " not in output:
            raise RuntimeError("guide output did not show the listed path and entered interpreter")
        if "from-env" not in output or "from-cli" not in output:
            raise RuntimeError(f"guide output did not demonstrate environment and CLI precedence: {output!r}")
        if demo.exists() or once.exists() or (root / "envs" / "demo").exists():
            raise RuntimeError("guide commands left an environment behind after removal")

        run([str(python), "-c", python_examples[0]], env=env, cwd=root)
        api_path = home / ".virtualenvs" / "demo-api"
        if api_path.exists():
            raise RuntimeError("Python API example did not remove its environment")

    print(
        f"GREEN C25: {len(shell_examples)} native shell blocks and "
        f"1 Python API block passed on {platform.system()}; exact local wheel installed"
    )
    print("NOTE: the PyPI install command is verified after publication in C28")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

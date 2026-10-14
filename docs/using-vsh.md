# Using vsh

`vsh` manages Python virtual environments. Version 0.8.0 requires Python 3.9
or newer. Install it after the 0.8.0 release is available on PyPI:

```sh
python -m pip install vsh==0.8.0
```

Before publication, the examples gate installs the exact locally built wheel in
a fresh environment. C28 verifies the PyPI command and artifact after release.

## Create an environment

Choose a name, environment directory, and Python interpreter. On POSIX shells:

```sh
python_path="$(python -c 'import sys; print(sys.executable)')"
venv_path="$HOME/.virtualenvs/demo"
vsh create --name demo --venv-path "$venv_path" --interpreter "$python_path"
```

On Windows PowerShell:

```powershell
$pythonPath = (python -c "import sys; print(sys.executable)").Trim()
$venvPath = Join-Path $HOME ".virtualenvs\demo"
vsh create --name demo --venv-path $venvPath --interpreter $pythonPath
```

## List environments

`list` discovers environments under the parent directory of the configured
`venv_path`. You can provide the values on the command line:

```sh
vsh list --name demo --venv-path "$venv_path"
```

Or use environment settings. These values apply to this process and its
children. On POSIX:

```sh
VSH_VENV_NAME=demo VSH_VENV_PATH="$venv_path" vsh list
```

In PowerShell:

```powershell
$env:VSH_VENV_NAME = "demo"
$env:VSH_VENV_PATH = $venvPath
vsh list
Remove-Item Env:VSH_VENV_NAME
Remove-Item Env:VSH_VENV_PATH
```

## Run a command in the environment

`enter` launches a child shell with the environment's executable directory
first on that child's `PATH`. It returns the child exit status; it does not
activate or modify the shell that launched vsh. Put shell arguments after `--`.

On POSIX, this runs Python in the child shell:

```sh
vsh enter --name demo --venv-path "$venv_path" --shell /bin/sh -- -c 'python -V'
```

On Windows PowerShell, use `cmd.exe` syntax after `--`:

```powershell
vsh enter --name demo --venv-path $venvPath --shell $env:ComSpec -- /C "python -V"
```

## Remove an environment

`--dry-run` validates the target and leaves it in place. Run the command again
without `--dry-run` to remove it:

```sh
vsh remove --name demo --venv-path "$venv_path" --dry-run
vsh remove --name demo --venv-path "$venv_path"
```

PowerShell:

```powershell
vsh remove --name demo --venv-path $venvPath --dry-run
vsh remove --name demo --venv-path $venvPath
```

## Create, enter, and remove an ephemeral environment

Use `--ephemeral` for a path that does not exist yet. vsh creates the
environment, runs the child shell, and removes the environment after it exits.

POSIX:

```sh
vsh create --name demo-once --venv-path "$HOME/.virtualenvs/demo-once" \
  --interpreter "$python_path" --ephemeral --shell /bin/sh -- -c 'python -V'
```

PowerShell:

```powershell
$oncePath = Join-Path $HOME ".virtualenvs\demo-once"
vsh create --name demo-once --venv-path $oncePath --interpreter $pythonPath `
  --ephemeral --shell $env:ComSpec -- /C "python -V"
```

## Configure with a TOML file

Save `demo.toml` in the current directory. Paths are regular TOML strings; use
forward slashes when writing Windows paths.

```toml
venv_name = "demo"
venv_path = "envs/demo"
```

The CLI applies configuration in this order: TOML file, `VSH_*` environment,
then command-line overrides. First create using the path from the file and a name
from the command line:

```sh
vsh create --config demo.toml --name demo --interpreter "$python_path"
```

PowerShell:

```powershell
vsh create --config demo.toml --name demo --interpreter $pythonPath
```

The next commands show an environment setting overriding the file, then a CLI
flag overriding the environment:

```sh
VSH_VENV_NAME=from-env vsh enter --config demo.toml --shell /bin/sh -- -c 'echo "$VSH_VENV_NAME"'
VSH_VENV_NAME=from-env vsh enter --config demo.toml --name from-cli --shell /bin/sh -- -c 'echo "$VSH_VENV_NAME"'
```

PowerShell:

```powershell
$env:VSH_VENV_NAME = "from-env"
vsh enter --config demo.toml --shell $env:ComSpec -- /C "echo %VSH_VENV_NAME%"
vsh enter --config demo.toml --name from-cli --shell $env:ComSpec -- /C "echo %VSH_VENV_NAME%"
Remove-Item Env:VSH_VENV_NAME
```

Remove the configured environment using the file path and a command-line name:

```sh
vsh remove --config demo.toml --name demo
```

PowerShell:

```powershell
vsh remove --config demo.toml --name demo
```

Configuration fields also accept the `VSH_` prefix, such as
`VSH_VENV_NAME` and `VSH_VENV_PATH`. Use `--config-path` to set an optional
sidecar file that `remove` also deletes if it exists. Create-only options
include `--site-packages`, `--without-pip`, `--prompt`, `--working`,
`--symlinks`, and `--copies`; `--python` selects the interpreter for one create
operation.

## Use the Python API

The installed package exports Rust-backed `Config`, `CreateOptions`, and `Venv`
classes. This example creates an environment, runs a command in its child
shell, checks the result, and removes it:

```python
import os
import sys
from pathlib import Path
from vsh import CreateOptions, Venv

if os.name == "nt":
    shell = Path(os.environ.get("COMSPEC", "cmd.exe"))
    command = ["/C", "echo hello from vsh"]
else:
    shell = Path("/bin/sh")
    command = ["-c", "python -c \"print('hello from vsh')\""]

venv = Venv(
    Path.home() / ".virtualenvs" / "demo-api",
    name="demo-api",
    interpreter_path=Path(sys.executable),
    shell_path=shell,
)
venv.create(CreateOptions(python=Path(sys.executable)))
assert venv.is_valid()
stdout, stderr, status = venv.enter(command)
assert status == 0, stderr.decode()
assert stdout.decode().strip() == "hello from vsh"
venv.remove()
```

`Config` and `CreateOptions` validate values when constructed. `Config` can
also load from a TOML file or the `VSH_*` environment and persist itself with
`store()`.

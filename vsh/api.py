"""vsh.api

This represents the programmatic public-facing api point for vsh.

"""
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Set, Tuple

from . import profiling
from .__metadata__ import package_metadata
from .builder import VenvBuilder
from .env import env
from .errors import InterpreterNotFound, InvalidEnvironmentError, PathNotFoundError, VenvConfigNotFound, VenvNameError
from .vendored import click, termlog
from .vsh_config import VshConfig

__all__ = ('create', 'enter', 'remove', 'show_venvs', 'show_version')


splash = f"""
       __      __    _     
       \ \    / /   | |    
        \ \  / /___ | |__  
         \ \/ // __|| '_ \ 
          \  / \__ \| | | |
           \/  |___/|_| |_|
                           
       The Virtual Environment Shell
       
         v{termlog.cyan(package_metadata.version)} [build: {termlog.grey(package_metadata.build)}]
                           
    """  # noqa: flake8 W291 W605 W293


def build_vsh_rc_file(venv_path: Path, working: Optional[Path] = None) -> Path:
    """Sets a default configuration.

    When the virtual environment is started, this particular file will
    set the current working folder to working.

    Args:
        venv_path: path to virtual environment
        working: path to startup folder

    Returns:
        path to created vshrc file
    """
    default_working_path = Path('.')
    working = Path(working or default_working_path)
    vsh_venv_config_path = venv_path / '.vshrc'
    if vsh_venv_config_path.parent.exists() and not vsh_venv_config_path.exists():
        if working.exists() and working.is_dir():
            with vsh_venv_config_path.open('w') as config:
                config.write(f'cd {working.absolute()}\n')
            termlog.echo(f'Set default path to: {f"{termlog.cyan(str(working))}"}')
            termlog.echo(f'To edit, update: {termlog.yellow(str(vsh_venv_config_path))}')
    return vsh_venv_config_path


def create(path: Path, site_packages: bool = False, overwrite: bool = False, symlinks: bool = False, upgrade: bool = False, include_pip: bool = False, prompt: str = '', python: str = '', verbose: int = 0, interactive: bool = False, dry_run: bool = False, working: Optional[Path] = None) -> Path:
    """Creates a virtual environment

    Notes: Wraps venv

    Args:
        path: path to virtual environment

        site_packages: use system packages within environment [default: False]
        overwrite: replace target folder [default: False]
        symlinks: create symbolic link to Python executable [default: True]
        upgrade: Upgrades existing environment with new Python executable [default: False]
        include_pip: Includes pip within virtualenv [default: True]
        prompt: Modifies prompt
        python: Version of python, python executable or path to python
        working: working path

        verbose: more output [default: 0]
        interactive: ask before updating system [default: False]
        dry_run: do not update system

    Returns:
        str: path to venv
    """
    verbose = max(int(verbose or 0), 0)
    path = path.expanduser().resolve().absolute()
    name = path.name
    builder = _get_builder(
        path=path,
        site_packages=site_packages,
        overwrite=overwrite,
        symlinks=symlinks,
        upgrade=upgrade,
        include_pip=include_pip,
        prompt=prompt,
    )
    interactive_prompt = f'Create virtual environment "{termlog.yellow(name)}" under: {termlog.green(path)}?'
    run_command = click.confirm(interactive_prompt) if interactive else True
    if run_command:
        if not dry_run:
            executable = _get_interpreter(python)
            if not executable:
                raise InterpreterNotFound(version=python)
            builder.create(env_dir=str(path), executable=str(executable))
            create_vsh_config(name=name, path=path, working=working)
        termlog.echo(f'Created virtual environment "{termlog.yellow(name)}" under: {termlog.green(path)}', verbose=verbose)
    return path


def create_vsh_config(name: str, path: Path, working: Optional[Path] = None, vsh_config_path: Optional[Path] = None) -> VshConfig:
    """Creates a vsh virtual environment configuration file

    Args:
        name: name of virtual environment
        path: path to virtual environment
        working: path of working dir when entering virtual environment
        vsh_config_path: path to vsh configuration file

    Returns:
        configuration created
    """
    config_file_path = find_vsh_config(name=name, check=False)
    config_file_path.parent.mkdir(parents=True, exist_ok=True)
    config = VshConfig(venv_name=name, venv_path=path, working_path=working, vsh_config_path=vsh_config_path)
    config.dump(Path(config.vsh_config_path))
    return config


def enter(path: Path, command: Optional[Iterable[str]] = None, verbose: int = 0, working: Optional[Path] = None, ignore_working: bool = False) -> int:
    """Enters a virtual environment

    Args:
        path:  path to virtual environment
        command: command to run in virtual env [default: shell]
        verbose: Adds more information to stdout
        working: Working folder path
        ignore_working: ignore the working folder path for this invocation

    Returns:
        return code for command run
    """
    with profiling.TimedExecutionBlock() as time:
        path = path.expanduser().resolve().absolute()
        # termlog.echo(splash, verbose=verbose)
        vsh_config_path = find_vsh_config(name=path.name, check=False)
        if not vsh_config_path.exists():
            config = create_vsh_config(name=path.name, path=path, working=working, vsh_config_path=vsh_config_path)
        else:
            config = read_vsh_config(path=vsh_config_path)
        if working and working != config.working_path:
            config.working_path = Path(working)
            config.dump(vsh_config_path)
        verbose = max(int(verbose or 0), 0)
        env = _update_environment(config=config)
        # Setup the environment scripts
        working_path = working or config.working_path
        cwd = Path.cwd() if ignore_working else Path(working_path or Path.cwd())
        # This should work for all POSIX environments as well as Powershell
        source = '.'
        commands = []
        if os.name == 'nt':
            prompt = env.get('PROMPT')
            commands.append('clear')
            commands.append(f'echo @\'\n{splash}\n\'@')
            commands.append('function prompt { \"' + prompt + '\" }')
        for vshrc_path in find_vsh_rc_files(config.working_path):
            if os.name == 'nt':
                if str(vshrc_path).startswith('\\\\') or ' ' in str(vshrc_path):
                    continue
            vshrc_command = f'{source} {vshrc_path}'
            commands.append(vshrc_command)
        if isinstance(command, (list, tuple)):
            command = ' '.join(command)
        commands.append(f'{command}')
        interactive = '-i' if sys.stdout.isatty() else ''
        if os.name == 'nt':
            shelled_command = f'{config.shell_path} -ExecutionPolicy Bypass -NoLogo -command "{"; ".join(commands)}"'
        else:
            shelled_command = f'{config.shell_path} {interactive} -c "{" && ".join(commands)}"'
        termlog.echo(f'Running in {termlog.cyan(config.venv_name)}: {termlog.green(shelled_command)}', verbose=verbose)
        proc = subprocess.run(shlex.split(shelled_command), cwd=cwd, env=env)
        termlog.echo(f'Execution time: {time}', verbose=verbose)
        termlog.echo(
            f'Command return code: {termlog.green(str(proc.returncode)) if proc.returncode == 0 else termlog.red(str(proc.returncode))}',
            verbose=verbose,
            )
    return proc.returncode


def find_environment_folders(path: Optional[Path] = None, verbose: int = 0) -> Iterable[Tuple[str, Path]]:
    """Find location of the virtual environments

    Args:
        path: path to virtual environment home
        verbose: control echo output

    Yields:
        - name: venv name
        - path: venv path

    """
    environment_count = 0
    for root, directories, files in os.walk(path or env.WORKON_HOME):
        found = []
        termlog.echo(f'Searching {root} for virtual environment', verbose=verbose)
        for index, name in enumerate(directories):
            directory = Path(root) / name
            if not validate_environment(directory):
                continue
            termlog.echo(f'Found {name} under {directory}', verbose=verbose - 1)
            yield name, directory
            environment_count += 1
            found.append(name)
        # This makes the search 'fast' by skipping out on sub folders
        #  that do not need to be searched because they have already
        #  been identified as valid environments
        directories[:] = [d for d in directories if d not in found]


def find_vsh_rc_files(venv_path: Path) -> Iterable[Path]:
    """Find the vshrc files

    Args:
        venv_path: path to virtual environment

    Yields:
        vshrc paths found
    """
    path_sequence = ['/usr/local/etc/vsh', env.HOME, venv_path]
    cmds = ['git rev-parse --show-toplevel', 'hg root']
    top_of_current_repo_path = None
    for cmd in cmds:
        cmd_list = shlex.split(cmd)
        if shutil.which(cmd_list[0]):
            top_of_current_repo_path = (
                Path(
                    subprocess.run(cmd_list, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                    .stdout.decode('utf-8')
                    .strip()
                )
                or None
            )
            if top_of_current_repo_path and top_of_current_repo_path.exists():
                path_sequence.append(top_of_current_repo_path)
                break
    # general set of paths to search for vsh configuration files
    paths = [p for p in map(Path, [p_ for p_ in path_sequence if p_]) if p.exists() and (p / '.vshrc').exists()]
    memoized_paths: Set[Path] = set()
    for p in paths:
        p = p.expanduser().resolve().absolute()
        config_path = p / '.vshrc'
        if not config_path.exists() and p == venv_path and top_of_current_repo_path:
            working = Path(top_of_current_repo_path)
            build_vsh_rc_file(p, working=working)
        if p.exists() and config_path.exists():
            if config_path.is_file():
                if config_path in memoized_paths:
                    continue
                memoized_paths.add(config_path)
                yield config_path
            elif config_path.is_dir():
                for root, folders, files in os.walk(str(config_path)):
                    root_path = Path(root)
                    for filename in files:
                        filepath = (root_path / filename).absolute()
                        if filepath in memoized_paths:
                            continue
                        memoized_paths.add(filepath)
                        breakpoint()
                        yield filepath


def find_vsh_config(name: str, check: bool = True) -> Path:
    """Finds the vsh venv configuration file

    Args:
        name: the name of the venv
        check: if true and vsh not found, then raises an error

    Raises:
        VenvConfigNotFound when check is True and config file is not found
    """
    if not name:
        raise VenvConfigNotFound(name=name)
    vsh_config_path = Path.home() / '.vsh' / f'{name}.cfg'
    if check and not vsh_config_path.exists():
        raise VenvConfigNotFound(name=name)
    return vsh_config_path


def get_venv_home(name: str, check: bool = True) -> Path:
    """Find the virtual environment's home given a name

    Args:
        name: the name of the existing virtual environment
        check: Raise a name error if true and name doesn't exist

    Returns:
        path: the path tot he existing virtual environment

    Raises:
        VenvNameError: when the name is not valid and check is True

    """
    default_path = env.WORKON_HOME
    venv_path = default_path / name
    if venv_path.exists() and venv_path.is_dir():
        if validate_venv_path(venv_path, check=False):
            return venv_path
    elif not check:
        return default_path / name
    raise VenvNameError(name=name)


def read_vsh_config(path: Path) -> VshConfig:
    """Reads vsh configuration file

    Args:
        path: path to the vsh configuration file

    Returns:
        vsh configuration
    """
    config = VshConfig()
    config.load(path)
    return config


def remove(path: Path, verbose: int = 0, interactive: bool = False, dry_run: bool = False, check: bool = False) -> Path:
    """Remove a virtual environment

    Args:
        path: path to virtual environment
        verbose: more output [default: 0]
        interactive: ask before updating system [default: False]
        dry_run: do not update system
        check: Raises PathNotFoundError if True and path isn't found [default: False]

    Raises:
        PathNotFoundError:  when check is True and path is not found

    Returns:
        folder path removed
    """
    verbose = max(int(verbose or 0), 0)
    check = False if check is None else check
    path = path.expanduser().resolve().absolute()
    if not validate_environment(path) and check is True:
        raise InvalidEnvironmentError(path=path)
    run_command = click.confirm(f'Remove {termlog.yellow(str(path))}?') == 'y' if interactive else True
    if run_command and not dry_run:
        if path.exists():
            shutil.rmtree(path)
            remove_venv_config(name=path.name)
        elif check is True:
            raise PathNotFoundError(path=path)
    termlog.echo(f'{termlog.cyan("Removed")}: {termlog.green(path)}', verbose=verbose)
    return path


def remove_venv_config(name: str) -> Path:
    """Removes a vsh virtual environment configuration file

    Args:
        name: name of virtual environment
        path: path to virtual environment
        working: path of working dir when entering virtual environment

    Returns:
        configuration file removed
    """
    config_file_path = find_vsh_config(name=name, check=False)
    if config_file_path.exists():
        config_file_path.unlink()
    return config_file_path


def show_venvs(path: Optional[Path] = None, verbose: int = 0):
    """Displays available virtual environments

    Args:
        path: path to virtual environment folder
        verbose: extra output

    """
    with profiling.TimedExecutionBlock() as time:
        path = path or env.WORKON_HOME or Path.cwd()
        venvs = sorted(find_environment_folders(path=path, verbose=verbose - 1))
        for name, path in venvs:
            termlog.echo(f'Found {termlog.yellow(name)} under: {termlog.yellow(path)}')
        termlog.echo(f'Found {len(venvs)} venvs in {time}', verbose=verbose)


def show_version():
    """Displays vsh package version
    """
    termlog.echo(f'{package_metadata["name"]} {package_metadata["version"]}')


def upgrade(path: Path, site_packages=None, overwrite=None, symlinks=None, include_pip=None, prompt=None, python=None, verbose=None, interactive=None, dry_run=None, working=None) -> Path:
    """Upgrades a virtual environment

    Notes: Wraps venv

    Args:
        path: path to virtual environment

        site_packages: use system packages within environment [default: False]
        overwrite: replace target folder [default: False]
        symlinks: create symbolic link to Python executable [default: True]
        include_pip: Includes pip within virtualenv [default: True]
        prompt: Modifies prompt
        python: Version of python, python executable or path to python
        working: working path

        verbose: more output [default: 0]
        interactive: ask before updating system [default: False]
        dry_run: do not update system

    Returns:
        str: path to venv
    """
    return create(path=path, site_packages=site_packages, overwrite=overwrite, symlinks=symlinks, upgrade=True, include_pip=include_pip, prompt=prompt, python=python, verbose=verbose, interactive=interactive, dry_run=dry_run, working=working)


def validate_environment(path: Path, check: bool = False) -> bool:
    """Validates if path is a valid virtual environment

    Args:
        path: path to virtual environment
        check: Raise an error if path isn't valid

    Raises:
        InvalidEnvironmentError: when environment is not valid

    Returns:
        True if valid virtual environment path
    """
    valid = None
    win32 = sys.platform == 'win32'
    validate_venv_path(path=path, check=check)

    # Expected structure
    structure = {
        'bin': 'Scripts' if win32 else 'bin',
        'include': 'Include' if win32 else 'include',
        'lib': os.path.join('Lib', 'site-packages') if win32 else os.path.join('lib', '*', 'site-packages'),
    }
    paths = {}
    for identifier, expected_path in structure.items():
        for p in path.glob(expected_path):
            # There should only be one path that matches the glob
            paths[identifier] = p
            break
    for identifier in structure:
        if identifier not in paths:
            valid = False
            if check:
                raise InvalidEnvironmentError(f'Could not find {structure[identifier]} under {path}.')

    if valid is not False and win32:
        # TODO: Add more validation for windows environments
        valid = valid is not False and True
    elif valid is not False:
        # check for activation scripts
        activation_scripts = list(paths['bin'].glob('activate.*'))
        valid = valid is not False and len(activation_scripts) > 0
        if check and valid is False:
            raise InvalidEnvironmentError(f'Could not find activation scripts under {path}.')

        # check for python binaries
        python_name = paths['lib'].parent.name
        python_ver_match = re.search(
            '(?P<interpreter>python|pypy)\.?(?P<major>\d+)(\.?(?P<minor>\d+))', python_name
        )  # noqa
        if python_ver_match:
            python_executable = paths['bin'].joinpath('python')
            python_ver_executable = paths['bin'].joinpath(python_name)
            if python_executable.exists():
                valid = valid is not False and True
            if check and valid is False:
                raise InvalidEnvironmentError(f'Could not find python executable under {path}.')
            if python_ver_executable.exists():
                valid = valid is not False and True
            if check and valid is False:
                raise InvalidEnvironmentError(f'Could not find {python_name} executable under {path}.')

    return True if valid else False


def validate_venv_path(path: Path, check: bool = False) -> bool:
    """Validates that a given path is a path to a virtual environment

    Args:
        path: the virtual environment path to check
        check: flag to toggle exception raising on invalid paths

    Raises:
        InvalidEnvironmentError: when check is true and path is invalid

    Returns:
        True if the path and path structure is valid
    """
    win32 = sys.platform == 'win32'
    standard_struct = {
        'bin': 'Scripts' if win32 else 'bin',
        'include': 'Include' if win32 else 'include',
        'lib': os.path.join('Lib', 'site-packages') if win32 else os.path.join('lib', '*', 'site-packages'),
    }
    standard_struct['python'] = f'{standard_struct["bin"]}/python'
    standard_struct['site-packages'] = f'{standard_struct["lib"]}/*/site-packages'
    valid = False
    if path and path.exists():
        checked = False
        subchecked = False
        for globbed_path in standard_struct.values():
            checked = True
            for resolved_path in path.glob(globbed_path):
                if not resolved_path.exists():
                    if check:
                        raise InvalidEnvironmentError(f'Could not find {globbed_path} under {path}.')

                    return valid
                subchecked = True
        valid = checked and subchecked
    if not valid and check:
        raise InvalidEnvironmentError(f'Invalid virtual environment path: {path}.')
    return valid


def validate_venv_name_and_path(name: Optional[str], path: Optional[Path], verbose: int = 1) -> Tuple[str, Optional[Path]]:
    """Validates that the name and the Path are valid

    Because this is a command-line interface, often we can make mistakes.
    This intends to catch some of the more common mistakes made when
    using the cli.  This is not intended to verify if the path and
    virtual environment exist.  It only checks to see if the name and
    path follow a standard convention.

    Args:
        name: the name of the virtual environment
        path: the path to the virtual environment
        verbose: control output

    Returns:
        name: the qualified name of the virtual environment
        path: the qualified path of the virtual environment

    """
    # Cuts down on improper vsh invocations where options are used in
    #  incorrect positions
    if name is None and path is None:
        raise VenvNameError(name=name)
    assert not name.startswith('-'), 'Virtual environment names may not start with "-"'
    assert ' ' not in name, 'Virtual environment names may not include spaces'
    if '/' in name and not path:
        path = Path(name).expanduser().resolve().absolute()
        name = path.name
    if name and not path:
        path = get_venv_home(name, check=False)
    return name, path


# ----------------------------------------------------------------------
# Support
# ----------------------------------------------------------------------
def _escape_zero_length_codes(prompt=None):
    # This is necessary because bash does something funky with PS1 and
    #  doesn't correctly calculate the length of the command-line.  When
    #  under a TMUX session, the command-line itself ends up getting
    #  corrupted when looking at history
    start = r'(\\e|\\xb1)\['
    directive = r'[^m]*'
    end = r'm'
    pattern = f'({start}{directive}{end})'
    replacement = r'\[\1\]'

    eng = re.compile(pattern)
    if os.name == 'nt':
        prompt = f'{env.PROMPT}'
    else:
        prompt = prompt or env.PS1 or env.PROMPT
        if prompt:
            prompt = eng.sub(replacement, prompt)
        else:
            prompt = r'\[\e[34m\]\w\[\e[0m\] \[\e[33m\]\$\[\e[0m\]'
    return prompt


def _get_builder(path: Path, site_packages=None, overwrite=None, symlinks=None, upgrade=None, include_pip=None, prompt=None):
    path = path.expanduser().resolve().absolute()
    name = path.name
    builder = VenvBuilder(
        system_site_packages=False if site_packages is None else site_packages,
        clear=False if overwrite is None else overwrite,
        symlinks=True if symlinks is None else symlinks,
        upgrade=False if upgrade is None else upgrade,
        with_pip=True if include_pip is None else include_pip,
        prompt=f'({name})' if prompt is None else prompt,
    )
    return builder


def _get_interpreter(python=None) -> Path:
    """Returns the interpreter given the string"""
    if not python:
        return Path(sys.executable)

    # Maybe the path is already supplied
    if Path(python).exists():
        return python

    # Guess path
    paths = [Path(path) for path in env.PATH.split(':')]

    # Assume that python is a version if it doesn't start with p
    python = f'python{python}' if not python.startswith('p') else python
    interpreters = [python]

    # Build potential interpreter paths
    interpreter_paths = [p / i for p in paths for i in interpreters]
    for path in interpreter_paths:
        if path.absolute().exists():
            # return the first one found
            return path
    raise InterpreterNotFound(version=python)


def _update_prompt(config: VshConfig, env: Dict[str, Any]):
    disable_prompt = env.get('VIRTUAL_ENV_DISABLE_PROMPT') or None
    if not disable_prompt:
        if os.name == 'nt':
            cmd = ['powershell.exe', '-Command', '\"(Get-Command Prompt).ScriptBlock\"']
            proc = subprocess.run(' '.join(cmd), shell=True, capture_output=True)
            prompt = proc.stdout.decode('utf-8')
            prompt = '\n'.join([l.strip('"') for l in prompt.split('\n') if not l.strip().startswith('#') and l.strip()])
            prompt = f'"{termlog.cyan(config.venv_name)} {prompt}'
            env['PROMPT'] = prompt
        else:
            shell = Path(env.get('SHELL') or '/bin/sh').name
            shell_prompt_mapping = {'bash': 'PS1', 'sh': 'PS1', 'zsh': 'PROMPT'}
            shell_prompt_var = shell_prompt_mapping.get(shell, '')
            default_prompt = termlog.cyan('\\w') + '\\$ '
            prompt = env.get(shell_prompt_var, None) or default_prompt
            prompt = _escape_zero_length_codes(prompt) if shell in ['bash', 'sh'] else prompt
            if shell_prompt_var:
                env[shell_prompt_var] = prompt


def _update_environment(config: VshConfig) -> Dict:
    """Updates environment similar to activate command from venv

    Args:
        config: vsh configuration

    Returns:
        environment variables set as defined by stdlib venv package

    """
    env = {k: v for k, v in os.environ.items()}
    # VSH specific variable to set venv name
    env[package_metadata['name'].upper()] = config.venv_name

    # Expected venv changes to environment variables during an activate
    env['VIRTUAL_ENV'] = str(config.venv_path)
    env['PATH'] = ':'.join([str(config.venv_path / 'bin')] + env['PATH'].split(':'))

    # Updates to shell prompt to show virtual environment info
    _update_prompt(config=config, env=env)
    return env

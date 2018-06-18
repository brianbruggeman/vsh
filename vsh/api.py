import itertools
import os
import re
import shlex
import shutil
import subprocess
import sys
import types
import venv
from pathlib import Path

from .__metadata__ import package_metadata
from .cli import support
from .cli.click import api as click
from .errors import InterpreterNotFound, InvalidEnvironmentError, PathNotFoundError

__all__ = ('create', 'enter', 'remove', 'show_envs', 'show_version')


class VenvBuilder(venv.EnvBuilder):

    def create(self, env_dir, executable=None):
        """
        Create a virtual environment in a directory.

        Args:
            env_dir (str): The target directory to create an environment in.
            executable (str, optional): path to python interpreter executable [default: sys.executable]
        """
        env_dir = os.path.abspath(env_dir)
        context = self.ensure_directories(env_dir=env_dir, executable=executable)
        # See issue 24875. We need system_site_packages to be False
        # until after pip is installed.
        true_system_site_packages = self.system_site_packages
        self.system_site_packages = False
        self.create_configuration(context)
        self.setup_python(context)
        if self.with_pip:
            self._setup_pip(context)
        if not self.upgrade:
            self.setup_scripts(context)
            self.post_setup(context)
        if true_system_site_packages:
            # We had set it to False before, now
            # restore it and rewrite the configuration
            self.system_site_packages = True
        self.create_configuration(context)

    def ensure_directories(self, env_dir, executable=None):
        """
        Create the directories for the environment.
        Returns a context object which holds paths in the environment,
        for use by subsequent logic.

        Args:
            env_dir (str): path to environment
            executable (str, optional): path to python interpreter executable [default: sys.executable]

        Returns:
            types.SimpleNamespace: context
        """
        env_dir = Path(env_dir)

        def create_if_needed(d):
            d = Path(d)
            if d and not d.exists():
                d.mkdir(parents=True, exist_ok=True)
            if not d or not d.is_dir():
                raise ValueError(f'Unable to create directory {d!r}')

        executable = executable or sys.executable
        if env_dir.exists() and self.clear:
            self.clear_directory(env_dir)
        context = types.SimpleNamespace()
        context.env_dir = str(env_dir)
        context.env_name = env_dir.stem
        prompt = self.prompt if self.prompt is not None else context.env_name
        context.prompt = f'({prompt}) '
        create_if_needed(env_dir)
        dirname, exename = os.path.split(os.path.abspath(executable))
        context.executable = executable
        context.python_dir = dirname
        context.python_exe = exename
        if sys.platform == 'win32':
            binname = 'Scripts'
            incpath = 'Include'
            libpath = env_dir / 'Lib' / 'site-packages'
        else:
            binname = 'bin'
            incpath = 'include'
            libpath = env_dir / 'lib' / exename / 'site-packages'
        path = env_dir / incpath
        context.inc_path = str(path)
        create_if_needed(path)
        create_if_needed(libpath)
        # Issue 21197: create lib64 as a symlink to lib on 64-bit non-OS X POSIX
        if (sys.maxsize > 2**32) and (os.name == 'posix') and (sys.platform != 'darwin'):
            link_path = os.path.join(env_dir, 'lib64')
            if not os.path.exists(link_path):   # Issue #21643
                os.symlink('lib', link_path)
        binpath = env_dir / binname
        context.bin_path = str(binpath)
        context.bin_name = binname
        context.env_exe = str(binpath / exename)
        create_if_needed(binpath)
        return context

    def _setup_pip(self, context):
        """Installs or upgrades pip in a virtual environment"""
        # We run ensurepip in isolated mode to avoid side effects from
        # environment vars, the current directory and anything else
        # intended for the global Python environment
        # Originally -Im, but -Esm works on both python2 and python3
        cmd = [context.env_exe, '-Esm', 'ensurepip', '--upgrade',
                                                     '--default-pip']
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)


def build_vsh_config_file(venv_path, startup_path=None):
    """Sets a default configuration.

    When the virtual environment is started, this particular file will
    set the current working folder to startup_path.

    Args:
        venv_path (str|Path): path to virtual environment
        startup_path (str|Path): path to startup folder
    """
    default_startup_path = Path('.')
    startup_path = Path(startup_path or default_startup_path)
    vsh_venv_config_path = venv_path / '.vshrc'
    if vsh_venv_config_path.parent.exists() and not vsh_venv_config_path.exists():
        if startup_path.exists() and startup_path.is_dir():
            with vsh_venv_config_path.open('w') as config:
                config.write(f'cd {startup_path.absolute()}\n')
            support.echo(f'Set default path to: {click.style(str(startup_path), fg="blue")}')
            support.echo(f'To edit, update: {click.style(str(vsh_venv_config_path), fg="yellow")}')


def create(path, site_packages=None, overwrite=None, symlinks=None, upgrade=None, include_pip=None, prompt=None, python=None, verbose=None, interactive=None, dry_run=None):
    """Creates a virtual environment

    Notes: Wraps venv

    Args:
        path (str): path to virtual environment

        site_packages (bool, optional): use system packages within environment [default: False]
        overwrite (bool, optional): replace target folder [default: False]
        symlinks (bool, optional): create symbolic link to Python executable [default: True]
        upgrade (bool, optional): Upgrades existing environment with new Python executable [default: False]
        include_pip (bool, optional): Includes pip within virtualenv [default: True]
        prompt (str, optional): Modifies prompt
        python (str, optional): Version of python, python executable or path to python

        verbose (int, optional): more output [default: 0]
        interactive (bool, optional): ask before updating system [default: False]
        dry_run (bool, optional): do not update system

    Returns:
        str: path to venv
    """
    verbose = max(int(verbose or 0), 0)
    path = os.path.expanduser(path) if path.startswith('~') else os.path.abspath(path)
    name = os.path.basename(path)
    builder = _get_builder(path=path, site_packages=site_packages, overwrite=overwrite, symlinks=symlinks, upgrade=upgrade, include_pip=include_pip, prompt=prompt)
    prompt = f'Create virtual environment "{name}" under: {path}?'
    run_command = click.confirm(prompt) if interactive else True
    if run_command:
        if not dry_run:
            executable = _get_interpreter(python)
            if not executable:
                raise InterpreterNotFound(version=python)
            builder.create(env_dir=path, executable=executable)
        support.echo('Created virtual environment "' + click.style(name, fg='yellow') + " under: " + click.style(path, fg='green'), verbose=verbose)
    return path


def enter(path, command=None, verbose=None):
    """Enters a virtual environment

    Args:
        path (str): path to virtual environment
        command (tuple|list|str, optional): command to run in virtual env [default: shell]
        verbose (int, optional): Adds more information to stdout
    """
    verbose = max(int(verbose or 0), 0)
    path = os.path.expanduser(path) if path.startswith('~') else os.path.abspath(path)
    shell = os.getenv("SHELL")
    command = command or shell
    env = _update_environment(path)
    venv_name = click.style(Path(path).name, fg='green')

    # Setup the environment scripts
    vshell_config_commands = '; '.join(f'source {filepath}' for filepath in find_vsh_config_files(path))
    if not isinstance(command, str):
        command = " ".join(command)
    if vshell_config_commands:
        command = f'{vshell_config_commands}; {command}'
    cmd_display = click.style(command, fg='green')
    if Path(shell).name in ['bash', 'zsh']:
        command = f'{shell} -i -c \"{command}\"'
        cmd_display = f'{shell} -i -c \"{cmd_display}\"'

    support.echo(click.style(f'Running command in "', fg='blue') + venv_name + click.style(f'": ', fg='blue') + cmd_display, verbose=max(verbose - 1, 0))

    # Activate and run
    return_code = subprocess.run(command, shell=True, env=env, universal_newlines=True)
    rc_color = 'green' if return_code == 0 else 'red'
    rc = click.style(str(return_code), fg=rc_color)
    support.echo(click.style('Command return code: ', fg='blue') + rc, verbose=verbose)
    return return_code


def find_vsh_config_files(venv_path=None):
    cmds = [
        'git rev-parse --show-toplevel',
        'hg root',
        ]
    top_of_current_repo_path = None
    for cmd in cmds:
        cmd = shlex.split(cmd)
        try:
            top_of_current_repo_path = Path(subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE).stdout.decode('utf-8').strip()) or None
            if top_of_current_repo_path:
                break
        except Exception:
            pass
    paths = [
        Path('/usr/local/etc/vsh'),
        Path(os.getenv('HOME')),
        Path('.'),
        Path(venv_path),
        top_of_current_repo_path,
        ]
    memoized_paths = set()
    for p in paths:
        if p is None:
            continue
        config_path = p / '.vshrc'
        if not config_path.exists() and str(p) == venv_path:
            startup_path = Path(top_of_current_repo_path or '.')
            build_vsh_config_file(p, startup_path=startup_path)
        if p.exists() and config_path.exists():
            if config_path.is_file():
                if config_path in memoized_paths:
                    continue
                memoized_paths.add(config_path)
                yield config_path
            elif config_path.is_dir():
                for root, folders, files in os.walk(str(config_path)):
                    root = Path(root)
                    for filename in files:
                        filepath = (root / filename).absolute()
                        if filepath in memoized_paths:
                            continue
                        memoized_paths.add(filepath)
                        yield filepath


def find_environment_folders(path=None):
    path = path or os.getenv('WORKON_HOME') or os.path.join(os.getenv('HOME'), '.virtualenvs')
    for root, directories, files in os.walk(path):
        found = []
        for index, name in enumerate(directories):
            directory = os.path.join(root, name)
            if not validate_environment(directory):
                continue
            yield name, directory
            found.append(name)
        # This makes the search "fast" by skipping out on folders
        #  that do not need to be searched because they have already
        #  been identified as valid environments
        directories[:] = [d for d in directories if d not in found]


def find_existing_venv_names(venvs_home=None):
    home = os.getenv('HOME')
    workon_home = os.getenv('WORKON_HOME') or Path(f'{home}/.virtualenvs')
    venvs_home = venvs_home or Path(workon_home) if workon_home and Path(workon_home).exists() else None

    if venvs_home and venvs_home.exists():
        standard_path = ['include', 'lib', 'bin']
        for path in os.scandir(venvs_home):
            if Path(path).is_dir():
                if Path(path).stem not in standard_path:
                    yield Path(path).stem


def remove(path, verbose=None, interactive=None, dry_run=None, check=None):
    """Remove a virtual environment

    Args:
        path (str): path to virtual environment
        verbose (int, optional): more output [default: 0]
        interactive (bool, optional): ask before updating system [default: False]
        dry_run (bool, optional): do not update system
        check (bool, optional): Raises PathNotFoundError if True and path isn't found [default: False]

    Raises:
        PathNotFoundError:  when check is True and path is not found

    Returns:
        str: folder path removed
    """
    verbose = max(int(verbose or 0), 0)
    check = False if check is None else check
    path = os.path.expanduser(path) if path.startswith('~') else os.path.abspath(path)
    if not validate_environment(path) and check is True:
        raise InvalidEnvironmentError(path=path)
    prompt = f'Remove {path}?'
    run_command = click.confirm(prompt) == 'y' if interactive else True
    if run_command and not dry_run:
        if os.path.exists(path):
            shutil.rmtree(path)
        elif check is True:
            raise PathNotFoundError(path=path)
    support.echo(click.style('Removed: ', fg='blue') + click.style(path, fg='green'), verbose=(max(verbose - 1, 0) and path))
    return path


def show_envs(path=None):
    path = path or os.getenv('WORKON_HOME')
    for name, path in find_environment_folders(path=path):
        print(f'Found {click.style(name, fg="yellow")} under: {click.style(path, fg="yellow")}')


def show_version():
    support.echo(f"{package_metadata['name']} {package_metadata['version']}")


def validate_environment(path, check=None):
    """Validates if path is a virtual environment

    Args:
        path (str): path to virtual environment
        check (bool, optional): Raise an error if path isn't valid

    Raises:
        InvalidEnvironmentError: when environment is not valid

    Returns:
        bool: True if valid virtual environment path
    """
    path = Path(path)
    valid = None
    win32 = sys.platform == 'win32'
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
        python_ver_data = re.search('(?P<interpreter>python|pypy)\.?(?P<major>\d+)(\.?(?P<minor>\d+))', python_name)
        if python_ver_data:
            python_ver_data = python_ver_data.groupdict()
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

    return valid


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
    prompt = prompt or os.getenv('PS1') or os.getenv('PROMPT')
    if prompt:
        prompt = eng.sub(replacement, prompt)
    else:
        prompt = r'\[\e[34m\]\w\[\e[0m\] \[\e[33m\]\$\[\e[0m\]'
    return prompt


def _get_builder(path, site_packages=None, overwrite=None, symlinks=None, upgrade=None, include_pip=None, prompt=None):
    path = os.path.expanduser(path) if path.startswith('~') else os.path.abspath(path)
    name = os.path.basename(path)
    builder = VenvBuilder(
        system_site_packages=False if site_packages is None else site_packages,
        clear=False if overwrite is None else overwrite,
        symlinks=True if symlinks is None else symlinks,
        upgrade=False if upgrade is None else upgrade,
        with_pip=True if include_pip is None else include_pip,
        prompt=f'({name})' if prompt is None else prompt,
        )
    return builder


def _get_interpreter(python=None):
    """Returns the interpreter given the string"""
    if python is None:
        return sys.executable

    # Maybe the path is already supplied
    if Path(python).exists():
        return python

    # Guess path
    paths = [Path(path) for path in os.getenv('PATH').split(':')]

    # Assume that python is a version if it doesn't start with p
    python = f'python{python}' if not python.startswith('p') else python
    interpreters = [python]

    # Build potential interpreter paths
    interpreter_paths = [p / i for p in paths for i in interpreters]
    for path in interpreter_paths:
        if path.absolute().exists():
            # return the first one found
            return path


def _update_environment(path):
    """Updates environment similar to activate from venv"""
    path = os.path.expanduser(path) if path.startswith('~') else os.path.abspath(path)
    name = os.path.basename(path)

    env = {k: v for k, v in os.environ.items()}
    env[package_metadata['name'].upper()] = name

    env['VIRTUAL_ENV'] = path
    env['PATH'] = ':'.join([os.path.join(env.get('VIRTUAL_ENV'), 'bin')] + env['PATH'].split(':'))

    shell = Path(env.get('SHELL') or '/bin/sh').name
    disable_prompt = env.get('VIRTUAL_ENV_DISABLE_PROMPT') or None
    shell_prompt_mapping = {
        'bash': 'PS1',
        'sh': 'PS1',
        'zsh': 'PROMPT'
        }
    shell_prompt_var = shell_prompt_mapping.get(shell)
    prompt = env.get(shell_prompt_var) or click.style("\w", fg="blue") + "\$ "
    prompt = _escape_zero_length_codes(prompt) if shell in ['bash', 'sh'] else prompt
    if shell_prompt_var and not disable_prompt:
        env[shell_prompt_var] = prompt

    return env

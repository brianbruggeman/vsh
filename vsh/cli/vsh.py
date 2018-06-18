import os
import subprocess
import sys
from pathlib import Path

from . import support
from .. import api
from .click import api as click


default_help = """
\b 
Available Virtual Environments:
    {envs}

""".format(envs="\n    ".join(f'{name:<12}' for name in sorted(api.find_existing_venv_names())))


@click.command(help=default_help, context_settings={'ignore_unknown_options': True, 'allow_interspersed_args': False})
@click.option('-c', '--copy', is_flag=True, help='Do not create symlinks for python')
@click.option('-C', '--create-only', is_flag=True, help='Only create venv, do not enter')
@click.option('-d', '--dry-run', is_flag=True, help='Do not make changes to the system')
@click.option('-e', '--ephemeral', is_flag=True, help='Create and remove')
@click.option('-i', '--interactive', is_flag=True, help='Run interactively')
@click.option('-l', '--ls', is_flag=True, help='Show available virtual environments')
@click.option('--no-pip', is_flag=True, help='Do not include pip')
@click.option('-o', '--overwrite', is_flag=True, help='Recreate venv')
@click.option('--path', metavar='PATH', help='Path to virtual environment')
@click.option('-p', '--python', metavar='VERSION', help='Python version to use')
@click.option('-r', '--remove', is_flag=True, help='Remove virtual enironment')
@click.option('-u', '--upgrade', is_flag=True, help='Upgrades to latest python version')
@click.option('-v', '--verbose', count=True, help='More output')
@click.option('-V', '--version', is_flag=True, help='Show version and exit')
@click.option('--shell-completion', is_flag=True, help='Show shell completion code')
@click.argument('name', metavar='VENV_NAME', type=click.OptionalChoice(api.find_existing_venv_names()), nargs=1, required=False)
@click.argument('command', required=False, nargs=-1)
@click.pass_context
def vsh(ctx, copy, create_only, dry_run, ephemeral, interactive, shell_completion, ls, no_pip, overwrite, path, python, remove, upgrade, verbose, version, name, command):
    if shell_completion:
        subprocess.run('_VSH_COMPLETE=source vsh', shell=True)
        sys.exit(0)

    verbose = verbose or 0
    return_code = 0
    if version:
        api.show_version()
        sys.exit(0)

    if ls:
        api.show_envs()
        sys.exit(0)

    if path and name:
        # favor path over name
        command = [name] + list(command)
        name = Path(path).name

    if not (path or name):
        click.echo(vsh.get_help(ctx))
        click.echo('\nERROR: A name or path must be provided.')
        sys.tracebacklimit = 0
        sys.exit(1)

    if not path:
        home = os.getenv('HOME')
        workon_home = os.getenv('WORKON_HOME') or os.path.join(home, '.virtualenvs')
        path = os.path.join(workon_home, name)

    # Determine if an environment already exists
    exists = api.validate_environment(path)

    if not command and not remove:
        command = os.getenv('SHELL')

    if exists and upgrade:
        # TODO: Add this
        #       Use pip freeze to capture everything installed currently
        #       Modify the python used
        #       Use pip and freeze list to rebuild virtual env with new python
        pass

    elif not exists and not remove:
        api.create(path, include_pip=not no_pip, overwrite=overwrite, symlinks=not copy, python=python, verbose=verbose)
        if ephemeral:
            remove = True

    if command and not create_only:
        return_code = api.enter(path, command, verbose=max(verbose - 1, 0))

    if ephemeral and not remove:
        quoted_name = '"{name}"'.format(name=click.style(name, fg="yellow"))
        rm_command = click.style(f'vsh -r {name}', fg='blue')
        support.echo(f'Virtual environment {quoted_name} existed previously.  Aborting removal.\nTo remove, run:\n\n    {rm_command}\n')

    if remove:
        api.remove(path, verbose=verbose, interactive=interactive, dry_run=dry_run)

    sys.tracebacklimit = 0
    sys.exit(return_code)

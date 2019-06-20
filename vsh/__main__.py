import sys
import textwrap
from pathlib import Path

from vsh import api
from vsh.env import env
from vsh.errors import VenvNameError
from vsh.vendored import click, termlog


def get_venvs(ctx, args, incomplete):
    folders = {name: path for name, path in sorted(api.find_environment_folders())}
    venvs = {name for name in folders if incomplete in name}
    return venvs


@click.command(context_settings={'ignore_unknown_options': True, 'allow_interspersed_args': False})
@click.option('-c', '--copy', is_flag=True if sys.platform != 'win32' else False, help='Do not create symlinks for python binaries during creation')
@click.option('-C', '--create-only', is_flag=True, help='Create virtual environment, but do not enter')
@click.option('-d', '--dry-run', is_flag=True, help='Do not make changes to the system')
@click.option('-e', '--ephemeral', is_flag=True, help='Create, enter and remove on vsh exit')
@click.option('-f', '--force', is_flag=True, help='Force removal options')
@click.option('-i', '--interactive', is_flag=True, help='Run interactively (debug)')
@click.option('-j', '--json', is_flag=True, help='Log messages to stdout in json')
@click.option('-l', '--list', 'ls', is_flag=True, help='Show available virtual environments')
@click.option('-m', '--monochrome', is_flag=True, help='Log messages to stdout without color')
@click.option('--no-pip', is_flag=True, help='Do not include pip')
@click.option('-o', '--overwrite', is_flag=True, help='Overwrite existing virtual environment')
@click.option('--path', metavar='PATH', help='Path to virtual environment', type=Path)
@click.option('-p', '--python', metavar='VERSION', help='Python version to use')
@click.option('-r', '--remove', is_flag=True, help='Remove virtual environment')
@click.option('-u', '--upgrade', is_flag=True, help='Upgrades to latest python version')
@click.option('-v', '--verbose', count=True, help='More output')
@click.option('-V', '--version', is_flag=True, help='Show version and exit')
@click.option('-w', '--working', metavar='PATH', default=None, help=f'Default startup PATH when entering virtual environment', type=Path)
@click.option('-W', '--ignore-working', 'ignore_working', is_flag=True, default=False, help=f'Ignore startup path when entering virtual environment [use: {Path.cwd()}]')
@click.argument('name', metavar='VENV_NAME', required=False, type=click.STRING, autocompletion=get_venvs)
@click.argument('command', required=False, nargs=-1)
@click.pass_context
def vsh(ctx, copy, create_only, dry_run, ephemeral, force, interactive, json, ls, monochrome, no_pip, overwrite, path, python, remove, upgrade, verbose, version, name, command, working, ignore_working):
    termlog.set_config(color=not monochrome, json=json, timestamp=False)
    if ls:
        api.show_venvs(verbose=verbose)
        exit(0)
    elif version:
        api.show_version()
        exit(0)
    else:
        try:
            name, path = api.validate_venv_name_and_path(name=name, path=path)
        except VenvNameError:
            termlog.echo(vsh.get_help(ctx))
            termlog.echo(f'\n{termlog.red("Error")}: Missing {termlog.cyan("name")} or {termlog.cyan("path")}.\n')
            exit(1)
    return_code = 0

    if path and name:
        # favor path over name
        command = list(command)
        name = Path(path).name

    if not (path or name):
        termlog.echo(vsh.get_help(ctx))
        termlog.echo(f'\n{termlog.red("Error")}: Missing {termlog.cyan("name")} or {termlog.cyan("path")}.\n')
        exit(1)

    if not path:
        path = api.get_venv_home(name=name)

    # Determine if an environment already exists
    exists = api.validate_environment(path)

    # when no command exists, default to the shell itself
    if not command and not remove:
        command = env.SHELL

    # when upgrade is requested, then perform upgrade
    if exists and upgrade:
        api.upgrade(
            path,
            include_pip=not no_pip,
            overwrite=overwrite,
            symlinks=not copy,
            python=python,
            working=working,
            verbose=verbose - 1,
        )

    elif not exists and not remove:
        api.create(
            path,
            include_pip=not no_pip,
            overwrite=overwrite,
            symlinks=not copy,
            python=python,
            working=working,
            verbose=verbose - 1,
        )
        if ephemeral:
            remove = True

    if (sys.platform in ['win32'] or command) and not create_only:
        return_code = api.enter(path, command, verbose=verbose, working=working, ignore_working=ignore_working)

    if ephemeral and not (force or remove):
        msg = textwrap.dedent(
            f'''\

        {termlog.yellow('WARNING: Ephemeral option ignored. Aborting removal.')}

        Virtual environment '{termlog.green(name)}' existed previously.
        To remove, run:

            {termlog.cyan(f'vsh -r {name}')}

        '''
        )  # noqa
        termlog.echo(msg)

    if remove:
        api.remove(path, verbose=verbose, interactive=interactive, dry_run=dry_run)

    sys.tracebacklimit = 0
    exit(return_code)


if __name__ == '__main__':
    vsh()

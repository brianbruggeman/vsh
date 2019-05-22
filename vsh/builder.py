import os
import subprocess
import sys
import types
import venv
from pathlib import Path
from typing import Optional


class VenvBuilder(venv.EnvBuilder):

    def create(self, env_dir: str, executable: Optional[str] = None):
        """
        Create a virtual environment in a directory.

        Args:
            env_dir: The target directory to create an environment in.
            executable: path to python interpreter executable [default: sys.executable]
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

    def ensure_directories(self, env_dir: str, executable: Optional[str] = None):
        """
        Create the directories for the environment.
        Returns a context object which holds paths in the environment,
        for use by subsequent logic.

        Args:
            env_dir: path to environment
            executable: path to python interpreter executable [default: sys.executable]

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

    def _setup_pip(self, context: types.SimpleNamespace):
        """Installs or upgrades pip in a virtual environment"""
        # We run ensurepip in isolated mode to avoid side effects from
        # environment vars, the current directory and anything else
        # intended for the global Python environment
        # Originally -Im, but -Esm works on both python2 and python3
        cmd = [context.env_exe, '-Esm', 'ensurepip', '--upgrade', '--default-pip']
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)

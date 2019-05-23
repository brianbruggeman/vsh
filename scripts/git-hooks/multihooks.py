#!/usr/bin/env python3
import errno
import os
import select
import shlex
import sys
from subprocess import PIPE, Popen

if sys.version.startswith('3'):
    basestring = str


def run(command, env=None, buffer_size=None):
    """Run the given command.

    Args:
        command(str or list): command
        env(dict): Environment variables to use
        cwd(str): Path to execute this command

    Returns:
        int: return code for process
    """
    command = shlex.split(command) if not isinstance(command, list) else command
    env = env or os.environ.copy()
    process = Popen(command, env=env, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    pipes = [process.stderr, process.stdout, process.stdin]
    filenos = [_.fileno() for _ in pipes]
    should_run = True
    fd_mapping = {
        process.stdout: sys.stdout,
        process.stderr: sys.stderr,
        # process.stdin: sys.stdin
        }
    while should_run:
        try:
            selectables = select.select(filenos, filenos, filenos)
        except select.error as e:
            if e.args[0] == errno.EINTR:
                continue
        if not any(selectables):
            continue
        for selected_list in selectables:
            for fileno in selected_list:
                for fd in pipes:
                    if fd.fileno() != fileno:
                        continue
                    rfd = fd_mapping.get(fd)
                    if rfd is None:
                        continue
                    for line in fd:
                        yield rfd, line.decode('utf-8')

        if process.poll() is not None:
            should_run = False
    yield None, process.returncode


def execute_hooks():
    hook = os.path.abspath(sys.argv[0])
    folder = hook + '.d'
    if os.path.exists(folder) and os.path.isdir(folder):
        for root, folders, files in os.walk(folder):
            for filename in files:
                filepath = os.path.join(root, filename)
                if os.access(filepath, os.X_OK):
                    for fd, line in run(filepath):
                        if fd is None and isinstance(line, int):
                            if line != 0:
                                return line
                            continue
                        fd.write(line)


if __name__ == '__main__':
    import sys
    exit(execute_hooks() or 0)

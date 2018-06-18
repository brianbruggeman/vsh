#!/usr/bin/env python
"""
Setup.py shouldn't be updated during normal development.

Update:
   entrypoints.txt  <-- add new command-line interfaces here
   requirements.txt  <-- required for package to run
   requirements/*.txt  <-- as appropriate
"""
import datetime
import itertools
import os
import shutil
import sys
from pathlib import Path

from setuptools import Command, setup

try:
    import pip._internal.req as req
except ImportError:
    import pip.req as req

try:
    import pypandoc
except ImportError:
    pypandoc = None


if sys.version_info < (3, 6):
    sys.stderr.write('Python 3.6+ is required for installation.\n')
    sys.tracebacklimit = 0
    sys.exit(1)


def main():
    """Run setup"""
    metadata = get_package_metadata()

    # Run setup
    setup(**metadata)


class CleanCommand(Command, object):
    description = 'Remove build artifacts and *.pyc'
    user_options = list()

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        repo_path = str(Path(__file__).parent)
        removables = [
            'build', '_build', 'dist', 'wheelhouse',
            '*.egg-info', '*.egg', '.eggs'
            ]
        for removable in removables:
            for path in os.scandir(repo_path):
                if Path(path).match(removable):
                    if path.is_dir():
                        shutil.rmtree(path)
                    elif path.is_file():
                        os.remove(path)

        for root, folders, files in os.walk(repo_path):
            for folder in folders:
                if folder == '__pycache__':
                    fpath = os.path.join(root, folder)
                    shutil.rmtree(fpath)
            for filename in files:
                fpath = os.path.join(root, filename)
                if Path(filename).match('*.py[co]'):
                    os.remove(fpath)


# ----------------------------------------------------------------------
# Support
# ----------------------------------------------------------------------
files_in_tree = set()
folders_in_tree = set()


def find_data_files(repo_path=None):
    """Captures files that are project specific"""
    repo_path = repo_path or Path(__file__).parent

    include = ['LICENSE', 'requirements', 'requirements*.txt', 'entrypoints.txt']
    found = [
        str(path)
        for path in scan_tree(repo_path)
        if (any(path.match(included) for included in include)
            or any(parent.match(included) for parent in path.parents for included in include))
        ]
    return found


def find_packages(repo_path=None):
    """Finds packages; replacement for setuptools.find_packages which
    doesn't support PEP 420.

    Lengthy discussion with no resolution:
        https://github.com/pypa/setuptools/issues/97

    Assumptions:
      * Packages are folders
      * Modules are files
      * Namespaces are folders without modules
      * setup.py is for a single package
      * the folder which contains setup.py is _not_ a package itself
      * each package falls under a single tree (e.g. requests, requests.api, etc.)
      * the package is complex enough to have multiple sub folders/modules

    Args:
        repo_path (str): path to check [default: path of setup.py]

    Returns:
        list(list, list, list): Returns packages, modules and namespaces

    """
    repo_path = repo_path or Path(__file__).parent
    packages = set()
    modules = set()
    namespaces = set()
    python_artifacts = ['__pycache__']
    repo_artifacts = ['.*']
    install_artifacts = ['*.egg-info']
    build_artifacts = ['dist', 'build']
    test_files = ['tests', 'test', '.tox']
    artifacts = install_artifacts + build_artifacts + repo_artifacts + python_artifacts + test_files
    for path in scan_tree(str(repo_path)):
        # Only include paths with .py
        if not path.match('*.py'):
            continue

        # check folders
        if any(p.match(artifact) for artifact in artifacts for p in path.parents):
            continue

        # There should be a valid package at this point
        package_name = str(path.parent).replace(os.path.sep, '.')
        module_name = str(path).replace(os.path.sep, '.').replace(path.suffix, '')
        if package_name == '.':
            module_name = '.' + module_name
            if module_name == '.setup':
                continue
            modules.add(module_name)
            continue

        modules.add(module_name)
        packages.add(package_name)

    # find namespaces
    for module_name in modules:
        module_path = Path(module_name.replace('.', os.path.sep))
        package_name = str(module_path.parent).replace(os.path.sep, '.')
        if package_name in packages:
            continue
        namespaces.add(package_name)

    return sorted(packages), sorted(modules), sorted(namespaces)


def get_entrypoints(path=None):
    """
    """
    entry_points = {}
    path = path or 'entrypoints.txt'
    if not os.path.exists(path):
        return entry_points

    with open(path) as stream:
        for line in stream:
            if not line.strip():
                continue
            if line.strip().startswith('#'):
                continue
            entry_points.setdefault('console_scripts', []).append(line.strip())
    return entry_points


def get_license(top_path=None):
    """Reads license file and returns"""
    repo_path = top_path or os.path.realpath(os.path.dirname(__file__))
    files = {f.lower(): f for f in os.listdir(repo_path)}
    permutations = itertools.product(['license'], ['', '.txt'])
    files = [os.path.join(repo_path, f) for l, f in files.items() if l in permutations]
    license = ''
    for filepath in files:
        if os.path.exists(filepath):
            with open(filepath, 'r') as stream:
                license = stream.read()
                break
    return license


def get_package_metadata(top_path=None):
    """Find the __metadata__.py file and read it"""
    repo_path = top_path or os.path.realpath(os.path.dirname(__file__))
    metadata = {}
    prefixes = ('.', '_')
    for root, folders, files in os.walk(repo_path):
        rel = root.replace(repo_path, '').lstrip(os.path.sep)
        folders[:] = [
            folder for folder in folders
            if not any(folder.startswith(prefix) for prefix in prefixes)
            ]
        for filename in files:
            filepath = Path(os.path.join(rel, filename))
            if filepath.name == '__metadata__.py':
                exec(filepath.open().read(), globals(), metadata)
                metadata = metadata.get('package_metadata') or metadata
                break
        if metadata:
            break

    requirements, dependency_links = get_package_requirements(top_path=top_path)
    packages, modules, namespaces = find_packages()
    # Package Properties
    metadata.setdefault('long_description', metadata.get('doc') or get_readme())
    metadata.setdefault('packages', packages)
    metadata.setdefault('include_package_data', True)

    # Requirements
    metadata.setdefault('setup_requires', requirements.get('setup') or [])
    metadata.setdefault('install_requires', requirements.get('install') or [])
    metadata.setdefault('tests_require', requirements.get('tests') or requirements.get('test') or [])
    metadata.setdefault('extras_require', requirements.get('extras') or [])
    metadata.setdefault('dependency_links', dependency_links)

    # CLI
    entry_points = get_entrypoints() or {}
    metadata.setdefault('entry_points', entry_points)

    # Packaging
    metadata.setdefault('platforms', ['any'])
    metadata.setdefault('zip_safe', False)

    year = datetime.datetime.now().year
    license = get_license() or 'Copyright {year} - all rights reserved'.format(year=year)
    metadata.setdefault('license', license)

    # Extra data
    metadata.setdefault('data_files', [('', find_data_files())])

    # Add setuptools commands
    metadata.setdefault('cmdclass', get_setup_commands())
    return metadata


def get_package_requirements(top_path=None):
    """Find all of the requirements*.txt files and parse them"""
    repo_path = top_path or os.path.realpath(os.path.dirname(__file__))
    requirements = {'extras': {}}
    dependency_links = set()
    # match on:
    #    requirements.txt
    #    requirements-<name>.txt
    #    requirements_<name>.txt
    #    requirements/<name>.txt
    options = '_-/'
    include_globs = ['requirements*.txt', 'requirements/*.txt']
    paths = [
        relpath
        for relpath in scan_tree(repo_path, include=include_globs)
        ]
    for path in paths:
        if 'requirements' in map(str, path.parents):
            name = path.name.replace(path.suffix, '')
        elif 'requirements' in path.name:
            name = path.name.replace('requirements', '').lstrip(options)
        else:
            raise Exception('Could not find requirements using ' + path)
        reqs_, deps = parse_requirements(str(path.absolute()))
        dependency_links.update(deps)
        if name in ['install', '']:
            requirements['install'] = reqs_
        elif name in ['test', 'tests']:
            requirements['tests'] = reqs_
            requirements['extras']['tests'] = reqs_
        elif name in ['setup']:
            requirements['setup'] = reqs_
        else:
            requirements['extras'][name] = reqs_

    all_reqs = set()
    dev_reqs = set()
    for name, req_list in requirements.items():
        if name in ['install']:
            all_reqs.update(req_list)
        elif name in ['extras']:
            for subname, reqs in req_list.items():
                all_reqs.update(reqs)
                dev_reqs.update(reqs)
        else:
            all_reqs.update(req_list)
            dev_reqs.update(req_list)

    requirements['extras']['dev'] = list(sorted(dev_reqs))
    requirements['extras']['all'] = list(sorted(all_reqs))
    return requirements, list(sorted(dependency_links))


def get_readme(top_path=None):
    """Read the readme for the repo"""
    path = top_path or os.path.realpath(os.path.dirname(__file__))
    found = {f.name.lower(): f.name for f in os.scandir(path)}
    permutations = [a + b for a, b in itertools.product(['readme'], ['.md', '.rst', '.txt'])]
    files = [os.path.join(path, f) for l, f in found.items() if l in permutations]
    readme = ''
    for filepath in files:
        if pypandoc and filepath.endswith('.md'):
            readme = pypandoc.convert(filepath, 'rst')
            break
        else:
            with open(filepath, 'r') as stream:
                readme = stream.read()
                break
    return readme


def get_setup_commands():
    """Returns setup command class list"""
    commands = {
        'clean': CleanCommand,
        }
    return commands


def parse_requirements(path):
    template = '{name}{spec}'
    requirements = set()
    dependency_links = set()
    for requirement in req.parse_requirements(path, session="somesession"):
        if requirement.markers is not None and not requirement.markers.evaluate():
            continue

        name = requirement.name
        spec = str(requirement.req.specifier) if len(str(requirement.req.specifier)) else ''
        req_ = template.format(name=name, spec=spec)
        if req_:
            requirements.add(req_)

        link = str(requirement.link) if requirement.link else ''
        if link:
            dependency_links.add(link)

        # TODO: What do we do with these?
        if requirement.options:
            pass

    return list(sorted(requirements)), list(sorted(dependency_links))


def scan_tree(top_path=None, include=None):
    """Finds files in tree

    * Order is random
    * Folders which start with . and _ are excluded unless excluded is used (e.g. [])
    * This list is memoized

    Args:
        top_path (str): top of folder to search
        include (list, optional): filters on include if present

    Yields:
        str: paths as found
    """
    repo_path = Path(__file__)
    if not files_in_tree:
        for root, folders, files in os.walk(str(top_path or repo_path)):
            rel = Path(root.replace(str(top_path or repo_path), '').lstrip('/'))
            # Control traversal
            folders[:] = [f for f in folders if f not in ['.git']]
            folders_in_tree.update(folders)
            # Yield files
            for filename in files:
                relpath = rel.joinpath(filename)
                if relpath not in files_in_tree:
                    files_in_tree.add(relpath)
                    if include is not None:
                        if any(relpath.match(inc) for inc in include):
                            yield relpath
                    else:
                        yield relpath
    else:
        for relpath in files_in_tree:
            if include:
                if any(relpath.match(inc) for inc in include):
                    yield relpath
            else:
                yield relpath


if __name__ == '__main__':
    main()

import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from setuptools import setup

from vsh import package_metadata

try:
    # pip10+
    import pip._internal.req as req
except ImportError:
    # pip9
    import pip.req as req


def main():
    repo_path = Path(__file__).parent

    modules = get_modules(package_metadata, repo_path)
    packages = parse_packages(modules)
    requirements = load_package_requirements(packages, repo_path)
    entrypoints = get_package_entrypoints(repo_path)

    setup(
        name=package_metadata.name,
        version=package_metadata.version,
        description=package_metadata.description,
        license=package_metadata.license,

        url=package_metadata.url,

        author=package_metadata.author,
        author_email=package_metadata.author_email,

        maintainer=package_metadata.maintainer,
        maintainer_email=package_metadata.maintainer_email,

        classifiers=list(package_metadata.classifiers),
        keywords=list(package_metadata.keywords),

        setup_requires=requirements.get('setup') or [],
        install_requires=requirements.get('install') or [],
        tests_require=requirements.get('tests') or [],
        extras_require=requirements.get('extras') or [],

        packages=packages,
        entry_points=entrypoints,
        )


def find_package_metadata_filepath(top_path: Path):
    for path in scan_repo(top_path):
        if path.name == '__metadata__.py':
            return path


def find_package_requirements_filepaths(top_path: Path) -> Tuple[str, Path]:
    for path in scan_repo(top_path):
        if path.name == 'requirements.txt':
            yield 'install', path
        elif path.name.startswith('requirements-') and path.name.endswith('.txt'):
            name = path.name.split('requirements-')[-1]
            yield name, path
        elif path.name.endswith('.txt') and 'requirements' in path.parts:
            yield path.stem, path


def get_package_entrypoints(top_path: Path) -> Dict[str, str]:
    entry_points = {}
    for path in scan_repo(top_path):
        if path.name == 'entrypoints.txt':
            for entry in parse_entrypoints(path):
                entry_points.setdefault('console_scripts', []).append(entry)
    return entry_points


def get_package_metadata(top_path=None):
    """Find the __metadata__.py file and read it"""
    repo_path = str(Path(top_path or Path(__file__).parent).absolute())
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
                d = dict(locals(), **globals())
                exec(filepath.open().read(), d, d)
                metadata = d.get('package_metadata') or metadata
                break
        if metadata:
            break


def get_modules(package_metadata, top_path: Path) -> List[str]:
    modules = []
    for path in scan_repo(top_path):
        if path.parts[0] == package_metadata.package_name:
            # Only collect subfolders that have a python file within
            #   its tree
            if path.is_dir():
                if any(path.glob('**/*.py')):
                    modules.append('.'.join(path.parts))
    return modules


def parse_packages(modules: List[str]) -> List[str]:
    packages = []
    for module_name in modules:
        if '.' not in module_name:
            packages.append(module_name)
    return packages


def load_package_metadata(path: Path):
    text = path.read_text(encoding='utf-8')
    d = dict(locals(), **globals())
    exec(text, d, d)
    metadata = d.get('package_metadata')
    return metadata


def load_package_requirements(packages: List[str], top_path: Path):
    package_requirements = {'extras': {'all': set(), 'dev': set()}}
    for name, path in find_package_requirements_filepaths(top_path):
        reqs, deps = parse_requirements(path)
        new_reqs = set(package_requirements.get(name) or [])
        new_reqs.update(reqs)
        if name not in ['install', 'test', 'tests', 'setup']:
            package_requirements['extras'].setdefault(name, set()).update(new_reqs)
            package_requirements['extras']['all'].update(new_reqs)
            package_requirements['extras']['dev'].update(new_reqs)
        else:
            if name in ['tests', 'test']:
                package_requirements.setdefault('tests', set()).update(new_reqs)
                package_requirements['extras'].setdefault(name, set()).update(new_reqs)
                package_requirements['extras']['dev'].update(new_reqs)
                package_requirements['extras']['all'].update(new_reqs)
            else:
                package_requirements['extras']['all'].update(new_reqs)
                package_requirements.setdefault(name, set()).update(new_reqs)

    # pip doesn't like sets as a list of requirements
    for key, value in package_requirements.items():
        if key == 'extras':
            extras = package_requirements.get(key) or {}
            for extra_name, reqs in extras.items():
                extras[extra_name] = sorted(reqs)
        else:
            package_requirements[key] = sorted(value)

    package_requirements['extras']['all'].extend(packages)
    return package_requirements


def parse_entrypoints(path: Path) -> Iterable:
    data = [
        line.strip()
        for line in path.read_text(encoding='utf-8').split('\n')
        if line.strip()
        if not line.strip().startswith('#')
        ]
    for line in data:
        yield line


def parse_requirements(path: Path):
    template = '{name}{spec}'
    requirements = set()
    dependency_links = set()
    for requirement in req.parse_requirements(str(path), session="somesession"):
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


@lru_cache(maxsize=None)
def scan_repo(top_path: Path):
    paths = []
    for root, folders, files in os.walk(str(top_path)):
        root = Path(root).relative_to(top_path)
        for folder_name in folders:
            paths.append(root / folder_name)
        for file_name in files:
            paths.append(root / file_name)
    return paths


if __name__ == '__main__':
    main()

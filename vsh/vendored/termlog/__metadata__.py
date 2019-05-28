"""This is imported by setup.py and contains all of the information
necessary to run setup.py
"""
import os
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, Tuple


# ----------------------------------------------------------------------
# Package Metadata
# ----------------------------------------------------------------------
@dataclass
class PackageMetadata:
    """Package metadata information

    Notes:
        This is used in setup, scripts, cli interface, endpoints, etc.

    Attributes:
        name: name of package
        package_name: import name for package
        title: short human readable title for package
        summary: long human readable title for package
        description: long description for package

        version: semantic version of package
        major: major component of semantic version (X._._)
        minor: minor component of semantic version (_.X._)
        micro: micro component of semantic version (_._.X)
        build: git sha value of build
        release: human friendly release name

        author: package author
        author_email: email for package author

        maintainer: package maintainer
        maintainer_email: package maintainer email

        copyright: copyright years of major work on package
        license: default license for package

        url: location for package repository or documentation

        classifiers:  python trove classifiers
        keywords: keywords for searching for package

    Example:
        The PackageMetadata attributes can be accessed by something
        like the following.

        >>> from termlog.__metadata__ import package_metadata
        >>> package_metadata.name
        termlog

    """
    name: str = 'termlog'
    version: str = '1.0.2'
    package_name: str = field(init=False, repr=False, default='')
    title: str = f'A terminal logging library'
    summary: str = 'Create beautiful terminal structured '\
                   'output for developers and production systems'

    major: int = field(init=False, repr=False)
    minor: int = field(init=False, repr=False)
    micro: int = field(init=False, repr=False)
    build: str = field(init=False, repr=False)
    release: str = field(init=False, repr=False)

    description: str = f'''{name} v{version}: {title}'''
    author: str = 'Brian Bruggeman'
    author_email: str = 'brian.m.bruggeman@gmail.com'

    maintainer: str = 'Brian Bruggeman'
    maintainer_email: str = 'brian.m.bruggeman@gmail.com'

    copyright: str = f'2019'
    license: str = f'MIT'

    url: str = 'https://github.com/brianbruggeman/termlog'
    bug_reports_url: str = 'https://github.com/brianbruggeman/termlog/issues'
    documentation_url: str = 'https://termlog.readthedocs.io/en/latest/'
    travis_CI_url: str = 'https://travis-ci.org/brianbruggeman/termlog'
    code_coverage_url: str = 'https://codecov.io/gh/brianbruggeman/termlog'
    project_urls: Dict = field(init=False, repr=False, default_factory=dict)

    classifiers: Tuple = (
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: MacOS',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: System :: Logging',
        'Topic :: Terminals',
        'Typing :: Typed',
        )

    keywords: Tuple = (
        'terminal',
        'logger',
        'docker',
        )

    @property
    def setup(self) -> Dict:
        """Returns setup.py friendly fields and values"""
        # see: https://packaging.python.org/specifications/core-metadata/
        required_fields = [
            'metadata_version', 'name', 'version',
            ]
        setup_friendly_fields = required_fields + [
            'platform', 'supported_platform', 'description',
            'description_content_type', 'keywords', 'home_page', 'download_url',
            'author', 'author_email', 'maintainer', 'maintainer_email',
            'license', 'classifier', 'requires_dist', 'requires_python',
            'requires_external', 'project_urls', 'provides_extra',
            'provides_dist', 'obsoletes_dist',

            'long_description', 'long_description_content_type',
            'license', 'version', 'author', 'author_email',
            'maintainer', 'maintainer_email', 'license', 'url',
            'classifiers', 'keywords'
            ]
        data = {}
        for key, value in asdict(self).items():
            if key in setup_friendly_fields:
                data[key] = value
        data['keywords'] = list(data['keywords'])
        data['classifiers'] = list(data['classifiers'])
        return data

    def __post_init__(self):
        self.package_name = self.name.replace('-', '_')
        self.major, self.minor, self.micro = list(map(int, self.version.split('.')))
        self.build = self._get_build() or ''
        if self.build:
            self.release = f'{self.name} {self.version} [build: {self.build}]'
        else:
            self.release = f'{self.name} {self.version}'
        for key, value in asdict(self).items():
            if key.endswith('_url'):
                name = ' '.join(key[:-4].split('_')).capitalize()
                self.project_urls.setdefault(name, value)

    def _get_build(self):
        # localhost
        git_sha = self._get_git_sha()
        if git_sha:
            return git_sha

        # AWS
        filepath_sha = self._get_filepath_git_sha()
        if filepath_sha:
            return filepath_sha

        # docker
        try:
            # In an effort to clearly identify where we use environment
            # variables, this will use config, but it creates both
            # a circular dependency and causes problems for setup.py
            # which reads this file.  So punt if there are problems
            git_sha_env = os.getenv('CDR_REST_GIT_SHA')
            if git_sha_env:
                return git_sha_env
        except ImportError:
            # Otherwise this will fail during setup.py
            print('Failed to capture build')
            for key, value in sorted(os.environ.items()):
                print(f'{key}: {value}')

    @staticmethod
    def _get_git_sha():
        # In a development enviromment this will have access to git
        #  and it's possible to simply query the last hash value
        git_command = ('git', 'rev-parse', '--short', 'HEAD')
        proc = subprocess.run(git_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode == 0:
            return proc.stdout.decode('utf-8').strip('\n')

    @staticmethod
    def _get_filepath_git_sha():
        # In a production environment, the hash value should be
        #  part of the file path
        for path_fragment in Path(__file__).absolute().parts:
            if not path_fragment or path_fragment == '/':
                continue
            if path_fragment.startswith('termlog-'):
                if 'git.sha' in path_fragment:
                    return path_fragment.split('termlog-')[-1]

    def keys(self):
        yield from self.__annotations__.keys()

    def __getitem__(self, item):
        if item in self.__annotations__.keys():
            value = getattr(self, item)
            return value
        raise AttributeError(f"Could not find {item}")

    def __iter__(self):
        for field in self.__annotations__.keys():
            yield field


package_metadata = PackageMetadata()

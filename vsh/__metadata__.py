import subprocess
from dataclasses import dataclass, field
from textwrap import dedent
from typing import Dict, Tuple

__all__ = ['package_metadata']


# ----------------------------------------------------------------------
# Package Metadata
# ----------------------------------------------------------------------
@dataclass
class PackageMetadata:
    """Package metadata information
    Notes:
        This is used in setup, scripts, cli interface, etc.

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

        >>> from vsh import package_metadata
        >>> package_metadata.name
        vsh

    """

    name: str = 'vsh'  # PEP 508
    version: str = '0.7.2'  # PEP 440
    package_name: str = field(init=False, repr=False, default='')
    title: str = 'Virtual Environment Shell'
    summary: str = f'Manager for python\'s virtual environments'
    description: str = dedent(
        f"""\
    {summary}

    This cli-based package provides a mechanism to control virtual
    environments for python packages.  It is meant to be useful for
    both production environments as well as everyday use.

    The goal is to let the tool run and get out of your way, providing
    a fast and easy mechanism to create, enter and remove virtual
    environments with a low amount of typing.

    """
    )

    # These are set in post init
    major: int = field(init=False, repr=False, default=0)
    minor: int = field(init=False, repr=False, default=0)
    micro: int = field(init=False, repr=False, default=0)
    build: str = field(init=False, repr=False, default='')
    release: str = field(init=False, repr=False, default='')

    author: str = 'Brian Bruggeman'
    author_email: str = 'brian.m.bruggeman@gmail.com'

    maintainer: str = 'Brian Bruggeman'
    maintainer_email: str = 'brian.m.bruggeman@gmail.com'

    copyright: str = f'2017-2018'
    license: str = 'MIT'

    url: str = 'https://github.com/brianbruggeman/vsh'

    classifiers: Tuple = (
        'Programming Language :: Python',
        'Natural Language :: English',
        'Development Status :: 4 - Beta',
        'Natural Language :: English',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 3.7',
    )

    keywords: Tuple = ('vsh', 'virtual environment', 'venv')

    @property
    def setup(self) -> Dict:
        """Returns setup.py friendly fields and values"""
        # see: https://packaging.python.org/specifications/core-metadata/
        required_fields = ['metadata_version', 'name', 'version']
        setup_friendly_fields = required_fields + [
            'platform',
            'supported_platform',
            'summary',
            'description',
            'description_content_type',
            'keywords',
            'home_page',
            'download_url',
            'author',
            'author_email',
            'maintainer',
            'maintainer_email',
            'license',
            'classifier',
            'requires_dist',
            'requires_python',
            'requires_external',
            'project_url',
            'provides_extra',
            'provides_dist',
            'obsoletes_dist',
            'long_description',
            'license',
            'version',
            'author',
            'author_email',
            'maintainer',
            'maintainer_email',
            'copyright',
            'license',
            'url',
            'classifiers',
            'keywords',
        ]
        data = {}
        for key in self.__annotations__.keys():
            if key in setup_friendly_fields:
                value = getattr(self, key)
                data[key] = value
        return data

    def __post_init__(self):
        self.package_name = self.name.replace('-', '_')
        self.major, self.minor, self.micro = list(map(int, self.version.split('.')))
        self.build = self._get_build() or ''
        if self.build:
            self.release = f'{self.name} {self.version} [build: {self.build}]'
        else:
            self.release = f'{self.name} {self.version}'

    def _get_build(self):
        # localhost
        git_sha = self._get_git_sha()
        if git_sha:
            return git_sha

    def _get_git_sha(self):
        # In a development enviromment this will have access to git
        #  and it's possible to simply query the last hash value
        git_command = ('git', 'rev-parse', '--short', 'HEAD')
        proc = subprocess.run(git_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode == 0:
            return proc.stdout.decode('utf-8').strip('\n')

    def __contains__(self, item):
        return hasattr(self, item)

    def __getitem__(self, item):
        if not hasattr(self, item):
            raise KeyError(f'Could not find {item}')
        return getattr(self, item)

    def __setitem__(self, key, value):
        setattr(self, key, value)


package_metadata = PackageMetadata()

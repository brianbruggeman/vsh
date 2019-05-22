import pytest


@pytest.mark.parametrize('field, expected', [
    ('name', 'vsh'),
    ('package_name', 'vsh'),
    ('title', 'Virtual Environment Shell'),
    ('author', 'Brian Bruggeman'),
    ('author_email', 'brian.m.bruggeman@gmail.com'),
    ('maintainer', 'Brian Bruggeman'),
    ('maintainer_email', 'brian.m.bruggeman@gmail.com'),
    ('copyright', '2017-2018'),
    ('license', 'MIT'),
    ('url', 'https://github.com/brianbruggeman/vsh'),
    ('classifiers', (
        'Programming Language :: Python', 'Natural Language :: English',
        'Development Status :: 4 - Beta',
        'Natural Language :: English',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 3.7',
        )),
    ('keywords', (
        'vsh',
        'virtual environment',
        'venv',
        )),
    ('summary', 'Manager for python\'s virtual environments'),
    ('description', None),
    ('build', None),
    ])
def test_metadata(field, expected):
    from vsh import package_metadata
    from vsh.__metadata__ import PackageMetadata

    p = PackageMetadata()
    assert p == package_metadata
    assert field in p
    if expected is not None:
        assert getattr(p, field) == expected
    else:
        assert getattr(p, field) is not None


def test_metadata_version():
    from vsh.__metadata__ import PackageMetadata

    p = PackageMetadata()
    version_fields = [
        'version', 'major', 'minor', 'micro', 'release'
        ]
    for field in version_fields:
        assert field in p

    assert p.version == f'{p.major}.{p.minor}.{p.micro}'
    if p.build:
        assert p.release == f'{p.name} {p.version} [build: {p.build}]'
    else:
        assert p.release == f'{p.name} {p.version}'


@pytest.mark.unit
@pytest.mark.parametrize("exc_name, message", [
    ('BaseError', None),
    ('BaseError', 'Test message'),
    ])
def test_project_exceptions(exc_name, message):
    from vsh import errors

    assert hasattr(errors, exc_name)
    Exception = getattr(errors, exc_name)
    with pytest.raises(Exception):
        if message:
            raise Exception(message)
        else:
            raise Exception()

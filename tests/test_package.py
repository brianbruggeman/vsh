import pytest


@pytest.mark.unit
@pytest.mark.parametrize("key, expected_value", [
    ("__name__", "vsh"),
    ("__description__", "A virtual environment shell"),
    ("__author__", "Brian Bruggeman"),
    ("__author_email__", "brian.m.bruggeman@gmail.com"),
    ("__maintainer__", "Brian Bruggeman"),
    ("__maintainer_email__", "brian.m.bruggeman@gmail.com"),
    ("__url__", "https://github.com/brianbruggeman/vsh"),
    ])
def test_project_metadata(key, expected_value):
    import vsh.__metadata__ as md

    fields = [_ for _ in dir(md)]
    value = getattr(md, key, None)
    assert key in fields
    assert value == expected_value


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

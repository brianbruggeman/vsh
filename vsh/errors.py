class BaseError(Exception):
    """Fancy error handler"""

    def __init__(self, message=None, **kwds):
        if message is not None:
            message = message.format(**kwds) if kwds else message
        else:
            message = self.__doc__.format(**kwds) if kwds else self.__doc__
        self.__msg__ = message
        Exception.__init__(self, message)

    def __repr__(self):
        cname = type(self).__name__
        message = self.__msg__
        return f'<{cname} {message}>'

    def __str__(self):
        return self.__msg__


class InterpreterNotFound(BaseError):
    """ERROR: Could not find interpreter for: {version}"""


class InvalidEnvironmentError(BaseError):
    """ERROR: Path is not a valid environment: {path}"""


class PathNotFoundError(BaseError):
    """ERROR: Could not find path: {path}"""

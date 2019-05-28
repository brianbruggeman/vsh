# flake8: noqa
from .__metadata__ import package_metadata   # isort:skip

__author__ = package_metadata.author
__version__ = package_metadata.version


from .colors import *
from .formatting import *
from .terminal import *


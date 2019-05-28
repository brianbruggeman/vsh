import os
from pathlib import Path


def scan_tree(path: Path):
    """Finds files in tree

    * Order is random
    * Folders which start with . and _ are excluded unless excluded is used (e.g. [])
    * This list is memoized

    Args:
        top_path: top of folder to search

    Yields:
        str: paths as found
    """
    for root, folders, files in os.walk(str(path)):
        relative_root = Path(root).relative_to(path)
        # Control traversal
        folders[:] = [f for f in folders if f not in [".git"]]
        # Yield files
        for filename in files:
            relative_path = relative_root / filename
            yield relative_path


class EmulateSequence:
    def __len__(self):
        return len(self.__annotations__.keys())

    def __iter__(self):
        for key in self.__annotations__.keys():
            yield getattr(self, key)


class EmulateMap:
    def keys(self):
        yield from self.__annotations__.keys()

    def values(self):
        for key in self.__annotations__.keys():
            yield getattr(self, key)

    def items(self):
        for key in self.__annotations__.keys():
            yield key, getattr(self, key)

    def __getitem__(self, item):
        if item not in self.__annotations__.keys():
            raise KeyError(f"Could not find {item}")
        return getattr(self, item)

    def __setitem__(self, key, value):
        if key not in self.__annotations__.keys():
            raise KeyError(f"Could not find {key}")
        setattr(self, key, value)


class TestParam(EmulateSequence, EmulateMap):
    """Base class for test params

    To make the parmas work, it must "look" like a param tuple so
    __len__ and __iter__ are added.
    """

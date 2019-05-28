import functools
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class factory:
    names: List[str] = field(default_factory=list)
    repository: Dict[Any, Any] = field(default_factory=dict)

    def __call__(self, cls, *args, **kwds):

        @functools.wraps(cls.__new__)
        def new(cls, *args, **kwds):
            cls_key = {}
            for index, name in enumerate(self.names):
                if name in kwds:
                    value = kwds.get(name)
                elif len(args) > index:
                    value = args[index]
                elif hasattr(cls, name):
                    value = getattr(cls, name)
                else:
                    # Guard for programming errors during development
                    raise KeyError(f'Could not find `{name}` in {cls} `__new__` invocation: args={args} kwds={kwds}')
                cls_key[name] = value
            vals = tuple(cls_key.values())
            if vals not in self.repository:
                instance = object.__new__(cls)
                self.repository[vals] = instance
            instance = self.repository[vals]
            return instance

        cls.__new__ = new

        return cls

import time
from dataclasses import dataclass
from typing import Callable


@dataclass
class TimedExecutionBlock:
    """Context manager for profiling the cpu time of a block of code

    Times a ``with`` block and provides elapsed time.

    """
    start: float = 0.0
    end: float = 0.0

    @property
    def now(self) -> Callable:
        return time.time

    @property
    def seconds(self) -> float:
        """Elapsed seconds time property.

        Returns:
            float: elapsed time in seconds
        """
        end = self.end or self.now()
        return end - self.start

    def __str__(self):
        duration = self.seconds
        if duration < 1.0:
            for unit in ['msec', 'usec', 'nsec']:
                if duration < 1.0:
                    duration = duration * 1000
                else:
                    break
            return f'{duration:0.2f} {unit}'
        elif duration > 60.0:
            unit = 'sec'
            for unit, interval in {'sec': 60, 'min': 60, 'hour': 24}.items():
                if duration >= interval:
                    duration = duration / interval
                else:
                    break
            return f'{duration:0.2f} {unit}'
        else:
            return f'{duration:0.2f} sec'

    def __enter__(self):
        self.start = self.now()
        return self

    def __exit__(self, _type, _value, _traceback):
        self.end = self.now()

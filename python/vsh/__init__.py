"""Validated Python bindings for vsh's Rust configuration and options."""

import sys

from ._vsh import Config, CreateOptions, Venv, VshConfigError, VshError, __version__, cli


def main() -> None:
    """Run the shared Rust CLI through the installed Python console entry."""
    raise SystemExit(cli(sys.argv[1:]))

__all__ = ["Config", "CreateOptions", "Venv", "VshConfigError", "VshError", "__version__", "main"]

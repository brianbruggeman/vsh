#!/usr/bin/env python3
"""Select exactly one tested 0.8.0 wheel for the native CI artifact upload."""

from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    wheels = list((ROOT / "target").glob("c24-wheels-*/*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(f"expected exactly one tested wheel, found {wheels}")
    wheel = wheels[0].resolve()
    if not wheel.name.startswith("vsh-0.8.0-"):
        raise RuntimeError(f"expected a vsh 0.8.0 wheel, got {wheel.name}")
    output = os.environ.get("GITHUB_OUTPUT")
    if output is None:
        raise RuntimeError("GITHUB_OUTPUT is required for release artifact selection")
    with open(output, "a", encoding="utf-8") as file:
        file.write(f"wheel={wheel}\n")
    print(f"Selected tested release wheel: {wheel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

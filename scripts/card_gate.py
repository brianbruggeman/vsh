#!/usr/bin/env python3
"""Small gate helpers for the vsh migration card ledger."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


_PYTEST_RESULT = re.compile(
    r"^(?:=+\s*)?(?P<summary>\d+\s+(?:passed|failed|error|errors|skipped|xfailed|xpassed|deselected|warnings?)"
    r"(?:,\s*\d+\s+(?:passed|failed|error|errors|skipped|xfailed|xpassed|deselected|warnings?))*)\s+in\s+.+?(?:\s*=*)$"
)
_TEST_COUNTS = re.compile(r"(?P<count>\d+)\s+(?P<kind>passed|failed|error|errors)")
_CARGO_RESULT = re.compile(r"^test result: (?P<status>ok|FAILED)\. (?P<summary>.*)$")


def passed_count(output: str) -> int:
    """Return passed tests from actual pytest or Cargo result summary lines."""
    total = 0
    for line in output.splitlines():
        pytest = _PYTEST_RESULT.match(line)
        cargo = _CARGO_RESULT.match(line)
        if pytest:
            total += sum(int(match.group("count")) for match in _TEST_COUNTS.finditer(pytest.group("summary")) if match.group("kind") == "passed")
        elif cargo:
            total += sum(int(match.group("count")) for match in _TEST_COUNTS.finditer(cargo.group("summary")) if match.group("kind") == "passed")
    return total


def failed_count(output: str) -> int:
    """Return failed tests reported by pytest or Cargo summary lines."""
    total = 0
    for line in output.splitlines():
        cargo = _CARGO_RESULT.match(line)
        pytest = _PYTEST_RESULT.match(line)
        if cargo:
            summary = cargo.group("summary")
        elif pytest:
            summary = pytest.group("summary")
        else:
            continue
        total += sum(int(match.group("count")) for match in _TEST_COUNTS.finditer(summary) if match.group("kind") in {"failed", "error", "errors"})
    return total


def result_is_green(exit_code: int, output: str) -> bool:
    """Require both a successful command and at least one passed test."""
    cargo_failed = any(
        match.group("status") == "FAILED" for line in output.splitlines() if (match := _CARGO_RESULT.match(line))
    )
    return exit_code == 0 and not cargo_failed and passed_count(output) > 0 and failed_count(output) == 0


def self_test() -> int:
    cases = (
        (0, "================ 12 passed, 3 deselected in 1.2s ================", True),
        (0, "test result: ok. 12 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out", True),
        (0, "================ 0 passed, 4 deselected in 1.2s ================", False),
        (0, "================ 12 passed, 1 failed in 1.2s ================", False),
        (0, "================ 1 failed, 12 passed in 1.2s ================", False),
        (1, "================ 12 passed in 1.2s ================", False),
        (0, "test result: FAILED. 12 passed; 1 failed; 0 ignored; 0 measured; 0 filtered out", False),
        (0, "test result: FAILED. 12 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out", False),
        (0, "no tests collected", False),
        (0, "log: 12 passed previously\nno tests collected", False),
        (0, "", False),
    )
    for exit_code, output, expected in cases:
        actual = result_is_green(exit_code, output)
        if actual != expected:
            print(f"FAIL: {exit_code=} {output=!r}: expected green={expected}, got {actual}", file=sys.stderr)
            return 1
    print(f"PASS: {len(cases)} gate cases; only result summaries count; zero-test selections are red")
    return 0


def run_card(card_id: str, command: list[str], log_path: Path) -> int:
    if not command:
        print("provide the validation command after --", file=sys.stderr)
        return 2
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(result.stdout)
    print(result.stdout, end="")
    passed = passed_count(result.stdout)
    if not result_is_green(result.returncode, result.stdout):
        print(f"RED {card_id}: exit={result.returncode}, reported passed={passed}, failed={failed_count(result.stdout)}", file=sys.stderr)
        return result.returncode or 1
    print(f"GREEN {card_id}: exit=0, reported passed={passed}; log={log_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="check the nonzero-test gate")
    parser.add_argument("--log", type=Path, help="save combined command output here")
    parser.add_argument("card_id", nargs="?")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if not args.card_id:
        parser.error("provide --self-test or a card ID followed by -- and a command")
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    log_path = args.log or Path("target/card-logs") / f"{args.card_id}.log"
    return run_card(args.card_id, command, log_path)


if __name__ == "__main__":
    raise SystemExit(main())

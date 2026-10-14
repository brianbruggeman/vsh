#!/usr/bin/env python3
"""Measure per-process CLI startup latency, CPU time, and peak RSS on Unix."""

import argparse
import json
import math
import os
import platform
import shlex
import statistics
import sys
import tempfile
import time


def sample(command):
    started = time.perf_counter_ns()
    with tempfile.TemporaryFile() as output:
        pid = os.fork()
        if pid == 0:
            os.dup2(output.fileno(), 1)
            os.dup2(output.fileno(), 2)
            try:
                os.execvpe(command[0], command, os.environ)
            except OSError as error:
                os.write(2, f"exec failed: {error}\n".encode())
                os._exit(127)
        _, status, usage = os.wait4(pid, 0)
        elapsed_ns = time.perf_counter_ns() - started
        output.seek(0)
        captured = output.read().decode("utf-8", "replace")

    rss_bytes = usage.ru_maxrss if sys.platform == "darwin" else usage.ru_maxrss * 1024
    exit_code = os.waitstatus_to_exitcode(status)
    return {
        "latency_ms": elapsed_ns / 1_000_000,
        "cpu_ms": (usage.ru_utime + usage.ru_stime) * 1000,
        "peak_rss_bytes": rss_bytes,
        "exit_code": exit_code,
        "output": captured,
    }


def summarize(samples):
    latencies = sorted(row["latency_ms"] for row in samples)
    mean = statistics.mean(latencies)
    stddev = statistics.pstdev(latencies)
    total_wall = sum(latencies) / 1000
    total_cpu = sum(row["cpu_ms"] for row in samples) / 1000
    percentile = lambda p: latencies[math.ceil(p * len(latencies)) - 1]
    return {
        "N": len(samples),
        "throughput_ops_per_sec": len(samples) / total_wall,
        "latency_ms": {
            "single_request": samples[0]["latency_ms"],
            "p50": percentile(0.50),
            "p90": percentile(0.90),
            "p99": percentile(0.99),
            "max": latencies[-1],
            "min": latencies[0],
            "mean": mean,
            "cov_percent": (stddev / mean * 100) if mean else 0,
        },
        "cpu_percent_of_sequential_wall": total_cpu / total_wall * 100,
        "peak_rss_bytes_max": max(row["peak_rss_bytes"] for row in samples),
        "errors": sum(row["exit_code"] != 0 for row in samples),
        "samples": samples,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--output", required=True)
    parser.add_argument("--rust-command", required=True)
    parser.add_argument("--python-command", required=True)
    args = parser.parse_args()
    if args.runs < 3:
        parser.error("--runs must be at least 3")
    results = {
        "measurement": "new-process CLI startup; OS page cache is not flushed",
        "host": {
            "platform": platform.platform(),
            "python": sys.version,
            "cpu_count": os.cpu_count(),
            "load_average_before": os.getloadavg(),
        },
        "commands": {},
    }
    for name, command_text in (
        ("rust", args.rust_command),
        ("python", args.python_command),
    ):
        command = shlex.split(command_text)
        samples = [sample(command) for _ in range(args.runs)]
        summary = summarize(samples)
        results["commands"][name] = {"argv": command, **summary}
    results["host"]["load_average_after"] = os.getloadavg()
    with open(args.output, "w", encoding="utf-8") as stream:
        json.dump(results, stream, indent=2)
        stream.write("\n")
    print(json.dumps({key: value for key, value in results.items() if key != "commands"}, indent=2))
    for name, row in results["commands"].items():
        print(name, json.dumps({key: value for key, value in row.items() if key != "samples"}))


if __name__ == "__main__":
    main()

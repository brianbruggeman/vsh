#!/usr/bin/env python3
"""Capture macOS malloc history and host load for Rust and Python CLI startup."""

import gzip
import json
import os
import pathlib
import platform
import re
import subprocess
import sys
import tempfile
import time


ROOT = pathlib.Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "docs/cards/evidence"


def summarize(text):
    allocated = re.findall(r"^ALLOC .*?\[size=(\d+)\]", text, re.MULTILINE)
    return {
        "malloc_alloc_events": len(allocated),
        "malloc_free_events": len(re.findall(r"^FREE ", text, re.MULTILINE)),
        "vm_alloc_events": len(re.findall(r"^VM_ALLOC ", text, re.MULTILINE)),
        "vm_dealloc_events": len(re.findall(r"^VM_DEALLOC ", text, re.MULTILINE)),
        "malloc_alloc_requested_bytes_total": sum(map(int, allocated)),
    }


def capture(name, command, dylib):
    environment = os.environ.copy()
    environment["MallocStackLogging"] = "1"
    environment["DYLD_INSERT_LIBRARIES"] = str(dylib)
    load_before = os.getloadavg()
    with tempfile.TemporaryFile() as output:
        process = subprocess.Popen(command, cwd=ROOT, env=environment, stdout=output, stderr=output)
        time.sleep(1)
        result = subprocess.run(
            ["/usr/bin/malloc_history", str(process.pid), "-allEvents"],
            text=True,
            capture_output=True,
            check=False,
        )
        load_after = os.getloadavg()
        exit_code = process.wait(timeout=20)
        output.seek(0)
        command_output = output.read().decode("utf-8", "replace")
    if result.returncode or exit_code:
        raise RuntimeError(
            f"capture failed: malloc_history={result.returncode}, process={exit_code}; "
            f"{result.stderr} {command_output}"
        )

    raw_path = EVIDENCE / f"C20-{name}-malloc-history.txt.gz"
    with gzip.open(raw_path, "wt", encoding="utf-8", compresslevel=9) as stream:
        stream.write(result.stdout)
    return {
        "command": command,
        "capture_command": ["/usr/bin/malloc_history", str(process.pid), "-allEvents"],
        "malloc_history_exit_code": result.returncode,
        "process_exit_code": exit_code,
        "host_load_average_before": load_before,
        "host_load_average_after": load_after,
        "summary": summarize(result.stdout),
        "command_output": command_output,
    }


def main():
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="vsh-c20-alloc-") as temporary:
        temporary = pathlib.Path(temporary)
        source = temporary / "pause_exit.c"
        dylib = temporary / "pause_exit.dylib"
        source.write_text(
            "#include <unistd.h>\n"
            "__attribute__((destructor)) static void pause_exit(void) { sleep(8); }\n",
            encoding="utf-8",
        )
        compile_command = ["cc", "-dynamiclib", "-o", str(dylib), str(source)]
        compiled = subprocess.run(compile_command, text=True, capture_output=True, check=False)
        if compiled.returncode:
            raise RuntimeError(compiled.stderr)

        records = {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "allocator_capture_load_is_sampled": True,
            "instrumentation": "MallocStackLogging=1, malloc_history -allEvents",
            "pause_dylib_source": source.read_text(encoding="utf-8"),
            "compile_command": compile_command,
            "compile_exit_code": compiled.returncode,
            "commands": {
                "rust": capture("rust", ["/tmp/cargo_target/release/vsh", "--version"], dylib),
                "python": capture("python", ["python3", "-m", "vsh", "--version"], dylib),
            },
        }
        (EVIDENCE / "C20-allocation-capture.json").write_text(
            json.dumps(records, indent=2) + "\n", encoding="utf-8"
        )
        (EVIDENCE / "C20-allocation-summary.json").write_text(
            json.dumps(
                {name: row["summary"] for name, row in records["commands"].items()},
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(json.dumps(records, indent=2))


if __name__ == "__main__":
    main()

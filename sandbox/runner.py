#!/usr/bin/env python3
"""Runs INSIDE the sandbox container. Compiles solution.cpp and runs it against
every test described in manifest.json, enforcing per-test CPU/memory/wall-clock
limits, and writes results.json.

Invoked as:  python3 /runner.py /work
where /work contains:
    solution.cpp
    manifest.json          {time_limit_ms, memory_limit_mb, tests:[{name,input_file,expected_file}]}
    tests/<name>.in / .out

Verdicts per test: AC | WA | TLE | RE | MLE
Compile failure short-circuits everything with {"compile_error": "..."}.
"""
import json
import os
import resource
import subprocess
import sys
import time


def main(workdir: str) -> None:
    manifest = json.load(open(os.path.join(workdir, "manifest.json")))
    time_limit_ms = manifest["time_limit_ms"]
    mem_limit_mb = manifest["memory_limit_mb"]

    src = os.path.join(workdir, "solution.cpp")
    exe = os.path.join(workdir, "solution")

    # --- compile ---
    compile_proc = subprocess.run(
        ["g++", "-O2", "-std=c++17", "-o", exe, src],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if compile_proc.returncode != 0:
        _write(workdir, {"compile_error": compile_proc.stderr[:8000]})
        return

    # --- run each test ---
    wall_timeout = time_limit_ms / 1000.0 + 0.5  # small buffer over the CPU limit
    cpu_seconds = max(1, int(round(time_limit_ms / 1000.0)))
    mem_bytes = mem_limit_mb * 1024 * 1024

    def set_limits() -> None:
        # Hard caps enforced by the kernel for the child process.
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 1))
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))

    results = []
    for test in manifest["tests"]:
        in_path = os.path.join(workdir, test["input_file"])
        exp_path = os.path.join(workdir, test["expected_file"])
        expected = open(exp_path).read()

        with open(in_path, "rb") as stdin_f:
            start = time.monotonic()
            try:
                proc = subprocess.run(
                    [exe],
                    stdin=stdin_f,
                    capture_output=True,
                    text=True,
                    timeout=wall_timeout,
                    preexec_fn=set_limits,
                )
                elapsed_ms = int((time.monotonic() - start) * 1000)
            except subprocess.TimeoutExpired:
                results.append({
                    "name": test["name"],
                    "verdict": "TLE",
                    "time_ms": time_limit_ms,
                    "time_limit_ms": time_limit_ms,
                })
                continue

        if proc.returncode != 0:
            # SIGXCPU (CPU rlimit) surfaces as a nonzero/killed return — treat a
            # near-limit kill as TLE, everything else as a runtime error.
            verdict = "TLE" if elapsed_ms >= time_limit_ms else "RE"
            entry = {
                "name": test["name"],
                "verdict": verdict,
                "time_ms": elapsed_ms,
                "time_limit_ms": time_limit_ms,
            }
            if verdict == "RE":
                entry["return_code"] = proc.returncode
                entry["stderr"] = proc.stderr[:2000]
            results.append(entry)
            continue

        if _normalise(proc.stdout) == _normalise(expected):
            results.append({
                "name": test["name"],
                "verdict": "AC",
                "time_ms": elapsed_ms,
                "time_limit_ms": time_limit_ms,
            })
        else:
            results.append({
                "name": test["name"],
                "verdict": "WA",
                "time_ms": elapsed_ms,
                "time_limit_ms": time_limit_ms,
                # keep previews small — the big test's input is multi-MB
                "input_preview": _preview(open(in_path).read()),
                "expected": _normalise(expected)[:2000],
                "got": _normalise(proc.stdout)[:2000],
            })

    _write(workdir, {"results": results})


def _normalise(s: str) -> str:
    return "\n".join(line.rstrip() for line in s.strip().splitlines())


def _preview(s: str, max_chars: int = 400) -> str:
    return s if len(s) <= max_chars else s[:max_chars] + " …(truncated)"


def _write(workdir: str, obj: dict) -> None:
    with open(os.path.join(workdir, "results.json"), "w") as f:
        json.dump(obj, f)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/work")

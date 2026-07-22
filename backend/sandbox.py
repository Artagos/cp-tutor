"""Host side of the sandbox. Given C++ source, build a work dir, run it in the
Docker sandbox against the problem's test suite, and return structured results.

Security: the container runs with --network=none, a memory cap, a CPU cap, and
an unprivileged user; runner.py additionally enforces per-test rlimits and
wall-clock timeouts. Generated code must never run outside this.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass

from .problem import PROBLEM

IMAGE = os.environ.get("CP_TUTOR_SANDBOX_IMAGE", "cp-tutor-sandbox")


@dataclass
class RunResult:
    ok: bool                     # True unless a compile error occurred
    compile_error: str | None
    results: list[dict]          # per-test dicts as produced by runner.py

    @property
    def all_accepted(self) -> bool:
        return self.ok and bool(self.results) and all(
            r["verdict"] == "AC" for r in self.results
        )

    def first_failure(self) -> dict | None:
        for r in self.results:
            if r["verdict"] != "AC":
                return r
        return None


def run_cpp(source: str) -> RunResult:
    """Compile and run `source` against the static problem's test suite."""
    with tempfile.TemporaryDirectory(prefix="cp_tutor_") as workdir:
        tests_dir = os.path.join(workdir, "tests")
        os.makedirs(tests_dir, exist_ok=True)

        with open(os.path.join(workdir, "solution.cpp"), "w", newline="\n") as f:
            f.write(source)

        manifest_tests = []
        for t in PROBLEM.tests:
            in_rel = f"tests/{t.name}.in"
            out_rel = f"tests/{t.name}.out"
            with open(os.path.join(workdir, in_rel), "w", newline="\n") as f:
                f.write(t.stdin)
            with open(os.path.join(workdir, out_rel), "w", newline="\n") as f:
                f.write(t.expected_stdout)
            manifest_tests.append(
                {"name": t.name, "input_file": in_rel, "expected_file": out_rel}
            )

        manifest = {
            "time_limit_ms": PROBLEM.time_limit_ms,
            "memory_limit_mb": PROBLEM.memory_limit_mb,
            "tests": manifest_tests,
        }
        with open(os.path.join(workdir, "manifest.json"), "w") as f:
            json.dump(manifest, f)

        _invoke_docker(workdir)

        results_path = os.path.join(workdir, "results.json")
        if not os.path.exists(results_path):
            return RunResult(
                ok=False,
                compile_error="Sandbox produced no results (the run crashed or "
                "timed out at the container level).",
                results=[],
            )
        payload = json.load(open(results_path))

    if "compile_error" in payload:
        return RunResult(ok=False, compile_error=payload["compile_error"], results=[])
    return RunResult(ok=True, compile_error=None, results=payload["results"])


def _invoke_docker(workdir: str) -> None:
    # Container-level caps; runner.py enforces finer per-test limits inside.
    container_mem_mb = PROBLEM.memory_limit_mb + 128
    cmd = [
        "docker", "run", "--rm",
        "--network=none",
        f"--memory={container_mem_mb}m",
        "--cpus=1",
        "--pids-limit=64",
        "-v", f"{os.path.abspath(workdir)}:/work",
        IMAGE,
    ]
    # Generous overall ceiling; per-test timeouts are handled inside the container.
    overall_timeout = (PROBLEM.time_limit_ms / 1000.0) * len(PROBLEM.tests) + 90
    subprocess.run(cmd, timeout=overall_timeout, capture_output=True, text=True)

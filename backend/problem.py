"""The single static problem the v0 prototype is built around.

Count Pairs With Sum K:
  Input:
    line 1: two integers  n  K
    line 2: n integers  a_1 .. a_n   (space separated)
  Output:
    one integer: the number of index pairs (i < j) with a_i + a_j == K

A naive O(n^2) double loop is the obvious first idea and TLEs on the big test;
the intended O(n) hash-map or O(n log n) sort+two-pointer passes. The time limit
is calibrated (see TIME_LIMIT_MS) so "bad algorithm fails, good algorithm passes"
regardless of small constant-factor differences.

Everything the AGENTS are allowed to see about the problem lives in `STATEMENT`
and `TAGS`. The intended solution / editorial is deliberately NOT stored here so
there is nothing for the tutor to leak.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field


# ---- what the agents may see -------------------------------------------------

STATEMENT = """\
Problem: Count Pairs With Sum K

You are given an array of n integers and a target value K.
Count the number of pairs of positions (i, j) with i < j such that
a_i + a_j == K.

Input
  Line 1: two integers  n  K
  Line 2: n integers a_1 a_2 ... a_n

Output
  A single integer: the number of valid pairs.

Constraints
  1 <= n <= 1_000_000
  -1_000_000_000 <= a_i, K <= 1_000_000_000

Example
  Input:
    5 6
    1 2 3 4 5
  Output:
    2
  (the pairs are 1+5 and 2+4)
"""

# Topic tags are safe to reveal — they describe the problem area, not the answer.
TAGS = ["arrays", "hashing", "sorting", "two-pointers"]

# The ONLY thing the translator is allowed to know: the raw I/O shape, stripped
# of all semantics. No mention of what the numbers mean, what to compute, or
# what problem this is. This lets the translator read input and print output
# while remaining unable to infer the intended solution.
INPUT_FORMAT = """\
Standard input:
  - Line 1: two integers, separated by a space. Call them n and k.
  - Line 2: n integers, separated by spaces.

Standard output:
  - Write the program's result to standard output.
"""

# Time limit the sandbox enforces per test. Calibrated so the intended O(n)/
# O(n log n) solution finishes comfortably on the 10^6 case while the naive
# O(n^2) solution (~10^12 operations) blows straight past it.
TIME_LIMIT_MS = 1500
MEMORY_LIMIT_MB = 256


# ---- the test suite (kept away from the agents) ------------------------------

@dataclass
class Test:
    name: str
    stdin: str
    expected_stdout: str


def _count_pairs(nums: list[int], k: int) -> int:
    """Reference solution used only to compute expected answers for the suite."""
    seen: dict[int, int] = {}
    count = 0
    for x in nums:
        count += seen.get(k - x, 0)
        seen[x] = seen.get(x, 0) + 1
    return count


def _fmt(n: int, k: int, nums: list[int]) -> str:
    return f"{n} {k}\n{' '.join(map(str, nums))}\n"


def build_tests() -> list[Test]:
    tests: list[Test] = []

    # small hand-written cases
    small = [
        ("example", 6, [1, 2, 3, 4, 5]),
        ("duplicates", 4, [2, 2, 2, 2, 0, 4]),  # C(4,2)=6 for the 2's, +1 for 0+4
        ("no_pairs", 100, [1, 2, 3]),
        ("negatives", 0, [-3, 3, -1, 1, 0, 0]),
        ("single", 5, [5]),
    ]
    for name, k, nums in small:
        tests.append(Test(name, _fmt(len(nums), k, nums), f"{_count_pairs(nums, k)}\n"))

    # the big case that forces a TLE on O(n^2). Generated deterministically
    # (fixed seed) so the expected answer is stable across runs.
    rng = random.Random(20260722)
    n = 1_000_000
    k = 1_000
    nums = [rng.randint(1, 1_000) for _ in range(n)]
    tests.append(Test("big_n_1e6", _fmt(n, k, nums), f"{_count_pairs(nums, k)}\n"))

    return tests


@dataclass
class Problem:
    statement: str = STATEMENT        # tutor + UI see this
    input_format: str = INPUT_FORMAT  # translator sees ONLY this (no semantics)
    tags: list[str] = field(default_factory=lambda: list(TAGS))
    time_limit_ms: int = TIME_LIMIT_MS
    memory_limit_mb: int = MEMORY_LIMIT_MB
    tests: list[Test] = field(default_factory=build_tests)


# Built once at import; the test suite is a few MB of ints for the big case.
PROBLEM = Problem()

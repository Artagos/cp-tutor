"""Feasibility pre-screen — runs BEFORE codegen.

Decides whether the learner's described solution is possible/feasible to carry
out at all. Like the translator, it is BLIND to the problem: its only context is
the raw input/output format and the user's description. It never sees the
statement or intended solution.

It must NOT reject a solution for being slow — a naive brute force is feasible
(that's the teaching point). It rejects only the genuinely impossible or
infeasible (non-algorithms, contradictions, references to unavailable data).
"""
from __future__ import annotations

from pydantic import BaseModel

from .llm import generate_structured
from .problem import Problem
from .prompts import feasibility_screen_system


class ScreenResult(BaseModel):
    feasible: bool
    # populated only when feasible is False — what is not possible/feasible
    issue: str = ""


def screen(problem: Problem, described_approach: str) -> ScreenResult:
    return generate_structured(
        feasibility_screen_system(problem),
        [{
            "role": "user",
            "content": (
                "Here is the solution the learner described. Decide whether it is "
                f"possible and feasible to carry out:\n\n{described_approach}"
            ),
        }],
        ScreenResult,
    )

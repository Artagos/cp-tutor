"""Guardrailed tutor — answers general CS questions in the abstract.

Its context (see prompts.tutor_system) contains the problem statement and tags
so it can recognise a problem-specific question and refuse, but never the
intended solution — so there is nothing to leak.
"""
from __future__ import annotations

from .llm import generate
from .prompts import tutor_system


def answer(message: str, history: list[dict] | None = None) -> str:
    messages = list(history or [])
    messages.append({"role": "user", "content": message})
    return generate(tutor_system(), messages)

"""Guardrailed tutor — answers general CS questions in the abstract.

Its context (see prompts.tutor_system) contains the problem statement and tags
so it can recognise a problem-specific question and refuse, but never the
intended solution — so there is nothing to leak.
"""
from __future__ import annotations

import anthropic

from .prompts import tutor_system

_client = anthropic.Anthropic()


def answer(message: str, history: list[dict] | None = None) -> str:
    messages = list(history or [])
    messages.append({"role": "user", "content": message})
    resp = _client.messages.create(
        model="claude-opus-4-8",
        max_tokens=1200,
        thinking={"type": "adaptive"},
        system=tutor_system(),
        messages=messages,
    )
    return "".join(b.text for b in resp.content if b.type == "text").strip()

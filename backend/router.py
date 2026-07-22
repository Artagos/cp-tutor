"""Intent router — the first layer of the guardrail.

A cheap Haiku call classifies each message into concept / strategy / solution /
chitchat. Only `concept` reaches the tutor freely; `strategy` is refused.
"""
from __future__ import annotations

from typing import Literal

import anthropic
from pydantic import BaseModel

from .prompts import ROUTER_SYSTEM

_client = anthropic.Anthropic()

Intent = Literal["concept", "strategy", "solution", "chitchat"]


class Routed(BaseModel):
    intent: Intent
    reason: str  # short justification, useful for debugging / logging


def route(message: str) -> Routed:
    resp = _client.messages.parse(
        model="claude-haiku-4-5",
        max_tokens=256,
        system=ROUTER_SYSTEM,
        messages=[{"role": "user", "content": message}],
        output_format=Routed,
    )
    return resp.parsed_output

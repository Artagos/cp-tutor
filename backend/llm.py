"""Thin LLM shim over Google Gemini (free tier).

All three agents go through here, so the provider lives in exactly one place.
Uses the native google-genai SDK because it supports Pydantic `response_schema`
structured outputs directly — the router and translator rely on that.

Auth: set GEMINI_API_KEY (or GOOGLE_API_KEY). Get a free key at
https://aistudio.google.com/apikey

Models are env-overridable so you can swap tiers without touching code:
  CP_TUTOR_ROUTER_MODEL   (default gemini-2.5-flash-lite — cheap classification)
  CP_TUTOR_MAIN_MODEL     (default gemini-2.5-flash      — tutor + translator)
"""
from __future__ import annotations

import os
from typing import Type, TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

ROUTER_MODEL = os.environ.get("CP_TUTOR_ROUTER_MODEL", "gemini-2.5-flash-lite")
MAIN_MODEL = os.environ.get("CP_TUTOR_MAIN_MODEL", "gemini-2.5-flash")

T = TypeVar("T", bound=BaseModel)

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    """Lazy so the package imports without a key present (tests, CI)."""
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        # genai.Client() also resolves the key from the env on its own; passing
        # it explicitly keeps the failure mode obvious if it's unset.
        _client = genai.Client(api_key=api_key) if api_key else genai.Client()
    return _client


def _to_contents(messages: list[dict]) -> list[types.Content]:
    """Convert [{'role': 'user'|'assistant', 'content': str}] to Gemini contents.
    Gemini uses 'model' for the assistant role."""
    contents: list[types.Content] = []
    for m in messages:
        role = "model" if m["role"] == "assistant" else "user"
        contents.append(
            types.Content(role=role, parts=[types.Part.from_text(text=m["content"])])
        )
    return contents


def generate(system: str, messages: list[dict], model: str = MAIN_MODEL) -> str:
    """Plain text generation (tutor, verdict explainer)."""
    resp = _get_client().models.generate_content(
        model=model,
        contents=_to_contents(messages),
        config=types.GenerateContentConfig(system_instruction=system),
    )
    return (resp.text or "").strip()


def generate_structured(
    system: str,
    messages: list[dict],
    schema: Type[T],
    model: str = MAIN_MODEL,
) -> T:
    """Structured generation validated against a Pydantic model (router, codegen)."""
    resp = _get_client().models.generate_content(
        model=model,
        contents=_to_contents(messages),
        config=types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_schema=schema,
        ),
    )
    parsed = resp.parsed
    if isinstance(parsed, schema):
        return parsed
    # Fallback if the SDK didn't auto-parse for some reason.
    return schema.model_validate_json(resp.text or "{}")

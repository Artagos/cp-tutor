"""Translator (pure executor): NL approach -> C++ -> sandbox -> faithful verdict.

Three steps:
  1. The LLM generates a C++ program implementing EXACTLY the described approach.
  2. The sandbox compiles & runs it against the test suite.
  3. The LLM phrases the verdict facts conversationally, under strict no-hints rules.

Step 3 only ever sees the deterministic verdict facts we hand it — never a
license to invent strategy advice.
"""
from __future__ import annotations

from pydantic import BaseModel

from .llm import generate, generate_structured
from .prompts import translator_codegen_system, VERDICT_EXPLAINER_SYSTEM
from .sandbox import RunResult, run_cpp


class GeneratedProgram(BaseModel):
    cpp_source: str
    # a plain-language restatement of the approach the code implements, so the
    # user can confirm we understood them
    approach_summary: str


def _generate_cpp(described_approach: str) -> GeneratedProgram:
    return generate_structured(
        translator_codegen_system(),
        [{
            "role": "user",
            "content": (
                "Here is the approach I want you to implement, exactly as "
                f"described:\n\n{described_approach}"
            ),
        }],
        GeneratedProgram,
    )


def _verdict_facts(program: GeneratedProgram, run: RunResult) -> str:
    """Deterministic, factual summary of what happened — the ONLY thing the
    verdict-explainer LLM is allowed to work from."""
    lines = [f"Approach we implemented: {program.approach_summary}"]

    if not run.ok:
        lines.append("Outcome: COMPILE ERROR")
        lines.append(f"Compiler output:\n{run.compile_error}")
        return "\n".join(lines)

    if run.all_accepted:
        slowest = max(run.results, key=lambda r: r["time_ms"])
        lines.append("Outcome: ACCEPTED — passed every test.")
        lines.append(
            f"Slowest test '{slowest['name']}': {slowest['time_ms']} ms "
            f"(limit {slowest['time_limit_ms']} ms)."
        )
        return "\n".join(lines)

    fail = run.first_failure()
    lines.append(f"Outcome: {fail['verdict']} on test '{fail['name']}'.")
    if fail["verdict"] == "TLE":
        lines.append(
            f"It exceeded the time limit: ran for at least {fail['time_ms']} ms, "
            f"limit is {fail['time_limit_ms']} ms."
        )
    elif fail["verdict"] == "WA":
        lines.append(f"Input (preview): {fail.get('input_preview', '')}")
        lines.append(f"Expected output: {fail.get('expected', '')}")
        lines.append(f"Your program's output: {fail.get('got', '')}")
    elif fail["verdict"] == "RE":
        lines.append(
            f"Runtime error (exit code {fail.get('return_code')}). "
            f"stderr: {fail.get('stderr', '')}"
        )
    # how many passed before the failure, for encouragement
    passed = sum(1 for r in run.results if r["verdict"] == "AC")
    lines.append(f"({passed} of {len(run.results)} tests passed.)")
    return "\n".join(lines)


def _explain(facts: str) -> str:
    return generate(VERDICT_EXPLAINER_SYSTEM, [{"role": "user", "content": facts}])


class TranslationOutcome(BaseModel):
    reply: str                 # conversational message shown to the user
    cpp_source: str            # kept server-side; surfaced only if asked
    verdict: str               # AC | WA | TLE | RE | CE
    approach_summary: str


def translate_and_run(described_approach: str) -> TranslationOutcome:
    program = _generate_cpp(described_approach)
    run = run_cpp(program.cpp_source)
    facts = _verdict_facts(program, run)
    reply = _explain(facts)

    if not run.ok:
        verdict = "CE"
    elif run.all_accepted:
        verdict = "AC"
    else:
        verdict = run.first_failure()["verdict"]

    return TranslationOutcome(
        reply=reply,
        cpp_source=program.cpp_source,
        verdict=verdict,
        approach_summary=program.approach_summary,
    )

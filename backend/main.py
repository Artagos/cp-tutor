"""FastAPI app tying router + tutor + translator together, plus a static chat UI.

Problems come from Codeforces (state.current / state.load_new); the user can ask
for a new one in chat ("give me another problem") or via the New-problem button.

POST /chat        {message, history?}     -> {intent, reply, meta}
POST /new-problem                         -> {problem}
GET  /problem                             -> current problem summary
GET  /                                    -> the chat UI
"""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import router, state, translator, tutor
from .problem import Problem
from .prompts import REFUSAL_MESSAGE

app = FastAPI(title="CP Tutor")

_FRONTEND = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")


class ChatRequest(BaseModel):
    message: str
    history: list[dict] | None = None  # tutor turns: [{"role","content"}, ...]


class ChatResponse(BaseModel):
    intent: str
    reply: str
    meta: dict = {}


def _summary(p: Problem) -> dict:
    return {
        "name": p.name,
        "statement": p.statement,
        "tags": p.tags,
        "url": p.url,
        "rating": p.rating,
        "source": p.source,
        "time_limit_ms": p.time_limit_ms,
        "num_sample_tests": len(p.tests),
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(os.path.abspath(_FRONTEND))


@app.get("/problem")
def problem() -> dict:
    return _summary(state.current())


@app.post("/new-problem")
def new_problem() -> dict:
    return _summary(state.load_new())


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    try:
        return _handle(req)
    except Exception as exc:  # keep the UI usable on transient LLM/sandbox errors
        return ChatResponse(
            intent="error",
            reply=(
                "Sorry — I hit a temporary hiccup talking to the model "
                "(it may be briefly overloaded). Please try that again."
            ),
            meta={"error": type(exc).__name__, "detail": str(exc)[:300]},
        )


def _handle(req: ChatRequest) -> ChatResponse:
    routed = router.route(req.message)
    prob = state.current()

    if routed.intent == "new_problem":
        prob = state.load_new()
        rating = f" (rating {prob.rating})" if prob.rating else ""
        return ChatResponse(
            intent="new_problem",
            reply=(
                f"Here's a new problem: {prob.name}{rating}. "
                "It's shown on the left. Read it, then describe how you'd solve "
                "it and I'll build and run your approach — or ask me about any "
                "general concept."
            ),
            meta={"problem": _summary(prob), "reason": routed.reason},
        )

    if routed.intent == "strategy":
        return ChatResponse(intent="strategy", reply=REFUSAL_MESSAGE,
                            meta={"reason": routed.reason})

    if routed.intent == "concept":
        return ChatResponse(intent="concept",
                            reply=tutor.answer(prob, req.message, req.history),
                            meta={"reason": routed.reason})

    if routed.intent == "solution":
        outcome = translator.translate_and_run(prob, req.message)
        return ChatResponse(
            intent="solution",
            reply=outcome.reply,
            meta={
                "verdict": outcome.verdict,
                "approach_summary": outcome.approach_summary,
                "cpp_source": outcome.cpp_source,
            },
        )

    # chitchat / fallback
    return ChatResponse(
        intent="chitchat",
        reply=(
            "Hi! Describe the solution you have in mind for the problem on the "
            "left and I'll run it, ask me to explain any general programming "
            "concept, or say 'give me another problem' to switch."
        ),
        meta={"reason": routed.reason},
    )

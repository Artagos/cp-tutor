"""FastAPI app tying the router + tutor + translator together, plus a static
chat UI.

POST /chat  {message, history?}  ->  {intent, reply, meta}
GET  /       -> the chat UI
GET  /problem -> the (agent-visible) problem statement + tags
"""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import router, tutor, translator
from .problem import PROBLEM
from .prompts import REFUSAL_MESSAGE

app = FastAPI(title="CP Tutor")

_FRONTEND = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")


class ChatRequest(BaseModel):
    message: str
    # prior turns for the tutor: [{"role": "user"|"assistant", "content": "..."}]
    history: list[dict] | None = None


class ChatResponse(BaseModel):
    intent: str
    reply: str
    meta: dict = {}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(os.path.abspath(_FRONTEND))


@app.get("/problem")
def problem() -> dict:
    return {"statement": PROBLEM.statement, "tags": PROBLEM.tags,
            "time_limit_ms": PROBLEM.time_limit_ms}


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

    if routed.intent == "strategy":
        return ChatResponse(
            intent="strategy",
            reply=REFUSAL_MESSAGE,
            meta={"reason": routed.reason},
        )

    if routed.intent == "concept":
        return ChatResponse(
            intent="concept",
            reply=tutor.answer(req.message, req.history),
            meta={"reason": routed.reason},
        )

    if routed.intent == "solution":
        outcome = translator.translate_and_run(req.message)
        return ChatResponse(
            intent="solution",
            reply=outcome.reply,
            meta={
                "verdict": outcome.verdict,
                "approach_summary": outcome.approach_summary,
                # source is returned for the demo UI; a real product would gate
                # this behind an explicit "show me the code" request
                "cpp_source": outcome.cpp_source,
            },
        )

    # chitchat / fallback
    return ChatResponse(
        intent="chitchat",
        reply=(
            "Hi! Describe the solution you have in mind for the problem and I'll "
            "run it, or ask me to explain any general programming concept."
        ),
        meta={"reason": routed.reason},
    )

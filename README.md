# CP Tutor — an agentic "explain your solution" competitive-programming coach

A chat-bot that lets **non-coders** solve competitive programming problems by
*describing their algorithm in plain words*. The system translates the described
approach into C++, runs it against a real test suite, and reports back what
happened — **faithfully, and without ever suggesting a better algorithm.**

Alongside the translator there's a **guardrailed tutor** that answers general CS
questions ("what is a hash map?") but refuses anything problem-specific ("should
I use a hash map here?"). No hints, no strategy — the learner does the thinking.

## The two capabilities

1. **Translator (pure executor)** — takes the user's described algorithm →
   generates C++ → compiles & runs in a sandbox against the test suite →
   reports the verdict (AC / WA / TLE / RE / CE). It implements *exactly* what
   the user described. It never optimizes, corrects the algorithm, or names a
   better one. When a solution TLEs, that timeout is the teaching signal.

2. **Tutor (guardrailed Q&A)** — answers general, abstract CS questions. It is
   deliberately **not given the problem's intended solution**, so it can't leak
   it. Problem-specific / strategy questions get a polite refusal.

A cheap **intent router** decides which agent each message goes to.

The LLM backend is **Google Gemini** (free tier) via the `google-genai` SDK,
routed through a single shim (`backend/llm.py`) so the provider is swappable.

## Architecture

```
 Chat UI ──▶ Router ──┬─▶ Tutor        conceptual Q&A, no hints
   (Gemini flash-lite)├─▶ Translator   NL → C++ → sandbox
                      └─▶ (refusal / chitchat handled inline)
                                │
                           Sandbox (Docker + g++)   compile & run vs tests
```

## The static problem (v0)

**Count Pairs With Sum K.** A naive O(n²) double loop is the obvious first idea
and *times out* on the n=10⁶ test; the intended O(n) hash-map / O(n log n)
sort+two-pointer passes. This single problem exercises the whole loop:
working-but-slow → TLE → the learner rethinks. See `backend/problem.py`.

## Layout

```
backend/
  main.py         FastAPI app + /chat endpoint
  llm.py          Gemini shim (the only provider-specific file)
  router.py       intent classifier (structured output)
  tutor.py        guardrailed conceptual Q&A
  translator.py   NL approach → C++ → sandbox → faithful verdict
  sandbox.py      host-side: build temp dir, invoke Docker, parse results
  problem.py      the static problem + generated test suite
  prompts.py      system prompts (pure-executor + no-hints rules live here)
  requirements.txt
sandbox/
  Dockerfile      python:3.11-slim + g++, bakes in runner.py
  runner.py       runs inside the container: compile + run tests with limits
frontend/
  index.html      minimal chat UI (no build step)
```

## Running it

Prereqs: Python 3.11+, Docker Desktop running, a free Gemini API key
(https://aistudio.google.com/apikey).

```bash
# 1. Build the sandbox image (once)
docker build -t cp-tutor-sandbox ./sandbox

# 2. Install backend deps
pip install -r backend/requirements.txt

# 3. Set your free Gemini key — either put it in a .env file (auto-loaded):
#      cp .env.example .env   # then edit .env and paste your key
#    or export it:
#      (PowerShell)  $env:GEMINI_API_KEY = "..."
#      (bash)        export GEMINI_API_KEY=...
#    NOTE: .env is gitignored. Never put a real key in .env.example (tracked).

# 4. Run the API
uvicorn backend.main:app --reload --app-dir .

# 5. Open the UI
#    visit http://localhost:8000  (index.html is served by FastAPI)
```

Then chat. Try:
- "what is a hash map?"          → tutor answers (allowed)
- "should I use a hash map?"     → refused (problem-specific)
- "I'll loop over every pair and count the ones summing to K" → translator
  builds it, runs it, and reports the TLE on the big test.

## Design notes / where to take it next

- **Guardrail** lives in `router.py` (intent classification) + the fact that
  `tutor.py`'s context never contains a solution. Strengthen by adding
  adversarial test prompts.
- **Time-limit calibration:** `problem.py` sets a limit calibrated so the
  intended solution passes comfortably and the naive one fails clearly.
- **Sandbox** is the security-critical piece — it runs LLM-generated code.
  It runs with `--network=none`, memory/CPU caps, and per-test wall-clock
  timeouts. Never run generated code outside it.
- Multi-problem support: make `problem.py` a lookup and pass a `problem_id`
  through the API. The agents already take the problem as a parameter.

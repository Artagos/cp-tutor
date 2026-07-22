# Sandbox image for compiling and running LLM-generated C++.
# Minimal: python (to run runner.py) + g++.
FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends g++ \
    && rm -rf /var/lib/apt/lists/*

# runner.py is baked in; the per-run work dir is bind-mounted at /work.
COPY runner.py /runner.py

# Run as an unprivileged user — defence in depth for untrusted code.
RUN useradd --create-home --uid 10001 sandbox
USER sandbox

ENTRYPOINT ["python3", "/runner.py", "/work"]

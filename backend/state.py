"""Server-side 'current problem' holder.

Single-user prototype: one active problem at a time, lazily loaded from
Codeforces on first use and replaced when the user asks for a new one. Falls
back to the offline problem if Codeforces is unreachable.
"""
from __future__ import annotations

import logging

from . import codeforces
from .problem import Problem, fallback_problem

log = logging.getLogger("cp_tutor.state")

_current: Problem | None = None


def _load() -> Problem:
    try:
        return codeforces.random_problem()
    except Exception as exc:
        log.warning("Codeforces fetch failed (%s); using offline fallback", exc)
        return fallback_problem()


def current() -> Problem:
    global _current
    if _current is None:
        _current = _load()
    return _current


def load_new() -> Problem:
    """Fetch a fresh problem and make it current."""
    global _current
    _current = _load()
    return _current

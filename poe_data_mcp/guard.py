"""Nudges for small local LLMs that loop on tool calls.

Small models ignore system-prompt rules but do read tool output, so the hints go there:
- an empty result gets "don't guess, ask the user for the English name"
- an identical repeat call (same tool + args within 10 min) gets "you already did this, answer now"
"""

import functools
import inspect
import re
import time

_MISS = re.compile(r"No [^\n]{0,60}(found|match)")
_MISS_HINT = ("\n\nNOTE: nothing found. Do not guess other names or retry variations. "
              "If the user's term was not English, stop and ask the user for the English name or a poewiki link.")
_DUP_NOTE = ("NOTE: you already made this exact call {s}s ago and got this same result. "
             "Do not call it again; answer the user now with what you have.\n\n")
_WINDOW = 600
_recent: dict[tuple, float] = {}  # ponytail: process-wide, single-user server; key by MCP session if shared


def _annotate(key: tuple, out):
    now = time.time()
    prev = _recent.get(key)
    if len(_recent) > 1000:
        _recent.clear()
    _recent[key] = now
    if not isinstance(out, str):
        return out
    if _MISS.match(out):
        out += _MISS_HINT
    if prev and now - prev < _WINDOW:
        out = _DUP_NOTE.format(s=int(now - prev)) + out
    return out


def guard(fn):
    def key(a, kw):
        return fn.__name__, repr(a), repr(sorted(kw.items()))

    if inspect.iscoroutinefunction(fn):
        @functools.wraps(fn)
        async def awrapper(*a, **kw):
            return _annotate(key(a, kw), await fn(*a, **kw))
        return awrapper

    @functools.wraps(fn)
    def wrapper(*a, **kw):
        return _annotate(key(a, kw), fn(*a, **kw))
    return wrapper

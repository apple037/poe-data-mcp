"""Nudges for small local LLMs that loop on tool calls.

Small models ignore system-prompt rules but do read tool output, so the hints go there:
- an empty result gets "don't guess, ask the user for the English name"
- an identical repeat call (same tool + args within 10 min) gets only "blocked, answer now", without
  the data again: echoing the same result back kept the 27B model looping
"""

import functools
import inspect
import re
import time

_MISS = re.compile(r"No [^\n]{0,60}(found|match)")
_MISS_HINT = ("\n\nNOTE: nothing found. Do not guess other names or retry variations. "
              "If the user's term was not English, stop and ask the user for the English name or a poewiki link.")
_DUP = ("BLOCKED: duplicate call. You already called this tool with these exact arguments and its "
        "result is earlier in this conversation. Do not call any tool again. Write your answer to the "
        "user now using the results you already have.")
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
    if prev and now - prev < _WINDOW:
        return _DUP
    if _MISS.match(out):
        out += _MISS_HINT
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

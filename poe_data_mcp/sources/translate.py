"""Traditional Chinese -> English PoE names via poedb.tw's autocomplete list (~7.8k entries)."""

import difflib
import time
from urllib.parse import unquote

import httpx

from poe_data_mcp.sources.common import HEADERS

URL = "https://poedb.tw/json/autocomplete_tw.json"
_cache: tuple[float, list[dict]] | None = None


def _entries() -> list[dict]:
    global _cache
    if _cache is None or time.time() - _cache[0] > 86400:
        resp = httpx.get(URL, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        _cache = (time.time(), resp.json())
    return _cache[1]


def _line(e: dict) -> str:
    english = unquote(e["value"]).replace("_", " ")
    return f"- {e['label']} → **{english}** ({e.get('desc', '')}) https://poedb.tw/us/{e['value']}"


def translate_term(name: str) -> str:
    """Translate a Traditional Chinese Path of Exile name (skill, passive, keystone, unique,
    ascendancy, mechanic keyword, currency...) to its English name using poedb.tw.

    Call this FIRST whenever the user uses a Chinese game term, then pass the English name
    to the other tools. Example: 絕對受難 → Perfect Agony, 遺守使徒 → Reliquarian.
    """
    name = name.strip()
    entries = _entries()
    exact = [e for e in entries if e["label"] == name]
    if exact:
        return "\n".join(_line(e) for e in exact) + "\n\nSource: https://poedb.tw/tw/"
    partial = [e for e in entries if name in e["label"] or (len(e["label"]) > 1 and e["label"] in name)]
    labels = {e["label"]: e for e in entries}
    fuzzy = [labels[l] for l in difflib.get_close_matches(name, list(labels), n=5, cutoff=0.5)]
    seen, cands = set(), []
    for e in partial + fuzzy:
        if e["label"] not in seen:
            seen.add(e["label"])
            cands.append(e)
    if not cands:
        return f"No poedb.tw translation found for '{name}'."
    return (f"Closest poedb.tw names for '{name}' (not an exact match; pick one only if it clearly fits):\n"
            + "\n".join(_line(e) for e in cands[:5]) + "\n\nSource: https://poedb.tw/tw/")

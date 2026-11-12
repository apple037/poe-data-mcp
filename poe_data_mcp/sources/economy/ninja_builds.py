"""poe.ninja build popularity (what gear/supports players of a skill use).

Uses poe.ninja's site-internal endpoints (no public API, may change without notice):
  /poe1/api/data/index-state                   -> leagues + snapshot versions (JSON)
  /poe1/api/builds/{version}/search?overview=  -> protobuf: per-dimension counts by dictionary index
  /poe1/api/builds/dictionary/{hash}           -> "NDIC" binary: index -> name

Format surprises fail loudly (NinjaFormatError) instead of returning empty/wrong data.
"""

import difflib
import os
import re
import struct
import time
from urllib.parse import quote_plus

import httpx

from poe_data_mcp.sources.common import HEADERS

NINJA = "https://poe.ninja/poe1"
LEAGUE = os.environ.get("POE_NINJA_BUILD_LEAGUE", "allflame")
_NOT_CHALLENGE = re.compile(r"standard|hardcore|\bhc\b|ssf|solo self-found|ruthless", re.I)
_RARITY_PREFIX = ("Rare ", "Magic ", "Normal ")


class NinjaFormatError(Exception):
    """poe.ninja returned data in a shape this parser does not understand."""


# --- binary decoding ---

def _pb_fields(buf: bytes):
    """Yield (field_number, value) for a protobuf message. Length-delimited values are bytes."""
    i, n = 0, len(buf)

    def varint():
        nonlocal i
        shift = result = 0
        while True:
            b = buf[i]
            i += 1
            result |= (b & 0x7F) << shift
            if b < 0x80:
                return result
            shift += 7

    while i < n:
        key = varint()
        field, wire = key >> 3, key & 7
        if wire == 0:
            yield field, varint()
        elif wire == 2:
            length = varint()
            yield field, buf[i:i + length]
            i += length
        elif wire == 1:
            i += 8
        elif wire == 5:
            i += 4
        else:
            raise NinjaFormatError(f"unsupported protobuf wire type {wire}")


def parse_search(raw: bytes) -> tuple[int, dict[str, tuple[str, dict[int, int]]], dict[str, str]]:
    """Return (total characters, {dimension: (dictionary name, {index: count})}, {dictionary name: hash})."""
    result = next((v for f, v in _pb_fields(raw) if f == 1), None)
    if not isinstance(result, bytes):
        raise NinjaFormatError("search response has no result message")
    total, dims, hashes = 0, {}, {}
    for f, v in _pb_fields(result):
        if f == 1 and isinstance(v, int):
            total = v
        elif f == 2:
            name = dict_name = ""
            counts: dict[int, int] = {}
            for g, w in _pb_fields(v):
                if g == 1:
                    name = w.decode()
                elif g == 2:
                    dict_name = w.decode()
                elif g == 3:
                    entry = dict(_pb_fields(w))
                    counts[entry.get(1, 0)] = entry.get(2, 0)
            dims[name] = (dict_name, counts)
        elif f == 6:
            ref = dict(_pb_fields(v))
            if 1 in ref and 2 in ref:
                hashes[ref[1].decode()] = ref[2].decode()
    if "class" not in dims or not hashes:
        raise NinjaFormatError("search response missing class dimension or dictionary refs")
    return total, dims, hashes


def decode_ndic(raw: bytes) -> list[str]:
    """Decode an NDIC dictionary into names in index order.

    Layout: b"NDIC", u32 version (2), u32 reserved, u32 count N, an index region we skip,
    then N one-byte lengths, then the N UTF-8 names concatenated. The index region's size is
    not known, so pick the split where the N lengths sum to exactly the remaining bytes and
    every name is printable.
    """
    if raw[:4] != b"NDIC" or len(raw) < 16:
        raise NinjaFormatError(f"dictionary magic {raw[:4]!r}, expected b'NDIC'")
    version, _, n = struct.unpack_from("<III", raw, 4)
    if version != 2:
        raise NinjaFormatError(f"dictionary version {version}, only 2 supported")
    # ponytail: O(len * N) split search; dictionaries are <100KB so it's fine
    for start in range(16, len(raw) - n + 1):
        lengths = raw[start:start + n]
        text_start = start + n
        if sum(lengths) != len(raw) - text_start:
            continue
        names, pos = [], text_start
        try:
            for ln in lengths:
                names.append(raw[pos:pos + ln].decode())
                pos += ln
        except UnicodeDecodeError:
            continue
        if all(s and s.isprintable() for s in names):
            return names
    raise NinjaFormatError(f"could not locate NDIC name table ({n} entries)")


# --- pure helpers ---

def resolve_skill(skill: str, gem_names: list[str]) -> tuple[str | None, list[str]]:
    """Case-insensitive exact match against gem names; otherwise (None, close matches)."""
    lower = {g.lower(): g for g in gem_names}
    if skill.lower() in lower:
        return lower[skill.lower()], []
    return None, difflib.get_close_matches(skill, gem_names, n=5, cutoff=0.6)


def new_challenge_leagues(build_leagues: list[dict], current: str) -> list[str]:
    """Names of public non-standard/HC/SSF/Ruthless leagues other than `current`."""
    return [
        lg["name"] for lg in build_leagues
        if lg["url"] != current
        and not re.fullmatch(r"pl\d+", lg["url"])
        and not _NOT_CHALLENGE.search(lg["name"])
    ]


# --- network (patched in tests) ---

_cache: dict[str, tuple[float, object]] = {}


def _get(url: str, ttl: float) -> httpx.Response:
    hit = _cache.get(url)
    if hit and time.time() - hit[0] < ttl:
        return hit[1]
    resp = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=30)
    resp.raise_for_status()
    _cache[url] = (time.time(), resp)
    return resp


def _index_state() -> dict:
    return _get(f"{NINJA}/api/data/index-state", 900).json()


def _search(version: str, league: str, skill: str) -> bytes:
    q = f"overview={league}&type=exp" + (f"&skills={quote_plus(skill)}" if skill else "")
    return _get(f"{NINJA}/api/builds/{version}/search?{q}", 900).content


def _dictionary(hash_: str) -> list[str]:
    return decode_ndic(_get(f"{NINJA}/api/builds/dictionary/{hash_}", 1e9).content)  # immutable by hash


# --- tool ---

def _table(title: str, counts: dict[int, int], names: list[str], total: int, top: int, skip_rarity=False) -> str:
    rows = []
    for idx, c in sorted(counts.items(), key=lambda kv: -kv[1]):
        name = names[idx] if idx < len(names) else f"#{idx}"
        if not c or (skip_rarity and name.startswith(_RARITY_PREFIX)):
            continue
        rows.append(f"| {name} | {c} | {c / total:.1%} |")
        if len(rows) >= top:
            break
    return f"### {title}\n| Name | Players | Share |\n|---|---|---|\n" + "\n".join(rows)


def get_build_stats(skill: str = "", top: int = 10) -> str:
    """poe.ninja build popularity for the configured league (default: last challenge league).

    With `skill` (English gem name, e.g. 'Cyclone'): ascendancy share, support gems, uniques,
    keystones and anoints used by characters whose main skill is that gem.
    Without `skill`: ascendancy share across the whole league.
    Shares are % of characters in the selection. Always cite the poe.ninja link in the output.
    """
    idx = _index_state()
    snap = next((s for s in idx["snapshotVersions"] if s["url"] == LEAGUE and s["type"] == "exp"), None)
    if not snap:
        return f"poe.ninja has no build snapshot for league '{LEAGUE}' (POE_NINJA_BUILD_LEAGUE)."
    version, league_name = snap["version"], snap["name"]

    total, dims, hashes = parse_search(_search(version, LEAGUE, skill))
    if skill and f"supportgems-{skill}" not in dims:
        # poe.ninja silently ignores unknown/miscased skill names and returns the whole league
        canonical, suggestions = resolve_skill(skill, _dictionary(hashes["gem"]))
        if not canonical:
            hint = f" Did you mean: {', '.join(suggestions)}?" if suggestions else ""
            return f"No poe.ninja builds found for skill '{skill}' in {league_name}.{hint}"
        skill = canonical
        total, dims, hashes = parse_search(_search(version, LEAGUE, skill))
        if f"supportgems-{skill}" not in dims:
            return f"No poe.ninja builds found for skill '{skill}' in {league_name}."

    names = lambda dim: _dictionary(hashes[dims[dim][0]])  # noqa: E731
    sections = [_table("Ascendancy", dims["class"][1], names("class"), total, 50)]
    if skill:
        for title, dim, skip in (("Support gems", f"supportgems-{skill}", False),
                                 ("Uniques (gear and jewels)", "items", True),
                                 ("Keystones", "keypassives", False),
                                 ("Anoints", "anointed", False)):
            if dim in dims:
                sections.append(_table(title, dims[dim][1], names(dim), total, top, skip))

    link = f"https://poe.ninja/poe1/builds/{LEAGUE}" + (f"?skills={quote_plus(skill)}" if skill else "")
    head = f"## poe.ninja builds: {skill or 'all skills'} — {league_name} ({total} characters)"
    out = "\n\n".join([head, *sections, f"Source: {link}"])
    new = new_challenge_leagues(idx["buildLeagues"], LEAGUE)
    if new:
        out += (f"\n\nNOTICE: new league(s) on poe.ninja: {', '.join(new)}. Still using {league_name}. "
                "Tell the user and ask whether to switch POE_NINJA_BUILD_LEAGUE.")
    return out

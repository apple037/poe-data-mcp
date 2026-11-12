import json
from pathlib import Path

import pytest

from poe_data_mcp.sources.economy import ninja_builds as nb

FIX = Path(__file__).parent / "fixtures" / "ninja"


def _dict(name):
    return nb.decode_ndic((FIX / f"dict_{name}.bin").read_bytes())


def test_decode_ndic_class_and_gem():
    classes = _dict("class")
    assert "Juggernaut" in classes and "Necromancer" in classes
    assert "Cyclone" in _dict("gem")


def test_decode_ndic_rejects_unknown_format():
    with pytest.raises(nb.NinjaFormatError):
        nb.decode_ndic(b"XXXX" + b"\0" * 20)


def test_parse_search_cyclone():
    total, dims, dict_hashes = nb.parse_search((FIX / "search_allflame_cyclone.pb").read_bytes())
    assert 0 < total < 124355  # filtered, not whole league
    assert "supportgems-Cyclone" in dims
    assert dims["class"][0] == "class"
    assert sum(dims["class"][1].values()) == total
    assert set(dict_hashes) >= {"class", "gem", "item", "keypassive", "anointed"}


def test_resolve_skill():
    gems = _dict("gem")
    assert nb.resolve_skill("cyclone", gems) == ("Cyclone", [])
    name, suggestions = nb.resolve_skill("Cyclon", gems)
    assert name is None and "Cyclone" in suggestions


def test_new_challenge_leagues():
    idx = json.loads((FIX / "index_state.json").read_text())
    assert nb.new_challenge_leagues(idx["buildLeagues"], "allflame") == []
    leagues = idx["buildLeagues"] + [{"name": "Hardcore Foo", "url": "foohc"}, {"name": "Foo", "url": "foo"}]
    assert nb.new_challenge_leagues(leagues, "allflame") == ["Foo"]


def test_get_build_stats_cyclone(monkeypatch):
    idx = json.loads((FIX / "index_state.json").read_text())
    names = {n: _dict(n) for n in ("class", "gem", "item", "keypassive", "anointed")}
    raw = (FIX / "search_allflame_cyclone.pb").read_bytes()
    _, _, hashes = nb.parse_search(raw)
    by_hash = {h: names[n] for n, h in hashes.items() if n in names}
    monkeypatch.setattr(nb, "_index_state", lambda: idx)
    monkeypatch.setattr(nb, "_search", lambda version, league, skill: raw)
    monkeypatch.setattr(nb, "_dictionary", lambda h: by_hash.get(h, []))

    out = nb.get_build_stats("Cyclone")
    assert "Allflame" in out and "Cyclone" in out
    assert "Ascendancy" in out and "%" in out
    assert "Support gems" in out and "Uniques" in out
    assert "Rare Helmet" not in out
    assert "https://poe.ninja/poe1/builds/allflame?skills=Cyclone" in out

import json
from pathlib import Path

from poe_data_mcp.sources import translate as tr

SAMPLE = json.loads((Path(__file__).parent / "fixtures" / "autocomplete_tw_sample.json").read_text())


def test_translate_exact(monkeypatch):
    monkeypatch.setattr(tr, "_entries", lambda: SAMPLE)
    out = tr.translate_term("絕對受難")
    assert "Perfect Agony" in out and "天賦" in out
    assert "https://poedb.tw/us/Perfect_Agony" in out
    assert "Reliquarian" in tr.translate_term(" 遺守使徒 ")
    assert "Ignite" in tr.translate_term("點燃")
    assert "Ash, Frost and Storm" in tr.translate_term("三相之力")


def test_translate_partial_and_miss(monkeypatch):
    monkeypatch.setattr(tr, "_entries", lambda: SAMPLE)
    out = tr.translate_term("絕對受")
    assert "Perfect Agony" in out and "not an exact match" in out
    assert tr.translate_term("完全不存在的詞").startswith("No poedb.tw translation found")

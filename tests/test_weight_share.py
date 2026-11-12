from poe_data_mcp.sources.crafting.craftofexile import affix_total_weight

TIERS = {
    "1": {"B": [{"ilvl": "1", "weighting": "1000"}, {"ilvl": "80", "weighting": "250"}]},
    "2": {"B": [{"ilvl": "1", "weighting": "500"}]},
    "3": {"B": [{"ilvl": "1", "weighting": "800"}]},   # suffix
    "4": {"B": [{"ilvl": "1", "weighting": "0"}]},     # unrollable prefix
}
DETAIL = {"1": {"affix": "prefix"}, "2": {"affix": "prefix"}, "3": {"affix": "suffix"}, "4": {"affix": "prefix"}}


def test_total_all_ilvl():
    assert affix_total_weight(TIERS, DETAIL, "B", "prefix", 100) == 1750


def test_total_respects_ilvl():
    assert affix_total_weight(TIERS, DETAIL, "B", "prefix", 50) == 1500


def test_share_zero_total():
    assert affix_total_weight(TIERS, DETAIL, "missing", "prefix", 100) == 0


def test_total_excludes_non_base_groups():
    tiers = {**TIERS, "5": {"B": [{"ilvl": "1", "weighting": "900"}]}}
    detail = {**DETAIL, "5": {"affix": "prefix", "id_mgroup": "2"}}
    assert affix_total_weight(tiers, detail, "B", "prefix", 100) == 1750


def test_format_share_only_prefix_suffix():
    from poe_data_mcp.sources.crafting.craftofexile import format_share
    assert format_share("250", "80", 100, 1000, "prefix", True) == "25.00%"
    assert format_share("250", "80", 100, 1000, "corrupted", True) == "—"
    assert format_share("250", "80", 100, 1000, "eldritch", True) == "—"
    assert format_share("250", "80", 50, 1000, "suffix", True) == "—"
    assert format_share("250", "80", 100, 1000, "prefix", False) == "—"


def test_craft_tiers_has_source_line(monkeypatch):
    from poe_data_mcp.sources.crafting import craftofexile as c
    data = {
        "tiers": {"1": {"B": [{"ilvl": "1", "weighting": "1000", "nvalues": "[[1,2]]"}]}},
        "modifiers": {"seq": [{"id_modifier": "1", "affix": "prefix", "modgroup": "g"}]},
    }
    monkeypatch.setattr(c, "_require_cache", lambda: None)
    monkeypatch.setattr(c, "_data", lambda: data)
    monkeypatch.setattr(c, "_lang", lambda: {"mod": {"1": "+# to maximum Life"}})
    monkeypatch.setattr(c, "_build_base_id_map", lambda: {"B": "two hand axe"})
    out = c.get_craft_tiers("axe", "maximum life")
    assert "100.00%" in out
    assert out.rstrip().endswith("Source: https://www.craftofexile.com/")

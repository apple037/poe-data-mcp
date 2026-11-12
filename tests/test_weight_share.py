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

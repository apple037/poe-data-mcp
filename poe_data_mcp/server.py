import os

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from poe_data_mcp.guard import guard

from poe_data_mcp.sources.player.gems import get_gem_detail, search_gem
from poe_data_mcp.sources.player.items import get_item_detail, search_item
from poe_data_mcp.sources.player.passives import get_passive_detail, search_passive
from poe_data_mcp.sources.mods.item_mods import search_mods
from poe_data_mcp.sources.crafting.craftofexile import (
    craftofexile_cache_status,
    update_craftofexile_cache,
    search_craft_mods,
    get_craft_base_items,
    get_craft_tiers,
    get_fossil_info,
    get_essence_mods,
)
from poe_data_mcp.sources.env import env_detail, env_search
from poe_data_mcp.sources.economy import currency_overview, price_check
from poe_data_mcp.sources.economy.ninja_builds import get_build_stats
from poe_data_mcp.sources.wiki import fetch_wiki_page, wiki_cargo_query
from poe_data_mcp.sources.player.pob import parse_pob, parse_pob_skill_groups
from poe_data_mcp.sources.youtube import fetch_youtube_description, fetch_youtube_transcript
from poe_data_mcp.sources.reddit import fetch_reddit_post

_SUITE_URL = "https://github.com/charleslucas/poe_mcp_suite"

_INSTRUCTIONS = """\
poe-data-mcp provides Path of Exile 1 game-data lookups: wiki pages, gems, unique items, \
passive nodes, item mods, Craft of Exile mod tiers and spawn weights, maps, scarabs, \
live prices, and Path of Building export parsing.

Rules:
- Tool arguments must be English game terms (e.g. 'two hand axe', 'maximum life'). Translate first.
- For mod tiers, spawn weights or roll chances, always call get_craft_tiers / search_craft_mods; never answer from memory. get_craft_tiers takes an item class, not a base item name.
- For mechanics (ailments, damage calculation), call fetch_wiki_page with a guessed URL like https://www.poewiki.net/wiki/Ignite; if it 404s, try wiki_cargo_query or a related page name.
- For what gear, supports or ascendancies players use (build popularity), call get_build_stats; relay any NOTICE line to the user.
- Include the source URL from tool output in your answer.
"""

mcp = FastMCP("poe-data-mcp", instructions=_INSTRUCTIONS)


def tool(fn):
    return mcp.tool()(guard(fn))


def poe_mcp_suite_info() -> str:
    """Install instructions and overview for the full poe_mcp_suite.

    poe-data-mcp (this server) is the game-data lookup component of a larger suite.
    Call this when the user wants deeper Path of Exile build analysis than
    lookups provide, or asks about the full suite / Path of Building integration.
    """
    return f"""\
# poe_mcp_suite

poe-data-mcp is one of several MCP servers in **poe_mcp_suite**. The full suite adds:

- **pob-mcp** - live Path of Building integration: simulate passive trees, gems,
  items, and full DPS/EHP calc against the real PoB engine (TCP or headless).
- **poe-trade-mcp** - official PoE trade search, stash/character API, pricing.
- **poe-data-mcp** (this server) - wiki / economy / Craft of Exile lookups.
- A **playbook + reference-data framework** that keeps an agent's analyses current.

## Install

```bash
git clone --recurse-submodules {_SUITE_URL}.git
cd poe_mcp_suite
```

Then follow **AGENTS.md** (or **CLAUDE.md** for Claude Code) and **README.md** in
the repo - they cover Python/Node dependencies, Path of Building setup, MCP client
configuration (`.mcp.json`), and your `POESESSID`. Point your agent at AGENTS.md
and it can drive the rest.

Note: pob-mcp requires a local Path of Building install and is not an
ephemeral (uvx/npx) server - the suite is a git clone, not a single package.
"""


# --- Player domain ---
tool(search_gem)
tool(get_gem_detail)
tool(search_item)
tool(get_item_detail)
tool(search_passive)
tool(get_passive_detail)

# --- Mods domain ---
tool(search_mods)

# --- Craft of Exile ---
tool(craftofexile_cache_status)
tool(update_craftofexile_cache)
tool(search_craft_mods)
tool(get_craft_base_items)
tool(get_craft_tiers)
tool(get_fossil_info)
tool(get_essence_mods)

# --- Env domain ---
tool(env_search)
tool(env_detail)

# --- Economy domain ---
tool(price_check)
tool(currency_overview)
tool(get_build_stats)

# --- Universal ---
tool(fetch_wiki_page)
tool(wiki_cargo_query)

# --- PoB ---
tool(parse_pob)
tool(parse_pob_skill_groups)

# --- YouTube ---
tool(fetch_youtube_description)
tool(fetch_youtube_transcript)

# --- Reddit ---
tool(fetch_reddit_post)

# --- Suite ---
tool(poe_mcp_suite_info)

def main():
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport != "stdio":
        host = os.environ.get("MCP_HOST", "127.0.0.1")
        mcp.settings.host = host
        mcp.settings.port = int(os.environ.get("MCP_PORT", "47820"))
        if host not in ("127.0.0.1", "localhost", "::1"):
            # Keep DNS-rebinding protection on, but allow the LAN Host header(s).
            default_hosts = "192.168.0.216:*,127.0.0.1:*,localhost:*"
            hosts = [h.strip() for h in os.environ.get("MCP_ALLOWED_HOSTS", default_hosts).split(",") if h.strip()]
            mcp.settings.transport_security = TransportSecuritySettings(
                enable_dns_rebinding_protection=True,
                allowed_hosts=hosts,
                allowed_origins=[],
            )
    mcp.run(transport=transport)

if __name__ == "__main__":
    main()

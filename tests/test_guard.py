import asyncio

from poe_data_mcp import guard as g


def test_miss_hint_and_duplicate_note():
    g._recent.clear()

    @g.guard
    def search(query: str) -> str:
        return f"No items found matching '{query}'."

    first = search(query="Absolute Agony")
    assert "ask the user" in first and "already made this exact call" not in first
    second = search(query="Absolute Agony")
    assert second.startswith("NOTE: you already made this exact call")
    assert "already made" not in search(query="Other")


def test_hit_passes_through_and_async_supported():
    g._recent.clear()

    @g.guard
    async def price(query: str) -> str:
        return "Mageblood: 150 divine"

    assert asyncio.run(price(query="Mageblood")) == "Mageblood: 150 divine"
    assert price.__name__ == "price"

from poe_data_mcp import server


def test_default_is_stdio(monkeypatch):
    for k in ("MCP_TRANSPORT", "MCP_HOST", "MCP_PORT"):
        monkeypatch.delenv(k, raising=False)
    called = {}
    monkeypatch.setattr(server.mcp, "run", lambda **kw: called.update(kw))
    server.main()
    assert called.get("transport", "stdio") == "stdio"


def test_http_from_env(monkeypatch):
    monkeypatch.setenv("MCP_TRANSPORT", "streamable-http")
    monkeypatch.setenv("MCP_HOST", "0.0.0.0")
    monkeypatch.setenv("MCP_PORT", "47820")
    called = {}
    monkeypatch.setattr(server.mcp, "run", lambda **kw: called.update(kw))
    server.main()
    assert called["transport"] == "streamable-http"
    assert server.mcp.settings.host == "0.0.0.0"
    assert server.mcp.settings.port == 47820


def test_lan_host_not_rejected_when_bound_to_all_interfaces(monkeypatch):
    monkeypatch.setenv("MCP_TRANSPORT", "streamable-http")
    monkeypatch.setenv("MCP_HOST", "0.0.0.0")
    monkeypatch.setattr(server.mcp, "run", lambda **kw: None)
    server.main()
    ts = server.mcp.settings.transport_security
    assert ts is None or not ts.enable_dns_rebinding_protection

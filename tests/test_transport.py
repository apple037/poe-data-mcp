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


def _lan_main(monkeypatch, allowed=None):
    monkeypatch.setenv("MCP_TRANSPORT", "streamable-http")
    monkeypatch.setenv("MCP_HOST", "0.0.0.0")
    if allowed is None:
        monkeypatch.delenv("MCP_ALLOWED_HOSTS", raising=False)
    else:
        monkeypatch.setenv("MCP_ALLOWED_HOSTS", allowed)
    monkeypatch.setattr(server.mcp, "run", lambda **kw: None)
    for attr in ("host", "port", "transport_security"):
        monkeypatch.setattr(server.mcp.settings, attr, getattr(server.mcp.settings, attr))
    server.main()
    return server.mcp.settings.transport_security


def test_lan_bind_keeps_protection_with_default_hosts(monkeypatch):
    ts = _lan_main(monkeypatch)
    assert ts.enable_dns_rebinding_protection is True
    assert ts.allowed_hosts == ["192.168.0.216:*", "127.0.0.1:*", "localhost:*"]
    assert ts.allowed_origins == []


def test_allowed_hosts_from_env(monkeypatch):
    ts = _lan_main(monkeypatch, " a.lan:*, b.lan ")
    assert ts.enable_dns_rebinding_protection is True
    assert ts.allowed_hosts == ["a.lan:*", "b.lan"]

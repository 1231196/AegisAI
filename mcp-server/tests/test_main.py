def test_import():
    """Verify the mcp module can be imported without error."""
    from app.main import mcp  # noqa: F401
    assert mcp.name == "Aegis AI MCP Tools"

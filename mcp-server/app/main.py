from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Aegis AI MCP Tools")

@mcp.tool()
def hello(name: str) -> str:
    return f"Hello {name}"

if __name__ == "__main__":
    mcp.run()
from .presentation import create_mcp_app

__all__ = ["create_mcp_app"]

def main() -> None:
    """Run the MCP server."""
    mcp = create_mcp_app()
    mcp.run()
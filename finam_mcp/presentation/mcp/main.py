from mcp.server.fastmcp import FastMCP

from finam_mcp.presentation.mcp.handlers import init_tools

from finam_mcp.configs import ServerConfig


def create_mcp_app(cfg: ServerConfig):

    mcp = FastMCP(
        name=cfg.SERVER.APP_NAME,
        host=cfg.SERVER.HOST,
        port=cfg.SERVER.PORT,
    )

    # Передаем конфигурацию Finam в handlers
    init_tools(mcp, cfg.FINAM)

    # mcp.run(transport="streamable-http")

    return mcp

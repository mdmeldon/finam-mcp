from mcp.server.fastmcp import FastMCP

from finam_mcp.presentation.mcp.handlers import init_tools, init_config

from finam_mcp.configs import Config


def create_mcp_app(cfg: Config):

    mcp = FastMCP(
        name=cfg.SERVER.APP_NAME,
        host=cfg.SERVER.HOST,
        port=cfg.SERVER.PORT,
    )

    init_config(cfg.FINAM)

    init_tools(mcp)

    return mcp

from .configs import Config
from .presentation import create_mcp_app

def main():
    cfg = Config()

    mcp = create_mcp_app(cfg.SERVER)
    mcp.run()
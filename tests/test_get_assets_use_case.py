import pytest

from finam_mcp.configs import FinamConfig
from finam_mcp.presentation.mcp.handlers import init_config


@pytest.mark.asyncio
async def test_get_assets_use_case():
    from finam_mcp.presentation.mcp.handlers import get_assets

    finam_config = FinamConfig()

    init_config(finam_config)
    assets = await get_assets()

    assert len(assets.details) == 50
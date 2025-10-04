from functools import partial

from finam_mcp.application.dtos import AssetListDTO, AssetDTO
from finam_mcp.application.interfaces.client import IClient


class GetAssets:
    def __init__(self, client: IClient) -> None:
        self._client = client

    async def __call__(self, ticker: str | None = None, name: str | None = None, limit: int = 50, offset: int = 0) -> AssetListDTO:
        assets = await self._client.assets()

        filtered_assets = filter(partial(self._filter, ticker=ticker, name=name), assets.assets)
        sorted_assets = sorted(filtered_assets, key=lambda asset: asset.id)

        return AssetListDTO.model_validate(sorted_assets[offset:limit+offset])

    def _filter(self, asset: AssetDTO, ticker: str | None = None, name: str | None = None) -> bool:
        return (not name or name.lower() in asset.name.lower()) and (not ticker or ticker.lower() in asset.ticker.lower())


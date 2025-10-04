from finam_mcp.application.dtos import AssetListDTO, AssetDTO, AssetType
from finam_mcp.application.interfaces.client import IClient


class GetAssets:
    def __init__(self, client: IClient) -> None:
        self._client = client

    async def __call__(self, symbol: str | None = None, ticker: str | None = None, mic: str | None = None, name: str | None = None, type: AssetType | None = None, limit: int = 50, offset: int = 0) -> AssetListDTO:
        assets = await self._client.assets()

        sorted_assets = sorted(assets.assets, key=lambda asset: asset.id)

        def generate():
            i = offset
            while sorted_assets and i < limit+offset:
                if not (asset := self._filter(sorted_assets.pop(), symbol=symbol, name=name, ticker=ticker, mic=mic, type=type)):
                    continue
                if i >= offset:
                    yield asset
                i += 1

        return AssetListDTO.model_validate(generate())

    @staticmethod
    def _filter(asset: AssetDTO, symbol: str | None = None, ticker: str | None = None, mic: str | None = None, name: str | None = None, type: AssetType | None = None) -> AssetDTO | None:
        if ((not name or name.lower() in asset.name.lower())
                and (not ticker or ticker.lower() in asset.ticker.lower())
                and (not symbol or symbol == asset.symbol)
                and (not mic or mic == asset.mic)
                and (not type or type == asset.type)):
            return asset


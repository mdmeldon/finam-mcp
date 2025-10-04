"""
MCP-инструменты для Finam API: торговля, справочники, котировки и управление аккаунтом.

Как это работает для LLM:
- Аутентификация выполняется однократно на уровне MCP-сервера с помощью переменных окружения
  FINAM_API_TOKEN и FINAM_ACCOUNT_ID. Из API-токена запрашивается короткоживущий JWT (~15 минут).
- Все вызовы инструментов автоматически используют валидный JWT. При 401 или близком истечении
  сроков действия токен обновляется прозрачно для инструмента.

Гарантии и поведение:
- Сетевая коммуникация выполняется через `aiohttp` к `https://api.finam.ru/`.
- Ошибки HTTP уровня API пробрасываются наверх как исключения. Структуры ответов валидируются Pydantic DTO.
- Временные параметры принимаются как строки ISO8601. Если таймзона не указана, по умолчанию используется UTC.
- Строковые параметры, представляющие Enum (например, стороны сделки или таймфрейм), могут быть переданы
  как имя enum (например, "SIDE_BUY", "TIME_FRAME_M5") или как собственное значение enum.

Возвращаемые значения:
- Все инструменты возвращают оболочку `OkResponse[T]` с полями:
  - `details`: десериализованный DTO-ответ API
  - `endpoint`: фактический REST-эндпоинт Finam
  - `method`: HTTP-метод запроса

Основные группы инструментов:
- Аккаунт и история: `get_account`, `trades`, `transactions`, `get_orders`, `get_order`, `cancel_order`.
- Справочные данные: `assets`, `get_asset`, `get_asset_params`, `exchanges`, `options_chain`, `schedule`, `clock`.
- Заявки: `place_order`.
- Рыночные данные: `bars`, `last_quote`, `latest_trades`, `order_book`.

Примечания к форматам:
- Символ инструмента задаётся в формате "TICKER@MIC" (например, "AAPL@XNGS").
- Временные интервалы указываются в ISO8601; при отсутствии таймзоны используется UTC.

См. официальную документацию REST API: https://tradeapi.finam.ru/docs/guides/rest/.
"""

import datetime
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

import aiohttp

from finam_mcp.application.dtos import (
    Side,
    OrderType,
    TimeInForce,
    StopCondition,
    ValidBefore,
    LegDTO,
    ValueDTO,
    TimeFrame,
    AccountDTO,
    TradesRespDTO,
    TransactionsRespDTO,
    ClockDTO,
    ExchangesRespDTO,
    AssetDTO,
    AssetParamsDTO,
    OptionsChainDTO,
    SymbolScheduleDTO,
    OrderDTO,
    GetOrdersDTO,
    BarsRespDTO,
    LastQuoteDTO,
    LatestTradesDTO,
    OrderBookRespDTO, AssetListDTO, OkResponse, AssetType,
)
from finam_mcp.application.use_cases.get_assets import GetAssets
from finam_mcp.infrastructure.core.client import Client
from finam_mcp.configs.server import FinamConfig

# Глобальная конфигурация, инициализируется при загрузке модуля
_config: Optional[FinamConfig] = None


def init_config(config: FinamConfig) -> None:
    """Инициализация конфигурации для handlers."""
    global _config
    _config = config


def _get_config() -> FinamConfig:
    """Получить текущую конфигурацию."""
    if _config is None:
        raise RuntimeError(
            "Конфигурация Finam не инициализирована. "
            "Убедитесь, что переменные окружения FINAM_API_TOKEN и FINAM_ACCOUNT_ID установлены."
        )
    return _config


def _parse_dt(value: str) -> datetime.datetime:
    dt = datetime.datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt


def _parse_enum(enum_cls, value: Any):
    if isinstance(value, enum_cls):
        return value
    if isinstance(value, str):
        # Пробуем по имени (e.g. "SIDE_BUY")
        try:
            return enum_cls[value]
        except Exception:
            pass
    # Пробуем по значению
    return enum_cls(value)


def _parse_leg(leg: Dict[str, Any]) -> LegDTO:
    return LegDTO(
        symbol=str(leg["symbol"]),
        quantity=ValueDTO(value=str(leg.get("quantity", "0"))),
        side=_parse_enum(Side, leg.get("side", "SIDE_UNSPECIFIED")),
    )


@asynccontextmanager
async def _build_client():
    """Создать клиент используя конфигурацию из окружения."""
    cfg = _get_config()
    session = aiohttp.ClientSession(base_url="https://api.finam.ru/")
    try:
        yield Client(token=cfg.API_TOKEN, session=session)
    finally:
        await session.close()


async def get_account() -> AccountDTO:
    """Получить сведения о счете из конфигурации MCP.

    Токен и `account_id` берутся из окружения. Параметры не требуются.

    :returns: Баланс, позиции, кэш, маржинальные параметры и др.
    :rtype: AccountDTO
    """
    cfg = _get_config()
    async with _build_client() as client:
        resp = await client.get_account(cfg.ACCOUNT_ID)
        return resp


async def trades(start_time: str, end_time: str, limit: int) -> TradesRespDTO:
    """История сделок за указанный период.

    :param start_time: Начало периода в ISO8601, например "2024-01-01T00:00:00Z"
    :type start_time: str
    :param end_time: Конец периода в ISO8601
    :type end_time: str
    :param limit: Максимальное число записей (1..1000)
    :type limit: int
    :returns: Список сделок
    :rtype: TradesRespDTO

    Пример:
        trades("2024-01-01T00:00:00Z", "2024-01-31T23:59:59Z", limit=500)
    """
    cfg = _get_config()
    async with _build_client() as client:
        resp = await client.trades(cfg.ACCOUNT_ID, _parse_dt(start_time), _parse_dt(end_time), limit=limit)
        return resp


async def transactions(start_time: str, end_time: str, limit: int) -> TransactionsRespDTO:
    """Транзакции аккаунта за период (пополнения, выводы, комиссии и пр.).

    :param start_time: Начало периода в ISO8601
    :type start_time: str
    :param end_time: Конец периода в ISO8601
    :type end_time: str
    :param limit: Максимальное число записей
    :type limit: int
    :returns: Список транзакций
    :rtype: TransactionsRespDTO
    """
    cfg = _get_config()
    async with _build_client() as client:
        resp = await client.transactions(cfg.ACCOUNT_ID, _parse_dt(start_time), _parse_dt(end_time), limit=limit)
        return resp


#
# Reference data
#

async def get_assets(symbol: str | None = None, ticker: str | None = None, mic: str | None = None,  name: str | None = None, type: AssetType | None = None, limit: int = 50, offset: int = 0) -> OkResponse[AssetListDTO]:
    """Список инструментов с фильтрами и пагинацией.

    :param symbol: Фильтр по символу, например "AAPL@XNGS"
    :type symbol: str | None
    :param ticker: Фильтр по тикеру, например "AAPL"
    :type ticker: str | None
    :param mic: Фильтр по бирже, например "XNGS"
    :type mic: str | None
    :param name: Фильтр по названию, например "Apple"
    :type name: str | None
    :param type: Фильтра по типу инструмента, например "EQUITIES"
    :type name: str | None
    :param limit: Размер страницы (по умолчанию 50)
    :type limit: int
    :param offset: Смещение (по умолчанию 0)
    :type offset: int
    :returns: Обертка с коллекцией инструментов
    :rtype: OkResponse[AssetListDTO]

    Пример:
        get_assets(ticker="AAPL", limit=20)
    """
    async with _build_client() as client:
        details = await GetAssets(client)(symbol=symbol, ticker=ticker, mic=mic, name=name, type=type, limit=limit, offset=offset)
        return OkResponse(details=details, endpoint="https://api.finam.ru/v1/assets", method="GET")


async def clock() -> OkResponse[ClockDTO]:
    """Текущее серверное время Finam.

    :returns: Серверное время
    :rtype: OkResponse[ClockDTO]
    """
    async with _build_client() as client:
        details = await client.clock()
        return OkResponse(details=details, endpoint="https://api.finam.ru/v1/assets/clock", method="GET")


async def exchanges() -> OkResponse[ExchangesRespDTO]:
    """Перечень торговых площадок (MIC), доступных в API.

    :returns: Список площадок
    :rtype: OkResponse[ExchangesRespDTO]
    """
    async with _build_client() as client:
        details = await client.exchanges()
        return OkResponse(details=details, endpoint="https://api.finam.ru/v1/exchanges", method="GET")


async def get_asset(symbol: str) -> OkResponse[AssetDTO]:
    """Подробная информация по инструменту.

    :param symbol: Полный символ, например "AAPL@XNGS"
    :type symbol: str
    :returns: Информация об инструменте
    :rtype: OkResponse[AssetDTO]
    """
    cfg = _get_config()
    async with _build_client() as client:
        details = await client.get_asset(cfg.ACCOUNT_ID, symbol)
        return OkResponse(details=details, endpoint="https://api.finam.ru/v1/assets/{symbol}", method="GET")


async def get_asset_params(symbol: str) -> OkResponse[AssetParamsDTO]:
    """Торговые параметры инструмента (лот, шаг цены, доступность long/short и др.).

    :param symbol: Полный символ, например "AAPL@XNGS"
    :type symbol: str
    :returns: Параметры торговли по инструменту
    :rtype: OkResponse[AssetParamsDTO]
    """
    cfg = _get_config()
    async with _build_client() as client:
        details = await client.get_asset_params(cfg.ACCOUNT_ID, symbol)
        return OkResponse(details=details, endpoint="https://api.finam.ru/v1/assets/{symbol}/params", method="GET")


async def options_chain(underlying_symbol: str) -> OkResponse[OptionsChainDTO]:
    """Цепочка опционов по базовому активу.

    :param underlying_symbol: Символ базового актива, например "AAPL@XNGS"
    :type underlying_symbol: str
    :returns: Набор опционных контрактов
    :rtype: OkResponse[OptionsChainDTO]
    """
    async with _build_client() as client:
        details = await client.options_chain(underlying_symbol)
        return OkResponse(details=details, endpoint="https://api.finam.ru/v1/assets/{underlying_symbol}/options", method="GET")


async def schedule(symbol: str) -> OkResponse[SymbolScheduleDTO]:
    """Расписание торгов по инструменту (сессии и интервалы).

    :param symbol: Полный символ, например "AAPL@XNGS"
    :type symbol: str
    :returns: Список торговых сессий и интервалов
    :rtype: OkResponse[SymbolScheduleDTO]
    """
    async with _build_client() as client:
        details = await client.schedule(symbol)
        return OkResponse(details=details, endpoint="https://api.finam.ru/v1/assets/{symbol}/schedule", method="GET")


#
# Orders
#

async def cancel_order(order_id: str) -> OkResponse[OrderDTO]:
    """Отменить существующую заявку по ее идентификатору.

    :param order_id: Идентификатор заявки
    :type order_id: str
    :returns: Состояние заявки после отмены
    :rtype: OkResponse[OrderDTO]
    """
    cfg = _get_config()
    async with _build_client() as client:
        details = await client.cancel_order(cfg.ACCOUNT_ID, order_id)
        return OkResponse(details=details, endpoint="https://api.finam.ru/v1/accounts/{account_id}/orders/{order_id}", method="GET")


async def get_order(order_id: str) -> OkResponse[OrderDTO]:
    """Получить детальную информацию по заявке.

    :param order_id: Идентификатор заявки
    :type order_id: str
    :returns: Детали заявки
    :rtype: OkResponse[OrderDTO]
    """
    cfg = _get_config()
    async with _build_client() as client:
        details = await client.get_order(cfg.ACCOUNT_ID, order_id)
        return OkResponse(details=details, endpoint="https://api.finam.ru/v1/accounts/{account_id}/orders/{order_id}", method="GET")


async def get_orders() -> OkResponse[GetOrdersDTO]:
    """Список всех заявок аккаунта из конфигурации MCP.

    :returns: Список заявок
    :rtype: OkResponse[GetOrdersDTO]
    """
    cfg = _get_config()
    async with _build_client() as client:
        details = await client.get_orders(cfg.ACCOUNT_ID)
        return OkResponse(details=details, endpoint="https://api.finam.ru/v1/accounts/{account_id}/orders", method="GET")


async def place_order(
    symbol: str,
    quantity: str,
    side: str,
    type: str,
    time_in_force: str,
    limit_price: Optional[str] = None,
    stop_price: Optional[str] = None,
    stop_condition: Optional[str] = None,
    legs: Optional[Dict[str, Any]] = None,
    client_order_id: Optional[str] = None,
    valid_before: Optional[str] = None,
    comment: Optional[str] = None,
) -> OkResponse[OrderDTO]:
    """Выставить новую заявку на инструмент.

    :param symbol: Символ инструмента, например "AAPL@XNGS"
    :type symbol: str
    :param quantity: Количество (строкой для сохранения точности)
    :type quantity: str
    :param side: Сторона сделки. Допустимые имена enum `Side`: SIDE_BUY | SIDE_SELL | SIDE_UNSPECIFIED
    :type side: str
    :param type: Тип заявки. Допустимые значения enum `OrderType`: ORDER_TYPE_MARKET | ORDER_TYPE_LIMIT | ORDER_TYPE_STOP | ORDER_TYPE_STOP_LIMIT | ORDER_TYPE_MULTI_LEG | ORDER_TYPE_UNSPECIFIED
    :type type: str
    :param time_in_force: Время жизни заявки. Допустимые имена enum `TimeInForce`: TIME_IN_FORCE_DAY | TIME_IN_FORCE_GOOD_TILL_CANCEL | TIME_IN_FORCE_GOOD_TILL_CROSSING | TIME_IN_FORCE_EXT | TIME_IN_FORCE_ON_OPEN | TIME_IN_FORCE_ON_CLOSE | TIME_IN_FORCE_IOC | TIME_IN_FORCE_FOK | TIME_IN_FORCE_UNSPECIFIED
    :type time_in_force: str
    :param limit_price: Лимитная цена (для LIMIT/STOP_LIMIT)
    :type limit_price: str | None
    :param stop_price: Стоп-цена (для STOP/STOP_LIMIT)
    :type stop_price: str | None
    :param stop_condition: Условие стопа. Имени enum `StopCondition`: STOP_CONDITION_LAST_UP | STOP_CONDITION_LAST_DOWN | STOP_CONDITION_UNSPECIFIED
    :type stop_condition: str | None
    :param legs: Для `ORDER_TYPE_MULTI_LEG`: {"symbol": str, "quantity": str, "side": "SIDE_BUY|SIDE_SELL"}
    :type legs: dict | None
    :param client_order_id: ИД клиента (идемпотентность/сопоставление)
    :type client_order_id: str | None
    :param valid_before: Ограничение действия. Имени enum `ValidBefore`: VALID_BEFORE_END_OF_DAY | VALID_BEFORE_GOOD_TILL_CANCEL | VALID_BEFORE_GOOD_TILL_DATE | VALID_BEFORE_UNSPECIFIED
    :type valid_before: str | None
    :param comment: Комментарий к заявке
    :type comment: str | None
    :returns: Детали созданной заявки и текущий статус
    :rtype: OkResponse[OrderDTO]

    Особенности:
    - Строковые enum-параметры допускают имена enum или соответствующие значения.
    - Для LIMIT указывайте `limit_price`; для STOP — `stop_price`; для STOP_LIMIT — оба.

    Пример:
        place_order(symbol="AAPL@XNGS", quantity="1", side="SIDE_BUY", type="ORDER_TYPE_LIMIT", time_in_force="TIME_IN_FORCE_DAY", limit_price="190.00")
    """
    cfg = _get_config()
    async with _build_client() as client:
        leg_dto: Optional[LegDTO] = _parse_leg(legs) if legs else None
        details = await client.place_order(
            account_id=cfg.ACCOUNT_ID,
            symbol=symbol,
            quantity=quantity,
            side=_parse_enum(Side, side),
            type=_parse_enum(OrderType, type),
            time_in_force=_parse_enum(TimeInForce, time_in_force),
            limit_price=limit_price or "",
            stop_price=stop_price or "",
            stop_condition=_parse_enum(
                StopCondition, stop_condition) if stop_condition else StopCondition.STOP_CONDITION_UNSPECIFIED,
            legs=leg_dto,  # type: ignore[arg-type]
            client_order_id=client_order_id or "",
            valid_before=_parse_enum(
                ValidBefore, valid_before) if valid_before else ValidBefore.VALID_BEFORE_UNSPECIFIED,
            comment=comment or "",
        )
        return OkResponse(details=details, endpoint="https://api.finam.ru/v1/accounts/{account_id}/orders", method="POST")


#
# Market data
#

async def bars(
    symbol: str,
    start_time: str,
    end_time: str,
    timeframe: str,
) -> OkResponse[BarsRespDTO]:
    """Агрегированные свечи (bars) по инструменту за период.

    :param symbol: Символ инструмента, например "AAPL@XNGS"
    :type symbol: str
    :param start_time: Начало периода в ISO8601
    :type start_time: str
    :param end_time: Конец периода в ISO8601
    :type end_time: str
    :param timeframe: Имя enum `TimeFrame`: TIME_FRAME_M1 | TIME_FRAME_M5 | TIME_FRAME_M15 | TIME_FRAME_M30 | TIME_FRAME_H1 | TIME_FRAME_H2 | TIME_FRAME_H4 | TIME_FRAME_H8 | TIME_FRAME_D | TIME_FRAME_W | TIME_FRAME_MN | TIME_FRAME_QR | TIME_FRAME_UNSPECIFIED
    :type timeframe: str
    :returns: Свечи по инструменту
    :rtype: OkResponse[BarsRespDTO]

    Пример:
        bars("AAPL@XNGS", "2024-01-01T10:00:00Z", "2024-01-01T16:00:00Z", "TIME_FRAME_M5")
    """
    async with _build_client() as client:
        details = await client.bars(
            symbol=symbol,
            start_time=_parse_dt(start_time),
            end_time=_parse_dt(end_time),
            timeframe=_parse_enum(TimeFrame, timeframe),
        )
        return OkResponse(details=details, endpoint="https://api.finam.ru/v1/instruments/{symbol}/bars", method="GET")


async def last_quote(symbol: str) -> OkResponse[LastQuoteDTO]:
    """Последняя котировка по инструменту (bid/ask/last/volume и др.).

    :param symbol: Символ инструмента, например "AAPL@XNGS"
    :type symbol: str
    :returns: Последняя котировка и связанные показатели
    :rtype: OkResponse[LastQuoteDTO]
    """
    async with _build_client() as client:
        details = await client.last_quote(symbol)
        return OkResponse(details=details, endpoint="https://api.finam.ru/v1/instruments/{symbol}/quotes/latest", method="GET")


async def latest_trades(symbol: str) -> OkResponse[LatestTradesDTO]:
    """Список последних сделок по инструменту.

    :param symbol: Символ инструмента, например "AAPL@XNGS"
    :type symbol: str
    :returns: Последние сделки
    :rtype: OkResponse[LatestTradesDTO]
    """
    async with _build_client() as client:
        details = await client.latest_trades(symbol)
        return OkResponse(details=details, endpoint="https://api.finam.ru/v1/instruments/{symbol}/trades/latest", method="GET")


async def order_book(symbol: str) -> OkResponse[OrderBookRespDTO]:
    """Текущий стакан заявок (уровни bid/ask, размеры, метки времени).

    :param symbol: Символ инструмента, например "AAPL@XNGS"
    :type symbol: str
    :returns: Текущий стакан заявок
    :rtype: OkResponse[OrderBookRespDTO]

    Пример:
        order_book("AAPL@XNGS")
    """
    async with _build_client() as client:
        details = await client.order_book(symbol)
        return OkResponse(details=details, endpoint="https://api.finam.ru/v1/instruments/{symbol}/orderbook", method="GET")


def get_asset_types() -> OkResponse[list[str]]:
    """Справочник поддерживаемых типов инструментов (локальный список).

    Возвращает перечень строковых идентификаторов типов инструментов, совместимых
    с фильтром `type` в инструментах получения списка активов.

    :returns: Список строковых идентификаторов типов (например, "EQUITIES", "FUNDS")
    :rtype: OkResponse[list[str]]

    Пример:
        get_asset_types()
    """
    details = ["EQUITIES", "FUNDS", "FUTURES", "BONDS", "OTHER", "CURRENCIES", "SWAPS", "INDICES", "SPREADS"]
    return OkResponse(details=details)


def get_mic_list() -> OkResponse[list[str]]:
    """Справочник распространённых кодов MIC бирж (локальный список).

    Список может использоваться для построения символов формата "TICKER@MIC"
    и для фильтрации по бирже. Для полного перечня и актуальности
    ориентируйтесь на официальную документацию Finam REST.

    :returns: Список строковых кодов MIC (например, "XNGS", "MISX")
    :rtype: OkResponse[list[str]]

    Пример:
        get_mic_list()
    """
    details = ['_EURB', 'XNCM', 'RTSX', '_NPRO', 'XNMS', 'XLON', 'XNYM', 'XSHG', 'XPAR', 'XNGS', 'PINX', 'XAMS', 'XETR', 'XNYS', '_MMBZ', 'XSHE', 'MISX', 'XBRU', 'XCEC', 'BATS', 'XNAS', 'XCBT', '_CMF', '_SPBZ', '_TRES', 'XLOM', '_CRYP', 'ARCX', 'XASE', 'XMAD', '_SCI', 'XGAT', 'XTKS', 'XHKG', 'XCME']
    return OkResponse(details=details)
from mcp.server.fastmcp import FastMCP

from .client import (
    init_config,
    get_account,
    trades,
    transactions,
    get_assets,
    clock,
    exchanges,
    get_asset,
    get_asset_params,
    options_chain,
    schedule,
    cancel_order,
    get_order,
    get_orders,
    place_order,
    bars,
    last_quote,
    latest_trades,
    order_book, get_asset_types, get_mic_list,
)


def init_tools(app: FastMCP) -> None:
    """Инициализация инструментов MCP с конфигурацией Finam."""

    # Accounts & portfolio
    app.add_tool(get_account, name="get_account", title="Get configured account summary (balances, positions, cash)")
    app.add_tool(trades, name="trades", title="List account trades within ISO8601 time window")
    app.add_tool(transactions, name="transactions",
                 title="List account transactions (cash movements, fees) in time window")

    # Reference data
    app.add_tool(get_assets, name="assets", title="Search assets: symbol, ticker, mic, name, type, pagination")
    app.add_tool(clock, name="clock", title="Get server time (Clock)")
    app.add_tool(exchanges, name="exchanges", title="List exchanges (MIC codes)")
    app.add_tool(get_asset, name="get_asset", title="Get asset by symbol like TICKER@MIC")
    app.add_tool(get_asset_params, name="get_asset_params",
                 title="Get trading params (lot, price step, long/short availability)")
    app.add_tool(options_chain, name="options_chain",
                 title="Get options chain for underlying symbol")
    app.add_tool(schedule, name="schedule",
                 title="Get trading schedule for symbol")

    # Orders
    app.add_tool(cancel_order, name="cancel_order", title="Cancel order by id")
    app.add_tool(get_order, name="get_order", title="Get order by id")
    app.add_tool(get_orders, name="get_orders", title="List account orders")
    app.add_tool(place_order, name="place_order", title="Place order (market/limit/stop/stop_limit/multi_leg)")

    # Market data
    app.add_tool(bars, name="bars", title="Get historical bars for symbol and timeframe")
    app.add_tool(last_quote, name="last_quote", title="Get last quote for symbol")
    app.add_tool(latest_trades, name="latest_trades",
                 title="Get latest trades for symbol")
    app.add_tool(order_book, name="order_book", title="Get order book for symbol")
    app.add_tool(get_asset_types, name="get_asset_types", title="List supported asset types (local dictionary)")
    app.add_tool(get_mic_list, name="get_mic_list", title="List common MIC exchange codes (local dictionary)")

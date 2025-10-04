#!/usr/bin/env python3
"""Скрипт для проверки регистрации MCP tools."""

import asyncio
from finam_mcp import create_mcp_app


async def main():
    app = create_mcp_app()
    tools = await app.list_tools()
    
    print(f"✅ Зарегистрировано {len(tools)} tools:")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description}")
    
    return len(tools)


if __name__ == "__main__":
    count = asyncio.run(main())
    if count > 0:
        print(f"\n🎉 Все {count} tools успешно зарегистрированы!")
    else:
        print("\n❌ Ошибка: tools не зарегистрированы!")
        exit(1)


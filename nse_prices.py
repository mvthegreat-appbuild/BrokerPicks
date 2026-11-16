
import asyncio
import json
from pathlib import Path
from datetime import datetime, timezone

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

NSE_URL = "https://mcp.nseindia.in/cmmkt/mcp"

async def main():
    source = json.loads(Path("picks.json").read_text(encoding="utf-8"))

    symbols = sorted({
        str(symbol).strip().upper()
        for item in source.get("items", [])
        for symbol in item.get("stocks", [])
        if symbol
    })

    prices = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "source": "NSE CM Market MCP",
        "delay_note": "NSE data may be delayed; informational use only.",
        "stocks": {}
    }

    async with streamable_http_client(
        NSE_URL,
        terminate_on_close=False
    ) as (read, write):

        async with ClientSession(read, write) as session:
            await session.initialize()

            for symbol in symbols:
                try:
                    result = await session.call_tool(
                        "cm_get_stock_quote",
                        {"symbol": symbol}
                    )

                    if result.is_error:
                        raise RuntimeError("NSE quote request failed")

                    content = next(
                        (part.text for part in result.content if hasattr(part, "text")),
                        ""
                    )

                    data = json.loads(content)
                    stock = data.get("stock", {})

                    if not stock.get("lastTradedPrice"):
                        raise ValueError("CMP unavailable")

                    prices["stocks"][symbol] = {
                        "cmp": stock.get("lastTradedPrice"),
                        "change": stock.get("change"),
                        "change_percent": stock.get("perChange"),
                        "open": stock.get("open"),
                        "high": stock.get("high"),
                        "low": stock.get("low"),
                        "volume": stock.get("volume"),
                        "timestamp": stock.get("latestTimestamp"),
                        "status": "success"
                    }

                    print("SUCCESS:", symbol)

                except Exception as error:
                    prices["stocks"][symbol] = {
                        "status": "unavailable",
                        "error": str(error)
                    }
                    print("FAILED:", symbol, error)

    Path("nse_prices.json").write_text(
        json.dumps(prices, indent=2),
        encoding="utf-8"
    )

    print("Saved nse_prices.json")
    print("Stocks processed:", len(symbols))
    print("Quotes received:", sum(
        1 for x in prices["stocks"].values()
        if x["status"] == "success"
    ))

if __name__ == "__main__":
    asyncio.run(main())
